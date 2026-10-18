"""Check existing terminal sessions without printing credentials or changing accounts."""
import json
from pathlib import Path
import shutil
import subprocess

CHECKS = {
    'github': ['gh', 'auth', 'status'],
    'azure': ['az', 'account', 'show', '--output', 'json'],
    'aws': ['aws', 'sts', 'get-caller-identity'],
    'databricks_MAX1102': ['databricks', 'current-user', 'me', '--profile', 'MAX1102'],
}


def main():
    result = {}
    for name, command in CHECKS.items():
        if not shutil.which(command[0]):
            result[name] = 'CLI missing'
            continue
        try:
            response = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                      timeout=20, check=False, stdin=subprocess.DEVNULL)
            result[name] = 'session works' if response.returncode == 0 else 'session unavailable'
        except subprocess.TimeoutExpired:
            result[name] = 'session check timed out'
    result['snowflake_config_exists'] = any((Path.home() / p).is_file() for p in
                                           ['.snowflake/connections.toml', '.snowsql/config'])
    result['snowflake_note'] = 'Configuration presence does not verify an active session.'
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
