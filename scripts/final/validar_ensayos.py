"""Comprueba los 15 ensayos independientes y el objetivo de acople >=90 %."""
import argparse
import json
from pathlib import Path

CONFIG = {"frontal": (0., 0.), "desalineacion_15": (15., 0.),
          "error_supervisor": (10., 0.03)}


def resumir(archivo):
    import math

    filas = [json.loads(linea) for linea in archivo.read_text().splitlines()]
    claves = {(d["escenario"], d["repeticion"]) for d in filas}
    if len(filas) != 15 or claves != {(e, r) for e in CONFIG for r in range(1, 6)}:
        raise ValueError("Se esperan cinco ensayos distintos por escenario.")
    totales = dict.fromkeys(CONFIG, 0)
    for d in filas:
        grados, residual = CONFIG[d["escenario"]]
        x, y, yaw = d["pose_inicial"]
        if not (d["tipo"] == "ensayo" and abs(x - 0.76) < 0.015
                and abs(y - (-1.4 + residual)) < 0.015
                and abs(yaw - math.radians(grados)) < math.radians(2)):
            raise ValueError(f"Pose de ensayo fuera de la configuración: {d}")
        if d["exito"]:
            if not (abs(d["ed_m"]) <= 0.01 and abs(d["et_deg"]) <= 5
                    and 1 <= d["acople_s"] <= 60.2 and d["reintentos"] == 0
                    and d["motivo"] == "TOLERANCIA_SOSTENIDA_1_SEGUNDO"):
                raise ValueError(f"Acople marcado como éxito fuera de criterio: {d}")
            totales[d["escenario"]] += 1
    exitos = sum(totales.values())
    return {"exitos_por_escenario": totales, "exitos": exitos, "intentos": 15,
            "tasa_pct": 100*exitos/15, "cumple_90_pct": exitos/15 >= .9}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registro", type=Path)
    args = parser.parse_args()
    resultado = resumir(args.registro)
    print(json.dumps(resultado, indent=2))
    return 0 if resultado["cumple_90_pct"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
