"""Require a reviewed snapshot before overwriting working Databricks notebooks."""
import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = ('00_common.py', '01_extract.py', '02_validate.py', '03_transform.py', '04_load.py')
HELPERS = {'settings', 'require_columns', 'read_stage', 'save_stage', 'table'}


def snapshot(root=ROOT):
    source = root / 'databricks/notebooks'
    files = {p.name: p for p in sorted(source.glob('*.py'))}
    missing = set(REQUIRED) - files.keys()
    if missing:
        raise ValueError('Missing notebooks: ' + ', '.join(sorted(missing)))
    trees = {name: ast.parse(path.read_text()) for name, path in files.items()}
    defined = {n.name for n in trees['00_common.py'].body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if HELPERS - defined:
        raise ValueError('00_common.py is incomplete: ' + ', '.join(sorted(HELPERS - defined)))
    return {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()}


def verify(root=ROOT):
    manifest = root / 'week4/databricks-reviewed.json'
    if not manifest.is_file():
        raise ValueError('Export and verify the working Databricks sources, then record their manifest.')
    record = json.loads(manifest.read_text())
    if record.get('files') != snapshot(root) or not record.get('successful_run_url'):
        raise ValueError('Notebook sources changed or successful run evidence is missing. Review again.')
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--record-run', help='URL of a successful run of these exact exported sources')
    args = parser.parse_args()
    try:
        if args.record_run:
            from urllib.parse import urlsplit
            url = urlsplit(args.record_run)
            if url.scheme != 'https' or not url.hostname or not url.hostname.endswith('.databricks.com') or url.username or url.password or url.query:
                raise ValueError('Use a Databricks run URL without credentials or query parameters.')
            record = {'schema_version': 1, 'successful_run_url': args.record_run, 'files': snapshot()}
            (ROOT / 'week4/databricks-reviewed.json').write_text(json.dumps(record, indent=2) + '\n')
            print('Manifest recorded. It is a review record, not an independent verification of the run.')
        else:
            verify()
            print('Reviewed notebook hashes match.')
    except (ValueError, SyntaxError) as exc:
        raise SystemExit(str(exc)) from None


if __name__ == '__main__':
    main()
