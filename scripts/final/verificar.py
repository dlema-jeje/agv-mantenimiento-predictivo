"""Verificación de inferencia y tres rondas por replay, sin simulador físico."""
import argparse
import json

import numpy as np

from caracteristicas import CLASES, FS, N, extraer
from diagnostico import Diagnostico
from rondas import ASIGNACIONES, BancoPrueba, ROOT, Rondas


def verificar_caracteristicas():
    from scipy.stats import kurtosis, skew
    x = np.loadtxt(ROOT / "datos/final/paridad_ventanas.csv", delimiter=",")
    f = np.arange(N // 2 + 1) * FS / N
    p = np.abs(np.fft.fft(x / N)[:, :N//2+1])**2
    p[:, 1:-1] *= 2
    rms = np.sqrt(np.mean(x*x, axis=1))
    pico = np.max(np.abs(x), axis=1)
    referencia = np.column_stack((rms, pico, kurtosis(x, axis=1, fisher=False),
        skew(x, axis=1), np.std(x, ddof=1, axis=1), pico/rms,
        *(p[:, mascara].sum(axis=1) for mascara in (f < 1000,
          (f >= 1000) & (f < 3000), f >= 3000))))
    porcentaje = 100 * abs(extraer(x) - referencia) / np.maximum(abs(referencia), 1e-12)
    assert np.all(porcentaje < 0.1)
    np.savetxt(ROOT / "resultados/final/paridad_numpy_scipy_pct.csv", porcentaje, delimiter=",")
    return float(porcentaje.max())


def verificar_rondas(ros=False):
    banco = BancoPrueba(ROOT / "datos/final/ventanas_prueba.npz")
    modelo = Diagnostico(ROOT / "modelos/diagnostico.npz")
    rutas = Rondas()
    pruebas = []
    if ros:
        import time
        import uuid
        import rclpy
        from rclpy.node import Node
        from std_msgs.msg import String
        from nodos import publicar
        rclpy.init()
        nodo = Node("prueba_replay_avance3")
        pub = nodo.create_publisher(String, "/inspeccion/acople_confirmado", 10)
        recibidos = {}
        def recibir(msg):
            dato = json.loads(msg.data)
            recibidos[dato["id"]] = dato
        nodo.create_subscription(String, "/diagnostico", recibir, 10)
    try:
        for n, cambios in enumerate(ASIGNACIONES, 1):
            rutas.pendientes = set(rutas.estados)
            plan = rutas.plan()
            ronda = {"ronda": n, "plan_inicial": [p["estacion"] for p in plan],
                     "prioridad_inicial": [p["prioridad"] for p in plan], "visitas": []}
            assert plan[0]["estacion"] == ("E3", "E2", "E5")[n-1]
            while rutas.pendientes:
                estacion = rutas.plan()[0]["estacion"]
                indice, ventana = banco.leer(n, estacion)
                if ros:
                    id_visita = str(uuid.uuid4())
                    solicitud = {"id": id_visita, "ronda": n, "estacion": estacion}
                    limite = time.monotonic() + 10
                    while id_visita not in recibidos and time.monotonic() < limite:
                        publicar(pub, solicitud)
                        rclpy.spin_once(nodo, timeout_sec=0.3)
                    respuesta = recibidos.pop(id_visita)
                    assert respuesta["ventana"] == indice
                    clase, confianza = respuesta["clase"], respuesta["confianza"]
                else:
                    clase, confianza = modelo.clasificar(ventana)
                assert clase == cambios.get(estacion, "normal")
                rutas.actualizar(estacion, clase)
                ronda["visitas"].append(dict(estacion=estacion, clase=clase,
                                             indice=indice, confianza=confianza))
            pruebas.append(ronda)
    finally:
        if ros:
            nodo.destroy_node()
            rclpy.shutdown()
    assert sum(len(r["visitas"]) for r in pruebas) == 15
    return pruebas


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keras", action="store_true")
    parser.add_argument("--ros", action="store_true")
    args = parser.parse_args()
    datos = ROOT / "datos/final"
    banco = BancoPrueba(datos / "ventanas_prueba.npz")
    modelo = Diagnostico(ROOT / "modelos/diagnostico.npz")
    p = modelo.probabilidades(banco.muestras)
    exactitud = np.mean(np.asarray(CLASES)[p.argmax(axis=1)] == banco.clases)
    json_datos = dict(modo="ros2_replay" if args.ros else "replay_local",
                      exactitud=float(exactitud), rondas=verificar_rondas(args.ros))
    if not args.ros:
        json_datos["diferencia_max_scipy_pct"] = verificar_caracteristicas()
    if args.keras:
        from tensorflow.keras.models import load_model
        red = load_model(ROOT / "modelos/diagnostico.keras", compile=False)
        z = ((extraer(banco.muestras) - modelo.media) / modelo.escala).astype(np.float32)
        esperado = red(z, training=False).numpy()
        np.testing.assert_allclose(p, esperado, rtol=1e-5, atol=1e-6)
        json_datos["diferencia_max_keras"] = float(abs(p - esperado).max())
    archivo = ROOT / "resultados/final" / f"{json_datos['modo']}.json"
    archivo.write_text(json.dumps(json_datos, indent=2))
    print(archivo, "· exactitud", exactitud, "· 15 diagnósticos")


if __name__ == "__main__":
    main()
