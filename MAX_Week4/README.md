# Semana 4: archivos preparados por día

Empieza por **[INICIAR_LUNES.md](INICIAR_LUNES.md)**. La carpeta ya está
descomprimida y versionada en GitHub; no necesitas volver a subir ni extraer el ZIP.

Todo se ejecuta desde la raíz de `gusbakers/max1102-pipeline` en Codespaces.

```bash
python3 MAX_Week4/install.py lunes --dry-run
python3 MAX_Week4/install.py lunes
```

El primer comando muestra el plan. El segundo coloca los archivos en sus rutas
definitivas y respalda los que sustituye. Conserva las pruebas existentes cuando
son iguales; si difieren, se detiene antes de escribir para permitir compararlas.
No hace commit, push, login ni despliegues. El lunes no necesita claves cloud.

| Día | Material preparado |
| --- | --- |
| Lunes | Las 25 pruebas de API compartidas en el chat, CI, comprobación del DAG y empaquetado |
| Martes | CD de API/notebooks y observabilidad básica |
| Miércoles | Inventario e importación con Terraform |
| Jueves | Monitor HTTP y revisión de costos |
| Viernes | Guion y evidencias de la demostración |

La guía completa está en [GUIA_Semana4.md](GUIA_Semana4.md). El bloque del lunes
se ajustó a `api/test_api.py`, `api/requirements-dev.txt` y Python 3.12.
Incluye el Dockerfile que utiliza tu configuración actual de Codespaces.

Preparar estos archivos no completa la semana: aún hay que instalar cada día,
comprobar GitHub Actions y ejecutar los pasos autenticados en tus cuentas.
Airflow continúa siendo un laboratorio en Codespaces; este paquete no crea
un servidor permanente ni habilita una infraestructura de pago.

El ZIP original se conserva como referencia. Usa esta carpeta para continuar:
contiene las correcciones posteriores a ese ZIP.
