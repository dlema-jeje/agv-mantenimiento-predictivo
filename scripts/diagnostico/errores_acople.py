#!/usr/bin/env python3

import argparse
import math


def normalizar(angulo):
    return math.atan2(math.sin(angulo), math.cos(angulo))


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--x", type=float, required=True)
    parser.add_argument("--y", type=float, required=True)
    parser.add_argument("--yaw", type=float, required=True)

    parser.add_argument("--gx", type=float, required=True)
    parser.add_argument("--gy", type=float, required=True)
    parser.add_argument("--gyaw", type=float, required=True)

    args = parser.parse_args()

    yaw_objetivo = math.radians(args.gyaw)
    yaw_actual = math.radians(args.yaw)

    dx = args.gx - args.x
    dy = args.gy - args.y

    error_longitudinal = (
        math.cos(yaw_objetivo) * dx
        + math.sin(yaw_objetivo) * dy
    )

    error_lateral = (
        -math.sin(yaw_objetivo) * dx
        + math.cos(yaw_objetivo) * dy
    )

    error_angular = normalizar(
        yaw_objetivo - yaw_actual
    )

    distancia = math.hypot(dx, dy)

    print(f"Distancia euclidiana: {distancia:.4f} m")
    print(f"Error longitudinal:  {error_longitudinal:.4f} m")
    print(f"Error lateral:       {error_lateral:.4f} m")
    print(
        f"Error angular:       "
        f"{math.degrees(error_angular):.2f} grados"
    )

    if error_longitudinal < 0:
        print("El objetivo está detrás del eje de acople.")
    else:
        print("El objetivo está delante del eje de acople.")


if __name__ == "__main__":
    main()
