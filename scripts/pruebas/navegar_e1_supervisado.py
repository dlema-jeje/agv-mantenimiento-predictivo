import math
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

import rclpy
from rclpy.action import ActionClient
from rclpy.action.client import GoalStatus
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.time import Time

from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from tf2_ros import Buffer, TransformListener, TransformException


GX, GY = 0.75, -1.40
MAX_TIEMPO = 120.0
MAX_SIN_PROGRESO = 45.0
PROGRESO_MINIMO = 0.05
PROGRESO_ANGULAR_MINIMO = 0.10


class PruebaE1(Node):
    def __init__(self):
        super().__init__("prueba_e1_supervisada")
        self.set_parameters([Parameter("use_sim_time", value=True)])
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.nav = ActionClient(self, NavigateToPose, "/navigate_to_pose")

    def posicion(self):
        tf = self.tf_buffer.lookup_transform(
            "map", "base_footprint", Time()
        )
        return tf.transform.translation.x, tf.transform.translation.y

    def objetivo(self):
        p = PoseStamped()
        p.header.frame_id = "map"
        p.header.stamp = self.get_clock().now().to_msg()
        p.pose.position.x = GX
        p.pose.position.y = GY
        p.pose.orientation.w = 1.0
        return p


def esperar(executor, futuro, segundos):
    limite = time.monotonic() + segundos
    while rclpy.ok() and not futuro.done():
        if time.monotonic() >= limite:
            raise TimeoutError("Tiempo de espera agotado")
        executor.spin_once(timeout_sec=0.1)
    return futuro.result()


def posicion_gazebo():
    try:
        salida = subprocess.check_output(
            ["gz", "model", "-m", "agv_waffle", "-i"],
            text=True,
            timeout=5
        )
        bloque = salida.split("pose {", 1)[1]
        bloque = bloque.split("joint {", 1)[0]
        x = float(re.search(r"\bx:\s*([-\d.eE+]+)", bloque).group(1))
        y = float(re.search(r"\by:\s*([-\d.eE+]+)", bloque).group(1))
        return x, y
    except Exception:
        return None


def registrar(resultado, duracion, tf_final, gz_final):
    ruta = Path("datos/registros/navegacion_e1.csv")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not ruta.exists()

    import csv
    with ruta.open("a", newline="") as archivo:
        escritor = csv.writer(archivo)
        if nuevo:
            escritor.writerow([
                "fecha", "resultado", "duracion_s",
                "tf_x", "tf_y", "gazebo_x", "gazebo_y"
            ])
        escritor.writerow([
            datetime.now().isoformat(),
            resultado,
            round(duracion, 2),
            *(tf_final if tf_final else ("", "")),
            *(gz_final if gz_final else ("", ""))
        ])


def main():
    rclpy.init()
    nodo = PruebaE1()
    executor = SingleThreadedExecutor()
    executor.add_node(nodo)

    handle = None
    resultado = "NO_INICIADO"
    inicio = time.monotonic()

    try:
        print("Esperando TF2...", flush=True)
        limite = time.monotonic() + 20

        while time.monotonic() < limite:
            executor.spin_once(timeout_sec=0.1)
            try:
                x, y = nodo.posicion()
                break
            except TransformException:
                pass
        else:
            raise RuntimeError("TF2 no disponible")

        print(f"Posición inicial TF2: ({x:.3f}, {y:.3f})")

        if not nodo.nav.wait_for_server(timeout_sec=10):
            raise RuntimeError("NavigateToPose no disponible")

        print("OBJETIVO: E1 (0.750, -1.400, 0°)")
        print("MAMDANI: DESACTIVADO")
        print("Enviando objetivo Nav2...", flush=True)

        goal = NavigateToPose.Goal()
        goal.pose = nodo.objetivo()

        handle = esperar(
            executor, nodo.nav.send_goal_async(goal), 10
        )

        if not handle.accepted:
            resultado = "RECHAZADO"
            return

        inicio = time.monotonic()
        futuro = handle.get_result_async()
        mejor_distancia = math.hypot(GX - x, GY - y)
        ultimo_progreso = inicio
        ultimo_reporte = inicio

        # Referencia angular para detectar progreso en los giros.
        mejor_error_angular = None

        def error_angular_actual():
            tf = nodo.tf_buffer.lookup_transform(
                "map", "base_footprint", Time()
            )
            q = tf.transform.rotation
            yaw = math.atan2(
                2.0 * (q.w * q.z + q.x * q.y),
                1.0 - 2.0 * (q.y * q.y + q.z * q.z)
            )
            return abs(math.atan2(math.sin(yaw), math.cos(yaw)))

        while not futuro.done():
            executor.spin_once(timeout_sec=0.1)
            ahora = time.monotonic()

            try:
                x, y = nodo.posicion()
                distancia = math.hypot(GX - x, GY - y)

                if distancia <= mejor_distancia - PROGRESO_MINIMO:
                    mejor_distancia = distancia
                    ultimo_progreso = ahora

                error_angular = error_angular_actual()

                if mejor_error_angular is None:
                    mejor_error_angular = error_angular

                elif (
                    error_angular <=
                    mejor_error_angular - PROGRESO_ANGULAR_MINIMO
                ):
                    mejor_error_angular = error_angular
                    ultimo_progreso = ahora

                if ahora - ultimo_reporte >= 5:
                    print(
                        f"Tiempo: {ahora-inicio:.1f}s | "
                        f"Distancia E1: {distancia:.3f}m",
                        flush=True
                    )
                    ultimo_reporte = ahora

            except TransformException:
                pass

            if ahora - inicio >= MAX_TIEMPO:
                resultado = "TIEMPO_MAXIMO"
                break

            if ahora - ultimo_progreso >= MAX_SIN_PROGRESO:
                resultado = "SIN_PROGRESO"
                break

        if futuro.done():
            estado = futuro.result().status
            if estado == GoalStatus.STATUS_SUCCEEDED:
                resultado = "NAV2_EXITO"
            elif estado == GoalStatus.STATUS_CANCELED:
                resultado = "CANCELADO"
            else:
                resultado = f"NAV2_ESTADO_{estado}"

        print(f"RESULTADO: {resultado}", flush=True)

    except KeyboardInterrupt:
        resultado = "INTERRUMPIDO"
        print("Interrupción recibida.", flush=True)

    except Exception as error:
        resultado = f"ERROR: {error}"
        print(resultado, flush=True)

    finally:
        if handle is not None and handle.accepted:
            try:
                if resultado != "NAV2_EXITO":
                    print("Solicitando cancelación...", flush=True)
                    cancelacion = handle.cancel_goal_async()
                    respuesta = esperar(executor, cancelacion, 10)
                    if respuesta.goals_canceling:
                        print("Cancelación aceptada.")
                    else:
                        print("ADVERTENCIA: cancelación no confirmada.")
            except Exception as error:
                print(f"ADVERTENCIA: error de cancelación: {error}")

        tf_final = None
        try:
            for _ in range(10):
                executor.spin_once(timeout_sec=0.1)
            tf_final = nodo.posicion()
        except Exception:
            pass

        gz_final = posicion_gazebo()
        duracion = time.monotonic() - inicio

        print(f"Posición final TF2: {tf_final}")
        print(f"Posición final Gazebo: {gz_final}")

        if tf_final and gz_final:
            discrepancia = math.hypot(
                tf_final[0] - gz_final[0],
                tf_final[1] - gz_final[1]
            )
            print(f"Discrepancia TF2-Gazebo: {discrepancia:.3f} m")

        registrar(resultado, duracion, tf_final, gz_final)
        print("Registro: datos/registros/navegacion_e1.csv")

        executor.remove_node(nodo)
        nodo.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
