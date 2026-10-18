"""Create import configurations from verified, non-secret resource identifiers."""
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[2]
inventory = json.loads((root / 'infra/inventory.json').read_text())
org = inventory['organization']
if org == 'TU_ORGANIZACION_HCP' or not re.fullmatch(r'[A-Za-z0-9_-]+', org):
    raise SystemExit('Enter your real HCP organization name.')
providers = {
 'azure': ('azurerm', 'hashicorp/azurerm', '~> 4.0',
           'features {}\n  resource_provider_registrations = "none"'),
 'identity': ('azuread', 'hashicorp/azuread', '~> 3.0', ''),
 'aws': ('aws', 'hashicorp/aws', '~> 6.0', ''),
 'databricks': ('databricks', 'databricks/databricks', '~> 1.0', ''),
 'snowflake': ('snowflake', 'snowflakedb/snowflake', '= 2.21.0',
               'preview_features_enabled = ["snowflake_stage_resource", "snowflake_file_format_resource", "snowflake_storage_integration_resource", "snowflake_pipe_resource"]'),
}
for name, (provider, source, version, body) in providers.items():
    resources = inventory.get(name, [])
    if not resources:
        raise SystemExit('Inventory is incomplete: ' + name)
    directory = root / 'infra' / name
    directory.mkdir(parents=True, exist_ok=True)
    if (directory / 'imports.tf').exists():
        raise SystemExit('Already generated: ' + name + '. Edit existing files; do not overwrite them.')
    seen = set()
    imports = []
    for r in resources:
        address, identifier = r['address'], r['id']
        if not re.fullmatch(provider + r'_[a-z0-9_]+\.[a-z0-9_]+', address):
            raise SystemExit('Invalid resource address: ' + address)
        if address in seen or re.search(r'TU_|ID_DEL_|NOMBRE_REAL|JOB_ID|OBJECT_ID|ID_FEDERACION', identifier):
            raise SystemExit('Replace placeholder/duplicate: ' + address)
        seen.add(address)
        imports.append('import {\n  to = ' + address + '\n  id = ' + json.dumps(identifier) + '\n}\n')
    config = ('terraform {\n  required_version = ">= 1.5, < 2.0"\n'
      '  required_providers {\n    ' + provider + ' = {\n'
      '      source = ' + json.dumps(source) + '\n'
      '      version = ' + json.dumps(version) + '\n    }\n  }\n}\n\n'
      'provider "' + provider + '" {\n  ' + body + '\n}\n')
    (directory / 'providers.tf').write_text(config)
    (directory / 'imports.tf').write_text('\n'.join(imports))
    (directory / 'cloud.tf').write_text('terraform {\n  cloud {\n'
      '    organization = ' + json.dumps(org) + '\n'
      '    workspaces { name = "max-week4-' + name + '" }\n  }\n}\n')
    print('Created configuration:', directory.relative_to(root))
print('Next: init, generate-config, review, protect, plan, import-only gate.')
