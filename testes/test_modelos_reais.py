"""Ativar com VENDETEXTO_TESTAR_MODELOS=1 após --modo preparar.

Estas verificações usam os pesos reais e não simulam as previsões.
"""
import os
from pathlib import Path
import sys
import unittest
import numpy as np

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
import vendetexto2 as app


@unittest.skipUnless(os.environ.get("VENDETEXTO_TESTAR_MODELOS") == "1",
                     "Defina VENDETEXTO_TESTAR_MODELOS=1 para testar os modelos locais reais")
class TestModelosReais(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dados = app.snapshot_api() + [
            {"titulo": "Feedback", "texto": "I love this software. It works perfectly and the new dashboard is fantastic!",
             "origem": "usuario", "idioma": "en"},
            {"titulo": "Feedback", "texto": "O aplicativo é horrível, trava o tempo todo e o suporte não resolve nada.",
             "origem": "usuario", "idioma": "pt"},
        ]
        cls.resultados = app.analisar_textos(dados)
        cls.emb, cls.matriz = app.analisar_semanticamente(cls.resultados, BASE / "modelos", offline=True)

    def test_cosseno_e_dimensoes(self):
        self.assertEqual(self.emb.shape, (7, 384))
        np.testing.assert_allclose(np.linalg.norm(self.emb, axis=1), 1., atol=1e-5)
        np.testing.assert_allclose(self.matriz, self.matriz.T, atol=1e-6)
        np.testing.assert_allclose(np.diag(self.matriz), 1., atol=1e-5)

    def test_texto_longo_completo_e_limites_reais(self):
        self.assertGreater(len(self.resultados[4]["analise_semantica"]["fragmentos"]), 1)
        for r in self.resultados:
            a = r["analise_semantica"]
            self.assertEqual(" ".join(f["texto"] for f in a["fragmentos"]).split(), r["texto_limpo"].split())
            for f in a["fragmentos"]:
                self.assertLessEqual(f["tokens_embeddings"], a["limites_tokens"]["embeddings"])
                self.assertLessEqual(f["tokens_sentimentos"], a["limites_tokens"]["sentimentos"])
            self.assertAlmostEqual(sum(a["sentimento"]["probabilidades"].values()), 1., places=5)

    def test_consultas_nao_entram_nos_candidatos_do_corpus(self):
        for i, r in enumerate(self.resultados):
            pares = r["analise_semantica"]["textos_similares"]
            self.assertTrue(all(p["indice"] < 5 and p["indice"] != i for p in pares))
            scores = [p["similaridade"] for p in pares]
            self.assertEqual(scores, sorted(scores, reverse=True))

    def test_casos_de_controle_bilingues(self):
        self.assertEqual(self.resultados[5]["analise_semantica"]["sentimento"]["rotulo"], "positivo")
        self.assertEqual(self.resultados[6]["analise_semantica"]["sentimento"]["rotulo"], "negativo")


if __name__ == "__main__":
    unittest.main()
