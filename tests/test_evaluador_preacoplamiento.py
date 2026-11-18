import math
import sys
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "scripts" / "integracion"),
)

from evaluador_preacoplamiento import evaluar_pose_preacoplamiento


class TestEvaluadorPreacoplamiento(unittest.TestCase):

    def datos(self, **cambios):
        base = dict(
            x=0.75,
            y=-1.4,
            yaw=0.0,
            objetivo_x=1.05,
            objetivo_y=-1.4,
            objetivo_yaw=0.0,
            nav2_finalizado=True,
            robot_detenido=True,
            sensores_validos=True,
        )
        base.update(cambios)
        return base

    def test_pose_y_seguridad_validas(self):
        resultado, errores, motivo = evaluar_pose_preacoplamiento(
            **self.datos()
        )
        self.assertTrue(resultado.confirmado)
        self.assertEqual(resultado.estado, "POSE_APTA")
        self.assertEqual(motivo, "PREACOPLE_APTO")
        self.assertAlmostEqual(errores["longitudinal"], 0.30)

    def test_error_lateral(self):
        resultado, _, motivo = evaluar_pose_preacoplamiento(
            **self.datos(y=-1.35)
        )
        self.assertFalse(resultado.confirmado)
        self.assertEqual(motivo, "ERROR_LATERAL_EXCESIVO")

    def test_error_angular(self):
        resultado, _, motivo = evaluar_pose_preacoplamiento(
            **self.datos(yaw=math.radians(15))
        )
        self.assertFalse(resultado.confirmado)
        self.assertEqual(motivo, "ERROR_ANGULAR_EXCESIVO")

    def test_nav2_no_finalizado(self):
        resultado, _, _ = evaluar_pose_preacoplamiento(
            **self.datos(nav2_finalizado=False)
        )
        self.assertFalse(resultado.confirmado)

    def test_robot_no_detenido(self):
        resultado, _, _ = evaluar_pose_preacoplamiento(
            **self.datos(robot_detenido=False)
        )
        self.assertFalse(resultado.confirmado)

    def test_sensores_invalidos(self):
        resultado, _, _ = evaluar_pose_preacoplamiento(
            **self.datos(sensores_validos=False)
        )
        self.assertFalse(resultado.confirmado)

    def test_coordenadas_nan(self):
        resultado, errores, motivo = evaluar_pose_preacoplamiento(
            **self.datos(x=float("nan"))
        )
        self.assertFalse(resultado.confirmado)
        self.assertIsNone(errores)
        self.assertEqual(motivo, "COORDENADAS_INVALIDAS")

    def test_coordenadas_inf(self):
        resultado, _, motivo = evaluar_pose_preacoplamiento(
            **self.datos(yaw=float("inf"))
        )
        self.assertFalse(resultado.confirmado)
        self.assertEqual(motivo, "COORDENADAS_INVALIDAS")

    def test_estaciones(self):
        for y in (-1.4, -0.7, 0.0, 0.7, 1.4):
            with self.subTest(y=y):
                resultado, _, _ = evaluar_pose_preacoplamiento(
                    **self.datos(y=y, objetivo_y=y)
                )
                self.assertTrue(resultado.confirmado)


if __name__ == "__main__":
    unittest.main()
