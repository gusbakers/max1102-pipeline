"""Public availability check; optional checks of monthly Databricks job freshness."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import urllib.request
from urllib.parse import urlencode, urlsplit

from smoke import probe


def evaluate_runs(runs, oldest_ms):
    """The latest failed run is an incident even when an older run succeeded."""
    if not runs:
        return {'status': 'failed', 'reason': 'no_runs'}
    runs = sorted(runs, key=lambda item: item.get('start_time', 0), reverse=True)
    state = runs[0].get('state', {})
    if state.get('result_state') in {'FAILED', 'TIMEDOUT', 'CANCELED'} or state.get('life_cycle_state') in {'INTERNAL_ERROR', 'SKIPPED'}:
        return {'status': 'failed', 'reason': 'latest_run_unsuccessful'}
    successes = [r for r in runs if r.get('state', {}).get('result_state') == 'SUCCESS']
    if not successes or max(r.get('end_time', 0) for r in successes) < oldest_ms:
        return {'status': 'failed', 'reason': 'last_success_too_old'}
    return {'status': 'ok', 'reason': 'recent_success', 'latest_state': state.get('life_cycle_state', 'unknown')}


def check_jobs():
    host = os.environ.get('DATABRICKS_HOST', '').rstrip('/')
    ids = [x.strip() for x in os.environ.get('DATABRICKS_JOB_IDS', '').split(',')]
    token = os.environ.get('DATABRICKS_TOKEN', '')
    parsed = urlsplit(host)
    if (parsed.scheme != 'https' or not parsed.hostname or not parsed.hostname.endswith('.databricks.com')
            or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment or not token
            or len(ids) != 4 or len(set(ids)) != 4 or any(not x.isdigit() for x in ids)):
        raise ValueError('Incomplete monitoring configuration')
    days = int(os.environ.get('PIPELINE_MAX_AGE_DAYS', '35'))
    if not 1 <= days <= 366:
        raise ValueError('Invalid freshness window')
    oldest = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
    from deploy_notebooks import NoRedirect
    opener = urllib.request.build_opener(NoRedirect())
    checks = []
    for job_id in ids:
        query = urlencode({'job_id': job_id, 'limit': 100, 'start_time_from': oldest})
        request = urllib.request.Request(host + '/api/2.1/jobs/runs/list?' + query,
                                        headers={'Authorization': 'Bearer ' + token})
        with opener.open(request, timeout=30) as response:
            data = json.load(response)
        checks.append({'job_id': job_id, **evaluate_runs(data.get('runs', []), oldest)})
    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', type=Path, default=Path('monitor-result.json'))
    parser.add_argument('--simulate-failure', action='store_true')
    parser.add_argument('--jobs', action='store_true')
    parser.add_argument('--drill', action='store_true')
    args = parser.parse_args()
    result = {'checked_at': datetime.now(timezone.utc).isoformat(), 'drill': args.drill or args.simulate_failure,
              'scope': 'HTTP availability; optional job success age, not data quality or a 24/7 SLA', 'checks': []}
    try:
        result['checks'].append({'component': 'api', **probe(args.url, attempts=3, delay=10)})
    except Exception as exc:
        result['checks'].append({'component': 'api', 'status': 'failed', 'reason': type(exc).__name__})
    if args.jobs:
        try:
            result['checks'].extend({'component': 'databricks', **item} for item in check_jobs())
        except Exception as exc:
            result['checks'].append({'component': 'databricks', 'status': 'failed', 'reason': type(exc).__name__})
    if args.simulate_failure:
        result['checks'].append({'component': 'alert_drill', 'status': 'failed', 'reason': 'intentional'})
    result['status'] = 'failed' if any(c['status'] != 'ok' for c in result['checks']) else 'ok'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    raise SystemExit(0 if result['status'] == 'ok' else 1)


if __name__ == '__main__':
    main()
