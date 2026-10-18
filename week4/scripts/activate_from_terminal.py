"""Activate Azure CD using existing az/gh sessions, with no credentials printed."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

REPO = 'gusbakers/max1102-pipeline'
ROOT = Path(__file__).resolve().parents[2]


def run(*command, as_json=False):
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True, timeout=180)
    return json.loads(result.stdout) if as_json else result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate-api', action='store_true', required=True,
                        help='Configure scoped identity, enable CD and request deployment of main')
    parser.parse_args()
    if any(not shutil.which(command) for command in ('gh', 'az')):
        raise SystemExit('Run in the Codespace with Azure CLI and GitHub CLI installed and authenticated.')
    run('gh', 'auth', 'status')
    run('az', 'account', 'show', '--output', 'json', as_json=True)
    head = run('gh', 'api', 'repos/' + REPO + '/commits/main', as_json=True)['sha']
    runs = run('gh', 'api', 'repos/' + REPO + '/actions/workflows/ci.yml/runs?branch=main&status=success&per_page=20', as_json=True)
    match = next((r for r in runs.get('workflow_runs', []) if r['head_sha'] == head
                  and r['event'] in ('push', 'workflow_dispatch')), None)
    if not match:
        raise SystemExit('The current main commit has no successful CI run. Wait for it before enabling CD.')
    private = ROOT / '.week4-private'
    private.mkdir(mode=0o700, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='oidc-', dir=private) as temporary:
        run('gh', 'run', 'download', str(match['id']), '--repo', REPO,
            '--name', 'oidc-subject-' + head, '--dir', temporary)
        record = json.loads((Path(temporary) / 'oidc-subject.json').read_text())
    if record.get('repository') != REPO or record.get('commit') != head:
        raise SystemExit('OIDC metadata does not belong to the expected repository/commit.')
    run(sys.executable, str(ROOT / 'week4/scripts/azure_oidc.py'), '--subject', record['subject'])
    run('gh', 'variable', 'set', 'ENABLE_CD', '--repo', REPO, '--body', 'true')
    run('gh', 'workflow', 'run', 'ci.yml', '--repo', REPO, '--ref', 'main', '-f', 'deploy=true')
    print('Azure federation configured; deployment requested. This is not yet proof of successful deployment.')
    print('Follow the new workflow: https://github.com/' + REPO + '/actions/workflows/ci.yml')
    print('The deploy-api job must pass health and exact-commit verification.')


if __name__ == '__main__':
    try:
        main()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        name = Path(exc.cmd[0]).name if isinstance(exc.cmd, (list, tuple)) else 'CLI'
        raise SystemExit(f'{name} operation failed. Check session/permissions in that terminal and rerun; no tokens were printed.') from None
