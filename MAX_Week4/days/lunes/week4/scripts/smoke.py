import argparse
import json
import time
import urllib.request
from urllib.parse import urlsplit

p = argparse.ArgumentParser()
p.add_argument('--url', required=True)
p.add_argument('--commit')
p.add_argument('--attempts', type=int, default=12)
p.add_argument('--delay', type=float, default=10)
args = p.parse_args()
parsed = urlsplit(args.url)
if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password:
    raise SystemExit('A public HTTPS URL without credentials is required.')
base = args.url.rstrip('/')
for attempt in range(args.attempts):
    try:
        started = time.perf_counter()
        with urllib.request.urlopen(base + '/health', timeout=30) as r:
            assert r.status == 200 and json.load(r).get('status') == 'ok'
        elapsed = round((time.perf_counter() - started) * 1000)
        if args.commit:
            with urllib.request.urlopen(base + '/version', timeout=30) as r:
                assert json.load(r)['commit'] == args.commit, 'Old deployment still active'
        print(json.dumps({'status':'ok', 'health_ms':elapsed, 'attempt':attempt + 1}))
        break
    except Exception as exc:
        print(f'Attempt {attempt + 1}: {type(exc).__name__}')
        if attempt + 1 == args.attempts:
            raise SystemExit('Health/version check failed; inspect deployment and logs.')
        time.sleep(args.delay)
