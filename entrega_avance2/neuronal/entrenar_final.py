#!/usr/bin/env python3
"""Adelanto neuronal MEC451: división temporal previa a segmentación."""

from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.io import loadmat
from scipy.stats import kurtosis, skew
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib

RAIZ = Path(__file__).resolve().parents[2]
ORIGEN = RAIZ / "datos" / "cwru"
DESTINO = RAIZ / "entrega_avance2" / "neuronal"
DESTINO.mkdir(parents=True, exist_ok=True)

ARCHIVOS = {
    "97.mat": "normal",
    "105.mat": "falla_interna",
    "118.mat": "falla_bola",
    "130.mat": "falla_externa",
}

VENTANA = 2048
PASO = 1024
FILAS = []

for archivo, etiqueta in ARCHIVOS.items():
    datos = loadmat(ORIGEN / archivo)
    candidatos = [
        (clave, np.asarray(valor).ravel())
        for clave, valor in datos.items()
        if clave.endswith("_DE_time") and isinstance(valor, np.ndarray)
    ]

    if len(candidatos) != 1:
        raise RuntimeError(
            f"{archivo}: se esperaba una señal DE_time; encontradas {len(candidatos)}"
        )

    señal = np.asarray(candidatos[0][1], dtype=float)
    n = len(señal)
    corte1 = int(n * 0.70)
    corte2 = int(n * 0.85)

    tramos = {
        "entrenamiento": (0, corte1),
        "validacion": (corte1, corte2),
        "prueba": (corte2, n),
    }

    for conjunto, (inicio, fin) in tramos.items():
        for posicion in range(inicio, fin - VENTANA + 1, PASO):
            ventana = señal[posicion:posicion + VENTANA]

            rms = float(np.sqrt(np.mean(ventana ** 2)))
            pico = float(np.max(np.abs(ventana)))

            FILAS.append({
                "registro": archivo,
                "clase": etiqueta,
                "conjunto": conjunto,
                "muestra_inicio": posicion,
                "muestra_fin_exclusivo": posicion + VENTANA,
                "rms": rms,
                "pico": pico,
                "curtosis": float(kurtosis(ventana, fisher=True)),
                "asimetria": float(skew(ventana)),
                "desviacion_estandar": float(np.std(ventana)),
                "factor_cresta": pico / rms if rms > 0 else 0.0,
            })

tabla = pd.DataFrame(FILAS)

if tabla.empty:
    raise RuntimeError("No se generaron ventanas.")

CARACTERISTICAS = [
    "rms", "pico", "curtosis", "asimetria",
    "desviacion_estandar", "factor_cresta",
]

if not np.isfinite(tabla[CARACTERISTICAS].to_numpy()).all():
    raise RuntimeError("Existen características no finitas.")

tabla.to_csv(DESTINO / "caracteristicas_cwru_final.csv", index=False)

entrenamiento = tabla[tabla["conjunto"] == "entrenamiento"]
validacion = tabla[tabla["conjunto"] == "validacion"]
prueba = tabla[tabla["conjunto"] == "prueba"]

modelo = Pipeline([
    ("escalador", StandardScaler()),
    ("clasificador", MLPClassifier(
        hidden_layer_sizes=(32, 16),
        max_iter=500,
        random_state=42,
        early_stopping=False,
    )),
])

modelo.fit(
    entrenamiento[CARACTERISTICAS],
    entrenamiento["clase"],
)

pred_validacion = modelo.predict(validacion[CARACTERISTICAS])
pred_prueba = modelo.predict(prueba[CARACTERISTICAS])

clases = sorted(tabla["clase"].unique())

resultados = {
    "division_temporal": [0.70, 0.15, 0.15],
    "ventana_muestras": VENTANA,
    "solapamiento": 0.50,
    "escalador_ajustado_solo_entrenamiento": True,
    "registros": list(ARCHIVOS.keys()),
    "ventanas_por_conjunto": {
        nombre: int(cantidad)
        for nombre, cantidad in tabla["conjunto"].value_counts().items()
    },
    "exactitud_validacion": float(accuracy_score(
        validacion["clase"], pred_validacion
    )),
    "exactitud_prueba": float(accuracy_score(
        prueba["clase"], pred_prueba
    )),
    "advertencia": (
        "Evaluacion temporal dentro de los mismos registros; "
        "no equivale a generalizacion a registros independientes."
    ),
}

(DESTINO / "resultados_final.json").write_text(
    json.dumps(resultados, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

(DESTINO / "reporte_final.txt").write_text(
    classification_report(
        prueba["clase"],
        pred_prueba,
        labels=clases,
        zero_division=0,
    ),
    encoding="utf-8",
)

pd.DataFrame(
    confusion_matrix(prueba["clase"], pred_prueba, labels=clases),
    index=clases,
    columns=clases,
).to_csv(DESTINO / "matriz_confusion_final.csv")

joblib.dump(modelo, DESTINO / "modelo_final.joblib")

print("=== ADELANTO NEURONAL GENERADO ===")
print("Ventanas:", len(tabla))
print("Entrenamiento:", len(entrenamiento))
print("Validación:", len(validacion))
print("Prueba:", len(prueba))
print("Exactitud validación:", resultados["exactitud_validacion"])
print("Exactitud prueba:", resultados["exactitud_prueba"])
print("CSV:", DESTINO / "caracteristicas_cwru_final.csv")
print("Modelo:", DESTINO / "modelo_final.joblib")
print("=== FIN PASO 211 ===")
