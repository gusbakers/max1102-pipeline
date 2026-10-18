"""Configure resumable, app-scoped Azure federation from an authenticated Codespace."""
import argparse
import json
from pathlib import Path
import re
import subprocess

REPO = 'gusbakers/max1102-pipeline'
STATE = Path('.week4-private/azure-identity.json')


def run(*args, json_output=False):
    result = subprocess.run(args, check=True, text=True, capture_output=True)
    return json.loads(result.stdout) if json_output else result.stdout.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--subject', required=True, help='Exact subject from the CI oidc-subject job; never paste a JWT')
    args = parser.parse_args()
    allowed = (r'repo:gusbakers(?:@82125756)?/max1102-pipeline(?:@1406118185)?:ref:refs/heads/main')
    if not re.fullmatch(allowed, args.subject):
        raise SystemExit('Subject must belong to this repository and main. Use the observed subject from CI.')
    account = run('az', 'account', 'show', '-o', 'json', json_output=True)
    app = run('az', 'webapp', 'show', '-g', 'rg-max-week2-api', '-n', 'maxweek2-gusbakers-972358cb', '-o', 'json', json_output=True)
    STATE.parent.mkdir(mode=0o700, exist_ok=True)
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    if state and state.get('scope') != app['id']:
        raise SystemExit('Recorded identity targets another application')

    def save():
        STATE.write_text(json.dumps(state, indent=2) + '\n')
        STATE.chmod(0o600)

    if 'client_id' not in state:
        existing = run('az', 'ad', 'app', 'list', '--display-name', 'max-week4-github', '-o', 'json', json_output=True)
        if len(existing) > 1:
            raise SystemExit('Several matching identities exist; select the correct one before continuing')
        identity = existing[0] if existing else run('az', 'ad', 'app', 'create', '--display-name', 'max-week4-github', '-o', 'json', json_output=True)
        state.update(client_id=identity['appId'], object_id=identity['id'], scope=app['id'])
        save()
    if 'service_principal_id' not in state:
        existing = run('az', 'ad', 'sp', 'list', '--filter', "appId eq '" + state['client_id'] + "'", '-o', 'json', json_output=True)
        principal = existing[0] if existing else run('az', 'ad', 'sp', 'create', '--id', state['client_id'], '-o', 'json', json_output=True)
        state['service_principal_id'] = principal['id']
        save()
    federation = {'name': 'github-main', 'issuer': 'https://token.actions.githubusercontent.com',
                  'subject': args.subject, 'audiences': ['api://AzureADTokenExchange']}
    existing = run('az', 'ad', 'app', 'federated-credential', 'list', '--id', state['object_id'], '-o', 'json', json_output=True)
    same = next((item for item in existing if item.get('name') == 'github-main'), None)
    if same and any(same.get(key) != value for key, value in federation.items()):
        raise SystemExit('Existing federation differs. Review it before changing trust.')
    if not same:
        file = STATE.parent / 'federation.json'
        file.write_text(json.dumps(federation))
        run('az', 'ad', 'app', 'federated-credential', 'create', '--id', state['object_id'], '--parameters', '@' + str(file), '-o', 'none')
    roles = run('az', 'role', 'assignment', 'list', '--assignee', state['service_principal_id'], '--scope', app['id'], '-o', 'json', json_output=True)
    if not any(r['roleDefinitionName'] == 'Website Contributor' and r['scope'].lower() == app['id'].lower() for r in roles):
        run('az', 'role', 'assignment', 'create', '--assignee-object-id', state['service_principal_id'],
            '--assignee-principal-type', 'ServicePrincipal', '--role', 'Website Contributor', '--scope', app['id'], '-o', 'none')
    for name, value in {'AZURE_CLIENT_ID': state['client_id'], 'AZURE_TENANT_ID': account['tenantId'],
                        'AZURE_SUBSCRIPTION_ID': account['id']}.items():
        run('gh', 'variable', 'set', name, '--repo', REPO, '--body', value)
    print('OIDC configured for the existing Web App. ENABLE_CD remains unchanged.')


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError:
        raise SystemExit('A cloud/CLI operation failed. State was saved; fix permissions/authentication and rerun.') from None
