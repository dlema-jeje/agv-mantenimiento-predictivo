#!/usr/bin/env python3
"""Adelanto neuronal CWRU del Avance 2."""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from scipy.io import loadmat
from scipy.stats import kurtosis, skew

from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = RAIZ / "entrega_avance2/neuronal"
SALIDA.mkdir(parents=True, exist_ok=True)

ARCHIVOS = {
    "Normal": "97_12k.mat",
    "Pista_interna": "105.mat",
    "Bola": "118.mat",
    "Pista_externa": "130.mat",
}

VENTANA = 2048
PASO = 1024


def cargar_senal(ruta):
    datos = loadmat(ruta)

    candidatos = []

    for nombre, valor in datos.items():
        if nombre.startswith("__"):
            continue

        if not isinstance(valor, np.ndarray):
            continue

        if not np.issubdtype(valor.dtype, np.number):
            continue

        if "DE_time" in nombre:
            candidatos.append((nombre, valor))

    if len(candidatos) != 1:
        raise RuntimeError(
            f"{ruta.name}: se esperaba una señal DE_time; "
            f"encontradas {len(candidatos)}"
        )

    nombre, matriz = candidatos[0]
    senal = np.asarray(matriz, dtype=float).ravel()

    if not np.all(np.isfinite(senal)):
        raise RuntimeError(
            f"{ruta.name}: valores no finitos"
        )

    print(
        f"{ruta.name}: {nombre}, "
        f"{len(senal)} muestras"
    )

    return senal


def caracteristicas(x):
    rms = np.sqrt(np.mean(x ** 2))
    pico = np.max(np.abs(x))

    return {
        "rms": float(rms),
        "pico": float(pico),
        "curtosis": float(kurtosis(
            x, fisher=False, bias=False
        )),
        "asimetria": float(skew(x, bias=False)),
        "desviacion": float(np.std(x, ddof=1)),
        "factor_cresta": float(
            pico / rms if rms > 0 else 0
        ),
    }


def segmentar(senal, clase, conjunto):
    filas = []

    for inicio in range(
        0, len(senal) - VENTANA + 1, PASO
    ):
        ventana = senal[inicio:inicio + VENTANA]

        fila = caracteristicas(ventana)
        fila["clase"] = clase
        fila["conjunto"] = conjunto
        fila["inicio_muestra"] = inicio
        filas.append(fila)

    return filas


def main():
    filas = []

    for clase, archivo in ARCHIVOS.items():
        ruta = RAIZ / "datos/cwru" / archivo

        if not ruta.is_file():
            raise FileNotFoundError(ruta)

        senal = cargar_senal(ruta)
        n = len(senal)

        i70 = int(n * 0.70)
        i85 = int(n * 0.85)

        partes = {
            "entrenamiento": senal[:i70],
            "validacion": senal[i70:i85],
            "prueba": senal[i85:],
        }

        for conjunto, tramo in partes.items():
            ventanas = segmentar(
                tramo, clase, conjunto
            )
            filas.extend(ventanas)

            print(
                f"  {conjunto}: "
                f"{len(ventanas)} ventanas"
            )

    tabla = pd.DataFrame(filas)

    columnas = [
        "rms",
        "pico",
        "curtosis",
        "asimetria",
        "desviacion",
        "factor_cresta",
    ]

    ruta_csv = SALIDA / "caracteristicas_cwru.csv"
    tabla.to_csv(ruta_csv, index=False)

    train = tabla[
        tabla["conjunto"] == "entrenamiento"
    ]
    val = tabla[
        tabla["conjunto"] == "validacion"
    ]
    test = tabla[
        tabla["conjunto"] == "prueba"
    ]

    escalador = StandardScaler()
    X_train = escalador.fit_transform(
        train[columnas]
    )
    X_val = escalador.transform(val[columnas])
    X_test = escalador.transform(test[columnas])

    modelo = MLPClassifier(
        hidden_layer_sizes=(32, 16),
        activation="relu",
        solver="adam",
        learning_rate_init=0.001,
        max_iter=150,
        random_state=42,
        early_stopping=False,
    )

    modelo.fit(X_train, train["clase"])

    pred_val = modelo.predict(X_val)
    pred_test = modelo.predict(X_test)

    acc_val = accuracy_score(
        val["clase"], pred_val
    )
    acc_test = accuracy_score(
        test["clase"], pred_test
    )

    reporte = classification_report(
        test["clase"],
        pred_test,
        zero_division=0,
    )

    matriz = confusion_matrix(
        test["clase"],
        pred_test,
        labels=list(ARCHIVOS),
    )

    joblib.dump(
        {
            "modelo": modelo,
            "escalador": escalador,
            "columnas": columnas,
        },
        SALIDA / "modelo_adelanto.joblib",
    )

    resumen = {
        "dataset": "CWRU",
        "clases": list(ARCHIVOS),
        "ventana": VENTANA,
        "solapamiento": 0.5,
        "division_temporal": "70/15/15",
        "ventanas_entrenamiento": len(train),
        "ventanas_validacion": len(val),
        "ventanas_prueba": len(test),
        "accuracy_validacion": float(acc_val),
        "accuracy_prueba": float(acc_test),
        "iteraciones": int(modelo.n_iter_),
        "nota": (
            "Entrenamiento inicial con scikit-learn. "
            "No equivale todavía al modelo TensorFlow/Keras "
            "requerido para la integración final."
        ),
    }

    (SALIDA / "resultados_adelanto.json").write_text(
        json.dumps(resumen, indent=2),
        encoding="utf-8",
    )

    (SALIDA / "reporte_clasificacion.txt").write_text(
        reporte,
        encoding="utf-8",
    )

    pd.DataFrame(
        matriz,
        index=list(ARCHIVOS),
        columns=list(ARCHIVOS),
    ).to_csv(SALIDA / "matriz_confusion.csv")

    print()
    print("===== RESULTADOS DEL ADELANTO =====")
    print(f"VENTANAS_TRAIN: {len(train)}")
    print(f"VENTANAS_VALIDACION: {len(val)}")
    print(f"VENTANAS_PRUEBA: {len(test)}")
    print(f"ACCURACY_VALIDACION: {acc_val:.4f}")
    print(f"ACCURACY_PRUEBA: {acc_test:.4f}")
    print(f"ITERACIONES: {modelo.n_iter_}")
    print("CSV_GENERADO: SI")
    print("MODELO_GUARDADO: SI")
    print()
    print(reporte)


if __name__ == "__main__":
    main()
