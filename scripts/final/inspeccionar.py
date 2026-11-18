"""Ejecuta el escenario final en el Waffle de Gazebo."""
import argparse
import csv
import json
import math
import time
import uuid
from pathlib import Path
import sys

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Range
from std_msgs.msg import String

from nodos import publicar
from rondas import ASIGNACIONES, ROOT, Rondas
sys.path[:0] = [str(ROOT / "scripts" / p) for p in ("difuso", "integracion")]
from controlador_agv_calibrado import crear_simulacion
from secuencia_acoplamiento import SecuenciaAcoplamiento


def angulo(valor):
    return math.atan2(math.sin(valor), math.cos(valor))


class Inspector(Node):
    def __init__(self, registro):
        super().__init__("priorizador")
        self.rondas = Rondas()
        self.registro = registro
        self.control = crear_simulacion()
        self.odom = None
        self.rangos = {}
        self.respuesta = None
        self.evento = None
        self.vel = self.create_publisher(Twist, "/cmd_vel", 10)
        self.acople = self.create_publisher(String, "/inspeccion/acople_confirmado", 10)
        self.ruta = self.create_publisher(String, "/ruta_priorizada", 10)
        self.create_subscription(Odometry, "/odom", self.recibir_odom, qos_profile_sensor_data)
        for lado in ("fi", "fd"):
            self.create_subscription(Range, f"/rango_{lado}",
                                     lambda msg, lado=lado: self.recibir_rango(msg, lado), 10)
        self.create_subscription(String, "/diagnostico", self.recibir_diagnostico, 10)
        with (ROOT / "datos/objetivos_acoplamiento.csv").open() as archivo:
            self.objetivos = {r["estacion"]: float(r["pre_y"]) for r in csv.DictReader(archivo)}

    def recibir_odom(self, msg):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        yaw = math.atan2(2 * (q.w*q.z + q.x*q.y), 1 - 2 * (q.y*q.y + q.z*q.z))
        sello = msg.header.stamp
        tiempo_sim = sello.sec + sello.nanosec * 1e-9
        self.odom = p.x, p.y, yaw, time.monotonic(), tiempo_sim

    def recibir_rango(self, msg, lado):
        valor = msg.range
        anterior = self.rangos.get(lado)
        if not msg.min_range < valor < msg.max_range:
            self.rangos.pop(lado, None)
            return
        if anterior and time.monotonic() - anterior[1] < 0.35:
            valor = 0.3 * valor + 0.7 * anterior[0]
        self.rangos[lado] = valor, time.monotonic()

    def recibir_diagnostico(self, msg):
        try:
            datos = json.loads(msg.data)
            if self.evento and all(datos[k] == v for k, v in self.evento.items()):
                self.respuesta = datos
        except (TypeError, ValueError, KeyError):
            self.get_logger().warning("Diagnóstico mal formado.")

    def avanzar_callbacks(self, espera=0.05):
        rclpy.spin_once(self, timeout_sec=espera)

    def esperar(self, listo, segundos, error):
        fin = time.monotonic() + segundos
        while rclpy.ok() and time.monotonic() < fin:
            if listo():
                return
            self.avanzar_callbacks()
        raise RuntimeError(error)

    def mover(self, v=0., w=0.):
        comando = Twist()
        comando.linear.x, comando.angular.z = float(v), float(w)
        self.vel.publish(comando)

    def pose(self):
        if self.odom is None or time.monotonic() - self.odom[3] > 0.6:
            raise RuntimeError("Odometría sin actualizar.")
        return self.odom[0] + self.offset_x, self.odom[1], self.odom[2]

    def navegar(self, destino, yaw_final=None, tolerancia=0.025):
        limite = time.monotonic() + 45
        while rclpy.ok() and time.monotonic() < limite:
            self.avanzar_callbacks()
            x, y, yaw = self.pose()
            dx, dy = destino[0] - x, destino[1] - y
            distancia = math.hypot(dx, dy)
            if distancia <= tolerancia and (yaw_final is None or abs(angulo(yaw_final-yaw)) < 0.045):
                self.mover()
                return
            giro = angulo((math.atan2(dy, dx) if distancia > tolerancia else yaw_final) - yaw)
            v = min(0.20, 1.5 * distancia) if distancia > tolerancia and abs(giro) < 0.18 else 0.
            self.mover(v, max(-0.9, min(0.9, 2.4 * giro)))
        raise RuntimeError(f"Tiempo de navegación agotado hacia {destino}")

    def retirar(self):
        limite = time.monotonic() + 32
        while rclpy.ok() and time.monotonic() < limite:
            self.avanzar_callbacks()
            x, _, yaw = self.pose()
            if x <= 0.51:
                self.mover()
                return
            # Mantener componente hacia el pasillo mientras se corrige el rumbo.
            giro = max(-0.7, min(0.7, -2.0 * yaw))
            velocidad = -0.11 if abs(yaw) < 0.55 else 0.
            self.mover(velocidad, giro)
        x, y, yaw = self.pose()
        raise RuntimeError(f"Retroceso agotado en x={x:.3f}, y={y:.3f}, yaw={yaw:.3f}.")

    def acoplar(self, estacion):
        objetivo_y = self.objetivos[estacion]
        secuencia = SecuenciaAcoplamiento()
        for intento in range(3):
            self.navegar((0.50, objetivo_y), tolerancia=0.018)
            self.navegar((0.76, objetivo_y), 0., tolerancia=0.014)
            x, y, yaw = self.pose()
            if abs(y - objetivo_y) > 0.03 or abs(yaw) > math.radians(10):
                raise RuntimeError(f"Preacople fuera de tolerancia en {estacion}")
            secuencia.iniciar(True)
            inicio_sim = self.odom[4]
            limite = time.monotonic() + 28
            while rclpy.ok() and time.monotonic() < limite:
                self.avanzar_callbacks()
                ahora = time.monotonic()
                self.pose()
                fi = self.rangos.get("fi")
                fd = self.rangos.get("fd")
                validos = fi is not None and fd is not None and ahora - min(fi[1], fd[1]) < 0.35
                ed = (fi[0]+fd[0])/2 - 0.10 if validos else math.nan
                et = math.atan((fi[0]-fd[0])/0.20) if validos else math.nan
                estado = secuencia.actualizar(error_distancia=ed, error_angular=et,
                                             sensores_validos=validos, seguridad_confirmada=True,
                                             ahora=self.odom[4])
                if estado.completado:
                    self.mover()
                    x, y, yaw = self.pose()
                    return {"ed_m": ed, "et_deg": math.degrees(et),
                            "x_m": x, "y_m": y, "yaw_deg": math.degrees(yaw),
                            "error_lateral_m": y - objetivo_y,
                            "acople_s": self.odom[4] - inicio_sim, "reintentos": intento}
                if estado.estado != "ACOPLE_DIFUSO":
                    break
                if estado.motivo == "CONFIRMANDO_TOLERANCIA":
                    self.mover()
                    continue
                self.control.input["ed"] = ed
                self.control.input["et"] = math.degrees(et)
                self.control.compute()
                self.mover(self.control.output["v"], self.control.output["w"])
            self.mover()
            if secuencia.estado == "ACOPLE_DIFUSO":
                secuencia.solicitar_recuperacion("TIEMPO_AGOTADO")
            if secuencia.estado == "FALLO":
                break
            self.retirar()
            secuencia.recuperacion_confirmada(True)
        raise RuntimeError(f"Acople fallido en {estacion} tras tres intentos")

    def guardar(self, datos):
        linea = json.dumps(datos, allow_nan=False)
        with self.registro.open("a", encoding="utf-8") as archivo:
            archivo.write(linea + "\n")
        self.get_logger().info(linea)

    def ejecutar(self):
        self.esperar(lambda: self.odom is not None and self.acople.get_subscription_count() > 0
                     and self.count_publishers("/diagnostico") > 0, 40,
                     "Se requieren odometría y nodos de diagnóstico.")
        # Gazebo puede publicar odometría desde el origen de spawn o en marco mundo.
        self.offset_x = -1.8 if abs(self.odom[0]) < 0.25 else 0.
        for ronda in range(1, len(ASIGNACIONES) + 1):
            self.rondas.pendientes = set(self.objetivos)
            plan = self.rondas.plan()
            publicar(self.ruta, {"ronda": ronda, "plan": plan})
            self.guardar({"tipo": "plan", "ronda": ronda, "plan": plan})
            while self.rondas.pendientes:
                estacion = self.rondas.plan()[0]["estacion"]
                metricas = self.acoplar(estacion)
                self.respuesta = None
                self.evento = {"id": str(uuid.uuid4()), "ronda": ronda, "estacion": estacion}
                publicar(self.acople, self.evento)
                self.esperar(lambda: self.respuesta is not None, 8,
                             f"Diagnóstico no recibido para {estacion}")
                self.rondas.actualizar(estacion, self.respuesta["clase"])
                plan = self.rondas.plan()
                publicar(self.ruta, {"ronda": ronda, "plan": plan})
                self.guardar({"tipo": "visita", **self.respuesta, **metricas, "pendientes": plan})
                self.retirar()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registro", type=Path, required=True)
    args, ros_args = parser.parse_known_args()
    args.registro.parent.mkdir(parents=True, exist_ok=True)
    args.registro.touch(exist_ok=False)
    rclpy.init(args=ros_args)
    nodo = Inspector(args.registro)
    try:
        nodo.ejecutar()
    except (RuntimeError, KeyboardInterrupt) as exc:
        nodo.guardar({"tipo": "interrupcion", "motivo": str(exc)})
        raise
    finally:
        if rclpy.ok():
            nodo.mover()
        nodo.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
