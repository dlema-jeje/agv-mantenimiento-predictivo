"""Inferencia NumPy con los mismos pesos y normalización exportados de Keras."""
import numpy as np

from caracteristicas import CLASES, NOMBRES, extraer


class Diagnostico:
    def __init__(self, archivo):
        with np.load(archivo, allow_pickle=False) as datos:
            if tuple(datos["clases"]) != CLASES or tuple(datos["nombres"]) != NOMBRES:
                raise ValueError("El modelo no respeta el contrato de características y clases.")
            self.media, self.escala = datos["media"], datos["escala"]
            self.pesos = [datos[k] for k in sorted(datos.files) if k.startswith("peso_")]

    def probabilidades(self, muestras):
        z = ((extraer(muestras) - self.media) / self.escala).astype(np.float32)
        for i in range(0, len(self.pesos), 2):
            z = z @ self.pesos[i] + self.pesos[i + 1]
            if i + 2 < len(self.pesos):
                z = np.maximum(z, 0)
        exp = np.exp(z - z.max(axis=-1, keepdims=True))
        return exp / exp.sum(axis=-1, keepdims=True)

    def clasificar(self, muestras):
        p = self.probabilidades(muestras)
        i = int(p.argmax())
        return CLASES[i], float(p[i])
