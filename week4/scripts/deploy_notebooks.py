"""Import the reviewed notebook set only after checking all target jobs are idle."""
import base64
import json
import os
from pathlib import Path
import re
import urllib.request
from urllib.parse import urlencode, urlsplit

from notebook_manifest import ROOT, verify


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Refusing to forward Databricks credentials across a redirect')


def main():
    verify()
    host = os.environ.get('DATABRICKS_HOST', '').rstrip('/')
    target = os.environ.get('DATABRICKS_NOTEBOOK_DIR', '').rstrip('/')
    token = os.environ.get('DATABRICKS_TOKEN', '')
    parsed = urlsplit(host)
    if (parsed.scheme != 'https' or not parsed.hostname or not parsed.hostname.endswith('.databricks.com')
            or parsed.username or parsed.password or parsed.query or parsed.path or parsed.fragment):
        raise SystemExit('Invalid Databricks workspace origin')
    if not re.fullmatch(r'/(?:Workspace/)?(?:Users|Shared)/[A-Za-z0-9_@. /+-]+', target) or '..' in target.split('/'):
        raise SystemExit('Invalid notebook directory')
    ids = [x.strip() for x in os.environ.get('DATABRICKS_JOB_IDS', '').split(',')]
    if not token or len(ids) != 4 or len(set(ids)) != 4 or any(not x.isdigit() for x in ids):
        raise SystemExit('DATABRICKS_TOKEN and four comma-separated DATABRICKS_JOB_IDS are required')
    opener = urllib.request.build_opener(NoRedirect())

    def call(route, payload=None):
        request = urllib.request.Request(host + '/api/2.1/' + route if route.startswith('jobs/') else host + '/api/2.0/' + route,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
        with opener.open(request, timeout=60) as response:
            return json.load(response)

    for job_id, notebook in zip(ids, ['01_extract', '02_validate', '03_transform', '04_load']):
        settings = call('jobs/get?' + urlencode({'job_id': job_id})).get('settings', {})
        paths = [t.get('notebook_task', {}).get('notebook_path') for t in settings.get('tasks', [])]
        if not paths and 'notebook_task' in settings:
            paths = [settings['notebook_task'].get('notebook_path')]
        expected = (target + '/' + notebook).removeprefix('/Workspace')
        if len(paths) != 1 or not paths[0] or paths[0].removeprefix('/Workspace') != expected:
            raise SystemExit('A target job does not reference the expected notebook. Deployment stopped.')
        result = call('jobs/runs/list?' + urlencode({'job_id': job_id.strip(), 'active_only': 'true', 'limit': 1}))
        if result.get('runs'):
            raise SystemExit('An operational job is active; retry deployment when the pipeline is idle')
    call('workspace/mkdirs', {'path': target})
    for p in sorted((ROOT / 'databricks/notebooks').glob('*.py')):
        call('workspace/import', {'path': target + '/' + p.stem, 'format': 'SOURCE', 'language': 'PYTHON',
                                  'content': base64.b64encode(p.read_bytes()).decode(), 'overwrite': True})
        print('Imported:', p.name)
    print('Notebook set imported. This operation is not atomic; see the recovery runbook.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        raise SystemExit('Notebook deployment stopped: ' + type(exc).__name__ + '. Check configuration and runbook.') from None
