# Activación con las sesiones existentes del Codespace

Ejecutar desde `/workspaces/max1102-pipeline` después de traer el commit integrado. No volver a usar `MAX_Week4/install.py`.

## Azure API

1. `python3 week4/scripts/check_access.py` debe mostrar sesiones funcionales para Azure y GitHub. Si la sesión venció, renovarla mediante `az login`/`gh auth login` en esa terminal. No pegar credenciales en el chat.
2. Actions debe tener una ejecución verde de `ci.yml` del main actual. El job `oidc-subject` publica el subject real como metadato, sin publicar su JWT. GitHub puede incluir IDs inmutables en subjects de repositorios nuevos; no copiar un subject antiguo de un tutorial.
3. Ejecutar:

   ```bash
   python3 week4/scripts/activate_from_terminal.py --activate-api
   ```

   El asistente descarga esos metadatos del run verde, reutiliza la sesión Azure, crea o reutiliza `max-week4-github`, configura la federación para main, asigna Website Contributor solo a la Web App existente, guarda IDs como GitHub Variables, activa `ENABLE_CD` y solicita un workflow de despliegue. No crea un App Service Plan ni imprime tokens.

4. Abrir el run que indique el script. Deben pasar `deploy-api` y la verificación de versión. Comprobar:

   ```bash
   python3 week4/scripts/smoke.py --url https://maxweek2-gusbakers-972358cb.azurewebsites.net --commit "$(git rev-parse origin/main)"
   ```

   Usar el SHA del run si main avanzó. Confirmar que `origin/main` está actualizado antes de usar el comando.

5. Para hacerlo por partes: copiar únicamente el subject del resumen de Actions y ejecutar `python3 week4/scripts/azure_oidc.py --subject 'SUBJECT_OBSERVADO'`. El script es reanudable; conserva su diario local en `.week4-private/azure-identity.json`. Requiere permisos del propietario para registrar la aplicación y asignar el rol en esa Web App. No amplía permisos si encuentra una federación distinta.
6. Configurar las reglas de main para exigir los cuatro checks de CI. Si se activa CD sin protección, sigue existiendo la posibilidad de un push directo; revisar Settings → Rules.

## Variables y secretos de Actions

| Nombre | Tipo | Uso |
|---|---|---|
| ENABLE_CD | Variable, `true` | Despliegue Azure después de CI en main |
| AZURE_CLIENT_ID / AZURE_TENANT_ID / AZURE_SUBSCRIPTION_ID | Variables | Federación; son identificadores, no secretos |
| ENABLE_MONITOR | Variable | `false` lo desactiva; por defecto activo |
| ENABLE_PIPELINE_MONITOR | Variable, `true` | Monitoreo Databricks opcional |
| DATABRICKS_HOST | Variable | `https://dbc-5bd6905e-128b.cloud.databricks.com` |
| DATABRICKS_JOB_IDS | Variable | Cuatro IDs, orden extract,validate,transform,load, separados por comas |
| DATABRICKS_NOTEBOOK_DIR | Variable | Carpeta real de los notebooks operativos |
| DATABRICKS_TOKEN | Secret | Credencial vigente con permisos mínimos para Jobs/workspace; nunca imprimirla |
| PIPELINE_MAX_AGE_DAYS | Variable | 35 por defecto, ajustar al calendario mensual acordado |
| ENABLE_DATABRICKS_CD | Variable, `true` | Solo después de revisar/exportar fuentes y definir ventana sin ejecuciones |
| ENABLE_AIRFLOW_CD | Variable, `true` | Solo con host y procedimiento de laboratorio configurados |
| AIRFLOW_HOST / AIRFLOW_USER | Variables | Host existente y usuario de despliegue |
| AIRFLOW_SSH_KEY / AIRFLOW_KNOWN_HOSTS | Secrets | Clave dedicada y huella verificada por un canal confiable |
| ENABLE_TERRAFORM_DRIFT | Variable, `true` | Solo después de adoptar Azure en estado remoto |
| AZURE_TF_CLIENT_ID | Variable | Identidad separada, lectora de Azure, con la misma federación main |
| TF_API_TOKEN | Secret | Acceso al workspace de estado HCP; no equivale a permisos para escribir en Azure |

## Databricks

No hay un manifiesto de revisión válido en esta entrega. El CD falla antes de tocar el workspace hasta que exista.

1. Con el perfil MAX1102, obtener las configuraciones de los cuatro Jobs y la carpeta real. Exportar los notebooks que ya funcionan a una carpeta de respaldo local (`.week4-private/`), comparar y luego actualizar `databricks/notebooks/` con las fuentes correctas.
2. Revisar funciones auxiliares, límites de fecha, idempotencia, controles GX y paths. Ejecutar en Databricks con datos sintéticos y registrar el run completo exitoso.
3. `python3 week4/scripts/notebook_manifest.py --record-run 'URL_DEL_RUN_EXITOSO'` guarda hashes y la referencia declarada. **El manifiesto no verifica por sí mismo el contenido del run remoto.** Revisar la evidencia antes de hacer commit.
4. Configurar variables/secreto. Pausar el DAG y cualquier schedule de Jobs, esperar que no haya runs activos y mantener esa ventana durante el despliegue. Los imports del workspace no son una transacción: no ejecutar el pipeline a mitad de la actualización.
5. El deploy verifica las rutas que usan los Jobs, rechaza Jobs activos y luego importa las fuentes revisadas. Verificar otra ejecución sintética y cerrar la ventana. Si cambian archivos, el manifiesto deja de coincidir y requiere nueva revisión.

La credencial de un perfil local no está disponible automáticamente para GitHub Actions. Configurar el secret mediante la interfaz de GitHub o stdin de `gh secret set`, evitando argumentos, historial y logs con el token.
