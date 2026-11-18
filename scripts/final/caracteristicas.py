"""Contrato de características compartido por entrenamiento e inferencia."""
import numpy as np

CLASES = ("normal", "inner_race", "outer_race", "ball")
NOMBRES = ("rms", "pico", "curtosis", "asimetria", "std", "cresta",
           "energia_0_1k", "energia_1_3k", "energia_3_6k")
N = 2048
FS = 12000


def extraer(ventanas):
    x = np.asarray(ventanas, dtype=np.float64)
    if x.ndim not in (1, 2) or x.shape[-1] != N or not np.isfinite(x).all():
        raise ValueError("Se requieren ventanas finitas de 2048 muestras.")
    centrada = x - x.mean(axis=-1, keepdims=True)
    var = np.mean(centrada**2, axis=-1)
    if np.any(var <= 0):
        raise ValueError("La ventana tiene varianza nula.")
    rms = np.sqrt(np.mean(x**2, axis=-1))
    pico = np.max(np.abs(x), axis=-1)
    potencia = np.abs(np.fft.rfft(x, axis=-1))**2 / N**2
    potencia[..., 1:-1] *= 2
    f = np.fft.rfftfreq(N, 1 / FS)
    return np.stack((
        rms, pico, np.mean(centrada**4, axis=-1) / var**2,
        np.mean(centrada**3, axis=-1) / var**1.5, np.sqrt(var * N / (N - 1)),
        pico / rms, potencia[..., f < 1000].sum(axis=-1),
        potencia[..., (f >= 1000) & (f < 3000)].sum(axis=-1),
        potencia[..., f >= 3000].sum(axis=-1),
    ), axis=-1)
