#!/usr/bin/env python3
"""Supervisor ROS 2 de secuencia de acoplamiento.

Diagnóstico únicamente. No publica comandos de velocidad.
"""

import argparse
import json
import math
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from nav_msgs.msg import Odometry

from secuencia_acoplamiento import SecuenciaAcoplamiento


from coordinador_recuperacion import CoordinadorRecuperacion

class SupervisorSecuenciaAcople(Node):
    def __init__(self, estacion):
        super().__init__("supervisor_secuencia_acople")
        self.estacion = estacion

        self.secuencia = SecuenciaAcoplamiento(
            tiempo_confirmacion=1.0,
            max_reintentos=2,
        )

        self.coordinador_recuperacion = CoordinadorRecuperacion(
            estacion=self.estacion,
            secuencia=self.secuencia,
        )

        self.preacoplamiento = "NO_CONFIRMADO"
        self.arbitro = None
        self.nav2 = None
        self.evidencia_nav2 = None
        self.t_evidencia_nav2 = 0.0
        self.mision_activa = None
        self.t_mision_activa = 0.0
        self.odom = None
        self.errores = None
        self.t_errores = 0.0

        self.t_preacoplamiento = 0.0
        self.t_arbitro = 0.0
        self.t_nav2 = 0.0
        self.t_odom = 0.0

        self.pub_estado = self.create_publisher(
            String, "/agv/estado_secuencia_acople", 10
        )

        self.create_subscription(
            String,
            "/agv/estado_preacoplamiento",
            self.recibir_preacoplamiento,
            10,
        )
        self.create_subscription(
            String,
            "/agv/estado_arbitro",
            self.recibir_arbitro,
            10,
        )
        self.create_subscription(
            String,
            "/agv/estado_nav2",
            self.recibir_nav2,
            10,
        )
        self.create_subscription(
            Odometry,
            "/odom",
            self.recibir_odom,
            10,
        )
        self.create_subscription(
            String,
            "/agv/evidencia_mision_nav2",
            self.recibir_evidencia_nav2,
            10,
        )
        self.create_subscription(
            String,
            "/agv/mision_nav2_activa",
            self.recibir_mision_activa,
            10,
        )

        self.create_subscription(
            String,
            "/agv/errores_acoplamiento",
            self.recibir_errores,
            10,
        )

        self.pub_recuperacion = self.create_publisher(
            String,
            "/agv/solicitud_recuperacion",
            10,
        )
        self._recuperacion_publicada = False

        self.create_timer(0.2, self.evaluar)

    def recibir_preacoplamiento(self, msg):
        self.preacoplamiento = msg.data.strip()
        self.t_preacoplamiento = time.monotonic()

    def recibir_arbitro(self, msg):
        self.arbitro = msg.data.strip()
        self.t_arbitro = time.monotonic()

    def recibir_nav2(self, msg):
        self.nav2 = msg.data.strip()
        self.t_nav2 = time.monotonic()

    def recibir_odom(self, msg):
        self.odom = msg
        self.t_odom = time.monotonic()

    def recibir_mision_activa(self, msg):
        self.mision_activa = None
        self.evidencia_nav2 = None
        self.t_mision_activa = time.monotonic()

        try:
            datos = json.loads(msg.data)

            if not isinstance(datos, dict):
                return

            if datos.get("estacion") != self.estacion:
                return

            if datos.get("estado") != "NO_CONFIRMADO":
                return

            identificador = datos.get("mision_id")

            if not isinstance(identificador, str):
                return

            import re
            if re.fullmatch(r"[A-Za-z0-9_-]{8,64}", identificador) is None:
                return

            self.mision_activa = datos

        except (ValueError, TypeError):
            return

    def recibir_evidencia_nav2(self, msg):
        self.t_evidencia_nav2 = time.monotonic()
        self.evidencia_nav2 = None

        try:
            datos = json.loads(msg.data)

            if not isinstance(datos, dict):
                return

            if datos.get("estacion") != self.estacion:
                return

            identificador = datos.get("mision_id")
            if not isinstance(identificador, str):
                return

            if datos.get("estado") != "FINALIZADO":
                return

            # La coincidencia de estación no demuestra que
            # esta misión sea la actualmente autorizada.
            # Se conserva la evidencia, pero no se autoriza.
            self.evidencia_nav2 = datos

        except (ValueError, TypeError):
            return

    def recibir_errores(self, msg):
        self.t_errores = time.monotonic()
        self.errores = None

        try:
            datos = json.loads(msg.data)

            if not isinstance(datos, dict):
                return

            if datos.get("valido") is not True:
                return

            distancia = datos.get("error_distancia_m")
            angular = datos.get("error_angular_rad")
            lateral = datos.get("error_lateral_m")
            estacion = datos.get("estacion")

            valores = (distancia, angular, lateral)

            if not all(
                isinstance(v, (int, float))
                and not isinstance(v, bool)
                and math.isfinite(v)
                for v in valores
            ):
                return

            if estacion != self.estacion:
                return

            self.errores = {
                "distancia": distancia,
                "angular": angular,
                "lateral": lateral,
                "estacion": estacion,
            }

        except (ValueError, TypeError, KeyError):
            return

    def fresco(self, instante, ahora):
        return instante > 0 and 0 <= ahora - instante <= 0.5

    def publicar(self, estado, motivo):
        mensaje = String()
        mensaje.data = f"{estado} | {motivo}"
        self.pub_estado.publish(mensaje)

    def evaluar(self):
        ahora = time.monotonic()

        seguridad = (
            self.fresco(self.t_arbitro, ahora)
            and self.arbitro == "STOP"
            and self.fresco(self.t_odom, ahora)
            and self.odom is not None
        )

        if self.secuencia.estado == "ESPERANDO_PREACOPLE":
            apto = (
                seguridad
                and self.fresco(self.t_preacoplamiento, ahora)
                and self.preacoplamiento == "POSE_APTA"
                and self.fresco(self.t_nav2, ahora)
                and self.nav2 == "FINALIZADO"
                and self.mision_activa is not None
                and self.evidencia_nav2 is not None
                # La identidad persiste durante el intento.
                # Solo la evidencia de finalización exige frescura.
                and self.t_mision_activa > 0.0
                and self.t_evidencia_nav2 > 0.0
                and self.t_evidencia_nav2 >= self.t_mision_activa
                and (
                    self.mision_activa["mision_id"]
                    == self.evidencia_nav2["mision_id"]
                )
                and self.evidencia_nav2["estado"] == "FINALIZADO"
            )

            # Sin autorización para mover el robot, no se inicia
            # una secuencia operativa de acoplamiento.
            self.publicar(
                "ESPERANDO_PREACOPLE",
                "POSE_APTA_DIAGNOSTICA" if apto
                else "PREACOPLAMIENTO_NO_CONFIRMADO",
            )
            return

        if self.secuencia.estado == "RECUPERACION":
            solicitud = (
                self.coordinador_recuperacion.retorno_pendiente
            )

            if solicitud is not None:
                if not self._recuperacion_publicada:
                    import json
                    mensaje = String()
                    mensaje.data = json.dumps({
                        "estacion": solicitud.estacion,
                        "mision_id": solicitud.mision_id,
                        "intento": solicitud.intento,
                        "estado": solicitud.estado,
                        "ejecucion_autorizada": False,
                    })
                    self.pub_recuperacion.publish(mensaje)
                    self._recuperacion_publicada = True

            self.publicar(
                "RECUPERACION",
                "RETORNO_PENDIENTE_SIN_AUTORIZACION",
            )
            return

        if self.secuencia.estado == "ACOPLE_DIFUSO":
            errores_validos = (
                self.errores is not None
                and self.fresco(self.t_errores, ahora)
            )

            resultado = self.secuencia.actualizar(
                error_distancia=(
                    self.errores["distancia"]
                    if errores_validos else float("nan")
                ),
                error_angular=(
                    self.errores["angular"]
                    if errores_validos else float("nan")
                ),
                sensores_validos=errores_validos,
                seguridad_confirmada=seguridad,
                ahora=ahora,
            )

            self.publicar(resultado.estado, resultado.motivo)
            return

        self.publicar(
            self.secuencia.estado,
            "SIN_AUTORIZACION_DE_MOVIMIENTO",
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--estacion",
        choices=["E1", "E2", "E3", "E4", "E5"],
        required=True,
    )
    args = parser.parse_args()

    rclpy.init()
    nodo = SupervisorSecuenciaAcople(args.estacion)

    try:
        rclpy.spin(nodo)
    finally:
        nodo.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
