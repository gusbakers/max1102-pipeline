import copy
from decimal import Decimal
import json
from pathlib import Path
import sys
import zipfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_import_plan import validate_plan
from cost_report import summarize
from generate_infra import render
from monitor import evaluate_runs
from notebook_manifest import HELPERS, REQUIRED, snapshot, verify
from package_api import package
import smoke


@pytest.mark.parametrize('actions', [['create'], ['update'], ['delete'], ['delete', 'create'], []])
def test_import_gate_blocks_all_cloud_mutations(actions):
    plan = {'format_version': '1.2', 'planned_values': {}, 'resource_changes': [
        {'mode': 'managed', 'address': 'aws_s3_bucket.lake', 'change': {'actions': actions}}]}
    with pytest.raises(ValueError, match='mutation'):
        validate_plan(plan)


def test_import_gate_accepts_import_only_and_requires_evidence():
    plan = {'format_version': '1.2', 'planned_values': {}, 'complete': True, 'resource_changes': [
        {'mode': 'managed', 'change': {'actions': ['no-op'], 'importing': {'id': 'existing'}}}]}
    assert validate_plan(plan, require_import=True) == 1
    for changes in [{'complete': False}, {'errored': True}, {'deferred_changes': [{}]}, {'resource_changes': []}]:
        with pytest.raises(ValueError):
            validate_plan(plan | changes, require_import=True)
    with pytest.raises(ValueError):
        validate_plan({})


def test_inventory_rejects_placeholders_duplicates_and_wrong_provider():
    inventory = {'organization': 'max-test', 'aws': [{'address': 'aws_s3_bucket.lake', 'id': 'existing-bucket'}]}
    assert 'aws_s3_bucket.lake' in render(inventory)['aws']['imports.tf']
    for entry in [{'address': 'aws_s3_bucket.lake', 'id': 'NOMBRE_REAL_BUCKET'},
                  {'address': 'azurerm_resource_group.api', 'id': 'x'}]:
        with pytest.raises(ValueError):
            render(inventory | {'aws': [entry]})
    with pytest.raises(ValueError):
        render(inventory | {'aws': inventory['aws'] * 2})
    with pytest.raises(ValueError):
        render({'organization': 'max-test'})


def test_package_allows_only_runtime_files(tmp_path):
    for name in ['main.py', 'requirements.txt', 'week4_observability.py', '.env', 'test_api.py', 'requirements-dev.txt']:
        (tmp_path / name).write_text('synthetic-test')
    target = tmp_path / 'release/api.zip'
    package(tmp_path, target, 'a' * 40)
    with zipfile.ZipFile(target) as archive:
        assert set(archive.namelist()) == {'main.py', 'week4_observability.py', 'requirements.txt', 'build-info.json'}
        assert json.loads(archive.read('build-info.json'))['commit'] == 'a' * 40


def test_notebook_review_rejects_incomplete_or_changed_sources(tmp_path):
    source = tmp_path / 'databricks/notebooks'
    source.mkdir(parents=True)
    (tmp_path / 'week4').mkdir()
    for name in REQUIRED:
        (source / name).write_text('# synthetic fixture\n')
    with pytest.raises(ValueError, match='incomplete'):
        snapshot(tmp_path)
    (source / '00_common.py').write_text('\n'.join(f'def {name}(): pass' for name in HELPERS))
    record = {'schema_version': 1, 'successful_run_url': 'https://test.databricks.com/jobs/1/runs/2', 'files': snapshot(tmp_path)}
    (tmp_path / 'week4/databricks-reviewed.json').write_text(json.dumps(record))
    verify(tmp_path)
    (source / '01_extract.py').write_text('# changed after review\n')
    with pytest.raises(ValueError, match='changed'):
        verify(tmp_path)


@pytest.mark.parametrize('url', ['http://example.com', 'https://user:pass@example.com', 'https://example.com/health', 'https://example.com?token=x'])
def test_smoke_rejects_bad_origins(url):
    with pytest.raises(ValueError):
        smoke.base_url(url)


def test_smoke_retries_and_rejects_old_commit(monkeypatch):
    calls = []
    def get(url):
        calls.append(url)
        if len(calls) == 1:
            raise TimeoutError()
        return {'status': 'ok'} if url.endswith('/health') else {'commit': 'old'}
    monkeypatch.setattr(smoke, 'get_json', get)
    monkeypatch.setattr(smoke.time, 'sleep', lambda _: None)
    with pytest.raises(RuntimeError):
        smoke.probe('https://example.com', commit='new', attempts=2, delay=0)
    assert len(calls) == 3


def test_latest_failed_job_is_not_hidden_by_previous_success():
    success = {'start_time': 100, 'end_time': 200, 'state': {'result_state': 'SUCCESS'}}
    failed = {'start_time': 300, 'state': {'result_state': 'FAILED'}}
    assert evaluate_runs([success], 50)['status'] == 'ok'
    assert evaluate_runs([success], 250)['reason'] == 'last_success_too_old'
    assert evaluate_runs([success, failed], 50)['reason'] == 'latest_run_unsuccessful'
    assert evaluate_runs([], 50)['status'] == 'failed'


def test_costs_are_exact_separated_by_unit_and_missing_is_not_zero():
    rows = [{'provider': 'azure', 'service': 'app', 'period': '2026-10', 'unit': 'USD', 'amount': '0.10'},
            {'provider': 'azure', 'service': 'app', 'period': '2026-10', 'unit': 'USD', 'amount': '0.20'},
            {'provider': 'snowflake', 'service': 'wh', 'period': '2026-10', 'unit': 'CREDITS', 'amount': '2'}]
    totals, missing = summarize(rows)
    assert totals[('azure', '2026-10', 'USD')] == Decimal('0.30')
    assert totals[('snowflake', '2026-10', 'CREDITS')] == 2
    assert 'aws' in missing
    with pytest.raises(ValueError, match='No billing data'):
        summarize([])
    with pytest.raises(ValueError, match='finite'):
        summarize([rows[0] | {'amount': 'NaN'}])
