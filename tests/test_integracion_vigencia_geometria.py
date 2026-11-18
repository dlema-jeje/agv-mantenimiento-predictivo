import sys
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "scripts" / "integracion"),
)

from evaluador_preacoplamiento import (
    evaluar_pose_preacoplamiento_con_vigencia,
)


class TestIntegracionVigenciaGeometria(unittest.TestCase):

    def datos(self, **cambios):
        base = dict(
            x=0.75,
            y=-1.4,
            yaw=0.0,
            objetivo_x=1.05,
            objetivo_y=-1.4,
            objetivo_yaw=0.0,
            ahora=100.0,
            t_nav2=99.8,
            t_arbitro=99.8,
            t_odom=99.8,
            t_sensores=99.8,
            estado_nav2="FINALIZADO",
            estado_arbitro="STOP",
            sensores_validos=True,
            robot_detenido=True,
        )
        base.update(cambios)
        return base

    def test_todo_confirmado(self):
        resultado, _, _, vigencia = (
            evaluar_pose_preacoplamiento_con_vigencia(**self.datos())
        )
        self.assertTrue(vigencia.valida)
        self.assertTrue(resultado.confirmado)
        self.assertEqual(resultado.estado, "POSE_APTA")

    def test_nav2_obsoleto(self):
        resultado, _, _, vigencia = (
            evaluar_pose_preacoplamiento_con_vigencia(
                **self.datos(t_nav2=99.0)
            )
        )
        self.assertFalse(vigencia.valida)
        self.assertFalse(resultado.confirmado)

    def test_arbitro_obsoleto(self):
        resultado, _, _, vigencia = (
            evaluar_pose_preacoplamiento_con_vigencia(
                **self.datos(t_arbitro=99.0)
            )
        )
        self.assertFalse(vigencia.valida)
        self.assertFalse(resultado.confirmado)

    def test_odom_obsoleta(self):
        resultado, _, _, vigencia = (
            evaluar_pose_preacoplamiento_con_vigencia(
                **self.datos(t_odom=99.0)
            )
        )
        self.assertFalse(vigencia.valida)
        self.assertFalse(resultado.confirmado)

    def test_sensores_obsoletos(self):
        resultado, _, _, vigencia = (
            evaluar_pose_preacoplamiento_con_vigencia(
                **self.datos(t_sensores=99.0)
            )
        )
        self.assertFalse(vigencia.valida)
        self.assertFalse(resultado.confirmado)

    def test_robot_en_movimiento(self):
        resultado, _, _, vigencia = (
            evaluar_pose_preacoplamiento_con_vigencia(
                **self.datos(robot_detenido=False)
            )
        )
        self.assertTrue(vigencia.valida)
        self.assertFalse(resultado.confirmado)

    def test_geometria_invalida(self):
        resultado, _, motivo, vigencia = (
            evaluar_pose_preacoplamiento_con_vigencia(
                **self.datos(y=-1.35)
            )
        )
        self.assertTrue(vigencia.valida)
        self.assertFalse(resultado.confirmado)
        self.assertEqual(motivo, "ERROR_LATERAL_EXCESIVO")

    def test_nav2_no_finalizado(self):
        resultado, _, _, vigencia = (
            evaluar_pose_preacoplamiento_con_vigencia(
                **self.datos(estado_nav2="NO_CONFIRMADO")
            )
        )
        self.assertFalse(vigencia.valida)
        self.assertFalse(resultado.confirmado)

    def test_arbitro_no_stop(self):
        resultado, _, _, vigencia = (
            evaluar_pose_preacoplamiento_con_vigencia(
                **self.datos(estado_arbitro="NAV2")
            )
        )
        self.assertFalse(vigencia.valida)
        self.assertFalse(resultado.confirmado)


if __name__ == "__main__":
    unittest.main()
