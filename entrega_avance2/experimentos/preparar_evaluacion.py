from pathlib import Path
import csv

base = Path("entrega_avance2/experimentos")
base.mkdir(parents=True, exist_ok=True)

escenarios = {
    "frontal": {
        "desalineacion_grados": 0,
        "desplazamiento_lateral_m": 0.0,
        "perturbacion": "ninguna",
    },
    "desalineacion_15": {
        "desalineacion_grados": 15,
        "desplazamiento_lateral_m": 0.0,
        "perturbacion": "ninguna",
    },
    "error_supervisor": {
        "desalineacion_grados": 10,
        "desplazamiento_lateral_m": 0.03,
        "perturbacion": "ninguna",
    },
    "perturbacion_lateral": {
        "desalineacion_grados": 0,
        "desplazamiento_lateral_m": 0.0,
        "perturbacion": "fuerza_lateral",
    },
}

columnas = [
    "escenario",
    "repeticion",
    "desalineacion_inicial_grados",
    "desplazamiento_lateral_inicial_m",
    "perturbacion",
    "tipo_ensayo",
    "estado",
    "error_distancia_final_m",
    "error_angular_final_grados",
    "error_lateral_final_m",
    "tiempo_acople_s",
    "oscilaciones",
    "reintentos",
    "acople_exitoso",
    "observaciones",
]

ruta = base / "matriz_20_ensayos.csv"

with ruta.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=columnas)
    writer.writeheader()

    for nombre, config in escenarios.items():
        for repeticion in range(1, 6):
            writer.writerow({
                "escenario": nombre,
                "repeticion": repeticion,
                "desalineacion_inicial_grados":
                    config["desalineacion_grados"],
                "desplazamiento_lateral_inicial_m":
                    config["desplazamiento_lateral_m"],
                "perturbacion": config["perturbacion"],
                "tipo_ensayo": "gazebo_pendiente",
                "estado": "NO_EJECUTADO",
                "error_distancia_final_m": "",
                "error_angular_final_grados": "",
                "error_lateral_final_m": "",
                "tiempo_acople_s": "",
                "oscilaciones": "",
                "reintentos": "",
                "acople_exitoso": "",
                "observaciones": "",
            })

redisenio = base / "comparacion_antes_despues.csv"

with redisenio.open(
    "w", newline="", encoding="utf-8"
) as f:
    writer = csv.writer(f)
    writer.writerow([
        "version",
        "escenario",
        "ensayos_ejecutados",
        "acoples_exitosos",
        "error_distancia_medio_m",
        "error_angular_medio_grados",
        "tiempo_medio_s",
        "observaciones",
    ])

print("ESCENARIOS: 4")
print("REPETICIONES_PLANIFICADAS: 20")
print("ENSAYOS_FISICOS_EJECUTADOS: 0")
print("MATRIZ:", ruta)
print("REDISENIO:", redisenio)
