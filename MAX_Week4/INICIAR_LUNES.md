# Lunes: iniciar CI desde tu avance actual

**Lugar:** terminal de GitHub Codespaces, dentro de
`/workspaces/max1102-pipeline`.

**Stack:** Python 3.12, pytest, FastAPI, Docker/Airflow y GitHub Actions.
Tus 25 pruebas locales ya pasaron en la sesión del 18 de octubre de 2026.
Falta incorporarlas al CI y comprobar la ejecución en GitHub.

## 1. Confirmar los archivos y abrir la rama

```bash
cd /workspaces/max1102-pipeline
git status --short
ls MAX_Week4

if git show-ref --verify --quiet refs/heads/week4-ci; then
  git switch week4-ci
else
  git switch -c week4-ci
fi
```

Revisa los cambios que ya tienes; Git conservará los compatibles al cambiar de
rama. Si Git indica un conflicto, conserva la salida para revisarla en el chat.
No es necesario borrar archivos ni descartar cambios.

## 2. Revisar e instalar el lunes

```bash
python3 MAX_Week4/install.py lunes --dry-run
python3 MAX_Week4/install.py lunes
git diff --stat
git diff -- .github/workflows/ci.yml .gitignore
```

| Ruta definitiva | Función |
| --- | --- |
| `api/test_api.py` | Los 25 casos que ya probaste, incluido el SDK con HTTP simulado |
| `api/requirements-dev.txt` | Dependencias de la API y pytest 9.1.1 |
| `.github/workflows/ci.yml` | Jobs `api-tests` y `check-dag` |
| `.devcontainer/Dockerfile` | Archivo que ya referencia tu devcontainer |
| `week4/scripts/package_api.py` | Empaquetar la API excluyendo secretos |
| `week4/scripts/smoke.py` | Comprobar la API desplegada a partir del martes |

Los archivos idénticos se conservan. Si tus pruebas o el Dockerfile local
difieren de la copia preparada, el instalador se detiene antes de escribir.
Los respaldos de archivos sustituidos quedan en `.week4-backups/`, ignorada por Git.
La carpeta `airflow/api/` y el archivo `.bak` local no se borran ni se agregan al commit.

## 3. Ejecutar las pruebas desde la carpeta correcta

Puedes usar tu entorno `.venv` actual:

```bash
source .venv/bin/activate
python -m pip install -r api/requirements-dev.txt
(
  cd api
  python -m pytest -q
)
python week4/scripts/package_api.py
```

Si `.venv` no existe, créalo primero con `python3 -m venv .venv`.
Resultado esperado: `25 passed`. Las llamadas al LLM y a HTTP están simuladas;
no necesitas introducir API keys ni ejecutar los Jobs de Databricks.
El aviso de deprecación de Starlette/httpx observado en esta sesión no impide
que las pruebas pasen; no cambies a httpx2 para ocultarlo.

## 4. Revisar y publicar el CI

```bash
git add .github/workflows/ci.yml .gitignore .devcontainer/Dockerfile
git add api/requirements-dev.txt api/test_api.py
git add week4/scripts/package_api.py week4/scripts/smoke.py
git diff --cached --stat
git diff --cached --name-only
```

Comprueba también lo que pudiera estar preparado de antes. El siguiente commit
incluye todos los archivos staged; no deben aparecer claves, `.env`, respaldos
ni estado de Terraform. Después:

```bash
git commit -m "Add API tests and extend pipeline CI"
git push -u origin week4-ci
```

En GitHub abre el Pull Request hacia `main`. Comprueba que `api-tests` y
`check-dag` terminen en verde. El segundo construye la imagen Docker existente
y valida las seis tareas del DAG; no ejecuta la carga en Databricks.

## 5. Completar las evidencias del lunes

Continúa con los pasos 1.3 y 1.5 de `GUIA_Semana4.md`: revisar las fuentes
reales de Databricks, demostrar un fallo y su corrección en CI, y proteger
`main` con los checks. La prueba temporal del fallo va en `api/test_ci_demo.py`.
El lunes estará completo cuando hayas verificado esas evidencias en GitHub;
la preparación de esta carpeta por sí sola no las sustituye.
