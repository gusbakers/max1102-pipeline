"""Package only explicitly allowed application files; never include .env."""
import json
import os
import subprocess
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[2]
source = root / 'api'
revision = os.environ.get('GITHUB_SHA') or subprocess.check_output(
    ['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
files = [source / name for name in ['main.py', 'week4_observability.py']
         if (source / name).is_file()]
files.append(source / 'requirements.txt')
if not (source / 'main.py').is_file():
    raise SystemExit('Missing api/main.py')
(root / 'release').mkdir(exist_ok=True)
with zipfile.ZipFile(root / 'release/api.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for p in sorted(files):
        z.write(p, str(p.relative_to(source)))
    z.writestr('build-info.json', json.dumps({'commit': revision}))
print('Created release/api.zip with Python, requirements, and commit metadata only.')
