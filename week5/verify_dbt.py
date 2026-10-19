"""Execute real dbt models locally, check known answers, reruns, and failing quality gates."""
from collections import defaultdict
from datetime import date
from decimal import Decimal
import json
import os
from pathlib import Path
import subprocess
import sys

import duckdb

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'dbt'
DBT = str(Path(sys.executable).with_name('dbt'))


def run(*commands, success=True):
    if commands[0] == 'build':
        commands = (*commands, '--select', 'resource_type:model', 'resource_type:test')
    command = [DBT, *commands, '--project-dir', str(PROJECT), '--profiles-dir', str(PROJECT),
               '--target', 'local', '--vars', '{use_fixtures: true}', '--no-use-colors']
    result = subprocess.run(command, cwd=PROJECT, text=True, capture_output=True,
                            env=os.environ | {'DBT_SEND_ANONYMOUS_USAGE_STATS': 'false'})
    if (result.returncode == 0) != success:
        print(result.stdout[-12000:])
        print(result.stderr[-2000:])
        raise AssertionError('Unexpected dbt result: ' + ' '.join(commands))
    return result


def snapshot():
    with duckdb.connect(str(PROJECT / 'target/claims.duckdb')) as conn:
        claims = conn.execute('SELECT * FROM claims ORDER BY claim_id').fetchall()
        report = conn.execute('SELECT specialty, claim_count, total_amount, report_month FROM report_monthly ORDER BY specialty, report_month').fetchall()
        quality = conn.execute('SELECT * FROM quality_summary').fetchone()
    return claims, report, quality


def verify():
    (PROJECT / 'target').mkdir(exist_ok=True)
    # This harness is deliberately fixed to the local database, never a cloud target.
    os.environ['DBT_DUCKDB_PATH'] = str(PROJECT / 'target/claims.duckdb')
    run('seed', '--full-refresh')
    run('build')
    claims, report, quality = snapshot()
    expected_claims, totals = [], defaultdict(lambda: [0, Decimal('0')])
    for i in range(60):
        when = date(2025, 11 + i // 30, i % 28 + 1)
        amount = Decimal(100 + i)
        if i == 1:
            when, amount = date(2025, 12, 31), Decimal(999)
        status = 'DENIED' if i % 3 == 0 else 'PAID'
        month = when.strftime('%Y-%m')
        expected_claims.append((f'C{i:03}', f'M{i:03}', f'P{i % 2 + 1}', when, status, amount, month))
        if status == 'PAID':
            key = ('Cardiology' if i % 2 == 0 else 'Primary care', month)
            totals[key][0] += 1
            totals[key][1] += amount
    expected_report = [(specialty, values[0], values[1], month)
                       for (specialty, month), values in sorted(totals.items())]
    assert claims == expected_claims, 'Claim-level known answers differ'
    assert report == expected_report, 'Monthly report known answers differ'
    assert quality == (69, 1, 8, 60), quality
    run('build')
    assert snapshot() == (claims, report, quality), 'Rerun changed the result'
    # A conflicting provider must fail the build rather than multiply financial amounts.
    with duckdb.connect(os.environ['DBT_DUCKDB_PATH']) as conn:
        conn.execute("INSERT INTO fixture_providers VALUES ('P1', 'Conflict', 'Other')")
    run('build', success=False)
    assert snapshot()[:2] == (claims, report), 'Provider failure changed published claims/report'
    run('seed', '--full-refresh')
    # Bad data beyond the inherited rejection budget must fail before downstream publication.
    with duckdb.connect(os.environ['DBT_DUCKDB_PATH']) as conn:
        conn.execute("UPDATE fixture_claims SET claim_amount='-1' WHERE claim_id < 'C020'")
    run('build', success=False)
    assert snapshot()[:2] == (claims, report), 'Quality failure changed published claims/report'
    run('seed', '--full-refresh')
    run('build')
    assert snapshot() == (claims, report, quality)
    run('docs', 'generate')
    summary = {'engine': 'DuckDB', 'cloud_execution': False, 'raw': 69, 'exact_duplicates': 1,
               'rejected': 8, 'valid': 60, 'report_rows': len(report),
               'checks': ['known_claims', 'known_report', 'reconciliation', 'idempotence',
                          'conflicting_provider_blocked', 'excessive_loss_blocked']}
    (PROJECT / 'target/week5-verification.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    verify()
