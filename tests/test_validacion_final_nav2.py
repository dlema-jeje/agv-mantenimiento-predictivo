import sys
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "scripts" / "integracion"),
)

from validacion_final_nav2 import validar_finalizacion_nav2


class TestValidacionFinalNav2(unittest.TestCase):

    def datos(self, **cambios):
        base = dict(
            exito_nav2=True,
            cancelacion_solicitada=False,
            stop_confirmado=True,
            velocidad_lineal=0.0,
            velocidad_angular=0.0,
            antiguedad_odom=0.05,
        )
        base.update(cambios)
        return base

    def test_exito_completo(self):
        r = validar_finalizacion_nav2(**self.datos())
        self.assertTrue(r.autorizado)
        self.assertEqual(r.estado, "FINALIZADO")

    def test_nav2_fallido(self):
        r = validar_finalizacion_nav2(
            **self.datos(exito_nav2=False)
        )
        self.assertFalse(r.autorizado)

    def test_cancelacion(self):
        r = validar_finalizacion_nav2(
            **self.datos(cancelacion_solicitada=True)
        )
        self.assertFalse(r.autorizado)

    def test_stop_no_confirmado(self):
        r = validar_finalizacion_nav2(
            **self.datos(stop_confirmado=False)
        )
        self.assertFalse(r.autorizado)

    def test_robot_en_movimiento(self):
        r = validar_finalizacion_nav2(
            **self.datos(velocidad_lineal=0.05)
        )
        self.assertFalse(r.autorizado)

    def test_movimiento_angular(self):
        r = validar_finalizacion_nav2(
            **self.datos(velocidad_angular=0.1)
        )
        self.assertFalse(r.autorizado)

    def test_odom_obsoleta(self):
        r = validar_finalizacion_nav2(
            **self.datos(antiguedad_odom=0.5)
        )
        self.assertFalse(r.autorizado)

    def test_nan(self):
        r = validar_finalizacion_nav2(
            **self.datos(velocidad_lineal=float("nan"))
        )
        self.assertFalse(r.autorizado)

    def test_sin_evidencia(self):
        r = validar_finalizacion_nav2(
            **self.datos(exito_nav2=None)
        )
        self.assertFalse(r.autorizado)

    def test_limites_estrictos(self):
        for cambios in (
            {"velocidad_lineal": 0.01},
            {"velocidad_angular": 0.03},
            {"antiguedad_odom": 0.3},
            {"antiguedad_odom": -1},
        ):
            with self.subTest(cambios=cambios):
                r = validar_finalizacion_nav2(
                    **self.datos(**cambios)
                )
                self.assertFalse(r.autorizado)


if __name__ == "__main__":
    unittest.main()
