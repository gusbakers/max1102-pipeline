#!/usr/bin/env bash
set -euo pipefail
# Run once, after az login. Only this app receives deployment access.
mkdir -p .week4-private
chmod 700 .week4-private
if [ -e .week4-private/azure-identity.json ]; then
  echo 'Identity already recorded. Reuse it; see guide before creating another.'
  exit 1
fi
APP_SCOPE=$(az webapp show -g rg-max-week2-api -n maxweek2-gusbakers-972358cb --query id -o tsv)
CLIENT_ID=$(az ad app create --display-name max-week4-github --query appId -o tsv)
APP_OBJECT=$(az ad app show --id "$CLIENT_ID" --query id -o tsv)
SP_OBJECT=$(az ad sp create --id "$CLIENT_ID" --query id -o tsv)
export CLIENT_ID APP_OBJECT SP_OBJECT APP_SCOPE
python3 - <<'PY'
import json, os
from pathlib import Path
Path('.week4-private/azure-identity.json').write_text(json.dumps({k:os.environ[k] for k in ['CLIENT_ID','APP_OBJECT','SP_OBJECT','APP_SCOPE']}, indent=2))
Path('.week4-private/federation.json').write_text(json.dumps({
 'name':'github-main', 'issuer':'https://token.actions.githubusercontent.com',
 'subject':'repo:gusbakers/max1102-pipeline:ref:refs/heads/main',
 'audiences':['api://AzureADTokenExchange']
}))
PY
az ad app federated-credential create --id "$CLIENT_ID" \
  --parameters @.week4-private/federation.json --output none
az role assignment create --assignee-object-id "$SP_OBJECT" \
  --assignee-principal-type ServicePrincipal --role 'Website Contributor' \
  --scope "$APP_SCOPE" --output none
gh variable set AZURE_CLIENT_ID --body "$CLIENT_ID"
gh variable set AZURE_TENANT_ID --body "$(az account show --query tenantId -o tsv)"
gh variable set AZURE_SUBSCRIPTION_ID --body "$(az account show --query id -o tsv)"
echo 'OIDC configured. ENABLE_CD is still disabled until you enable it.'
