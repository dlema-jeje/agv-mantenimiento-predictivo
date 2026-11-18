"""Descarga CWRU 0 hp y entrena las dos arquitecturas exigidas."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlretrieve

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.io import loadmat
from scipy.signal import resample_poly
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler
import tensorflow as tf

from caracteristicas import CLASES, FS, N, NOMBRES, extraer

ROOT = Path(__file__).resolve().parents[2]
REGISTROS = (("97", 48000), ("105", 12000), ("130", 12000), ("118", 12000))
PARTES = ("train", "val", "test")


def preparar(origen, destino):
    origen.mkdir(parents=True, exist_ok=True)
    ventanas, filas, fuentes = [], [], []
    for clase, (numero, hz) in zip(CLASES, REGISTROS):
        ruta = origen / f"{numero}.mat"
        url = f"https://engineering.case.edu/sites/default/files/{numero}.mat"
        if not ruta.exists():
            temporal = ruta.with_suffix(".part")
            urlretrieve(url, temporal)
            loadmat(temporal)
            temporal.replace(ruta)
        señal = loadmat(ruta)[f"X{int(numero):03d}_DE_time"].ravel()
        fuentes.append(dict(archivo=ruta.name, clase=clase, fs=hz, muestras=len(señal),
                            sha256=hashlib.sha256(ruta.read_bytes()).hexdigest(), url=url))
        limites = (0, len(señal) * 70 // 100, len(señal) * 85 // 100, len(señal))
        for parte, inicio, fin in zip(PARTES, limites[:-1], limites[1:]):
            tramo = señal[inicio:fin]
            if hz != FS:
                tramo = resample_poly(tramo, 1, hz // FS)
            for offset in range(0, len(tramo) - N + 1, N // 2):
                ventanas.append(tramo[offset:offset + N])
                filas.append((clase, parte, ruta.name, inicio, fin, offset))
    x = np.asarray(ventanas)
    meta = pd.DataFrame(filas, columns=["clase", "conjunto", "archivo",
                                      "inicio_tramo_original", "fin_tramo_original", "inicio_12k"])
    tabla = meta.join(pd.DataFrame(extraer(x), columns=NOMBRES))
    tabla.to_csv(destino / "caracteristicas.csv", index=False)
    test = meta.conjunto == "test"
    np.savez_compressed(destino / "ventanas_prueba.npz", muestras=x[test],
                        clases=meta.loc[test, "clase"].to_numpy(dtype=str))
    indices = [np.flatnonzero(test & (meta.clase == c))[0] for c in CLASES]
    indices.append(np.flatnonzero(test & (meta.clase == "ball"))[1])
    np.savetxt(destino / "paridad_ventanas.csv", x[indices], delimiter=",", fmt="%.17g")
    np.savetxt(destino / "paridad_python.csv", extraer(x[indices]), delimiter=",", fmt="%.17g")
    (destino / "fuentes.json").write_text(json.dumps(fuentes, indent=2))
    return tabla


def conjunto(x, y, entrenar=False):
    ds = tf.data.Dataset.from_tensor_slices((x, y))
    if entrenar:
        ds = ds.shuffle(len(x), seed=451)
    opciones = tf.data.Options()
    opciones.threading.private_threadpool_size = 1
    return ds.batch(32).with_options(opciones)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--origen", type=Path, default=ROOT / "datos/cwru_original")
    args = parser.parse_args()
    datos = ROOT / "datos/final"
    salida = ROOT / "resultados/final"
    modelos = ROOT / "modelos"
    for ruta in (datos, salida, modelos):
        ruta.mkdir(parents=True, exist_ok=True)
    tabla = preparar(args.origen, datos)
    x = {p: tabla.loc[tabla.conjunto == p, list(NOMBRES)].to_numpy() for p in PARTES}
    y = {p: np.array([CLASES.index(c) for c in tabla.loc[tabla.conjunto == p, "clase"]])
         for p in PARTES}
    scaler = StandardScaler().fit(x["train"])
    x = {p: scaler.transform(v).astype(np.float32) for p, v in x.items()}
    redes, resumen = {}, {}
    for capas in (1, 2):
        tf.keras.utils.set_random_seed(451)
        capas_red = [tf.keras.Input((len(NOMBRES),)), tf.keras.layers.Dense(32, activation="relu"),
                     tf.keras.layers.Dropout(0.2)]
        if capas == 2:
            capas_red.append(tf.keras.layers.Dense(16, activation="relu"))
        red = tf.keras.Sequential(capas_red + [tf.keras.layers.Dense(4, activation="softmax")])
        red.compile(tf.keras.optimizers.Adam(1e-3), "categorical_crossentropy", metrics=["accuracy"])
        # El presupuesto es 100 épocas. La parada temprana se habilita en la 50.
        historial = red.fit(
            conjunto(x["train"], np.eye(4, dtype=np.float32)[y["train"]], True),
            validation_data=conjunto(x["val"], np.eye(4, dtype=np.float32)[y["val"]]),
            epochs=100, callbacks=[tf.keras.callbacks.EarlyStopping(
                monitor="val_loss", patience=12, restore_best_weights=True, start_from_epoch=49)],
            verbose=0,
        )
        h = pd.DataFrame(historial.history)
        h.index += 1
        h.to_csv(salida / f"historial_{capas}.csv", index_label="epoca")
        redes[capas] = red
        val = red(x["val"], training=False).numpy()
        resumen[capas] = dict(parametros=red.count_params(), epocas=len(h),
                              val_accuracy=float(np.mean(val.argmax(axis=1) == y["val"])),
                              val_loss=float(-np.log(val[np.arange(len(val)), y["val"]]).mean()))
    elegido = min(redes, key=lambda c: (resumen[c]["val_loss"], resumen[c]["parametros"]))
    red = redes[elegido]
    red.save(modelos / "diagnostico.keras")
    pred = red(x["test"], training=False).numpy().argmax(axis=1)
    pesos = {f"peso_{i}": peso for i, peso in enumerate(red.get_weights())}
    np.savez_compressed(modelos / "diagnostico.npz", media=scaler.mean_, escala=scaler.scale_,
                        nombres=NOMBRES, clases=CLASES, **pesos)
    cm = confusion_matrix(y["test"], pred, labels=np.arange(4))
    pd.DataFrame(cm, index=CLASES, columns=CLASES).to_csv(salida / "confusion.csv",
                                                       index_label="real")
    pd.DataFrame(classification_report(y["test"], pred, labels=np.arange(4),
                 target_names=CLASES, output_dict=True, zero_division=0)).T.to_csv(salida / "metricas.csv")
    (salida / "resumen.json").write_text(json.dumps(dict(
        arquitecturas=resumen, elegido=elegido, exactitud=float(np.mean(pred == y["test"])),
        muestras={p: len(v) for p, v in y.items()}, tensorflow=tf.__version__), indent=2))
    graficar(salida, cm)


def graficar(salida, cm):
    fig, ejes = plt.subplots(2, 2, figsize=(9, 5), layout="constrained")
    for c, columna in enumerate(ejes.T, 1):
        h = pd.read_csv(salida / f"historial_{c}.csv")
        for ax, campo, titulo in zip(columna, ("loss", "accuracy"), ("Pérdida", "Exactitud")):
            ax.plot(h.epoca, h[campo], label="Entrenamiento")
            ax.plot(h.epoca, h[f"val_{campo}"], label="Validación")
            ax.set(xlabel="Época", ylabel=titulo, title=f"{c} capa(s) oculta(s)")
            ax.grid(alpha=0.2)
            ax.legend(fontsize=8)
    fig.savefig(salida / "curvas.png", dpi=170)
    etiquetas = ["Normal", "P. interna", "P. externa", "Bola"]
    fig, ax = plt.subplots(figsize=(4.8, 4.3), layout="constrained")
    ax.imshow(cm, cmap="Blues")
    ax.set(xticks=range(4), yticks=range(4), xticklabels=etiquetas,
           yticklabels=etiquetas, xlabel="Predicción", ylabel="Clase real")
    for i, j in np.ndindex(4, 4):
        ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                color="white" if cm[i, j] > cm.max() / 2 else "#142137")
    fig.savefig(salida / "confusion.png", dpi=170)


if __name__ == "__main__":
    main()
