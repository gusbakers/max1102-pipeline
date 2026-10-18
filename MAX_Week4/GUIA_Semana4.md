# Semana 4: automatización y operación

Gustavo | Healthcare Platform / MAX | Guía por días

Esta guía continúa el repositorio gusbakers/max1102-pipeline. El bloque del lunes se actualizó el 18 de octubre de 2026 sobre la versión 534021997702f672e89e725758655f235bf2a416 de GitHub y las 25 pruebas compartidas en el chat. Para retomar tu avance, empieza por INICIAR_LUNES.md. Los recursos de tus cuentas cloud no se han inspeccionado en directo: los pasos de inventario sirven para confirmar su estado antes de modificarlos.

El paquete contiene archivos preparados, un instalador por día y esta guía. Todo el código se edita en GitHub Codespaces. Azure, Databricks, AWS y Snowflake ejecutan sus partes respectivas. No necesitas instalar nada en tu computadora personal.

## Qué quedará funcionando

| Día | Trabajo | Resultado comprobable |
|---|---|---|
| Lunes | CI | Pruebas de API y del DAG en cada PR y cambio en main |
| Martes | CD | Despliegue de la API y notebooks revisados; SHA verificable |
| Miércoles | Terraform | Recursos reales importados, código revisado y estado remoto |
| Jueves | Operación | Logs, métricas, alertas probadas y costos documentados |
| Viernes | Demostración | Evidencias del recorrido completo y límites del laboratorio |

La práctica mantiene Airflow en Docker dentro de Codespaces. Al apagar Codespaces, Airflow se detiene. El CD del DAG a un servicio Airflow permanente no queda resuelto con esta configuración: el código se valida y se entrega como artefacto, y el entorno de laboratorio se actualiza con git pull. La API Azure y el despliegue de notebooks sí se ejecutan desde GitHub sin depender de Codespaces.

Azure F1 y GitHub Actions programado no ofrecen un servicio de producción con SLA. Esto permite practicar los mecanismos de producción usando tus cuentas actuales; no equivale a un sistema disponible 24/7. No se añade un servidor de pago. Debes comprobar las cuotas y el consumo real: AWS S3, Snowflake, logs o un servicio fuera de su cuota pueden generar cargos.

## Preparación: abrir y colocar el paquete

**Stack y lugar:** navegador > GitHub > tu repositorio > Code > Codespaces > abrir tu Codespace existente. En VS Code web: Terminal > New Terminal.

**Paso 0.1. Confirmar que estás en el proyecto correcto.** Ejecuta en la terminal de Codespaces:

```bash
cd "$(git rev-parse --show-toplevel)"
pwd
git remote -v
git status --short
```

La ruta puede ser /workspaces/max1102-pipeline o el nombre que tenga tu Codespace. El remoto debe corresponder a gusbakers/max1102-pipeline. Los comandos siguientes se ejecutan desde esa raíz. Si hay trabajo sin guardar, revísalo antes de cambiar de rama; no uses reset --hard ni borres archivos para dejar el árbol limpio.

**Paso 0.2. Sincronizar la carpeta preparada.** MAX_Week4 ya está descomprimida en el repositorio. Desde main en tu Codespace:

```bash
git pull --ff-only origin main
ls MAX_Week4
```

Debes ver install.py, days, INICIAR_LUNES.md y GUIA_Semana4.md. Usa esta carpeta actualizada; el ZIP original conserva una versión anterior. El instalador copia los archivos de cada día a sus rutas definitivas y conserva respaldos locales.

**Paso 0.3. Evitar desplegar notebooks antiguos.** En GitHub existe un 02_validate.py con controles PySpark, pero no se ve la suite de Great Expectations. Además, el 00_common.py publicado no contiene algunas funciones llamadas por los notebooks. No concluyas que tu workspace funciona igual que GitHub: primero recupera la versión que ya probaste en Databricks.

**Lugar:** Databricks > Jobs & Pipelines > max1102_02_validate > Tasks > abrir el notebook usado por ese Job. Localiza la carpeta de los notebooks operacionales, incluidos 00_common, extract, validate, transform y load. Copia su ruta desde el workspace. Confirma también que la suite GX está integrada en ese validate y que falla el Job cuando la validación no pasa; una suite ejecutada solo en otro notebook no bloquea el DAG.

**Lugar del código:** terminal de Codespaces. Usa tu perfil ya configurado MAX1102:

```bash
mkdir -p .week4-private/working-notebooks
read -r -p "Ruta de la carpeta de notebooks en Databricks: " NOTEBOOK_DIR
databricks workspace export-dir \
  "$NOTEBOOK_DIR" .week4-private/working-notebooks \
  --overwrite --profile MAX1102
```

La exportación solo lee Databricks. No cambia sus notebooks. Tras instalar el lunes, .week4-private estará ignorado por Git. Revisa los .py exportados y copia únicamente los notebooks operacionales a databricks/notebooks; no copies tokens, .env, datos ni notebooks exploratorios con claves pegadas. Compara con git diff. Si el workspace todavía no tiene GX integrado, esa integración sigue pendiente: no habilites CD de notebooks ni presentes la validación como terminada.

## Lunes: configurar las pruebas automáticas

**Objetivo:** un cambio que rompe el API o el DAG queda identificado antes del despliegue.

**Paso 1.1. Crear la rama e instalar los archivos. Lugar: terminal de Codespaces.**

```bash
git switch -c week4-ci
python3 MAX_Week4/install.py lunes
git status --short
git diff -- .github/workflows/ci.yml .gitignore
```

Si week4-ci ya existe por un intento anterior, usa git switch week4-ci. El instalador actualiza el CI que ya tenías y añade pruebas de API. No inicia Docker ni ejecuta los Jobs de Databricks.

| Archivo definitivo | Para qué sirve |
|---|---|
| .github/workflows/ci.yml | GitHub ejecuta los trabajos api-tests y check-dag |
| api/test_api.py | 25 casos sobre autenticación, validación, respuesta, fallos y serialización real del SDK sin red |
| api/requirements-dev.txt | Incluye requirements.txt y pytest 9.1.1 para pruebas |
| .devcontainer/Dockerfile | Archivo que referencia la configuración actual de Codespaces |
| week4/scripts/package_api.py | ZIP permitido: Python, requirements y versión; excluye .env |
| week4/scripts/smoke.py | Comprueba la API desplegada; se utiliza a partir del martes |

**Paso 1.2. Probar la API en Codespaces.**

```bash
python3 -m venv .venv-week4
source .venv-week4/bin/activate
python -m pip install -r api/requirements-dev.txt
(
  cd api
  python -m pytest -q
)
```

Resultado esperado para el código revisado: 25 passed. Estas pruebas sustituyen Gemini por una respuesta simulada; no llaman a tu cuenta ni gastan tokens. Comprueban el contrato de la API, no la calidad semántica de un modelo real.

**Paso 1.3. Sincronizar los notebooks comprobados.** Ya instalado el .gitignore del lunes, copia los notebooks exportados en el paso 0.3 a su carpeta Git. En el explorador puedes seleccionar los .py y copiar/pegar en databricks/notebooks. Mantén los nombres que usan los Jobs. Después:

```bash
git diff -- databricks/notebooks
python -m compileall -q databricks/notebooks
```

La compilación detecta errores de sintaxis de Python; no ejecuta Spark, GX ni dbutils. La prueba real será una ejecución en Databricks. Verifica que 00_common y sus funciones auxiliares estén incluidos en Git, y que el notebook de validación sea el correcto.

**Paso 1.4. Subir los cambios revisados y abrir el PR.**

```bash
git add .gitignore .github/workflows/ci.yml week4
git add .devcontainer/Dockerfile api/test_api.py api/requirements-dev.txt
git add databricks/notebooks
git diff --cached --stat
git diff --cached --name-only
git commit -m "Add API tests and extend pipeline CI"
git push -u origin week4-ci
```

No uses git add .: añade las rutas concretas. Revisa que no aparezcan claves, .env, estado de Terraform ni archivos privados. En GitHub abre Compare & pull request, con destino main. La pestaña Checks del PR debe mostrar api-tests y check-dag en verde. check-dag construye la imagen Docker y comprueba las seis tareas; no enciende tu Airflow ni ejecuta cargas cloud.

**Paso 1.5. Demostrar que el CI detecta un fallo.** Antes de fusionar el PR, crea api/test_ci_demo.py desde el explorador con este contenido:

```python
def test_ci_failure_demo():
    assert False, "Fallo intencional para comprobar CI"
```

Haz commit y push de ese archivo. Comprueba que api-tests queda rojo. Elimina solo ese archivo de prueba, haz otro commit y push, y espera a que vuelva a verde. Guarda los enlaces de ambas ejecuciones en tu evidencia. En GitHub > Settings > Rules > Rulesets, crea una regla activa para main que requiera Pull Request y los checks api-tests/check-dag. Al trabajar solo, no exijas la aprobación de otra persona. No actives bypass para omitir los checks.

Fusiona el PR una vez verde. Después en Codespaces:

```bash
git switch main
git pull --ff-only
```

**Lunes terminado cuando:** el PR demuestra rojo/verde, el DAG pasa sus comprobaciones, las fuentes actuales están en Git y main está protegido. Todavía no hay despliegue automático.

## Martes: completar el despliegue automático

**Objetivo:** los cambios que llegan a main y pasan CI actualizan Azure y los notebooks habilitados.

**Paso 2.1. Instalar CD. Lugar: terminal de Codespaces.**

```bash
git switch -c week4-cd
python3 MAX_Week4/install.py martes
(
  cd api
  python -m pytest -q
)
git diff --stat
```

Se amplía el mismo ci.yml con deploy-api y deploy-notebooks. Ambos dependen de api-tests y check-dag. Se añade api/week4_observability.py y una pequeña integración en api/main.py. El nuevo /version devuelve el commit; los logs muestran ruta, código HTTP, duración y request_id, sin registrar headers ni bodies. Si tu main.py cambió y el instalador no reconoce su estructura, abre api/main.py y añade después de app = FastAPI(...):

```python
try:
    from .week4_observability import install as install_observability
except ImportError:
    from week4_observability import install as install_observability
install_observability(app)
```

**Paso 2.2. Confirmar Azure existente. Lugar: terminal de Codespaces.**

```bash
az login --use-device-code
az account show --query '{subscription:id,tenant:tenantId}' -o table
az webapp show -g rg-max-week2-api \
  -n maxweek2-gusbakers-972358cb \
  --query '{name:name,state:state,plan:serverFarmId}' -o table
az appservice plan show -g rg-max-week2-api \
  -n plan-max-week2-free --query '{name:name,sku:sku.name}' -o table
```

La guía reutiliza la Web App maxweek2-gusbakers-972358cb y el grupo rg-max-week2-api. Confirma el plan real; se espera F1 según el despliegue anterior. No crees otra aplicación si un nombre no coincide: toma el nombre que devuelva tu cuenta y actualiza el workflow y el script antes de continuar. Verifica en Azure > Web App > Configuration/Stack settings que siga usando Python 3.12 y el startup que ya funcionaba: python -m uvicorn main:app --host 0.0.0.0 --port 8000.

**Paso 2.3. Autorizar a GitHub con OIDC.** En vez de guardar una contraseña de Azure, el Job recibe una identidad temporal. Ejecuta una sola vez:

```bash
gh auth status
bash week4/scripts/azure_oidc.sh
```

El script crea una aplicación Entra, un service principal y una confianza para main de este repositorio. Asigna Website Contributor únicamente sobre tu Web App y guarda tres variables del repositorio: AZURE_CLIENT_ID, AZURE_TENANT_ID y AZURE_SUBSCRIPTION_ID. Son identificadores, no API keys. Las claves APP_API_KEY y GEMINI_API_KEY siguen en los ajustes de Azure; el ZIP no las lleva.

Debes tener permiso para crear aplicaciones Entra y asignar roles sobre esa Web App. Si Azure devuelve AuthorizationFailed, se necesita ese permiso en la cuenta; no se resuelve contratando un plan. Si el script falla después de crear la identidad, conserva .week4-private/azure-identity.json y completa la operación faltante con esa misma identidad, evitando duplicados. No repitas el script creando cuentas nuevas.

**Paso 2.4. Preparar CD de Databricks.** Antes de habilitarlo, repite la revisión de fuentes del lunes. Verifica que cada Job apunta a la carpeta que vas a actualizar. No debe haber ejecuciones activas durante la primera publicación porque los notebooks se importan uno por uno.

```bash
gh variable set DATABRICKS_HOST \
  --body "https://dbc-5bd6905e-128b.cloud.databricks.com"
read -r -p "Ruta exacta de los notebooks usada por los Jobs: " NOTEBOOK_DIR
gh variable set DATABRICKS_NOTEBOOK_DIR --body "$NOTEBOOK_DIR"
gh secret set DATABRICKS_TOKEN
```

El último comando te permite introducir el token sin escribirlo en el código ni en el historial. Usa un token válido del workspace con permiso sobre esa carpeta; utiliza el mecanismo de autenticación admitido por tu cuenta. Si tu administrador no permite tokens personales, este script necesita adaptarse a OAuth antes de habilitarlo. Nunca pegues el token en el chat.

Crea week4/databricks-reviewed.txt desde el explorador, indicando la fecha y que verificaste la carpeta, las dependencias y la suite de calidad. Este archivo no debe incluir secretos. Su existencia evita habilitar accidentalmente la publicación antes de la revisión. No demuestra por sí solo que GX funciona: conserva también la ejecución real.

**Paso 2.5. Habilitar, abrir PR y fusionar.**

```bash
gh variable set ENABLE_CD --body true
gh variable set ENABLE_DATABRICKS_CD --body true
git add .github/workflows/ci.yml api/main.py api/week4_observability.py week4
git diff --cached --stat
git commit -m "Automate Azure and reviewed notebook deployment"
git push -u origin week4-cd
```

Abre el PR en GitHub, espera los checks y fusiona. El PR ejecuta pruebas; el push a main resultante ejecuta CD. Run workflow manual ejecuta CI, pero no el despliegue: es intencional para evitar publicar desde una rama incorrecta.

**Paso 2.6. Comprobar publicación real.** En GitHub > Actions > MAX Week 4 CI-CD, abre la ejecución asociada al merge. Deben pasar api-tests, check-dag, deploy-api y deploy-notebooks. Azure hace el build de dependencias Python usando requirements.txt. La prueba final compara /version con el SHA de esa ejecución.

```bash
curl -fsS https://maxweek2-gusbakers-972358cb.azurewebsites.net/health
curl -fsS https://maxweek2-gusbakers-972358cb.azurewebsites.net/version
```

Espera status ok y el commit desplegado. /health solo prueba el servidor; no valida Gemini ni Snowflake. En Databricks abre el notebook para confirmar su versión. La publicación no ejecuta los Jobs y no cambia sus parámetros. El artefacto airflow-source del workflow contiene DAG y configuración; no significa que haya un servidor Airflow desplegado automáticamente.

**Recuperación:** si una nueva versión falla, crea un PR que revierta el cambio problemático y fusiónalo después de CI. Se volverá a desplegar la versión corregida. El smoke test detecta fallos, pero no ejecuta un rollback por sí mismo. Mientras investigas puedes desactivar nuevas publicaciones con gh variable set ENABLE_CD --body false. La API ya publicada no se borra por desactivar CD.

**Martes terminado cuando:** hay despliegue verde, SHA correcto, notebook revisado publicado y API respondiendo independientemente de Codespaces. Si CD Databricks está deshabilitado, anótalo como pendiente, no como completado.

## Miércoles: definir e incorporar infraestructura con Terraform

**Objetivo:** adoptar recursos existentes sin recrearlos. Este es el bloque más largo: Azure, identidad, S3, Jobs de Databricks y objetos de Snowflake tienen configuraciones diferentes.

**Paso 3.1. Instalar los archivos. Lugar: raíz del repositorio en Codespaces.**

```bash
git switch main
git pull --ff-only
git switch -c week4-iac
python3 MAX_Week4/install.py miercoles
cp infra/inventory.example.json infra/inventory.json
```

El inventario contiene identificadores y nombres; no contraseñas. Completarlo es obligatorio. No se ha inventado tu bucket S3 ni los Job IDs. Las cuentas cloud y el workspace gratuito se consideran plataformas existentes: se gestionan los objetos de este proyecto, no se recrean esas cuentas.

**Paso 3.2. Instalar Terraform en Codespaces.** Si terraform version ya funciona y es >=1.5 y <2.0, conserva esa instalación. De lo contrario, este bloque descarga 1.13.5 y verifica su checksum oficial:

```bash
mkdir -p .week4-private/terraform-bin
cd .week4-private/terraform-bin
curl -fsSLO https://releases.hashicorp.com/terraform/1.13.5/terraform_1.13.5_linux_amd64.zip
curl -fsSLO https://releases.hashicorp.com/terraform/1.13.5/terraform_1.13.5_SHA256SUMS
python3 - <<'PY'
from pathlib import Path
import hashlib, zipfile
name = 'terraform_1.13.5_linux_amd64.zip'
expected = next(line.split()[0] for line in
    Path('terraform_1.13.5_SHA256SUMS').read_text().splitlines()
    if line.endswith(name))
assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected
with zipfile.ZipFile(name) as z:
    z.extract('terraform', '.')
Path('terraform').chmod(0o755)
PY
cd ../..
export PATH="$PWD/.week4-private/terraform-bin:$PATH"
terraform version
```

Esto usa el Codespace Linux x86_64. En una terminal nueva, repite únicamente el export PATH desde la raíz del repositorio. No altera tu equipo personal.

**Paso 3.3. Configurar estado remoto. Stack: HCP Terraform, navegador.** En https://app.terraform.io crea una organización Free y cinco workspaces con flujo CLI: max-week4-azure, max-week4-identity, max-week4-aws, max-week4-databricks y max-week4-snowflake. En Settings > General de cada workspace cambia Execution Mode a Local. HCP guardará el estado y sus versiones; los comandos se ejecutarán en Codespaces. Comprueba la opción Free y las condiciones antes de continuar. La documentación consultada indica hasta 500 recursos gestionados sin cargo.

No guardes terraform.tfstate en GitHub, aunque el repositorio sea privado. El estado puede contener valores sensibles. En Codespaces ejecuta terraform login y completa el flujo del navegador; el token se introduce en la terminal de Terraform, no en un archivo .tf. Escribe el nombre exacto de la organización en infra/inventory.json.

**Paso 3.4. Obtener los IDs de Azure.** En terminal, con tu sesión az login activa:

```bash
az group show -n rg-max-week2-api --query id -o tsv
az appservice plan show -g rg-max-week2-api \
  -n plan-max-week2-free --query id -o tsv
az webapp show -g rg-max-week2-api \
  -n maxweek2-gusbakers-972358cb --query id -o tsv
az ad app list --display-name max-week4-github \
  --query '[].{object:id,client:appId}' -o table
```

Copia los tres resource IDs en la sección azure. Para identity toma CLIENT_ID, APP_OBJECT y SP_OBJECT del archivo privado que creó el script OIDC. Puedes abrirlo en el editor; son identificadores. Usa estos comandos sustituyendo los marcadores por esos IDs:

```bash
az ad app federated-credential list --id ID_OBJETO_APP \
  --query '[].{name:name,id:id}' -o table
az role assignment list --assignee ID_OBJETO_SP --all \
  --query "[?roleDefinitionName=='Website Contributor'].{id:id,scope:scope}" -o table
```

Selecciona solo la asignación cuyo scope es tu Web App. Completa las formas de importación exactas del JSON: /applications/ID para la aplicación, el OBJECT_ID del service principal sin prefijo, y APP_OBJECT/federatedIdentityCredential/FEDERATION_ID para la confianza OIDC. Inventaría también cualquier otro recurso del proyecto que aparezca en el grupo, por ejemplo un Application Insights ya creado; el modelo no lo supone existente.

**Paso 3.5. Obtener los datos AWS. Stack: consola AWS y AWS CLI en Codespaces.** En S3 copia el nombre y región del bucket de tu práctica. En Permissions verifica que Block all public access está activado. Completa el nombre del bucket en aws del inventario. Si ese control no existe, no inventes su importación: créalo de forma deliberada y verificada o registra el pendiente antes de continuar.

Si no tienes aws en Codespaces, instálalo en el entorno de práctica con python -m pip install awscli; después aws configure. Usa las credenciales del usuario IAM de laboratorio que ya tiene acceso al bucket, no las del usuario root. AWS CLI guarda las claves fuera del repositorio. Comprueba identidad y región:

```bash
aws sts get-caller-identity
aws s3api get-bucket-location --bucket NOMBRE_REAL_BUCKET
export AWS_REGION="REGION_REAL"
```

Una ubicación null equivale a us-east-1. En el inventario añade los recursos que realmente existan y sean de este proyecto: aws_s3_bucket_versioning, aws_s3_bucket_server_side_encryption_configuration, aws_s3_bucket_lifecycle_configuration o aws_s3_bucket_policy, usando como ID el nombre del bucket; aws_iam_role usando el nombre del rol. No añadas recursos inexistentes para forzar el ejemplo. Los objetos de datos S3 los gestiona el pipeline, no se importan uno por uno a Terraform.

**Paso 3.6. Obtener los IDs Databricks.** En Jobs & Pipelines abre max1102_01_extract, max1102_02_validate, max1102_03_transform y max1102_04_load. Copia el Job ID que aparece en los detalles/URL y ponlo en el inventario. En Catalog confirma workspace.max1102_pipeline y el Volume raw. Si tienes otros Jobs o recursos del proyecto, incorpóralos al inventario.

Para autenticar Terraform con la configuración existente:

```bash
export DATABRICKS_CONFIG_PROFILE=MAX1102
export DATABRICKS_HOST="https://dbc-5bd6905e-128b.cloud.databricks.com"
```

No incluyas databricks_notebook en Terraform si esos mismos notebooks ya los despliega GitHub Actions; cada objeto debe tener un responsable claro. Terraform gestiona los Jobs y el contenedor de datos; el pipeline gestiona tablas y contenido.

**Paso 3.7. Verificar Snowflake. Lugar: Snowsight > SQL worksheet.**

```sql
SELECT CURRENT_ORGANIZATION_NAME(), CURRENT_ACCOUNT_NAME(), CURRENT_USER();
SHOW SCHEMAS IN DATABASE MAX1201_S3_LAB;
SHOW STAGES IN DATABASE MAX1201_S3_LAB;
SHOW FILE FORMATS IN DATABASE MAX1201_S3_LAB;
SHOW PIPES IN DATABASE MAX1201_S3_LAB;
SHOW INTEGRATIONS;
```

El ejemplo usa LANDING, pero si S3_LAKE está en PUBLIC debes escribir PUBLIC en su ID. No importes PUBLIC como si hubieras creado un esquema LANDING allí. Importa únicamente los esquemas propios del proyecto. Mantén las comillas internas del JSON para database, schema y warehouse. Añade los file formats realmente usados: ID DATABASE|SCHEMA|FILE_FORMAT. Para storage_integration, el ID es su nombre. Para snowflake_pipe, el ID es DATABASE|SCHEMA|PIPE. Si no existe Snowpipe, no lo presentes como implementado. El proveedor fija la versión 2.21.0 y habilita explícitamente estos cuatro recursos preview para evitar depender de cambios futuros.

**Autenticación Snowflake para Terraform.** Usa key-pair en tu usuario autorizado. En Codespaces:

```bash
mkdir -p .week4-private
umask 077
openssl genrsa -out .week4-private/snowflake_rsa.pem 2048
openssl pkcs8 -topk8 -inform PEM -outform PEM -nocrypt \
  -in .week4-private/snowflake_rsa.pem \
  -out .week4-private/snowflake_key.p8
openssl rsa -in .week4-private/snowflake_key.p8 -pubout \
  -out .week4-private/snowflake_key.pub
```

En Snowsight ejecuta DESCRIBE USER "TU_USUARIO_REAL" y revisa RSA_PUBLIC_KEY_2_FP. Si ese slot ya está ocupado, no lo reemplaces: reutiliza una identidad autorizada o coordina otro slot. Si está vacío, copia solo el contenido base64 de snowflake_key.pub, sin líneas BEGIN/END y sin saltos, y registra:

```sql
ALTER USER "TU_USUARIO_REAL" SET RSA_PUBLIC_KEY_2='CONTENIDO_PUBLICO';
```

La clave pública se puede mostrar; el archivo .p8 y la clave privada no. No vuelvas a generar una clave si ya la registraste. En la terminal:

```bash
read -r -p "Organización Snowflake: " SNOWFLAKE_ORGANIZATION_NAME
read -r -p "Cuenta Snowflake: " SNOWFLAKE_ACCOUNT_NAME
read -r -p "Usuario Snowflake: " SNOWFLAKE_USER
export SNOWFLAKE_ORGANIZATION_NAME SNOWFLAKE_ACCOUNT_NAME SNOWFLAKE_USER
export SNOWFLAKE_AUTHENTICATOR=SNOWFLAKE_JWT
export SNOWFLAKE_PRIVATE_KEY="$(cat .week4-private/snowflake_key.p8)"
export SNOWFLAKE_ROLE=ACCOUNTADMIN
```

ACCOUNTADMIN corresponde a la adopción inicial en tu cuenta personal de laboratorio; para un entorno de equipo utiliza un rol de Terraform con permisos delimitados. No publiques credenciales dentro del stage. Si el stage utiliza claves AWS en lugar de storage integration, conserva esos valores en variables sensibles y estado remoto protegido; no los copies a main.tf.

**Paso 3.8. Generar configuración de importación. Lugar: terminal de Codespaces.** Revisa que inventory.json no tenga marcadores pendientes. No es necesario que sean exactamente los recursos del ejemplo: debe coincidir con tu inventario real.

```bash
export ARM_SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
python3 week4/scripts/generate_infra.py
terraform fmt -recursive infra
```

Esto escribe providers.tf, imports.tf y cloud.tf para cada plataforma. No crea recursos cloud. Los import blocks indican qué recursos existentes adoptará Terraform. Guarda también .terraform.lock.hcl cuando se cree, para fijar las versiones efectivamente usadas.

**Paso 3.9. Importar un módulo cada vez.** Empieza por Azure. Después repite sustituyendo azure por identity, aws, databricks y snowflake:

```bash
terraform -chdir=infra/azure init
terraform -chdir=infra/azure plan -generate-config-out=generated.tf
```

El primer plan puede mostrar errores de campos incompatibles generados por el proveedor. Abre infra/azure/generated.tf, resuelve solo los campos señalados conservando la configuración real y vuelve a ejecutar plan sin -generate-config-out. No ejecutes apply mientras haya errores. generated.tf está ignorado porque puede contener secretos.

Para Azure, sustituye app_settings por una variable sensible. Declara variable "app_settings" con type = map(string) y sensitive = true; en el recurso usa app_settings = var.app_settings. Puedes proporcionar los valores actuales sin imprimirlos:

```bash
export TF_VAR_app_settings="$(az webapp config appsettings list \
  -g rg-max-week2-api -n maxweek2-gusbakers-972358cb \
  --query '[].{name:name,value:value}' -o json | \
  python3 -c 'import json,sys; print(json.dumps({x["name"]:x["value"] for x in json.load(sys.stdin)}))')"
```

Aplica el mismo criterio a cualquier secreto del stage Snowflake. Un valor marcado sensitive aún puede estar en el estado: el estado permanece en HCP. Una vez revisado:

```bash
python3 week4/scripts/protect_generated.py infra/azure/generated.tf
terraform -chdir=infra/azure fmt
terraform -chdir=infra/azure validate
terraform -chdir=infra/azure plan -out=import.tfplan
terraform -chdir=infra/azure show -json import.tfplan > .week4-private/azure-plan.json
python3 week4/scripts/check_import_plan.py .week4-private/azure-plan.json
```

Resultado exigido: importaciones sin add/change/destroy. El control bloquea cambios reales, incluidos reemplazos. Si falla, compara HCL y estado real; no elimines el control ni uses -auto-approve. Corrige y vuelve a generar el plan. Si pasa, aplica exactamente ese archivo:

```bash
terraform -chdir=infra/azure apply import.tfplan
terraform -chdir=infra/azure plan
```

Espera No changes. Repite el proceso para los otros cuatro módulos. Un plan posterior con cambios impide dar la adopción por terminada.

**Paso 3.10. Convertir la configuración en código mantenible.** Cuando generated.tf esté saneado, muévelo a main.tf dentro de su módulo; no dejes ambos archivos porque duplicarías los recursos. Reemplaza referencias fijas por dependencias reales: en la Web App usa service_plan_id = azurerm_service_plan.api.id y resource_group_name = azurerm_resource_group.api.name; en el plan usa la misma referencia de resource group. En los objetos Snowflake conecta database/schema mediante referencias a los recursos del módulo. En los controles del bucket usa bucket = aws_s3_bucket.lake.id. Mantén prevent_destroy. Vuelve a ejecutar fmt, validate y plan: el resultado debe seguir siendo No changes.

La generación automática copia atributos; no diseña todas las dependencias por ti. Comprueba la creación desde cero con un plan revisado en otro entorno únicamente cuando esté autorizado y presupuestado; no borres tus recursos para demostrar reproducibilidad.

```bash
git add infra week4/scripts .github/workflows/terraform.yml
git diff --cached --name-only
git diff --cached
git commit -m "Adopt existing project infrastructure with Terraform"
git push -u origin week4-iac
```

Revisa especialmente main.tf. No incluyas generated.tf, *.tfstate*, *.tfplan, .auto.tfvars.json ni .week4-private. Los .tfvars y planes están ignorados. Abre el PR y fusiónalo al verificar que el inventario está completo y cada módulo tiene un plan sin cambios.

El workflow MAX Terraform Validate comprueba formato y configuración de los cinco módulos en el PR, sin autenticarse en tus cuentas cloud. No sustituye el plan autenticado que ejecutaste en Codespaces. Añade sus checks a la regla de main después de que aparezcan por primera vez.

**Miércoles terminado cuando:** el inventario coincide con todos los recursos propios del proyecto, el estado está en HCP, los cinco módulos pasan validación/plan y el código saneado está en Git. Si falta un rol, integración, pipe o recurso existente, anótalo y complétalo: importar solo el bucket y la Web App no equivale a toda la infraestructura.

## Jueves: verificar monitoreo, alertas y costos

**Paso 4.1. Instalar el monitor. Lugar: terminal de Codespaces.**

```bash
git switch main
git pull --ff-only
git switch -c week4-operations
python3 MAX_Week4/install.py jueves
gh variable set ENABLE_MONITOR --body true
git add .github/workflows/monitor.yml week4
git commit -m "Add health monitoring and operational review"
git push -u origin week4-operations
```

Abre y fusiona el PR. monitor.yml solo se programa cuando está en main. A los 17 minutos de cada hora consulta /health; reintenta tres veces para tolerar el arranque en frío de F1. No mantiene la API siempre encendida. Los horarios de GitHub pueden retrasarse y el monitor puede deshabilitarse tras 60 días de inactividad del repositorio.

**Paso 4.2. Probar una alerta real sin tumbar el servicio. Lugar: GitHub web.** En tu perfil > Settings > Notifications > Actions, activa notificaciones de ejecuciones fallidas por web o email. Luego repositorio > Actions > MAX Monitor API > Run workflow > simulate_failure activado > Run. Debe fallar deliberadamente y debes recibir la notificación. Repite con simulate_failure desactivado: debe volver a verde. Guarda el enlace y la hora de ambas ejecuciones. Ver un job rojo sin comprobar la recepción del aviso no completa la prueba de alertas.

**Paso 4.3. Ver métricas y logs en Azure.** En Azure Portal > Web App > Monitoring > Metrics, selecciona el último intervalo de una hora y agrega Requests, Average Response Time y Http 5xx, según los nombres que aparezcan para tu recurso. Guarda la vista o fíjala en tu dashboard. Genera tráfico abriendo /health, /version y una petición de prueba desde /docs. Comprueba luego las métricas. En Monitoring > Log stream busca eventos http_request con status y duration_ms. Si necesitas habilitar salida a archivos del contenedor:

```bash
az webapp log config -g rg-max-week2-api \
  -n maxweek2-gusbakers-972358cb --docker-container-logging filesystem
az webapp log tail -g rg-max-week2-api -n maxweek2-gusbakers-972358cb
```

Ctrl+C cierra únicamente la visualización de logs. No copies claves ni bodies a la evidencia. Log stream ayuda al diagnóstico; no es almacenamiento durable centralizado. Si ya tienes Application Insights, revisa allí requests, failures y performance. Si no existe, esta ruta usa métricas de plataforma, logs y monitor externo; no afirma que Application Insights esté instalado ni activa servicios de pago por defecto.

**Paso 4.4. Monitorear el pipeline y la calidad.** En Databricks abre cada uno de los cuatro Jobs > Notifications y añade tu propio correo en On failure; configura también duración si tienes un umbral medido. Si los Jobs ya están gestionados por Terraform, incorpora esa configuración en sus bloques email_notifications/on_failure y aplica un plan revisado, en vez de dejar cambios manuales fuera del código.

En Airflow > DAG > Grid, revisa el estado de las seis tareas, intentos, duración y logs. validate tiene retries=0 para no repetir datos inválidos; las tareas transitorias admiten un reintento. El notify actual registra el éxito en logs y no envía un mensaje por sí mismo. Los fallos de preparación y del propio Airflow no quedan cubiertos por las notificaciones de Databricks: dentro del laboratorio revisa Grid y docker compose ps. La alerta automática de salud del host Airflow requiere un host accesible permanente y queda como pendiente de producción.

Para probar que la validación avisa, usa una copia del Job/notebook con datos sintéticos de prueba o parámetros que provoquen una validación fallida. No corrompas la tabla válida. Confirma: falla el Job, falla validate en la ejecución de prueba, transform/load no avanzan y llega el aviso. Luego ejecuta con datos válidos. Conserva el resultado de la suite real y el último batch_id/report_month publicado. /health no detecta datos desactualizados.

**Paso 4.5. Revisar costos.** Abre week4/costos.md en Codespaces y completa las filas con evidencia de los portales. Usa el mismo intervalo para todos los servicios:

| Servicio | Dónde revisar |
|---|---|
| Azure | Cost Management > Cost analysis, filtrado por el grupo del proyecto |
| AWS | Billing and Cost Management > Bills y Free Tier; revisar S3 y requests |
| Snowflake | Admin > Cost Management; créditos y saldo de la cuenta |
| Databricks | Cuotas/uso disponibles para tu edición; duración de los Jobs |
| GitHub | Settings > Billing and licensing > Usage: Actions y Codespaces |
| Gemini | AI Studio/Google Cloud: uso del proyecto y límites |
| HCP Terraform | Organization > Plan/Billing: confirmar Free y recursos |

Puedes abrir week4/sql/snowflake_review.sql en Codespaces, copiar su contenido a una SQL worksheet de Snowflake y ejecutar por bloques. SHOW no requiere despertar el warehouse; las consultas de ACCOUNT_USAGE sí pueden usar cómputo y tienen retraso de actualización. Miden créditos, no automáticamente dólares. Ejecuta esa revisión una vez y deja el warehouse suspendido al terminar.

Configura en Terraform auto_suspend = 60 y auto_resume = true si corresponde al warehouse de laboratorio, revisa el plan y aplica solo ese cambio. No cambies tamaños o tiers sin revisar su costo. Para Azure confirma F1. Detén Codespaces tras la sesión. S3 sigue conservando objetos y puede acumular almacenamiento aunque no ejecutes nada; no existe un botón general de apagar AWS.

**Jueves terminado cuando:** tienes métricas y logs de requests reales, una alerta recibida y recuperación verde, evidencia de fallo de calidad/control del pipeline y una tabla con consumo, créditos y dinero facturado separados. Registra como pendientes los controles que no se hayan demostrado.

## Viernes: presentar y demostrar el flujo completo

**Paso 5.1. Preparar la evidencia. Lugar: Codespaces.**

```bash
git switch main
git pull --ff-only
python3 MAX_Week4/install.py viernes
```

Abre week4/demo.md. Completa la columna Resultado observado con enlaces y resultados medidos. Ya tienes el guion de una presentación de 8-10 minutos. No necesitas inventar porcentajes de ahorro ni repetir métricas de una ejecución antigua como si fueran las de hoy.

**Paso 5.2. Ejecutar una demostración controlada.**

1. Muestra un PR con CI pasando y su despliegue a main.
2. Abre /version y compara el SHA con la ejecución de GitHub.
3. En Codespaces actualiza main y reconstruye la imagen Airflow si cambió Dockerfile.
4. Enciende Airflow, abre el puerto privado 8080 y ejecuta el DAG con un mes existente, como 2025-12 si sigue disponible.
5. Observa prepare, extract, validate, transform, load y notify. Muestra el reporte y la evidencia de calidad.
6. Si S3/Snowflake aún reciben snapshots manuales, dilo y muestra esa carga como paso separado. Esta semana no convierte automáticamente el snapshot en Snowpipe.
7. Muestra un evento de log, las métricas, el simulacro de alerta, un plan Terraform sin cambios y el cuadro de costos.

**Lugar: terminal de Codespaces.** Conserva tu .env y conexión databricks_default existentes; el paquete no las reemplaza.

```bash
docker build -t max1102-airflow:3.2.0 airflow
export AIRFLOW_IMAGE_NAME=max1102-airflow:3.2.0
export AIRFLOW_PROJ_DIR=./airflow
docker compose up -d
docker compose ps
```

El docker-compose actual usa AIRFLOW_PROJ_DIR para montar dags/logs/config/plugins. El valor ./airflow hace que corresponda a las carpetas del repositorio. No uses docker compose down -v, porque eliminaría el volumen con el estado de Airflow. Si la instancia ya se inicializó en semanas anteriores, conserva ese volumen y su configuración.

**Paso 5.3. Confirmar independencia de la API y apagar el laboratorio.** Espera a que termine el DAG. Guarda la evidencia revisada, haz commit y push de week4/demo.md y week4/costos.md. Después:

```bash
docker compose down
gh codespace stop --codespace "$CODESPACE_NAME"
```

En el navegador vuelve a abrir https://maxweek2-gusbakers-972358cb.azurewebsites.net/health. La respuesta proviene de Azure, no de Codespaces. Si quieres detener también las verificaciones periódicas, GitHub > Actions > MAX Monitor API > menú de tres puntos > Disable workflow. Desactivar el monitor no elimina la Web App.

## Criterio de cierre y límites pendientes

No se considera completa la semana por tener todos los archivos creados. Debe existir evidencia de ejecución y recuperación. El mínimo de esta práctica es: CI rojo/verde; publicación del commit correcto; notebooks actuales; infraestructura importada sin cambios inesperados; alerta recibida; costos reales; demo de datos y API.

Para cerrar literalmente un ticket de producción 24/7 faltaría contratar o utilizar un host persistente de Airflow, desplegar allí automáticamente los cambios, persistir logs/estado y monitorizar ese host y la frescura de datos. Cualquier recurso cloud omitido del inventario también queda pendiente. Estas limitaciones deben figurar en la presentación y no ocultarse detrás de un check verde.

## Problemas habituales

| Síntoma | Comprobación |
|---|---|
| El instalador no encuentra .git/api | Estás fuera de la raíz del repositorio |
| CI falla al importar la API | Revisar requirements.txt y el primer traceback del Job |
| Databricks publica código viejo | Exportar fuente actual, revisar diff y ruta de los Jobs |
| deploy-api aparece skipped | Solo corre en push a main con ENABLE_CD=true |
| OIDC devuelve AADSTS70021 | Revisar subject exacto repo:gusbakers/max1102-pipeline:ref:refs/heads/main |
| Azure devuelve 403 | Revisar Website Contributor sobre la Web App y propagación del rol |
| Azure devuelve 502 al inicio | Revisar build Python, startup, logs y tiempo de arranque en frío |
| /version no coincide | El despliegue nuevo no está activo; revisar Actions y logs |
| Terraform propone reemplazar recursos | No aplicar; corregir HCL/IDs/importación hasta obtener cero cambios |
| Terraform pide credenciales en HCP | Execution Mode debe ser Local en los cinco workspaces |
| Stage de Snowflake no existe | Verificar esquema y rol con SHOW STAGES; LANDING/PUBLIC importa |
| Warehouse ya suspendido | No repetir SUSPEND; comprobar el estado antes |
| Monitor rojo sin notificación | Configurar notificaciones Actions y repetir el simulacro |

## Fuentes oficiales para consultar

GitHub Actions / despliegue Python en Azure: https://docs.github.com/en/actions/how-tos/deploy/deploy-to-third-party-platforms/python-to-azure-app-service

Azure OIDC y GitHub Actions: https://learn.microsoft.com/en-us/azure/app-service/deploy-github-actions

Comandos de workspace Databricks: https://docs.databricks.com/aws/en/dev-tools/cli/reference/workspace-commands

Terraform: importar y generar configuración: https://developer.hashicorp.com/terraform/language/import/generating-configuration

HCP planes y ejecución local: https://developer.hashicorp.com/terraform/cloud-docs/overview y https://developer.hashicorp.com/terraform/cli/cloud

Proveedor Snowflake y autenticación: https://github.com/snowflakedb/terraform-provider-snowflake/tree/main/docs

Notificaciones GitHub Actions: https://docs.github.com/en/actions/concepts/workflows-and-actions/notifications-for-workflow-runs

Limitaciones de programación de Actions: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows

Azure App Service plans: https://learn.microsoft.com/en-us/azure/app-service/overview-hosting-plans
