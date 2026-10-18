"""Bounded, credential-free checks of the public API. Importable for tests."""
import argparse
import json
import time
import urllib.request
from urllib.parse import urlsplit


def base_url(value):
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/')):
        raise ValueError('Use an HTTPS origin without credentials, path, query or fragment.')
    return value.rstrip('/')


def get_json(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'max1102-monitor/1.0'})
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status != 200:
            raise ValueError('Unexpected HTTP status')
        return json.load(response)


def check_once(url, commit=None):
    base = base_url(url)
    started = time.monotonic()
    if get_json(base + '/health').get('status') != 'ok':
        raise ValueError('Unexpected health response')
    if commit and get_json(base + '/version').get('commit') != commit:
        raise ValueError('Deployed commit does not match the tested artifact')
    return {'status': 'ok', 'health_ms': round((time.monotonic() - started) * 1000)}


def probe(url, commit=None, attempts=3, delay=10):
    base_url(url)
    if not 1 <= attempts <= 30 or not 0 <= delay <= 60:
        raise ValueError('Invalid retry limits')
    for attempt in range(1, attempts + 1):
        try:
            return {**check_once(url, commit), 'attempt': attempt}
        except Exception as exc:
            # Provider responses and URLs may contain sensitive data. Log only the class.
            print(json.dumps({'attempt': attempt, 'error': type(exc).__name__}))
            if attempt == attempts:
                raise RuntimeError('Health/version check failed') from None
            time.sleep(delay)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--commit')
    parser.add_argument('--attempts', type=int, default=12)
    parser.add_argument('--delay', type=float, default=10)
    args = parser.parse_args()
    try:
        print(json.dumps(probe(args.url, args.commit, args.attempts, args.delay)))
    except (ValueError, RuntimeError) as exc:
        raise SystemExit(str(exc)) from None


if __name__ == '__main__':
    main()
