"""Summarize actual exported costs. Never infer zero usage or convert credits to money."""
import argparse
import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re

PROVIDERS = {'azure', 'aws', 'databricks', 'snowflake', 'github'}


def summarize(rows):
    totals = {}
    seen = set()
    for row in rows:
        provider, period, unit = (row[k].strip() for k in ('provider', 'period', 'unit'))
        if provider not in PROVIDERS or not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', period):
            raise ValueError('Unknown provider or invalid period')
        if not re.fullmatch(r'[A-Z][A-Z0-9_]{1,15}', unit) or not row['service'].strip():
            raise ValueError('Use an explicit unit/currency and service')
        try:
            amount = Decimal(row['amount'])
        except InvalidOperation:
            raise ValueError('Invalid amount') from None
        if not amount.is_finite():
            raise ValueError('Amount must be finite')
        key = (provider, period, unit)
        totals[key] = totals.get(key, Decimal(0)) + amount
        seen.add(provider)
    if not totals:
        raise ValueError('No billing data. An empty export is not evidence of zero cost.')
    return totals, sorted(PROVIDERS - seen)


def report(totals, missing):
    lines = ['# Revisión de costos con datos exportados', '',
             '| Proveedor | Periodo | Unidad/moneda | Total |', '|---|---|---|---:|']
    for (provider, period, unit), value in sorted(totals.items()):
        lines.append(f'| {provider} | {period} | {unit} | {value:f} |')
    lines.extend(['', 'Proveedores sin evidencia: ' + (', '.join(missing) or 'ninguno') + '.', '',
                  'Las unidades y los periodos se mantienen separados. Créditos/DBU no equivalen a USD.',
                  'Registrar aparte el origen, rango de fechas, descuentos y fecha de exportación.'])
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('csv', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        with args.csv.open(newline='') as source:
            result = report(*summarize(csv.DictReader(source)))
    except (ValueError, KeyError) as exc:
        raise SystemExit(str(exc)) from None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result)
    print('Report created:', args.output)


if __name__ == '__main__':
    main()
