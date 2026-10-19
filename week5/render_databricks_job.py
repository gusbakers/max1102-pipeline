"""Render a new manual Databricks job pinned to an exact source commit."""
import argparse
import json
import re


def job_settings(warehouse_id, revision, raw_format='csv'):
    if not re.fullmatch(r'[0-9a-f]{16}', warehouse_id):
        raise ValueError('Use the actual 16-character SQL warehouse ID')
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Use a full Git commit SHA')
    if raw_format not in {'csv', 'parquet'}:
        raise ValueError('Unsupported raw format')
    return {
        'name':'max_week5_claims_dbt', 'max_concurrent_runs':1, 'timeout_seconds':1800,
        'git_source':{'git_url':'https://github.com/gusbakers/max1102-pipeline.git',
                      'git_provider':'gitHub', 'git_commit':revision},
        'environments':[
            {'environment_key':'notebook', 'spec':{'environment_version':'4'}},
            {'environment_key':'dbt', 'spec':{'environment_version':'4',
                'dependencies':['dbt-core==1.11.16','dbt-databricks==1.11.8']}}],
        'tasks':[
            {'task_key':'land_raw', 'environment_key':'notebook', 'max_retries':0,
             'notebook_task':{'notebook_path':'databricks/week5/01_land_raw.py', 'source':'GIT',
                              'base_parameters':{'raw_format':raw_format}}},
            {'task_key':'dbt_build', 'environment_key':'dbt', 'max_retries':0,
             'depends_on':[{'task_key':'land_raw'}],
             'dbt_task':{'project_directory':'dbt', 'source':'GIT', 'warehouse_id':warehouse_id,
                         'catalog':'workspace', 'schema':'max1102_week5',
                         'commands':['dbt build --vars "{use_fixtures: false}"']}}]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--warehouse-id', required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--raw-format', choices=['csv','parquet'], default='csv')
    args = parser.parse_args()
    try:
        print(json.dumps(job_settings(args.warehouse_id, args.commit, args.raw_format), indent=2))
    except ValueError as exc:
        parser.error(str(exc))
