from pathlib import Path
import sys
import csv

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts/difuso"))

from controlador_agv import crear_simulacion

SALIDA = RAIZ / "entrega_avance2/comparacion"
SALIDA.mkdir(parents=True, exist_ok=True)

CASOS = [
    ("pasado_alineado", -0.04, 0),
    ("acoplado_alineado", 0, 0),
    ("muy_cerca_positivo", 0.04, 12),
    ("muy_cerca_negativo", 0.04, -12),
    ("cerca_alineado", 0.15, 0),
    ("lejos_alineado", 0.40, 0),
    ("lejos_positivo", 0.40, 15),
    ("lejos_negativo", 0.40, -15),
    ("cerca_positivo", 0.20, 7),
    ("cerca_negativo", 0.20, -7),
]

resultados = []

for nombre, ed, et in CASOS:
    sim = crear_simulacion()

    sim.input["ed"] = ed
    sim.input["et"] = et
    sim.compute()

    v = float(sim.output["v"])
    w = float(sim.output["w"])

    resultados.append({
        "caso": nombre,
        "ed_m": ed,
        "et_grados": et,
        "v_python_m_s": v,
        "w_python_rad_s": w,
    })

ruta = SALIDA / "diez_entradas_python.csv"

with ruta.open("w", newline="", encoding="utf-8") as f:
    escritor = csv.DictWriter(
        f, fieldnames=list(resultados[0])
    )
    escritor.writeheader()
    escritor.writerows(resultados)

print("===== DIEZ ENTRADAS MAMDANI =====")

for r in resultados:
    print(
        f"{r['caso']:24s} "
        f"ed={r['ed_m']:+.3f} "
        f"et={r['et_grados']:+.1f} "
        f"v={r['v_python_m_s']:+.5f} "
        f"w={r['w_python_rad_s']:+.5f}"
    )

print()
print("CASOS_EJECUTADOS_PYTHON:", len(resultados))
print("CSV:", ruta)
print("COMPARACION_CON_MATLAB: PENDIENTE")
print("MOVIMIENTO_SOLICITADO: NO")
