"""Reject any managed-resource create, update, delete or replacement."""
import json
import sys

plan = json.load(open(sys.argv[1]))
if plan.get('errored') or plan.get('deferred_changes'):
    raise SystemExit('Incomplete or deferred plan: do not apply.')
changes = []
for resource in plan.get('resource_changes', []):
    actions = resource.get('change', {}).get('actions', [])
    if resource.get('mode') == 'managed' and actions != ['no-op']:
        changes.append((resource['address'], actions))
if changes:
    for address, actions in changes:
        print(address, actions)
    raise SystemExit('BLOCKED: importing must not alter cloud resources. Fix the configuration and re-plan.')
print('OK: import/state updates only; no cloud resource mutations planned.')
