import base64
import json
import os
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

root = Path(__file__).resolve().parents[2]
host = os.environ['DATABRICKS_HOST'].rstrip('/')
target = os.environ['DATABRICKS_NOTEBOOK_DIR'].rstrip('/')
token = os.environ['DATABRICKS_TOKEN']
if urlsplit(host).scheme != 'https' or not target.startswith(('/Users/', '/Workspace/Users/', '/Shared/', '/Workspace/Shared/')):
    raise SystemExit('Verify DATABRICKS_HOST and DATABRICKS_NOTEBOOK_DIR.')
if not (root / 'week4/databricks-reviewed.txt').exists():
    raise SystemExit('Export the working notebooks, review them, then create week4/databricks-reviewed.txt.')
source = root / 'databricks/notebooks'
files = sorted(source.glob('*.py'))
if not files:
    raise SystemExit('No Python notebooks found.')
for expected in ['00_common.py','01_extract.py','02_validate.py','03_transform.py','04_load.py']:
    if not (source / expected).is_file():
        raise SystemExit('Missing operational notebook: ' + expected)

def post(route, payload):
    request = urllib.request.Request(host + '/api/2.0/' + route,
        data=json.dumps(payload).encode(),
        headers={'Authorization':'Bearer ' + token, 'Content-Type':'application/json'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()

post('workspace/mkdirs', {'path': target})
for p in files:
    post('workspace/import', {
        'path': target + '/' + p.stem, 'format':'SOURCE', 'language':'PYTHON',
        'content': base64.b64encode(p.read_bytes()).decode(), 'overwrite':True,
    })
    print('Imported:', p.name)
print('Notebooks updated. Jobs were not executed or changed.')
