# Jueves — revisión de costos

**Estado: pendiente de exportaciones reales.** El tier gratuito o un warehouse suspendido no demuestran por sí solos que la cuenta completa tenga costo cero. No se han leído las cuentas de facturación desde esta terminal.

| Servicio | Evidencia del periodo | Revisión / posible ajuste | Estado |
|---|---|---|---|
| Azure | Exportación de Cost Management, SKU y consumo del plan | Confirmar F1; identificar recursos ajenos al laboratorio y egreso | Sin acceso |
| AWS | Exportación de Billing y uso del bucket real | Almacenamiento, solicitudes, transferencia; lifecycle solo después de revisar retención | Sin acceso |
| Databricks | Uso de la cuenta/edición y detalle de Jobs | Duración, retries, consumo/DBU; no multiplicar por un precio inventado | Sin acceso |
| Snowflake | Metering del warehouse y contrato/créditos de prueba | AUTO_SUSPEND, tamaño, queries repetidas; suspender al terminar | Sin acceso |
| GitHub | Billing de Actions/Codespaces y retención | Detener Codespaces inactivos y revisar artifacts de 14 días | Sin acceso |

1. Elegir el mismo rango de fechas y anotar la zona horaria. Usar exportaciones existentes de los portales; no habilitar productos de costo adicional solo para medir este laboratorio.
2. Guardar los originales en `.week4-private/`. Ejecutar `week4/sql/snowflake_review.sql` con un rol de lectura autorizado. Los SELECT pueden requerir compute; realizarlos durante una sesión breve. SHOW no obliga por sí solo a reanudar el warehouse.
3. Copiar `week4/costs.example.csv` a `.week4-private/costs.csv` y completar una fila por servicio con los importes realmente observados. Campos: `provider,service,period,unit,amount`; providers permitidos: azure,aws,databricks,snowflake,github. Usar `USD`, `CREDITS`, `DBU`, etc., según la fuente.
4. Generar el resumen:

   ```bash
   python3 week4/scripts/cost_report.py .week4-private/costs.csv --output .week4-private/cost-review.md
   ```

5. El reporte suma con decimales, mantiene unidades/periodos separados y enumera proveedores sin evidencia. Un CSV vacío falla; no genera un total de cero ficticio. No mezclar subtotales y totales en las filas porque duplicaría el gasto.
6. Registrar una decisión por oportunidad: evidencia inicial, cambio propuesto, impacto funcional, propietario, fecha y medición posterior. No borrar datos ni reducir retención sin el alcance acordado.
7. Si Terraform ya gestiona un ajuste, editarlo allí. Si todavía no lo gestiona, capturar el valor real antes de adoptarlo para evitar drift accidental.

La revisión está cerrada únicamente cuando existen importes/rango documentados y acciones justificadas. “Ahorro esperado” y “ahorro medido” se reportan por separado.
