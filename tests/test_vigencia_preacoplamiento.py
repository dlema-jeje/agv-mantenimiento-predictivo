import sys
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "scripts" / "integracion"),
)

from vigencia_preacoplamiento import verificar_vigencia


class TestVigenciaPreacoplamiento(unittest.TestCase):

    def datos(self, **cambios):
        base = dict(
            ahora=100.0,
            t_nav2=99.8,
            t_arbitro=99.8,
            t_odom=99.8,
            t_sensores=99.8,
            estado_nav2="FINALIZADO",
            estado_arbitro="STOP",
            max_edad=0.5,
        )
        base.update(cambios)
        return base

    def test_evidencias_vigentes(self):
        resultado = verificar_vigencia(**self.datos())
        self.assertTrue(resultado.valida)

    def test_nav2_no_finalizado(self):
        resultado = verificar_vigencia(
            **self.datos(estado_nav2="NO_CONFIRMADO")
        )
        self.assertFalse(resultado.valida)

    def test_arbitro_no_stop(self):
        resultado = verificar_vigencia(
            **self.datos(estado_arbitro="NAV2")
        )
        self.assertFalse(resultado.valida)

    def test_evidencias_obsoletas(self):
        for campo in (
            "t_nav2", "t_arbitro", "t_odom", "t_sensores"
        ):
            with self.subTest(campo=campo):
                resultado = verificar_vigencia(
                    **self.datos(**{campo: 99.0})
                )
                self.assertFalse(resultado.valida)

    def test_evidencias_ausentes(self):
        for campo in (
            "t_nav2", "t_arbitro", "t_odom", "t_sensores"
        ):
            with self.subTest(campo=campo):
                resultado = verificar_vigencia(
                    **self.datos(**{campo: 0.0})
                )
                self.assertFalse(resultado.valida)

    def test_tiempo_futuro(self):
        resultado = verificar_vigencia(
            **self.datos(t_nav2=101.0)
        )
        self.assertFalse(resultado.valida)

    def test_nan(self):
        resultado = verificar_vigencia(
            **self.datos(t_odom=float("nan"))
        )
        self.assertFalse(resultado.valida)

    def test_limite_temporal(self):
        resultado = verificar_vigencia(
            **self.datos(t_nav2=99.5)
        )
        self.assertTrue(resultado.valida)

    def test_fuera_del_limite(self):
        resultado = verificar_vigencia(
            **self.datos(t_nav2=99.49)
        )
        self.assertFalse(resultado.valida)

    def test_no_acepta_booleanos_como_tiempos(self):
        resultado = verificar_vigencia(
            **self.datos(t_nav2=True)
        )
        self.assertFalse(resultado.valida)


if __name__ == "__main__":
    unittest.main()
