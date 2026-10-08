import csv
import random
from datetime import date, timedelta
from pathlib import Path

rng = random.Random(1102)
out = Path(__file__).resolve().parent

specialties = [
    "Cardiology",
    "Dermatology",
    "General Practice",
    "Neurology",
    "Oncology",
    "Orthopedics",
    "Pediatrics",
    "Psychiatry",
]

providers = [
    {
        "provider_id": f"P{i:04d}",
        "provider_name": f"Provider {i}",
        "specialty": specialties[(i - 1) % len(specialties)],
    }
    for i in range(1, 1201)
]

claims = []

for i in range(1, 50001):
    claims.append(
        {
            "claim_id": f"C{i:06d}",
            "member_id": f"M{rng.randint(1, 10000):05d}",
            "provider_id": f"P{rng.randint(1, 1200):04d}",
            "service_date": (
                date(2025, 1, 1) + timedelta(days=rng.randint(0, 364))
            ).isoformat(),
            "claim_status": rng.choices(
                ["PAID", "DENIED", "PENDING"],
                weights=[70, 20, 10],
            )[0],
            "claim_amount": round(rng.uniform(50, 5000), 2),
        }
    )

# Introducir errores intencionales para practicar la validación.
for row in claims[0:250]:
    row["service_date"] = "2025-02-30"

for row in claims[250:500]:
    row["claim_amount"] = -abs(row["claim_amount"])

for row in claims[500:750]:
    row["provider_id"] = "P9999"

for row in claims[750:1000]:
    row["member_id"] = ""

# Agregar 100 duplicados exactos.
claims.extend(row.copy() for row in claims[-100:])

# Guardar los dos archivos CSV con encabezados.
for filename, rows in [
    ("claims.csv", claims),
    ("providers.csv", providers),
]:
    with (out / filename).open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

print(f"claims {len(claims)} filas")
print(f"providers {len(providers)} filas")