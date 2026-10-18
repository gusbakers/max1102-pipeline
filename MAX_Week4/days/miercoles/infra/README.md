# Adopción de infraestructura existente

La configuración se genera desde los recursos reales. inventory.example.json
es un modelo, no evidencia de que esos recursos ya estén gestionados.

1. Inventariar todos los recursos del proyecto y completar inventory.json.
2. HCP Terraform: crear los cinco workspaces y elegir ejecución Local.
3. Ejecutar generate_infra.py; autenticarse en los proveedores.
4. Por cada módulo: init; plan -generate-config-out=generated.tf.
5. Corregir campos incompatibles que indique el proveedor. Separar secretos
   mediante variables sensitive; mantener generated.tf privado e ignorado.
6. Agregar prevent_destroy, construir un plan guardado y pasar check_import_plan.py.
7. Aplicar exclusivamente ese plan; confirmar un plan posterior sin cambios.
8. Copiar configuración saneada a main.tf, borrar generated.tf y volver a planificar.
9. Reemplazar IDs fijos por referencias entre recursos antes de considerar
   reproducible la configuración; revisar cada dependencia y validar el plan.
10. Commit de .tf, inventory.json y .terraform.lock.hcl; nunca state ni planes.

AWS: bucket y sus controles separados no son todos los permisos. Incluir
versionado, cifrado, lifecycle, policy, roles IAM e integraciones que realmente
se hayan creado. No importar políticas/recursos compartidos ajenos al proyecto.
Snowflake: verificar esquema real de S3_LAKE (LANDING/PUBLIC) e incorporar los
file formats, pipes e integrations que existan. Las tablas/datos se gestionan
por el pipeline y migraciones SQL versionadas. La cuenta de Snowflake y el
workspace gratuito de Databricks son plataformas existentes, fuera del alcance
de recreación de esta práctica; sus objetos del proyecto sí se inventarían.
Airflow: Dockerfile y Compose describen el entorno de laboratorio; el hosting
persistente de producción es un pendiente explícito, no un recurso ya resuelto.
