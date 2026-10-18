"""Install one day's files with preflight checks and local backups."""
import argparse
import datetime
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('day', choices=['lunes', 'martes', 'miercoles', 'jueves', 'viernes'])
    parser.add_argument('--dry-run', action='store_true', help='Mostrar cambios sin escribir archivos')
    args = parser.parse_args()
    root = Path.cwd()
    if not (root / '.git').exists() or not (root / 'api/main.py').is_file():
        raise SystemExit('Ejecuta desde la raíz del repositorio que contiene .git y api/main.py.')
    package = Path(__file__).resolve().parent
    source = package / 'days' / args.day
    files = [(p, root / p.relative_to(source)) for p in sorted(source.rglob('*')) if p.is_file()]
    if not files:
        raise SystemExit('Faltan los archivos del día seleccionado.')

    # These files already exist in Gustavo's Codespace. Preserve local revisions.
    preserve = {'api/test_api.py', 'api/requirements-dev.txt', '.devcontainer/Dockerfile'}
    conflicts = []
    for src, dst in files:
        rel = dst.relative_to(root).as_posix()
        if dst.exists() and not dst.is_file():
            conflicts.append(rel + ': el destino no es un archivo')
        elif rel in preserve and dst.exists() and dst.read_bytes() != src.read_bytes():
            conflicts.append(rel + ': hay una versión local diferente; revísala antes de instalar')

    api_main = root / 'api/main.py'
    api_content = api_main.read_text()
    add_observability = args.day == 'martes' and '# Week4 observability' not in api_content
    anchor = 'api_key_header = APIKeyHeader'
    if args.day == 'martes':
        for name in ['api/test_api.py', 'api/requirements-dev.txt', 'week4/scripts/package_api.py']:
            if not (root / name).is_file():
                conflicts.append(name + ': instala primero el lunes')
        if add_observability and anchor not in api_content:
            conflicts.append('api/main.py: cambió la estructura; revisa la integración de observabilidad')
    if conflicts:
        raise SystemExit('DETENIDO antes de modificar archivos:\n- ' + '\n- '.join(conflicts))

    ignore = root / '.gitignore'
    text = ignore.read_text() if ignore.exists() else ''
    rules = ['/.week4-private/', '/.week4-backups/', '/.venv-week4/', '/release/',
             '**/.terraform/', '*.tfstate*', '*.tfplan', '*.tfvars', '*.tfvars.json',
             'infra/**/generated*.tf', 'infra/**/plan*.json']
    missing = [rule for rule in rules if rule not in text.splitlines()]
    ignore_content = text.rstrip('\n') + '\n\n# MAX Week 4 local-only files\n' + '\n'.join(missing) + '\n'
    changes = [(src, dst) for src, dst in files
               if not dst.exists() or src.read_bytes() != dst.read_bytes()]
    for src, dst in files:
        action = 'Sin cambios' if dst.exists() and src.read_bytes() == dst.read_bytes() else 'Instalar'
        print(f'{action}: {dst.relative_to(root)}')
    if missing:
        print('Actualizar: .gitignore (respaldos, entornos y estado de Terraform)')
    if add_observability:
        print('Actualizar: api/main.py (endpoint de versión y logs)')
    if args.dry_run:
        print('Vista previa completada. No se modificó ningún archivo.')
        return

    backup = root / '.week4-backups' / (
        datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '-' + args.day)

    def save_previous(path):
        if path.exists():
            previous = backup / path.relative_to(root)
            previous.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, previous)

    if missing:
        save_previous(ignore)
        ignore.write_text(ignore_content)
    for src, dst in changes:
        save_previous(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    if add_observability:
        save_previous(api_main)
        addition = '''# Week4 observability
try:
    from .week4_observability import install as install_observability
except ImportError:
    from week4_observability import install as install_observability
install_observability(app)

'''
        api_main.write_text(api_content.replace(anchor, addition + anchor, 1))
    print('Instalación completada. Revisa: git diff; git status --short.')
    if backup.exists():
        print('Respaldos locales:', backup)
    print('No se hicieron commits, pushes, logins ni despliegues.')


if __name__ == '__main__':
    main()
