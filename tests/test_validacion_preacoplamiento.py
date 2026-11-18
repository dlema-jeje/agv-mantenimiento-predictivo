import sys
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "scripts" / "integracion"),
)

from validacion_preacoplamiento import validar_preacoplamiento


class TestValidacionPreacoplamiento(unittest.TestCase):

    def datos(self, **cambios):
        datos = dict(
            geometria_apta=True,
            nav2_finalizado=True,
            robot_detenido=True,
            sensores_validos=True,
        )
        datos.update(cambios)
        return datos

    def test_todas_las_condiciones(self):
        resultado = validar_preacoplamiento(**self.datos())
        self.assertTrue(resultado.confirmado)
        self.assertEqual(resultado.estado, "POSE_APTA")

    def test_geometria_invalida(self):
        resultado = validar_preacoplamiento(
            **self.datos(geometria_apta=False)
        )
        self.assertFalse(resultado.confirmado)

    def test_nav2_no_finalizado(self):
        resultado = validar_preacoplamiento(
            **self.datos(nav2_finalizado=False)
        )
        self.assertFalse(resultado.confirmado)

    def test_robot_en_movimiento(self):
        resultado = validar_preacoplamiento(
            **self.datos(robot_detenido=False)
        )
        self.assertFalse(resultado.confirmado)

    def test_sensores_invalidos(self):
        resultado = validar_preacoplamiento(
            **self.datos(sensores_validos=False)
        )
        self.assertFalse(resultado.confirmado)

    def test_evidencia_ausente(self):
        for campo in self.datos():
            with self.subTest(campo=campo):
                resultado = validar_preacoplamiento(
                    **self.datos(**{campo: None})
                )
                self.assertFalse(resultado.confirmado)

    def test_valores_no_booleanos(self):
        for valor in (1, "True", [], 0):
            with self.subTest(valor=valor):
                resultado = validar_preacoplamiento(
                    **self.datos(geometria_apta=valor)
                )
                self.assertFalse(resultado.confirmado)


if __name__ == "__main__":
    unittest.main()
