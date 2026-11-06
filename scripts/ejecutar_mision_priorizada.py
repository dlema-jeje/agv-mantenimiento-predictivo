#!/usr/bin/env python3
"""Ejecutor ROS 2 Nav2 de la misión priorizada (AGV, punto 1.4).

Modo predeterminado: simulación de lectura, sin movimiento.
Usar --ejecutar para enviar objetivos a NavigateToPose.
"""
import argparse
import csv
import math
import sys
from pathlib import Path


def cargar_mision(raiz):
    orden_path = raiz / 'datos' / 'orden_priorizado.csv'
    objetivos_path = raiz / 'datos' / 'objetivos_navegacion.csv'
    with objetivos_path.open(newline='', encoding='utf-8-sig') as f:
        lector = csv.DictReader(f)
        requeridas = {'estacion', 'x', 'y', 'yaw', 'qx', 'qy', 'qz', 'qw'}
        if not requeridas.issubset(lector.fieldnames or []):
            raise ValueError(f'Columnas insuficientes en {objetivos_path}')
        objetivos = {}
        for fila in lector:
            nombre = f"E{int(fila['estacion'])}"
            if nombre in objetivos:
                raise ValueError(f'Estación repetida: {nombre}')
            pose = {k: float(fila[k]) for k in ('x', 'y', 'yaw', 'qx', 'qy', 'qz', 'qw')}
            if not all(math.isfinite(v) for v in pose.values()):
                raise ValueError(f'Pose no finita en {nombre}')
            norma = math.sqrt(sum(pose[k]**2 for k in ('qx', 'qy', 'qz', 'qw')))
            if abs(norma - 1.0) > 0.01:
                raise ValueError(f'Cuaternión inválido en {nombre}: norma={norma}')
            objetivos[nombre] = pose
    with orden_path.open(newline='', encoding='utf-8-sig') as f:
        lector = csv.DictReader(f)
        requeridas = {'orden', 'desde', 'estacion', 'prioridad', 'regla', 'distancia_m'}
        if not requeridas.issubset(lector.fieldnames or []):
            raise ValueError(f'Columnas insuficientes en {orden_path}')
        filas = list(lector)
    if not filas:
        raise ValueError('La misión está vacía')
    mision = []
    anterior = 'Base'
    vistos = set()
    for indice, fila in enumerate(filas, 1):
        destino = fila['estacion'].strip()
        desde = fila['desde'].strip()
        if int(fila['orden']) != indice:
            raise ValueError(f'Orden discontinuo en fila {indice}')
        if desde != anterior:
            raise ValueError(f'Continuidad incorrecta: esperado desde={anterior}, obtenido={desde}')
        if destino not in objetivos:
            raise ValueError(f'Destino desconocido: {destino}')
        if destino in vistos:
            raise ValueError(f'Estación duplicada en misión: {destino}')
        vistos.add(destino)
        distancia = float(fila['distancia_m'])
        if not math.isfinite(distancia) or distancia < 0:
            raise ValueError(f'Distancia inválida en {destino}')
        mision.append((destino, objetivos[destino], fila['prioridad'], fila['regla'], distancia))
        anterior = destino
    return mision



def guardar_registro_visita(raiz, estacion, prioridad, regla,
                           distancia, resultado, duracion,
                           posicion=None):
    import csv
    from datetime import datetime

    archivo = raiz / 'datos' / 'registros' / 'inspecciones.csv'
    archivo.parent.mkdir(parents=True, exist_ok=True)

    columnas = [
        'fecha_hora', 'estacion', 'prioridad', 'regla',
        'resultado_nav2', 'duracion_s',
        'x_final', 'y_final', 'distancia_planificada_m'
    ]

    fila = {
        'fecha_hora': datetime.now().astimezone().isoformat(timespec='seconds'),
        'estacion': estacion,
        'prioridad': prioridad,
        'regla': regla,
        'resultado_nav2': resultado,
        'duracion_s': round(duracion, 3),
        'x_final': '' if posicion is None else posicion[0],
        'y_final': '' if posicion is None else posicion[1],
        'distancia_planificada_m': distancia
    }

    nuevo = not archivo.exists() or archivo.stat().st_size == 0

    with archivo.open('a', newline='', encoding='utf-8') as f:
        escritor = csv.DictWriter(f, fieldnames=columnas)
        if nuevo:
            escritor.writeheader()
        escritor.writerow(fila)

    print(f'Registro guardado: {estacion} -> {resultado}', flush=True)



def obtener_posicion_amcl(nodo, espera_s=3.0):
    import time
    import rclpy
    from geometry_msgs.msg import PoseWithCovarianceStamped
    from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy

    posicion = {'valor': None}

    qos = QoSProfile(depth=10)
    qos.reliability = ReliabilityPolicy.RELIABLE
    qos.durability = DurabilityPolicy.VOLATILE

    def recibir(msg):
        if msg.header.frame_id == 'map':
            p = msg.pose.pose.position
            posicion['valor'] = (p.x, p.y)

    sub = nodo.create_subscription(
        PoseWithCovarianceStamped,
        '/amcl_pose',
        recibir,
        qos
    )

    try:
        limite = time.monotonic() + espera_s
        while rclpy.ok() and posicion['valor'] is None:
            if time.monotonic() >= limite:
                break
            rclpy.spin_once(nodo, timeout_sec=0.1)
        return posicion['valor']
    finally:
        nodo.destroy_subscription(sub)


def ejecutar_ros(mision, espera_servidor, tiempo_objetivo):
    import time
    import rclpy
    from rclpy.action import ActionClient
    from rclpy.node import Node
    from rclpy.duration import Duration
    from rclpy.time import Time
    from action_msgs.msg import GoalStatus
    from geometry_msgs.msg import PoseStamped
    from nav2_msgs.action import NavigateToPose

    rclpy.init()
    nodo = Node('ejecutor_mision_priorizada')
    nodo.set_parameters([])
    cliente = ActionClient(nodo, NavigateToPose, '/navigate_to_pose')
    objetivo_activo = None
    try:
        print('Esperando servidor /navigate_to_pose...', flush=True)
        if not cliente.wait_for_server(timeout_sec=espera_servidor):
            raise RuntimeError('Nav2 no ofrece /navigate_to_pose. Comprueba bt_navigator.')
        for i, (nombre, pose, prioridad, regla, distancia) in enumerate(mision, 1):
            inicio_visita = time.monotonic()

            msg = NavigateToPose.Goal()
            msg.pose = PoseStamped()
            msg.pose.header.frame_id = 'map'
            # Se usa el reloj ROS, compatible con use_sim_time.
            msg.pose.header.stamp = nodo.get_clock().now().to_msg()
            msg.pose.pose.position.x = pose['x']
            msg.pose.pose.position.y = pose['y']
            msg.pose.pose.position.z = 0.0
            msg.pose.pose.orientation.x = pose['qx']
            msg.pose.pose.orientation.y = pose['qy']
            msg.pose.pose.orientation.z = pose['qz']
            msg.pose.pose.orientation.w = pose['qw']
            print(f'[{i}/{len(mision)}] Navegando a {nombre} (P={prioridad}, Dijkstra={distancia:.3f} m)...', flush=True)
            futuro = cliente.send_goal_async(msg)
            rclpy.spin_until_future_complete(nodo, futuro, timeout_sec=espera_servidor)
            if not futuro.done():
                raise RuntimeError(f'Tiempo agotado esperando aceptación de {nombre}')
            objetivo_activo = futuro.result()
            if objetivo_activo is None or not objetivo_activo.accepted:
                raise RuntimeError(f'Nav2 rechazó {nombre}')
            resultado_futuro = objetivo_activo.get_result_async()
            # Timeout de tiempo de pared, sin depender de pausas del reloj simulado.
            import time
            limite = time.monotonic() + tiempo_objetivo
            while rclpy.ok() and not resultado_futuro.done():
                rclpy.spin_once(nodo, timeout_sec=0.5)
                if time.monotonic() >= limite:
                    print(f'Tiempo límite en {nombre}; solicitando cancelación...', flush=True)
                    cancel = objetivo_activo.cancel_goal_async()
                    rclpy.spin_until_future_complete(nodo, cancel, timeout_sec=10.0)
                    raise RuntimeError(f'Tiempo límite de navegación hacia {nombre}')
            if not resultado_futuro.done():
                raise RuntimeError(f'No se recibió resultado de {nombre}')
            resultado = resultado_futuro.result()
            if resultado is None or resultado.status != GoalStatus.STATUS_SUCCEEDED:
                estado = 'sin resultado' if resultado is None else str(resultado.status)
                guardar_registro_visita(
                    Path(__file__).resolve().parent.parent,
                    nombre, prioridad, regla, distancia,
                    'ABORTED' if resultado is not None and resultado.status == GoalStatus.STATUS_ABORTED else 'CANCELED' if resultado is not None and resultado.status == GoalStatus.STATUS_CANCELED else 'SIN_RESULTADO',
                    time.monotonic() - inicio_visita
                )
                raise RuntimeError(f'Navegación a {nombre} no exitosa (status={estado}). Misión detenida.')
            print(f'  OK: {nombre} alcanzada.', flush=True)
            guardar_registro_visita(
                Path(__file__).resolve().parent.parent,
                nombre, prioridad, regla, distancia,
                'SUCCEEDED',
                time.monotonic() - inicio_visita,
                obtener_posicion_amcl(nodo)
            )

            objetivo_activo = None
        print('MISIÓN COMPLETADA: todas las estaciones visitadas.', flush=True)
    except KeyboardInterrupt:
        print('\nInterrupción: solicitando cancelación del objetivo activo...', flush=True)
        if objetivo_activo is not None and objetivo_activo.accepted:
            futuro = objetivo_activo.cancel_goal_async()
            rclpy.spin_until_future_complete(nodo, futuro, timeout_sec=10.0)
        raise
    finally:
        cliente.destroy()
        nodo.destroy_node()
        rclpy.shutdown()


def main():
    parser = argparse.ArgumentParser(description='Misión priorizada de inspección, Nav2 ROS 2 Humble')
    parser.add_argument('--raiz', type=Path, default=Path.home() / 'agv_predictivo')
    parser.add_argument('--ejecutar', action='store_true', help='Permite mover el robot (sin este argumento solo valida CSV)')
    parser.add_argument('--espera-servidor', type=float, default=20.0)
    parser.add_argument('--tiempo-objetivo', type=float, default=180.0, help='Máximo por estación, segundos de pared')
    args = parser.parse_args()
    try:
        mision = cargar_mision(args.raiz)
        print('MISIÓN PRIORIZADA:')
        for i, (nombre, pose, prioridad, regla, distancia) in enumerate(mision, 1):
            print(f" {i}. {nombre}: x={pose['x']:.4f}, y={pose['y']:.4f}, P={prioridad}, {regla}, D={distancia:.3f} m")
        print(f'Distancia Dijkstra acumulada sin retorno: {sum(item[4] for item in mision):.3f} m')
        if not args.ejecutar:
            print('VALIDACIÓN COMPLETADA. No se ha enviado ningún objetivo a Nav2.')
            print('Para mover el robot deliberadamente, añade --ejecutar.')
            return 0
        ejecutar_ros(mision, args.espera_servidor, args.tiempo_objetivo)
        return 0
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
