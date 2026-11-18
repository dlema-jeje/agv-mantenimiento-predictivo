"""Verifica arquitectura, particiones, escalado, métricas y paridad archivada."""
import argparse
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
from sklearn.preprocessing import StandardScaler

from caracteristicas import CLASES, FS, N, NOMBRES, extraer
from diagnostico import Diagnostico
from rondas import BancoPrueba, ROOT
from validar_gazebo import validar as validar_gazebo
from verificar import verificar_caracteristicas
from validar_ensayos import resumir as validar_ensayos

DATOS = ROOT / "datos/final"
RESULTADOS = ROOT / "resultados/final"
MODELOS = ROOT / "modelos"


def auditar():
    with ZipFile(MODELOS / "diagnostico.keras") as archivo:
        config = json.loads(archivo.read("config.json"))
    entrada, d32, dropout, d16, salida = [c["config"] for c in config["config"]["layers"]]
    assert entrada["batch_shape"][-1] == 9 and dropout["rate"] == .2
    assert [(c["units"], c["activation"]) for c in (d32, d16, salida)] == [
        (32, "relu"), (16, "relu"), (4, "softmax")]
    compilacion = config["compile_config"]
    assert compilacion["optimizer"]["class_name"] == "Adam"
    assert np.isclose(compilacion["optimizer"]["config"]["learning_rate"], 1e-3)
    assert compilacion["loss"] == "categorical_crossentropy"

    tabla = pd.read_csv(DATOS / "caracteristicas.csv")
    fuentes = json.loads((DATOS / "fuentes.json").read_text())
    for fuente in fuentes:
        archivo = tabla.loc[tabla.archivo == fuente["archivo"]]
        n = fuente["muestras"]
        cortes = (0, n * 70 // 100, n * 85 // 100, n)
        for fase, inicio, fin in zip(("train", "val", "test"), cortes[:-1], cortes[1:]):
            filas = archivo[archivo.conjunto == fase]
            assert (filas.clase == fuente["clase"]).all()
            assert (filas.inicio_tramo_original == inicio).all()
            assert (filas.fin_tramo_original == fin).all()
            muestras = ((fin - inicio) * FS + fuente["fs"] - 1) // fuente["fs"]
            np.testing.assert_array_equal(filas.inicio_12k, np.arange(0, muestras - N + 1, N//2))
    assert tabla.conjunto.value_counts().to_dict() == {"train": 285, "val": 55, "test": 55}

    modelo = Diagnostico(MODELOS / "diagnostico.npz")
    parametros = sum(p.size for p in modelo.pesos)
    assert parametros == 916
    escalador = StandardScaler().fit(tabla.loc[tabla.conjunto == "train", list(NOMBRES)])
    np.testing.assert_allclose(modelo.media, escalador.mean_, rtol=1e-10, atol=1e-12)
    np.testing.assert_allclose(modelo.escala, escalador.scale_, rtol=1e-10, atol=1e-12)

    historiales = {}
    for capas in (1, 2):
        h = pd.read_csv(RESULTADOS / f"historial_{capas}.csv")
        assert 50 <= len(h) <= 100 and np.isfinite(h.to_numpy()).all()
        id_mejor = h.loc[h.epoca >= 50, "val_loss"].idxmin()
        historiales[capas] = {
            "epocas": len(h), "mejor_epoca_habilitada": int(h.loc[id_mejor, "epoca"]),
            "val_loss": float(h.loc[id_mejor, "val_loss"]),
            "val_accuracy": float(h.loc[id_mejor, "val_accuracy"])}
    assert historiales[2]["val_loss"] < historiales[1]["val_loss"]

    banco = BancoPrueba(DATOS / "ventanas_prueba.npz")
    prueba = tabla[tabla.conjunto == "test"]
    np.testing.assert_array_equal(banco.clases, prueba.clase)
    np.testing.assert_allclose(extraer(banco.muestras), prueba[list(NOMBRES)], rtol=1e-10, atol=1e-12)
    pred = np.array(CLASES)[modelo.probabilidades(banco.muestras).argmax(axis=1)]
    cm = confusion_matrix(banco.clases, pred, labels=CLASES)
    np.testing.assert_array_equal(cm, pd.read_csv(RESULTADOS / "confusion.csv", index_col=0).loc[list(CLASES), list(CLASES)])
    precision, recall, _, _ = precision_recall_fscore_support(banco.clases, pred, labels=CLASES)
    np.testing.assert_allclose(np.column_stack((precision, recall)), pd.read_csv(
        RESULTADOS / "metricas.csv", index_col=0).loc[list(CLASES), ["precision", "recall"]])
    exactitud = np.trace(cm) / cm.sum()
    assert exactitud >= .92
    return {"parametros": parametros, "pesos_float32_bytes": 4 * parametros,
            "historiales": historiales, "exactitud": float(exactitud),
            "matriz_confusion": cm.tolist(), "paridad_scipy_pct": verificar_caracteristicas(),
            "gazebo_rondas_archivadas": validar_gazebo(RESULTADOS / "gazebo_rondas_revision.jsonl"),
            "gazebo_escenarios": validar_ensayos(RESULTADOS / "acople_escenarios_1_3.jsonl")}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--matlab", type=Path, help="CSV de valores que generó MATLAB.")
    args = parser.parse_args()
    prueba = auditar()
    if args.matlab:
        python = np.loadtxt(DATOS / "paridad_python.csv", delimiter=",")
        matlab = np.loadtxt(args.matlab, delimiter=",")
        assert matlab.shape == python.shape == (5, 9) and np.isfinite(matlab).all()
        error = (100 * abs(matlab - python) / np.maximum(abs(python), 1e-12)).max()
        assert error < .1, f"Error relativo {error:.8g} %"
        prueba["paridad_csv_motor_externo_pct"] = float(error)
    print(json.dumps(prueba, indent=2))


if __name__ == "__main__":
    main()
