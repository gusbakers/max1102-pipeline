"""Package only explicitly allowed application files; never include .env."""
import json
import os
import subprocess
import zipfile
from pathlib import Path

def package(source, output, revision):
    import re
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Expected a full Git commit SHA')
    names = ['main.py', 'week4_observability.py', 'requirements.txt']
    if any(not (source / name).is_file() for name in names):
        raise ValueError('Application files are missing')
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in names:
            archive.write(source / name, name)
        archive.writestr('build-info.json', json.dumps({'commit': revision}))


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    revision = os.environ.get('GITHUB_SHA') or subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    package(root / 'api', root / 'release/api.zip', revision)
    print('Created release/api.zip with Python, requirements, and commit metadata only.')
