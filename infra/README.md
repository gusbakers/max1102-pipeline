# Terraform: adoptar la infraestructura existente

El objetivo es que Git describa los recursos reales sin recrear lo que ya funciona. En esta entrega existe una definición Azure de referencia y herramientas de adopción; todavía no existe un estado importado/verificado de las cuentas del propietario.

## Directorios y propiedad

- `azure/`: definición de referencia de RG, plan Linux F1 y Web App Python 3.12. CI valida su esquema; no se ejecuta `apply` aquí.
- `inventory.example.json`: tipos y nombres conocidos; los identificadores pendientes deben reemplazarse con evidencia del proveedor.
- `inventory.json`: inventario local, ignorado por Git.
- `adopted/<proveedor>/`: raíz operativa que genera el asistente; se versiona el HCL revisado y su `.terraform.lock.hcl` después de la importación.

**Usar un solo estado por recurso.** Para esta adopción, `adopted/azure/` es la raíz elegida. No aplicar también `azure/`. Los módulos de referencia no configuran un backend y no deben crear recursos duplicados.

## 1. Inventario real

Desde el Codespace autenticado, obtener IDs y configuración de RG `rg-max-week2-api`, plan `plan-max-week2-free`, Web App `maxweek2-gusbakers-972358cb`, identidad de despliegue y su role assignment. Azure CLI permite consultar IDs con `az group show`, `az appservice plan show`, `az webapp show` y `az role assignment list`.

Completar además, cuando exista acceso:

- AWS: bucket real, región, public-access block, cifrado, versioning, políticas/roles de integración y ciclo de vida existentes.
- Databricks: cuatro Jobs, schema `workspace.max1102_pipeline`, Volume `raw`, permisos y configuraciones que pertenezcan al proyecto.
- Snowflake: database `MAX1201_S3_LAB`, warehouse `MAX1201_S3_WH`, stage **`PUBLIC.S3_LAKE`**, file formats, integraciones, pipes y grants que existan. No crear un schema LANDING por suposición. PUBLIC es el schema predeterminado; no importarlo como un schema independiente sin comprobar el soporte del proveedor.
- AzureAD: aplicación, principal y credencial federada, con IDs de objeto correctos.

El ejemplo no es un inventario exhaustivo. Registrar los recursos fuera de alcance y su propietario; no declarar “toda la infraestructura como código” hasta reconciliar el listado real contra el estado. El generador admite listas vacías para adoptar por proveedor; rechaza placeholders y duplicados.

## 2. Estado remoto

Usar la organización HCP del propietario si el servicio disponible se ajusta al presupuesto. Crear un workspace por proveedor, llamado `max-week4-azure`, `max-week4-identity`, etc., en **Execution Mode: Local**: la ejecución usa la terminal autenticada, mientras HCP mantiene estado y locking. No iniciar un plan remoto con secretos que solo existen en tu terminal.

Si no hay backend remoto autorizado, detenerse después de validar el HCL. No ejecutar imports con estado local y dar por cerrado este requisito. State, plan y HCL generado pueden contener valores sensibles; no subirlos como artifacts públicos de Actions.

```bash
cp infra/inventory.example.json infra/inventory.json
# Editar el inventario y organization con datos verificados.
python3 week4/scripts/generate_infra.py
terraform login
```

El generador se detiene si ya existen archivos: no pisa una configuración curada.

## 3. Generar y revisar, un proveedor a la vez

Ejemplo Azure; usar las credenciales de la sesión local y la suscripción esperada. Terraform 1.13.5 es la versión del CI.

```bash
umask 077
terraform -chdir=infra/adopted/azure init
terraform -chdir=infra/adopted/azure plan -generate-config-out=generated.tf
python3 week4/scripts/protect_generated.py infra/adopted/azure/generated.tf
```

El HCL generado puede requerir corregir atributos incompatibles o extraer valores sensibles. Revisar manualmente antes de versionar. Reemplazar secretos por variables sensibles/referencias aprobadas; no ignorar un recurso entero para ocultar drift. Si un proveedor no genera una configuración utilizable, escribirla según el esquema de la versión bloqueada y repetir el plan.

Después de sanear y verificar el contenido:

```bash
mv infra/adopted/azure/generated.tf infra/adopted/azure/managed.tf
terraform -chdir=infra/adopted/azure fmt
terraform -chdir=infra/adopted/azure validate
terraform -chdir=infra/adopted/azure plan -out=adoption.tfplan
mkdir -p .week4-private
terraform -chdir=infra/adopted/azure show -json adoption.tfplan > .week4-private/azure-plan.json
python3 week4/scripts/check_import_plan.py .week4-private/azure-plan.json --require-import
```

El gate acepta únicamente `no-op` de recursos gestionados, con metadatos de importación. Rechaza create/update/delete/replacement, planes incompletos, errores y cambios diferidos. Si falla, corregir HCL para que coincida con lo existente; no saltarse el control.

## 4. Aplicar exactamente la importación revisada

Solo después de que el comando anterior termine correctamente, y manteniendo el mismo plan:

```bash
terraform -chdir=infra/adopted/azure apply adoption.tfplan
terraform -chdir=infra/adopted/azure plan -detailed-exitcode
```

El segundo comando debe salir con 0. El código 2 significa diferencias; el 1, error. Repetir el proceso por proveedor. Versionar HCL saneado y locks, guardar la evidencia en un lugar privado y registrar cantidades/direcciones sin valores sensibles en el PR. No utilizar `-auto-approve` sobre un plan nuevo ni ejecutar `destroy`.

`prevent_destroy` ayuda a bloquear borrados/reemplazos dentro del HCL, pero no impide borrar la configuración ni sustituye una revisión del plan.

## 5. Drift y mantenimiento

`terraform.yml` verifica **solo Azure** después de adoptar `infra/adopted/azure/managed.tf`. Requiere:

- `ENABLE_TERRAFORM_DRIFT=true`.
- `TF_API_TOKEN` para el estado HCP y el workspace en ejecución local.
- Una identidad `AZURE_TF_CLIENT_ID` con OIDC para main y **Reader** en el alcance que incluye los recursos adoptados. Separarla de la identidad de despliegue y no conceder permisos de escritura para comprobar drift.
- `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`.

El workflow nunca ejecuta apply ni publica el plan. Si falla por permisos, indica comprobación incompleta, no “sin drift”. Integrar controles equivalentes por proveedor después de tener sus credenciales y estado; hasta entonces, no afirmar cobertura multicloud de drift.

## Fuentes de implementación

- [Generación de HCL desde import blocks](https://developer.hashicorp.com/terraform/language/import/generating-configuration)
- [OIDC de GitHub](https://docs.github.com/en/actions/reference/security/oidc)
- [Proveedor AzureRM](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
- [Proveedor Snowflake](https://registry.terraform.io/providers/snowflakedb/snowflake/2.21.0/docs)
