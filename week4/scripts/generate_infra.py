"""Generate import roots atomically after validating the complete supplied inventory."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
PROVIDERS = {
    'azure': ('azurerm', 'hashicorp/azurerm', '~> 4.0', 'features {}\n  resource_provider_registrations = "none"'),
    'identity': ('azuread', 'hashicorp/azuread', '~> 3.0', ''),
    'aws': ('aws', 'hashicorp/aws', '~> 6.0', ''),
    'databricks': ('databricks', 'databricks/databricks', '~> 1.0', ''),
    'snowflake': ('snowflake', 'snowflakedb/snowflake', '= 2.21.0',
                  'preview_features_enabled = ["snowflake_stage_resource", "snowflake_file_format_resource", "snowflake_storage_integration_resource", "snowflake_pipe_resource"]'),
}


def render(inventory):
    org = inventory.get('organization', '')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', org) or org.startswith('TU_'):
        raise ValueError('Set the real HCP Terraform organization')
    result = {}
    for name, (provider, source, version, body) in PROVIDERS.items():
        resources = inventory.get(name, [])
        if not resources:
            continue
        seen = set()
        blocks = []
        for item in resources:
            address, identifier = item['address'], item['id']
            if (not re.fullmatch(provider + r'_[a-z0-9_]+\.[a-z0-9_]+', address)
                    or address in seen or not isinstance(identifier, str) or not identifier.strip()
                    or re.search(r'TU_|ID_DEL_|NOMBRE_REAL|JOB_ID|OBJECT_ID|ID_FEDERACION', identifier)):
                raise ValueError('Unverified/duplicate inventory entry: ' + str(address))
            seen.add(address)
            blocks.append('import {\n  to = ' + address + '\n  id = ' + json.dumps(identifier) + '\n}\n')
        result[name] = {
            'imports.tf': '\n'.join(blocks),
            'providers.tf': ('terraform {\n  required_version = ">= 1.5, < 2.0"\n  required_providers {\n    '
                             + provider + ' = {\n      source = ' + json.dumps(source) + '\n      version = '
                             + json.dumps(version) + '\n    }\n  }\n}\nprovider "' + provider + '" {\n  ' + body + '\n}\n'),
            'cloud.tf': 'terraform {\n  cloud {\n    organization = ' + json.dumps(org)
                        + '\n    workspaces { name = "max-week4-' + name + '" }\n  }\n}\n',
        }
    if not result:
        raise ValueError('Inventory has no verified resources')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--inventory', type=Path, default=ROOT / 'infra/inventory.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'infra/adopted')
    args = parser.parse_args()
    try:
        rendered = render(json.loads(args.inventory.read_text()))
        conflicts = [args.output / cloud / name for cloud, files in rendered.items() for name in files
                     if (args.output / cloud / name).exists()]
        if conflicts:
            raise ValueError('Output already exists; review existing configuration instead of regenerating')
    except (ValueError, KeyError, TypeError) as exc:
        raise SystemExit(str(exc)) from None
    for cloud, files in rendered.items():
        dest = args.output / cloud
        dest.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            (dest / name).write_text(content)
        print('Created:', dest)
    print('Generate actual resource HCL from the account, sanitize it, then enforce the import-only plan gate.')


if __name__ == '__main__':
    main()
