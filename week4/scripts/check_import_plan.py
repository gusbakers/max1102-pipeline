"""Fail closed unless a complete Terraform plan contains only state imports/no-ops."""
import argparse
import json
from pathlib import Path


def validate_plan(plan, require_import=False):
    if not isinstance(plan, dict) or not plan.get('format_version') or 'planned_values' not in plan:
        raise ValueError('Not a Terraform JSON plan')
    if plan.get('errored') or plan.get('deferred_changes') or plan.get('complete') is False:
        raise ValueError('Incomplete, errored or deferred plan')
    if not isinstance(plan.get('resource_changes', []), list):
        raise ValueError('Invalid resource_changes')
    imports = 0
    for resource in plan.get('resource_changes', []):
        if resource.get('mode') not in {'managed', 'data'}:
            raise ValueError('Unknown resource mode')
        change = resource.get('change', {})
        actions = change.get('actions', [])
        if resource['mode'] == 'managed' and actions != ['no-op']:
            raise ValueError('Cloud mutation blocked: ' + resource.get('address', 'unknown'))
        if resource['mode'] == 'data' and actions not in (['read'], ['no-op']):
            raise ValueError('Unexpected data source change')
        imports += int(bool(change.get('importing')))
    if require_import and imports == 0:
        raise ValueError('No imports found; confirm that this is the adoption plan')
    return imports


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('plan', type=Path)
    parser.add_argument('--require-import', action='store_true')
    args = parser.parse_args()
    try:
        imports = validate_plan(json.loads(args.plan.read_text()), args.require_import)
    except (ValueError, KeyError, TypeError) as exc:
        raise SystemExit('BLOCKED: ' + str(exc)) from None
    print(f'OK: {imports} import(s); no managed resource create/update/delete.')


if __name__ == '__main__':
    main()
