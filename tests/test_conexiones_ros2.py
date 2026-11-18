import ast
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def leer(ruta):
    return (RAIZ / ruta).read_text(encoding="utf-8")


class TestConexionesROS2(unittest.TestCase):

    def test_arbitro_recibe_nav2_suavizado(self):
        codigo = leer("scripts/integracion/arbitro_velocidades.py")
        self.assertIn('"/cmd_vel_nav_smooth"', codigo)

    def test_arbitro_recibe_mamdani(self):
        codigo = leer("scripts/integracion/arbitro_velocidades.py")
        self.assertIn('"/cmd_vel_mamdani"', codigo)

    def test_arbitro_publica_cmd_vel(self):
        codigo = leer("scripts/integracion/arbitro_velocidades.py")
        self.assertIn('Twist, "/cmd_vel"', codigo)

    def test_arbitro_inicia_stop(self):
        codigo = leer("scripts/integracion/arbitro_velocidades.py")
        self.assertIn('self.modo = "STOP"', codigo)

    def test_arbitro_bloquea_movimiento(self):
        codigo = leer("scripts/integracion/arbitro_velocidades.py")
        self.assertIn('!= "STOP"', codigo)

    def test_mamdani_publica_en_topico_intermedio(self):
        codigo = leer("scripts/difuso/nodo_acoplamiento_ros2.py")
        self.assertIn('"/cmd_vel_mamdani"', codigo)

    def test_mamdani_no_autoriza_ejecucion(self):
        codigo = leer("scripts/difuso/nodo_acoplamiento_ros2.py")
        self.assertIn('self.ejecutar = False', codigo)

    def test_supervisor_no_autoriza_sin_nav2(self):
        codigo = leer("scripts/integracion/supervisor_autorizacion.py")
        self.assertIn('NAV2_NO_CONFIRMADO', codigo)

    def test_supervisor_no_autoriza_sin_preacople(self):
        codigo = leer("scripts/integracion/supervisor_autorizacion.py")
        self.assertIn('PREACOPLAMIENTO_NO_CONFIRMADO', codigo)

    def test_archivos_python_sintaxis(self):
        archivos = [
            "scripts/integracion/arbitro_velocidades.py",
            "scripts/integracion/cliente_nav2_supervisado.py",
            "scripts/integracion/supervisor_autorizacion.py",
            "scripts/integracion/orquestador_mision.py",
            "scripts/difuso/nodo_acoplamiento_ros2.py",
        ]
        for archivo in archivos:
            with self.subTest(archivo=archivo):
                ast.parse(leer(archivo), filename=archivo)


if __name__ == "__main__":
    unittest.main()
