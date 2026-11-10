import math
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.action.client import GoalStatus
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.time import Time

from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import ComputePathToPose
from nav2_msgs.srv import GetCostmap
from tf2_ros import Buffer, TransformListener, TransformException


RADIO_ROBOT = 0.22
MARGEN = 0.05
RADIO_COMPROBACION = RADIO_ROBOT + MARGEN
PASO_MUESTREO = 0.025


class Validador(Node):
    def __init__(self):
        super().__init__("validador_costmap_e1")
        self.set_parameters([Parameter("use_sim_time", value=True)])
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)

        self.planificador = ActionClient(
            self, ComputePathToPose, "/compute_path_to_pose"
        )
        self.costmap_cliente = self.create_client(
            GetCostmap, "/global_costmap/get_costmap"
        )

    def pose(self, x, y):
        p = PoseStamped()
        p.header.frame_id = "map"
        p.header.stamp = self.get_clock().now().to_msg()
        p.pose.position.x = x
        p.pose.position.y = y
        p.pose.orientation.w = 1.0
        return p


def esperar(executor, futuro, segundos):
    limite = time.monotonic() + segundos
    while rclpy.ok() and not futuro.done():
        if time.monotonic() >= limite:
            raise TimeoutError("Operación ROS excedió el tiempo permitido")
        executor.spin_once(timeout_sec=0.1)
    return futuro.result()


def comprobar_huella(mapa, x, y):
    meta = mapa.metadata
    res = meta.resolution
    ancho = meta.size_x
    alto = meta.size_y
    ox = meta.origin.position.x
    oy = meta.origin.position.y

    # Se comprueban todas las celdas que pueden tocar
    # el círculo del robot, con margen de seguridad.
    ix_min = math.floor((x - RADIO_COMPROBACION - ox) / res)
    ix_max = math.floor((x + RADIO_COMPROBACION - ox) / res)
    iy_min = math.floor((y - RADIO_COMPROBACION - oy) / res)
    iy_max = math.floor((y + RADIO_COMPROBACION - oy) / res)

    max_coste = 0

    for iy in range(iy_min, iy_max + 1):
        for ix in range(ix_min, ix_max + 1):
            if ix < 0 or iy < 0 or ix >= ancho or iy >= alto:
                return False, "FUERA_DEL_MAPA", 255

            # Punto de la celda más próximo al centro del robot.
            xmin = ox + ix * res
            xmax = xmin + res
            ymin = oy + iy * res
            ymax = ymin + res

            cercano_x = max(xmin, min(x, xmax))
            cercano_y = max(ymin, min(y, ymax))

            distancia = math.hypot(x - cercano_x, y - cercano_y)

            if distancia > RADIO_COMPROBACION:
                continue

            coste = int(mapa.data[iy * ancho + ix])
            max_coste = max(max_coste, coste)

            if coste == 255:
                return False, "ZONA_DESCONOCIDA", coste

            if coste >= 253:
                return False, "OBSTACULO_O_INFLACION_INSCRITA", coste

    return True, "SIN_OBSTACULO_CRITICO", max_coste


def main():
    rclpy.init()
    nodo = Validador()
    executor = SingleThreadedExecutor()
    executor.add_node(nodo)

    try:
        print("Esperando localización...", flush=True)
        tf = None
        limite = time.monotonic() + 20

        while time.monotonic() < limite:
            executor.spin_once(timeout_sec=0.1)
            try:
                tf = nodo.buffer.lookup_transform(
                    "map", "base_footprint", Time()
                )
                break
            except TransformException:
                pass

        if tf is None:
            print("RESULTADO: TF_NO_DISPONIBLE")
            return

        x = tf.transform.translation.x
        y = tf.transform.translation.y

        print(f"Inicio: ({x:.3f}, {y:.3f})")
        print("Destino: (0.750, -1.400)")

        if not nodo.planificador.wait_for_server(timeout_sec=5):
            print("RESULTADO: PLANIFICADOR_NO_DISPONIBLE")
            return

        if not nodo.costmap_cliente.wait_for_service(timeout_sec=5):
            print("RESULTADO: COSTMAP_NO_DISPONIBLE")
            return

        solicitud = nodo.costmap_cliente.call_async(GetCostmap.Request())
        respuesta_mapa = esperar(executor, solicitud, 10)
        mapa = respuesta_mapa.map

        print(
            f"Mapa: {mapa.metadata.size_x} x "
            f"{mapa.metadata.size_y}, "
            f"resolución {mapa.metadata.resolution:.3f} m"
        )

        objetivo = ComputePathToPose.Goal()
        objetivo.start = nodo.pose(x, y)
        objetivo.goal = nodo.pose(0.75, -1.40)
        objetivo.use_start = True

        handle = esperar(
            executor,
            nodo.planificador.send_goal_async(objetivo),
            10
        )

        if not handle.accepted:
            print("RESULTADO: PLAN_RECHAZADO")
            return

        resultado = esperar(
            executor, handle.get_result_async(), 20
        )

        if resultado.status != GoalStatus.STATUS_SUCCEEDED:
            print(f"RESULTADO: PLAN_FALLIDO_{resultado.status}")
            return

        puntos = resultado.result.path.poses
        if not puntos:
            print("RESULTADO: RUTA_VACIA")
            return

        # Interpolación para no dejar huecos entre puntos.
        muestras = []
        for a, b in zip(puntos, puntos[1:]):
            ax, ay = a.pose.position.x, a.pose.position.y
            bx, by = b.pose.position.x, b.pose.position.y
            n = max(1, math.ceil(math.hypot(bx-ax, by-ay) / PASO_MUESTREO))
            for k in range(n):
                t = k / n
                muestras.append((ax + t*(bx-ax), ay + t*(by-ay)))

        ultimo = puntos[-1].pose.position
        muestras.append((ultimo.x, ultimo.y))

        max_coste = 0

        for indice, (px, py) in enumerate(muestras):
            apto, motivo, coste = comprobar_huella(mapa, px, py)
            max_coste = max(max_coste, coste)

            if not apto:
                print(f"Muestra: {indice + 1}/{len(muestras)}")
                print(f"Posición: ({px:.3f}, {py:.3f})")
                print(f"Motivo: {motivo}")
                print(f"Coste: {coste}")
                print("RESULTADO: RUTA_BLOQUEADA")
                return

        print(f"Puntos originales: {len(puntos)}")
        print(f"Muestras comprobadas: {len(muestras)}")
        print(f"Coste máximo: {max_coste}")
        print("RESULTADO: RUTA_SIN_COLISION_CRITICA_EN_COSTMAP")
        print("MOVIMIENTO: NO")

    except Exception as error:
        print(f"RESULTADO: ERROR_VALIDACION: {error}")

    finally:
        executor.remove_node(nodo)
        nodo.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
