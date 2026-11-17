"""Testes de regressão sem baixar modelos ou consultar a API."""
import json
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
import vendetexto2 as app


class TokenizadorDidatico:
    """Só testa o algoritmo de divisão. Não substitui os modelos nos testes reais."""
    def encode(self, texto, add_special_tokens=True, **kwargs):
        return list(range(len(texto.split()) + (2 if add_special_tokens else 0)))


class TestPipeline(unittest.TestCase):
    def test_componentes_executam_e_conservam_contexto(self):
        r = app.analisar_textos([{"titulo": "Relato", "texto": "Quero um painel. O filtro precisa funcionar.",
                                 "origem": "usuario", "idioma": "pt"}])[0]
        self.assertEqual(r["pipeline_spacy"], ["sentencizer", "requisitos_vendetexto"])
        self.assertIn("painel", r["categorias"])
        self.assertIn("filtro", r["categorias"])
        self.assertGreaterEqual(len(r["sentencas"]), 2)
        self.assertTrue(any(t["sentenca"] == "O filtro precisa funcionar." for t in r["trechos_requisitos"]))

    def test_nao_confunde_substrings_com_requisitos(self):
        r = app.analisar_textos([{"titulo": "Equipe", "texto": "O preconceito prejudica as pessoas.",
                                 "origem": "usuario", "idioma": "pt"}])[0]
        self.assertNotIn("preco", r["categorias"])

    def test_sem_spacy_falha_com_orientacao(self):
        app.criar_analisadores.cache_clear()
        with patch.object(app, "spacy", None):
            with self.assertRaisesRegex(RuntimeError, "spaCy indisponível"):
                app.criar_analisadores()
        app.criar_analisadores.cache_clear()

    def test_limpeza_mantem_rotulo_de_link(self):
        self.assertEqual(app.limpar("Veja [o painel](https://example.org). &amp; filtros"),
                         "Veja o painel. & filtros")


class TestFragmentacao(unittest.TestCase):
    def test_cobre_todas_as_palavras_sem_repetir(self):
        sentencas = ["Uma frase curta.", " ".join(f"palavra{i}" for i in range(55))]
        tok = TokenizadorDidatico()
        partes = app.fragmentar_sentencas(sentencas, [tok, tok], [12, 9])
        self.assertEqual(" ".join(partes).split(), " ".join(sentencas).split())
        self.assertTrue(all(len(tok.encode(p)) <= 9 for p in partes))

    def test_peso_reflete_tamanho_do_fragmento(self):
        vetor, probs = app.agregar_fragmentos(
            [[1., 0.], [0., 1.]],
            [{"positivo": 1., "neutro": 0., "negativo": 0.},
             {"positivo": 0., "neutro": 0., "negativo": 1.}], [1, 3])
        self.assertAlmostEqual(probs["positivo"], .25)
        self.assertAlmostEqual(probs["negativo"], .75)
        self.assertAlmostEqual(float(vetor @ vetor), 1.)


class TestRegressao(unittest.TestCase):
    def test_coleta_repete_falha_transitoria_sem_trocar_por_cache(self):
        item = {"title": "Issue atual", "body": "Sales report", "html_url": "https://example.org/1"}
        respostas = [app.URLError("timeout transitório")]
        respostas += [io.BytesIO(json.dumps(item).encode()) for _ in app.ISSUE_IDS]
        with patch.object(app, "urlopen", side_effect=respostas) as consultar, patch.object(app.time, "sleep"):
            dados = app.coletar_issues()
        self.assertEqual(consultar.call_count, len(app.ISSUE_IDS) + 1)
        self.assertEqual(len(dados), 5)
        self.assertTrue(all(r["titulo"] == "Issue atual" for r in dados))

    def test_indicadores_herdados(self):
        caderno = app.indicadores(app.ler_vendas(BASE / "dados/vendas_ficticias.csv", "Caderno"))
        caneca = app.indicadores(app.ler_vendas(BASE / "dados/vendas_ficticias.csv", "Caneca"))
        self.assertAlmostEqual(caderno["elasticidade_preco"], 1.)
        self.assertEqual(caderno["receita_depois"], 960.)
        self.assertAlmostEqual(caneca["elasticidade_preco"], .4)
        self.assertEqual(caneca["receita_depois"], 1056.)

    def test_preco_constante_nao_divide_por_zero(self):
        r = app.indicadores([{"preco": 10, "quantidade": 100}, {"preco": 10, "quantidade": 80}])
        self.assertIsNone(r["elasticidade_preco"])

    def test_executa_de_outra_pasta_com_espacos(self):
        with tempfile.TemporaryDirectory(prefix="VendeTexto teste ") as pasta:
            r = subprocess.run([sys.executable, str(BASE / "vendetexto2.py"),
                                "--modo", "demo", "--somente-etapa1", "--produto", "Caneca",
                                "--requisito", "Quero preço de R$ 12,00 e 80 unidades vendidas",
                                "--saida", str(Path(pasta) / "resultado")], cwd=pasta,
                               capture_output=True, text=True, encoding="utf-8", timeout=60,
                               env={**os.environ, "PYTHONUTF8": "1"})
            self.assertEqual(r.returncode, 0, r.stderr)
            dados = json.loads((Path(pasta) / "resultado/analise.json").read_text(encoding="utf-8"))
            resumo = json.loads((Path(pasta) / "resultado/resumo.json").read_text(encoding="utf-8"))
            self.assertEqual(len(dados), 6)
            self.assertEqual(resumo["textos_corpus"], 5)
            self.assertEqual(resumo["consultas_usuario"], 1)
            self.assertFalse(resumo["etapa2_executada"])
            self.assertEqual(dados[-1]["numeros_re"]["valores"], ["R$ 12,00"])

    def test_offline_rejeita_coleta(self):
        r = subprocess.run([sys.executable, str(BASE / "vendetexto2.py"), "--modo", "coletar", "--offline"],
                           capture_output=True, timeout=30)
        self.assertEqual(r.returncode, 2)

    def test_calculadora_tres_modalidades(self):
        r = subprocess.run([sys.executable, str(BASE / "vendetexto2.py"), "--modo", "calculadora"],
                           input="50\n40\n100\n109\ns\n100\n112\ns\n100\n95\n",
                           capture_output=True, text=True, encoding="utf-8", timeout=30,
                           env={**os.environ, "PYTHONUTF8": "1"})
        self.assertEqual(r.returncode, 0, r.stderr)
        for valor in ("0.45", "+0.75", "+0.25"):
            self.assertIn(valor, r.stdout)


if __name__ == "__main__":
    unittest.main()
