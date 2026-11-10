#!/usr/bin/env python3
from adaptador_acople_seguro import AdaptadorAcopleSeguro
"""Nodo de acoplamiento difuso del AGV - Avance 2.

Modo por defecto: diagnóstico, sin movimiento.
La ejecución física requiere un supervisor de seguridad externo.
"""

import argparse
import csv
from datetime import datetime
import math
import sys
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.time import Time
from rclpy.duration import Duration
from tf2_ros import Buffer, TransformListener, TransformException
from rclpy.qos import (
    QoSProfile,
    ReliabilityPolicy,
    DurabilityPolicy,
    HistoryPolicy,
)
from geometry_msgs.msg import Twist, PoseWithCovarianceStamped

sys.path.insert(0, str(Path(__file__).resolve().parent))
from controlador_agv_calibrado import crear_simulacion
from monitor_seguridad import distancia_frontal
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan, Range
from supervisor_geometrico import (
    calcular_errores,
    evaluar_preacople,
    evaluar_acople,
)


def normalizar_angulo(angulo):
    return math.atan2(math.sin(angulo), math.cos(angulo))


class NodoAcoplamiento(Node):

    def __init__(self, args):
        super().__init__("nodo_acoplamiento_difuso")

        self.objetivo_x = args.x
        self.objetivo_y = args.y
        self.objetivo_yaw = math.radians(args.yaw)

        self.distancia_deseada = args.distancia
        self.tolerancia_distancia = args.tolerancia
        self.tolerancia_angular = math.radians(args.tolerancia_angular)

        self.tiempo_estable = args.tiempo_estable
        self.tiempo_maximo = args.tiempo_maximo

        self.adaptador_seguro = AdaptadorAcopleSeguro()

        self.velocidad_odom = None
        self.tiempo_velocidad_odom = None
        self.sub_velocidad_odom = self.create_subscription(
            Odometry,
            "/odom",
            self.recibir_velocidad_odom,
            10,
        )
        self.ejecutar = False
        if args.ejecutar:
            self.get_logger().warning(
                "EJECUCION BLOQUEADA: integración aún en validación"
            )

        self.simulacion = crear_simulacion()

        self.ultimo_scan = None
        self.instante_scan = None
        self.sub_scan = self.create_subscription(
            LaserScan, "/scan", self.recibir_scan, 10
        )

        # Sensores frontales virtuales.
        self.alpha_rangos = 0.3
        self.rango_fi = None
        self.rango_fd = None
        self.tiempo_fi = None
        self.tiempo_fd = None

        self.sub_rango_fi = self.create_subscription(
            Range, "/rango_fi", self.recibir_rango_fi, 10
        )
        self.sub_rango_fd = self.create_subscription(
            Range, "/rango_fd", self.recibir_rango_fd, 10
        )

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.pose = None
        self.ultima_pose = None

        self.inicio = time.monotonic()
        self.inicio_estable = None
        self.finalizado = False
        self.estado_final = "EN_PROCESO"
        self.ultimo_motivo = "SIN_EVALUAR"
        self.archivo_registro = (
            Path(__file__).resolve().parents[2]
            / "datos/registros/acoplamientos.csv"
        )
        self.registro_guardado = False
        self.ultimos_errores = None

        qos_amcl = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )

        self.sub_pose = self.create_subscription(
            PoseWithCovarianceStamped,
            "/amcl_pose",
            self.recibir_pose,
            qos_amcl
        )

        self.pub_vel = self.create_publisher(
            Twist,
            "/cmd_vel_mamdani",
            10
        )

        self.timer = self.create_timer(0.2, self.controlar)

        self.get_logger().info(
            f"Objetivo: ({self.objetivo_x:.3f}, "
            f"{self.objetivo_y:.3f}), "
            f"yaw={args.yaw:.2f} grados"
        )

        self.get_logger().info(
            "MODO EJECUCION" if self.ejecutar
            else "MODO DIAGNOSTICO - SIN MOVIMIENTO"
        )

    def recibir_scan(self, msg):
        self.ultimo_scan = msg
        self.instante_scan = time.monotonic()

    def recibir_rango_fi(self, msg):
        self._actualizar_rango("fi", msg)

    def recibir_rango_fd(self, msg):
        self._actualizar_rango("fd", msg)

    def _actualizar_rango(self, lado, msg):
        valor = float(msg.range)
        ahora = time.monotonic()

        if (
            not math.isfinite(valor)
            or valor < 0.0
            or valor > 1.2
        ):
            setattr(self, f"rango_{lado}", None)
            setattr(self, f"tiempo_{lado}", None)
            return

        anterior = getattr(self, f"rango_{lado}")

        filtrado = (
            valor if anterior is None
            else self.alpha_rangos * valor
            + (1.0 - self.alpha_rangos) * anterior
        )

        setattr(self, f"rango_{lado}", filtrado)
        setattr(self, f"tiempo_{lado}", ahora)

    def calcular_errores_sensores(self):
        ahora = time.monotonic()

        if self.rango_fi is None or self.rango_fd is None:
            return None, "RANGOS_INVALIDOS"

        if self.tiempo_fi is None or self.tiempo_fd is None:
            return None, "RANGOS_SIN_TIEMPO"

        if (
            ahora - self.tiempo_fi > 0.5
            or ahora - self.tiempo_fd > 0.5
        ):
            return None, "RANGOS_DESACTUALIZADOS"

        if abs(self.tiempo_fi - self.tiempo_fd) > 0.15:
            return None, "RANGOS_NO_SINCRONIZADOS"

        ed = (
            (self.rango_fi + self.rango_fd) / 2.0
            - self.distancia_deseada
        )

        et = math.degrees(
            math.atan(
                (self.rango_fi - self.rango_fd) / 0.20
            )
        )

        return (ed, et), "RANGOS_APTOS"

    def comprobar_lidar(self):
        if self.ultimo_scan is None or self.instante_scan is None:
            return False, "SIN_LIDAR"

        if time.monotonic() - self.instante_scan > 1.0:
            return False, "LIDAR_DESACTUALIZADO"

        distancia = distancia_frontal(self.ultimo_scan)

        if distancia is None:
            return False, "SIN_LECTURAS_FRONTALES_VALIDAS"

        if distancia < 0.30:
            return False, f"OBSTACULO_FRONTAL_{distancia:.3f}m"

        return True, "LIDAR_APTO"

    def recibir_pose(self, msg):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation

        yaw = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y),
            1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        )

        self.pose = (p.x, p.y, yaw)
        self.ultima_pose = time.monotonic()

    def actualizar_pose_tf(self):
        try:
            transformacion = self.tf_buffer.lookup_transform(
                "map",
                "base_footprint",
                Time(),
                timeout=Duration(seconds=0.05),
            )

            p = transformacion.transform.translation
            q = transformacion.transform.rotation

            yaw = math.atan2(
                2.0 * (q.w * q.z + q.x * q.y),
                1.0 - 2.0 * (q.y * q.y + q.z * q.z),
            )

            self.pose = (p.x, p.y, yaw)
            self.ultima_pose = time.monotonic()
            return True

        except TransformException as exc:
            self.get_logger().warning(
                f"No se pudo consultar TF: {exc}"
            )
            return False

    def detener(self):
        if self.ejecutar:
            self.pub_vel.publish(Twist())

    def guardar_registro(self):
        if self.registro_guardado:
            return

        archivo = self.archivo_registro
        archivo.parent.mkdir(parents=True, exist_ok=True)

        errores = self.ultimos_errores or {}
        columnas = [
            "fecha_hora", "modo", "objetivo_x", "objetivo_y",
            "objetivo_yaw_deg", "resultado", "ultimo_motivo",
            "duracion_s", "error_longitudinal_m",
            "error_lateral_m", "error_angular_deg"
        ]

        fila = {
            "fecha_hora": datetime.now().astimezone().isoformat(
                timespec="seconds"
            ),
            "modo": "EJECUCION" if self.ejecutar else "DIAGNOSTICO",
            "objetivo_x": self.objetivo_x,
            "objetivo_y": self.objetivo_y,
            "objetivo_yaw_deg": math.degrees(self.objetivo_yaw),
            "resultado": self.estado_final,
            "ultimo_motivo": self.ultimo_motivo,
            "duracion_s": round(time.monotonic() - self.inicio, 3),
            "error_longitudinal_m": errores.get("longitudinal", ""),
            "error_lateral_m": errores.get("lateral", ""),
            "error_angular_deg": (
                math.degrees(errores["angular"])
                if "angular" in errores else ""
            ),
        }

        nuevo = not archivo.exists() or archivo.stat().st_size == 0

        with archivo.open("a", newline="", encoding="utf-8") as f:
            escritor = csv.DictWriter(f, fieldnames=columnas)
            if nuevo:
                escritor.writeheader()
            escritor.writerow(fila)

        self.registro_guardado = True
        self.get_logger().info(f"Registro guardado: {archivo}")

    def terminar(self, mensaje):
        self.detener()
        self.estado_final = mensaje
        self.finalizado = True
        self.guardar_registro()
        self.get_logger().info(mensaje)

    def recibir_velocidad_odom(self, msg):
        v = float(msg.twist.twist.linear.x)
        w = float(msg.twist.twist.angular.z)

        if math.isfinite(v) and math.isfinite(w):
            self.velocidad_odom = (v, w)
            self.tiempo_velocidad_odom = time.monotonic()
        else:
            self.velocidad_odom = None
            self.tiempo_velocidad_odom = None

    def robot_realmente_detenido(self):
        if self.velocidad_odom is None:
            return False

        if self.tiempo_velocidad_odom is None:
            return False

        if time.monotonic() - self.tiempo_velocidad_odom > 0.5:
            return False

        v, w = self.velocidad_odom

        return abs(v) <= 0.01 and abs(w) <= 0.02

    def notificar_fallo_supervisor(self, motivo, ahora):
        if self.adaptador_seguro.maquina.estado.value != "ACOPLE_DIFUSO":
            return

        decision = self.adaptador_seguro.actualizar(
            ed=float("nan"),
            et_deg=float("nan"),
            sensores_validos=False,
            seguridad_apta=False,
            v=0.0,
            w=0.0,
            ahora=ahora,
        )
        self.get_logger().warning(
            f"SUPERVISOR: {motivo} | ESTADO={decision.estado}"
        )

    def controlar(self):
        if self.finalizado:
            return

        ahora = time.monotonic()

        # La pose de control procede de TF2.
        # No reutilizar una pose anterior si TF no está disponible.
        if not self.actualizar_pose_tf():
            self.inicio_estable = None
            self.notificar_fallo_supervisor("TF_NO_DISPONIBLE", ahora)
            self.detener()
            return

        if ahora - self.inicio > self.tiempo_maximo:
            self.terminar("TIEMPO MAXIMO ALCANZADO")
            return

        if self.pose is None:
            self.get_logger().info("Esperando AMCL...")
            return

        if ahora - self.ultima_pose > 1.0:
            self.inicio_estable = None
            self.detener()
            self.get_logger().warning("AMCL desactualizado")
            return

        x, y, yaw = self.pose

        seguro, motivo_seguridad = self.comprobar_lidar()
        if not seguro:
            self.inicio_estable = None
            self.notificar_fallo_supervisor(motivo_seguridad, ahora)
            self.detener()
            self.get_logger().warning(
                f"ACOPLAMIENTO BLOQUEADO: {motivo_seguridad}"
            )
            return

        errores = calcular_errores(
            x, y, yaw,
            self.objetivo_x,
            self.objetivo_y,
            self.objetivo_yaw,
        )

        self.ultimos_errores = errores
        # Autorizar el preacoplamiento una sola vez.
        if self.adaptador_seguro.maquina.estado.value == "PREACOPLE":
            apto, motivo = evaluar_preacople(errores)
            entradas_previas, _ = self.calcular_errores_sensores()

            decision = self.adaptador_seguro.autorizar(
                pose_apta=apto,
                robot_detenido=self.robot_realmente_detenido(),
                sensores_validos=entradas_previas is not None,
                ahora=ahora,
            )

            if decision.estado != "ACOPLE_DIFUSO":
                self.detener()
                self.get_logger().warning(
                    f"PREACOPLE BLOQUEADO: {decision.motivo}"
                )
                return

        # Control sensorial supervisado por máquina de estados.
        entradas, estado_rangos = self.calcular_errores_sensores()

        if entradas is None:
            decision = self.adaptador_seguro.actualizar(
                ed=float("nan"),
                et_deg=float("nan"),
                sensores_validos=False,
                seguridad_apta=False,
                v=0.0,
                w=0.0,
                ahora=ahora,
            )
            self.detener()
            self.get_logger().warning(
                f"ESTADO={decision.estado} | {decision.motivo}"
            )
            return

        ed, et = entradas

        if not (-0.05 <= ed <= 0.45 and -20.0 <= et <= 20.0):
            decision = self.adaptador_seguro.actualizar(
                ed=ed,
                et_deg=et,
                sensores_validos=True,
                seguridad_apta=False,
                v=0.0,
                w=0.0,
                ahora=ahora,
            )
            self.detener()
            self.get_logger().warning(
                f"ESTADO={decision.estado} | ENTRADAS_FUERA_UNIVERSO"
            )
            return

        try:
            self.simulacion.input["ed"] = ed
            self.simulacion.input["et"] = et
            self.simulacion.compute()

            v = float(self.simulacion.output["v"])
            w = float(self.simulacion.output["w"])
        except Exception as exc:
            self.detener()
            self.get_logger().error(f"ERROR_DIFUSO: {exc}")
            return

        decision = self.adaptador_seguro.actualizar(
            ed=ed,
            et_deg=et,
            sensores_validos=True,
            seguridad_apta=True,
            v=v,
            w=w,
            ahora=ahora,
        )

        if decision.estado == "COMPLETADO":
            self.terminar("ACOPLAMIENTO COMPLETADO")
            return

        if decision.estado != "ACOPLE_DIFUSO":
            self.detener()
            self.get_logger().warning(
                f"ESTADO={decision.estado} | {decision.motivo}"
            )
            return

        comando = Twist()
        comando.linear.x = decision.v
        comando.angular.z = decision.w

        # Diagnóstico obligatorio hasta validar seguridad integral.
        self.get_logger().info(
            f"MAMDANI DIAGNOSTICO | "
            f"FI={self.rango_fi:.4f} "
            f"FD={self.rango_fd:.4f} "
            f"ed={ed:+.4f} m "
            f"et={et:+.2f} deg "
            f"v={comando.linear.x:+.4f} m/s "
            f"w={comando.angular.z:+.4f} rad/s "
            f"| SIN PUBLICAR MOVIMIENTO"
        )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--x", type=float, required=True)
    parser.add_argument("--y", type=float, required=True)

    parser.add_argument("--yaw", type=float, default=0.0)

    parser.add_argument(
        "--distancia", type=float, default=0.0
    )

    parser.add_argument(
        "--tolerancia", type=float, default=0.01
    )

    parser.add_argument(
        "--tolerancia-angular", type=float, default=5.0
    )

    parser.add_argument(
        "--tiempo-estable", type=float, default=1.0
    )

    parser.add_argument(
        "--tiempo-maximo", type=float, default=60.0
    )

    parser.add_argument(
        "--ejecutar", action="store_true"
    )

    args = parser.parse_args()

    if (
        args.distancia < 0
        or args.tolerancia <= 0
        or not 0 < args.tolerancia_angular <= 180
        or args.tiempo_estable <= 0
        or args.tiempo_maximo <= 0
    ):
        parser.error("Parametros de tolerancia o tiempo invalidos")

    # Bloqueo preventivo de movimiento hasta integrar
    # supervisor, comprobación de obstáculos y exclusividad /cmd_vel.
    if args.ejecutar:
        parser.error(
            "Ejecucion bloqueada: falta integrar el supervisor "
            "y las protecciones de seguridad."
        )

    rclpy.init()
    nodo = NodoAcoplamiento(args)

    try:
        rclpy.spin(nodo)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        nodo.detener()
        nodo.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
