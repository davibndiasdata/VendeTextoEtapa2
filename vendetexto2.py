"""VendeTexto - etapa 2 de Modelagem de Dados Não Estruturados (UFPB).

Base da etapa 2 elaborada por Angélica Maria da Silva.
Equipe: Angélica Maria da Silva, Leonardo Pessoa de Souza e
Davi Batista Nóbrega Dias. Revisão técnica com apoio do ChatGPT.

Exemplos: python vendetexto2.py --modo cache
          python vendetexto2.py --modo preparar
          python vendetexto2.py --modo cache --offline

Os textos da API sao demandas de software, nao dados de vendas. As vendas do
CSV sao ficticias e servem apenas para demonstrar os indicadores.
"""

from __future__ import annotations

import argparse
import csv
import importlib
import json
import math
import re
import sys
import os
import time
import hashlib
import html
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    import matplotlib.pyplot as plt
except Exception as erro:  # pragma: no cover - depende do ambiente do terminal
    plt = None
    MATPLOTLIB_ERRO = erro
else:
    MATPLOTLIB_ERRO = None

try:
    import spacy
    from spacy.matcher import PhraseMatcher
    from spacy.language import Language
    from spacy.tokens import Doc
except Exception as erro:  # pragma: no cover - depende do ambiente do terminal
    spacy = None
    PhraseMatcher = None
    SPACY_ERRO = erro
else:
    SPACY_ERRO = None


BASE = Path(__file__).resolve().parent
ISSUE_IDS = (40751, 43635, 7788, 43935, 53760)
API = "https://api.github.com/repos/frappe/erpnext/issues/{}"
SENTIMENTO_MODELO = "lxyuan/distilbert-base-multilingual-cased-sentiments-student"
EMBEDDING_MODELO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
# Revisões fixas dos modelos, para repetir a mesma análise após o download.
EMBEDDING_REVISAO = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
SENTIMENTO_REVISAO = "cf991100d706c13c0a080c097134c05b7f436c45"
ROTULOS = {"positive": "positivo", "neutral": "neutro", "negative": "negativo"}
VERSAO = "2.0.0"
TERMOS = {
    "vendas": ("sales", "selling", "vendas", "venda"),
    "preco": ("price", "pricing", "price revision", "preço", "preco"),
    "painel": ("dashboard", "sales analytics report", "sales report", "painel", "gráfico", "grafico"),
    "filtro": ("filter", "filters", "filtro", "filtros"),
    "cliente": ("customer name", "customer names", "nome do cliente"),
    "acesso": ("permissions", "permission", "access control", "permissão", "acesso"),
    "quantidade": ("quantity sold", "units sold", "sales volume", "quantidade vendida", "unidades vendidas"),
    "receita": ("revenue", "turnover", "faturamento", "receita"),
    "elasticidade": ("elasticity", "elasticidade", "sensibilidade ao preço"),
}


def coletar_issues() -> list[dict]:
    """Busca titulo e corpo de cinco issues publicas pela API do GitHub."""
    registros = []
    for numero in ISSUE_IDS:
        print(f"Coletando issue #{numero} pela API do GitHub...")
        req = Request(
            API.format(numero),
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "VendeTexto-MDNE-estudo",
            },
        )
        for tentativa in range(2):
            try:
                with urlopen(req, timeout=15) as resposta:
                    item = json.load(resposta)
                break
            except (HTTPError, URLError, TimeoutError) as erro:
                transitorio = not isinstance(erro, HTTPError) or erro.code in (429, 500, 502, 503, 504)
                if tentativa == 0 and transitorio:
                    print(f"  Falha transitória em #{numero}; tentando mais uma vez...")
                    time.sleep(.5)
                    continue
                raise RuntimeError(
                    f"Falha ao consultar issue #{numero}: {erro}. "
                    "Verifique a internet/limite da API ou use --modo cache."
                ) from erro
        registros.append(
            {
                "origem": "API GitHub",
                "idioma": "en",
                "titulo": item.get("title", ""),
                "texto": item.get("body") or "",
                "url": item.get("html_url", ""),
            }
        )
    return registros


def exemplos_locais() -> list[dict]:
    """Exemplos redigidos para treinar a demonstracao sem internet."""
    arquivo = BASE / "dados" / "exemplos_texto.json"
    return json.loads(arquivo.read_text(encoding="utf-8"))


def snapshot_api() -> list[dict]:
    """Le copia real das issues coletadas antes, sem precisar de internet."""
    arquivo = BASE / "dados" / "issues_api_snapshot.json"
    return json.loads(arquivo.read_text(encoding="utf-8"))


def limpar(texto: str) -> str:
    """Remove ruídos comuns de Markdown/HTML usando expressoes regulares."""
    texto = re.sub(r"```[\s\S]*?```", " ", texto)
    texto = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", texto)
    texto = re.sub(r"<[^>]+>|https?://\S+", " ", texto)
    texto = html.unescape(texto)
    return re.sub(r"\s+", " ", texto).strip()


def extrair_numeros(texto: str) -> dict:
    """Localiza valores e unidades quando constam da descricao."""
    valores = re.findall(r"R\$\s*\d+(?:[.,]\d{2})?", texto)
    unidades = re.findall(r"\b\d+\s*(?:unidades?|units?|qty)\b", texto, re.I)
    return {"valores": valores[:5], "unidades": unidades[:5]}


class ExtratorRequisitos:
    """Componente por regras: recebe um Doc, anota requisitos e devolve o Doc."""

    def __init__(self, nlp):
        self.matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
        for categoria, termos in TERMOS.items():
            self.matcher.add(categoria, [nlp.make_doc(termo) for termo in termos])

    def __call__(self, doc):
        evidencias = {}
        trechos = []
        for match_id, inicio, fim in self.matcher(doc):
            categoria = doc.vocab.strings[match_id]
            trecho = doc[inicio:fim]
            evidencias.setdefault(categoria, set()).add(trecho.text)
            trechos.append({"categoria": categoria, "expressao": trecho.text,
                           "sentenca": trecho.sent.text})
        doc._.evidencias_requisitos = {k: sorted(v) for k, v in evidencias.items()}
        doc._.trechos_requisitos = trechos
        return doc


if spacy is not None:
    for nome in ("evidencias_requisitos", "trechos_requisitos"):
        if not Doc.has_extension(nome):
            Doc.set_extension(nome, default=None)

    @Language.factory("requisitos_vendetexto")
    def criar_extrator_requisitos(nlp, name):
        return ExtratorRequisitos(nlp)


@lru_cache(maxsize=1)
def criar_analisadores() -> dict:
    """Pipeline explícita: tokenização, sentenças e extração de requisitos.

    É uma pipeline por regras, sem lematização ou NER estatísticos.
    As sentenças alimentam a fragmentação usada pelos modelos Transformers.
    """
    if spacy is None or PhraseMatcher is None:
        raise RuntimeError(
            f"spaCy indisponível ({SPACY_ERRO}). Execute instalar_windows.bat "
            "ou python -m pip install -r requirements.txt."
        )
    saida = {}
    for idioma in ("pt", "en"):
        nlp = spacy.blank(idioma)
        nlp.add_pipe("sentencizer")
        nlp.add_pipe("requisitos_vendetexto")
        saida[idioma] = nlp
    return saida


def analisar_textos(registros: list[dict]) -> list[dict]:
    analisadores = criar_analisadores()
    resultados = []
    for registro in registros:
        idioma = registro.get("idioma", "en")
        if idioma not in analisadores:
            raise ValueError(f"Idioma {idioma!r} não suportado. Use pt ou en.")
        nlp = analisadores[idioma]
        original = registro["titulo"] + ". " + registro["texto"]
        texto_limpo = limpar(original)
        if not texto_limpo:
            raise ValueError("Há um registro sem conteúdo textual após a limpeza.")
        doc = nlp(texto_limpo)
        evidencias = doc._.evidencias_requisitos
        sentencas = []
        for sentenca in doc.sents:
            # Markdown pode levar o sentencizer a separar '_' de uma palavra.
            # Unir limites sem espaço conserva exatamente as palavras da entrada.
            if sentencas and sentenca.start_char and not doc.text[sentenca.start_char-1].isspace():
                sentencas[-1] += sentenca.text
            elif sentenca.text.strip():
                sentencas.append(sentenca.text.strip())
        resultados.append(
            {
                "titulo": registro["titulo"],
                "id": registro.get("url", "").rstrip("/").split("/")[-1] or f"texto-{len(resultados)+1}",
                "idioma": idioma,
                "texto_limpo": texto_limpo,
                "url": registro.get("url", ""),
                "origem": registro["origem"],
                "categorias": sorted(evidencias),
                "evidencias": {k: sorted(v)[:4] for k, v in evidencias.items()},
                "numeros_re": extrair_numeros(original),
                "tokens": len(doc),
                "pipeline_spacy": nlp.pipe_names,
                "sentencas": sentencas,
                "trechos_requisitos": doc._.trechos_requisitos,
            }
        )
    return resultados


def ler_vendas(caminho: Path, produto: str) -> list[dict]:
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        registros = list(csv.DictReader(arquivo))
    linhas = []
    for registro in registros:
        if registro["produto"].lower() != produto.lower():
            continue
        preco = float(registro["preco"].replace(",", "."))
        quantidade = int(registro["quantidade"])
        if not math.isfinite(preco) or preco <= 0 or quantidade <= 0:
            raise ValueError("Preco e quantidade precisam ser positivos.")
        linhas.append(
            {"periodo": registro["periodo"], "preco": preco, "quantidade": quantidade}
        )
    if len(linhas) != 2:
        raise ValueError(f"O produto {produto!r} precisa de exatamente dois periodos.")
    return linhas


def indicadores(linhas: list[dict]) -> dict:
    """Elasticidade descritiva com percentuais sobre o valor inicial."""
    antes, depois = linhas
    p1, p2 = antes["preco"], depois["preco"]
    q1, q2 = antes["quantidade"], depois["quantidade"]
    variacao_p = (p2 - p1) / p1
    variacao_q = (q2 - q1) / q1
    elasticidade = abs(variacao_q / variacao_p) if variacao_p else None
    if elasticidade is None:
        classe = "indefinida: preco nao variou"
    elif math.isclose(elasticidade, 1, rel_tol=1e-9):
        classe = "unitaria no intervalo"
    elif elasticidade > 1:
        classe = "elastica no intervalo"
    else:
        classe = "inelastica no intervalo"
    return {
        "preco_variacao_pct": variacao_p * 100,
        "quantidade_variacao_pct": variacao_q * 100,
        "elasticidade_preco": elasticidade,
        "classe": classe,
        "receita_antes": p1 * q1,
        "receita_depois": p2 * q2,
    }


def grafico(linhas: list[dict], produto: str, caminho: Path) -> None:
    """Mostra somente os dois pontos observados; nao estima curva de demanda."""
    if plt is None:
        print(f"Aviso: matplotlib indisponivel ({MATPLOTLIB_ERRO}); grafico de faturamento nao foi gerado.")
        return
    periodos = [x["periodo"] for x in linhas]
    receitas = [x["preco"] * x["quantidade"] for x in linhas]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(periodos, receitas, color=["#227A9B", "#17375E"])
    ax.set_title(f"Faturamento demonstrativo: {produto}")
    ax.set_ylabel("R$")
    ax.set_ylim(0, max(receitas) * 1.25)
    for i, valor in enumerate(receitas):
        ax.text(i, valor + max(receitas) * 0.025, f"R$ {valor:,.0f}", ha="center")
    fig.tight_layout()
    fig.savefig(caminho, dpi=150)
    plt.close(fig)


def grafico_categorias(resultados: list[dict], caminho: Path) -> None:
    """Conta uma categoria uma vez por issue e exclui o pedido digitado."""
    if plt is None:
        print(f"Aviso: matplotlib indisponivel ({MATPLOTLIB_ERRO}); grafico de categorias nao foi gerado.")
        return
    base = [r for r in resultados if r["origem"] != "usuario"]
    contagem = Counter(cat for r in base for cat in r["categorias"])
    if not contagem:
        return
    categorias, quantidades = zip(*contagem.most_common())
    fig, ax = plt.subplots(figsize=(8, 4))
    barras = ax.barh(categorias[::-1], quantidades[::-1], color="#137C9E")
    ax.set_xlim(0, len(base) + 0.5)
    ax.set_xlabel(f"Textos com a categoria (n={len(base)})")
    ax.set_title("Categorias nas issues" if base[0]["origem"] == "API GitHub" else "Categorias nos exemplos")
    ax.bar_label(barras, padding=3)
    fig.tight_layout()
    fig.savefig(caminho, dpi=150)
    plt.close(fig)


def exibir(resultados: list[dict], med: dict, produto: str) -> None:
    base = [r for r in resultados if r["origem"] != "usuario"]
    contagem = Counter(cat for r in base for cat in r["categorias"])
    print("\nREQUISITOS TEXTUAIS (sem o pedido digitado pelo usuario)")
    for categoria, quantidade in contagem.most_common():
        print(f"  {categoria}: {quantidade}/{len(base)}")
    for r in resultados:
        print(f"\n  #{r['id']} {r['titulo']} | {r['origem']}")
        print(f"  Pipeline spaCy: {', '.join(r['pipeline_spacy'])}")
        print(f"  Sentenças: {len(r['sentencas'])} | tokens spaCy: {r['tokens']}")
        print(f"  Categorias: {', '.join(r['categorias']) or 'nenhuma'}")
        print(f"  Evidencias spaCy: {r['evidencias']}")
        print(f"  Padroes re: {r['numeros_re']}")
        if "analise_semantica" in r:
            analise = r["analise_semantica"]
            sentimento = analise["sentimento"]
            print(
                f"  Sentimento Transformers: {sentimento['rotulo']} "
                f"(score agregado {sentimento['confianca']:.3f})"
            )
            print(f"  Distribuição: {sentimento['probabilidades']}")
            print(f"  Fragmentos analisados: {len(analise['fragmentos'])}; "
                  f"embedding do documento: {analise['embedding']['dimensoes']} dimensões")
            if analise["textos_similares"]:
                mais_similar = analise["textos_similares"][0]
                print(
                    f"  Texto mais similar: #{mais_similar['id']} {mais_similar['titulo']} "
                    f"(cosseno {mais_similar['similaridade']:.3f})"
                )
        if r["url"]:
            print(f"  Fonte: {r['url']}")
    print(f"\nPAINEL DE VENDAS: {produto} | base ficticia")
    print(f"  Preco: {med['preco_variacao_pct']:+.1f}%")
    print(f"  Quantidade vendida: {med['quantidade_variacao_pct']:+.1f}%")
    print(f"  Receita: R$ {med['receita_antes']:.2f} -> R$ {med['receita_depois']:.2f}")
    valor = med["elasticidade_preco"]
    print(f"  Elasticidade: {valor:.2f}" if valor is not None else "  Elasticidade: indefinida")
    print(f"  Leitura: {med['classe']}")
    print("  Observacao: dois periodos nao demonstram efeito causal do preco.")


@lru_cache(maxsize=2)
def carregar_modelos(pasta: Path, offline: bool = False):
    """Baixa uma vez e carrega os dois modelos em CPU, sem executar código remoto."""
    try:
        sentence_transformers = importlib.import_module("sentence_transformers")
        transformers = importlib.import_module("transformers")
        torch = importlib.import_module("torch")
        torch.set_num_threads(min(4, os.cpu_count() or 1))
    except (ImportError, OSError) as erro:
        raise RuntimeError(
            f"Dependências da etapa 2 indisponíveis ({erro}). "
            "Execute instalar_windows.bat ou siga o README. "
            "Para conferir apenas a etapa 1, use --somente-etapa1."
        ) from erro
    pasta = Path(pasta)
    pasta_emb, pasta_sent = pasta / "embeddings", pasta / "sentimentos"
    if offline and not all((p / "config.json").is_file() for p in (pasta_emb, pasta_sent)):
        raise RuntimeError("Modelos locais incompletos. Com internet, execute primeiro: "
                           "python vendetexto2.py --modo preparar")
    try:
        if (pasta_emb / "config.json").is_file():
            modelo_embeddings = sentence_transformers.SentenceTransformer(
                str(pasta_emb), device="cpu", local_files_only=True,
                tokenizer_kwargs={"fix_mistral_regex": False})
        else:
            print("Preparando modelo de embeddings (primeiro uso precisa de internet)...")
            modelo_embeddings = sentence_transformers.SentenceTransformer(
                EMBEDDING_MODELO, revision=EMBEDDING_REVISAO, device="cpu",
                tokenizer_kwargs={"fix_mistral_regex": False})
            modelo_embeddings.save(str(pasta_emb))
        if (pasta_sent / "config.json").is_file():
            fonte_sent, opcoes = str(pasta_sent), {"local_files_only": True}
        else:
            print("Preparando modelo de sentimentos (primeiro uso precisa de internet)...")
            fonte_sent, opcoes = SENTIMENTO_MODELO, {"revision": SENTIMENTO_REVISAO}
        # Estes modelos usam Unigram/WordPiece, não a regex de tokenizadores Mistral.
        tokenizer = transformers.AutoTokenizer.from_pretrained(
            fonte_sent, fix_mistral_regex=False, **opcoes)
        modelo_sent = transformers.AutoModelForSequenceClassification.from_pretrained(
            fonte_sent, use_safetensors=True, **opcoes)
        if not (pasta_sent / "config.json").is_file():
            modelo_sent.save_pretrained(str(pasta_sent), safe_serialization=True)
            tokenizer.save_pretrained(str(pasta_sent))
        classificador = transformers.pipeline(
            "sentiment-analysis", model=modelo_sent, tokenizer=tokenizer, device=-1)
    except (OSError, ValueError, RuntimeError) as erro:
        raise RuntimeError(
            f"Não foi possível carregar os modelos: {erro}. "
            "No primeiro uso, verifique a internet e execute --modo preparar. "
            "Se uma pasta de modelo estiver incompleta, remova apenas essa pasta e prepare novamente."
        ) from erro
    return modelo_embeddings, classificador


def fragmentar_sentencas(sentencas: list[str], tokenizers: list, limites: list[int]) -> list[str]:
    """Conserva todas as palavras e respeita o limite de AMBOS os modelos.

    Agrupa sentenças curtas e divide sentenças longas em limites de palavras.
    Não há truncamento nem sobreposição que conte duas vezes a mesma passagem.
    """
    def cabe(texto):
        return all(len(tok.encode(texto, add_special_tokens=True, truncation=False,
                                  verbose=False)) <= limite
                   for tok, limite in zip(tokenizers, limites))

    fragmentos = []
    atual = ""
    for sentenca in sentencas:
        palavras = sentenca.split()
        while palavras:
            # Busca do maior prefixo que cabe. Reduz os testes em textos longos.
            inicio, fim = 1, len(palavras)
            melhor = 0
            while inicio <= fim:
                meio = (inicio + fim) // 2
                candidato = " ".join(filter(None, [atual, " ".join(palavras[:meio])]))
                if cabe(candidato):
                    melhor, inicio = meio, meio + 1
                else:
                    fim = meio - 1
            if melhor:
                atual = " ".join(filter(None, [atual, " ".join(palavras[:melhor])]))
                palavras = palavras[melhor:]
            if palavras:
                if not atual:
                    raise ValueError("Uma palavra excede o limite dos modelos. "
                                     "Revise URLs ou sequências sem espaços na entrada.")
                fragmentos.append(atual)
                atual = ""
    if atual:
        fragmentos.append(atual)
    return fragmentos


def agregar_fragmentos(vetores, distribuicoes: list[dict], pesos: list[int]):
    """Média ponderada dos vetores e scores, seguida de normalização L2."""
    import numpy as np
    if len(vetores) != len(distribuicoes) or len(pesos) != len(vetores) or not pesos:
        raise ValueError("Fragmentos, probabilidades e pesos devem corresponder.")
    if any(p <= 0 for p in pesos):
        raise ValueError("Pesos dos fragmentos devem ser positivos.")
    vetor = np.average(vetores, axis=0, weights=pesos)
    norma = np.linalg.norm(vetor)
    if not np.isfinite(norma) or norma <= 0:
        raise ValueError("O modelo gerou um embedding inválido.")
    probabilidades = {rotulo: float(np.average([d[rotulo] for d in distribuicoes], weights=pesos))
                      for rotulo in ROTULOS.values()}
    return vetor / norma, probabilidades


def analisar_semanticamente(resultados: list[dict], pasta_modelos: Path,
                           offline: bool = False, limite_similares: int = 3):
    """Infere por fragmento, agrega por documento e compara o corpus original."""
    import numpy as np
    if not resultados:
        raise ValueError("A análise precisa de pelo menos um texto.")
    modelo_emb, classificador = carregar_modelos(pasta_modelos, offline)
    tokenizer_emb, tokenizer_sent = modelo_emb.tokenizer, classificador.tokenizer
    limites = [int(modelo_emb.max_seq_length),
               min(int(tokenizer_sent.model_max_length),
                   int(classificador.model.config.max_position_embeddings))]
    grupos = [fragmentar_sentencas(r["sentencas"], [tokenizer_emb, tokenizer_sent], limites)
              for r in resultados]
    fragmentos = [texto for grupo in grupos for texto in grupo]
    if not fragmentos or any(not grupo for grupo in grupos):
        raise ValueError("Há texto sem fragmentos analisáveis.")
    print(f"Analisando {len(resultados)} textos em {len(fragmentos)} fragmentos, em CPU...")
    vetores = modelo_emb.encode(fragmentos, convert_to_numpy=True, normalize_embeddings=True,
                               batch_size=8, show_progress_bar=False)
    # Os limites já foram conferidos antes da inferência. Nunca cortar silenciosamente.
    sentimentos = classificador(fragmentos, batch_size=8, top_k=None, truncation=False)
    documentos, posicao = [], 0
    for resultado, grupo in zip(resultados, grupos):
        detalhes, probs, pesos = [], [], []
        for texto in grupo:
            distribuicao = {ROTULOS[x["label"].lower()]: float(x["score"])
                            for x in sentimentos[posicao + len(detalhes)]}
            if set(distribuicao) != set(ROTULOS.values()):
                raise ValueError("O classificador não retornou as três classes esperadas.")
            tokens_emb = len(tokenizer_emb.encode(texto, add_special_tokens=True))
            tokens_sent = len(tokenizer_sent.encode(texto, add_special_tokens=True))
            peso = len(tokenizer_emb.encode(texto, add_special_tokens=False))
            probs.append(distribuicao)
            pesos.append(peso)
            detalhes.append({"texto": texto, "tokens_embeddings": tokens_emb,
                             "tokens_sentimentos": tokens_sent, "peso": peso,
                             "probabilidades": distribuicao})
        vetor, probabilidades = agregar_fragmentos(
            vetores[posicao:posicao + len(grupo)], probs, pesos)
        documentos.append(vetor)
        posicao += len(grupo)
        rotulo = max(probabilidades, key=probabilidades.get)
        resultado["analise_semantica"] = {
            "sentimento": {"rotulo": rotulo, "confianca": probabilidades[rotulo],
                           "probabilidades": probabilidades, "modelo": SENTIMENTO_MODELO,
                           "revisao": SENTIMENTO_REVISAO,
                           "agregacao": "média das probabilidades ponderada por tokens do embedding"},
            "embedding": {"modelo": EMBEDDING_MODELO, "revisao": EMBEDDING_REVISAO,
                          "dimensoes": int(vetor.shape[0]),
                          "agregacao": "média ponderada dos vetores normalizados e nova normalização L2"},
            "limites_tokens": {"embeddings": limites[0], "sentimentos": limites[1]},
            "fragmentos": detalhes,
        }
    embeddings = np.asarray(documentos)
    matriz = np.clip(embeddings @ embeddings.T, -1, 1)
    for indice, resultado in enumerate(resultados):
        similares = [{"indice": j, "id": outro["id"], "titulo": outro["titulo"],
                      "url": outro["url"], "similaridade": float(matriz[indice, j])}
                     for j, outro in enumerate(resultados)
                     if j != indice and outro["origem"] != "usuario"]
        similares.sort(key=lambda item: item["similaridade"], reverse=True)
        resultado["analise_semantica"]["textos_similares"] = similares[:limite_similares]
    return embeddings, matriz


def salvar_resultados_avancados(resultados, embeddings, matriz, pasta: Path) -> None:
    """Exporta dados auditáveis e gráficos da etapa 2, excluindo a consulta do corpus."""
    import numpy as np
    np.save(pasta / "embeddings.npy", embeddings)
    with (pasta / "sentimentos.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "titulo", "origem", "sentimento", "score_agregado",
                    "positivo", "neutro", "negativo", "fragmentos"])
        for r in resultados:
            a = r["analise_semantica"]
            s = a["sentimento"]
            w.writerow([r["id"], r["titulo"], r["origem"], s["rotulo"], s["confianca"],
                        *[s["probabilidades"][c] for c in ROTULOS.values()], len(a["fragmentos"])])
    with (pasta / "similaridade.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id"] + [r["id"] for r in resultados])
        for r, linha in zip(resultados, matriz):
            w.writerow([r["id"], *map(float, linha)])
    if plt is None:
        return
    indices = [i for i, r in enumerate(resultados) if r["origem"] != "usuario"]
    base = [resultados[i] for i in indices]
    contagem = Counter(r["analise_semantica"]["sentimento"]["rotulo"] for r in base)
    rotulos = list(ROTULOS.values())
    fig, ax = plt.subplots(figsize=(7, 4))
    barras = ax.bar(rotulos, [contagem[r] for r in rotulos],
                    color=["#258568", "#718396", "#BA4B4B"])
    ax.bar_label(barras, padding=3)
    ax.set_ylim(0, max(1, len(base)) + 1)
    ax.set_yticks(range(len(base) + 1))
    ax.set_ylabel("Textos")
    ax.set_title(f"Sentimentos previstos no corpus (n={len(base)})")
    fig.tight_layout()
    fig.savefig(pasta / "sentimentos.png", dpi=170)
    plt.close(fig)
    if not indices:
        return
    m = matriz[np.ix_(indices, indices)]
    fig, ax = plt.subplots(figsize=(7, 5))
    im = ax.imshow(m, cmap="Blues", vmin=-1, vmax=1)
    nomes = ["#" + r["id"] for r in base]
    ax.set_xticks(range(len(base)), nomes, rotation=30, ha="right")
    ax.set_yticks(range(len(base)), nomes)
    for i in range(len(base)):
        for j in range(len(base)):
            ax.text(j, i, f"{m[i,j]:.2f}", ha="center", va="center",
                    color="white" if m[i,j] > .4 else "#172D40")
    ax.set_title(f"Similaridade de cosseno entre textos (n={len(base)})")
    fig.colorbar(im, ax=ax, label="Cosseno (não é probabilidade)")
    fig.tight_layout()
    fig.savefig(pasta / "similaridade.png", dpi=170)
    plt.close(fig)


def ler_positivo(rotulo: str) -> float:
    """Pede um numero positivo; repete a pergunta se a entrada for invalida."""
    while True:
        entrada = input(f"{rotulo}: ").strip().replace(",", ".")
        try:
            numero = float(entrada)
        except ValueError:
            print("Digite um numero, por exemplo 12 ou 12,50.")
            continue
        if not math.isfinite(numero) or numero <= 0:
            print("Digite um numero maior que zero.")
            continue
        return numero


def perguntar_opcao(rotulo: str) -> bool:
    while True:
        escolha = input(f"{rotulo} (s/n): ").strip().lower()
        if escolha in ("s", "n"):
            return escolha == "s"
        print("Responda com s ou n.")


def calculadora() -> None:
    """Aplica as variacoes simples apresentadas nos PDFs da disciplina."""
    print("CALCULADORA: informe valores positivos, sem separador de milhar.")
    print("As vendas sao usadas como aproximacao da quantidade demandada.")
    p1 = ler_positivo("Preco do produto antes")
    p2 = ler_positivo("Preco do produto depois")
    q1 = ler_positivo("Vendas antes")
    q2 = ler_positivo("Vendas depois")
    med = indicadores([{"preco": p1, "quantidade": q1}, {"preco": p2, "quantidade": q2}])
    dq = med["quantidade_variacao_pct"] / 100
    dp = med["preco_variacao_pct"] / 100
    print(f"Preco: {med['preco_variacao_pct']:+.2f}% | Vendas: {med['quantidade_variacao_pct']:+.2f}%")
    print(f"Receita: R$ {med['receita_antes']:.2f} -> R$ {med['receita_depois']:.2f}")
    ed = med["elasticidade_preco"]
    print(f"Elasticidade-preco da demanda (modulo): {ed:.2f} ({med['classe']})" if ed is not None
          else "Elasticidade-preco da demanda: indefinida (preco nao mudou).")

    if perguntar_opcao("Calcular elasticidade cruzada com o preco de outro produto?"):
        y1 = ler_positivo("Preco do outro produto antes")
        y2 = ler_positivo("Preco do outro produto depois")
        dy = (y2 - y1) / y1
        print(f"Preco do outro produto: {dy * 100:+.2f}%")
        if dy == 0:
            print("Elasticidade cruzada: indefinida (preco do outro produto nao mudou).")
        else:
            exy = dq / dy
            leitura = ("sinal compativel com substitutos" if exy > 0 else
                       "sinal compativel com complementares" if exy < 0 else
                       "sem variacao nas vendas; nao prova independencia")
            print(f"Elasticidade cruzada: {exy:+.2f} ({leitura}).")

    if perguntar_opcao("Calcular elasticidade da oferta deste produto?"):
        s1 = ler_positivo("Quantidade ofertada antes (nao vendas)")
        s2 = ler_positivo("Quantidade ofertada depois (nao vendas)")
        ds = (s2 - s1) / s1
        print(f"Quantidade ofertada: {ds * 100:+.2f}%")
        if dp == 0:
            print("Elasticidade da oferta: indefinida (preco nao mudou).")
        else:
            es = ds / dp
            leitura = ("sinais opostos; conferir se a curva de oferta mudou" if es < 0 else
                       "oferta elastica" if es > 1 else
                       "oferta unitaria" if math.isclose(es, 1, rel_tol=1e-9) else
                       "oferta inelastica")
            print(f"Elasticidade da oferta: {es:+.2f} ({leitura}).")
    print("Comparar dois momentos nao prova que o preco causou as mudancas.")


def main() -> int:
    parser = argparse.ArgumentParser(description="VendeTexto - etapa 2: requisitos, semântica e sentimentos")
    parser.add_argument("--modo", choices=("cache", "demo", "coletar", "calculadora", "preparar"), default="cache")
    parser.add_argument("--produto", choices=("Caderno", "Caneca"), default="Caderno")
    parser.add_argument("--requisito", default="", help="Descricao adicional em portugues")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--analise-avancada", dest="analise_avancada", action="store_true",
                       help="Executa a etapa 2 (já é o comportamento padrão)")
    grupo.add_argument("--somente-etapa1", dest="analise_avancada", action="store_false",
                       help="Executa somente categorias, regex e painel herdados da etapa 1")
    parser.set_defaults(analise_avancada=True)
    parser.add_argument("--offline", action="store_true", help="Usa apenas modelos locais e não permite nova coleta")
    parser.add_argument("--modelos", type=Path, default=BASE / "modelos", help="Pasta local dos dois modelos")
    parser.add_argument("--saida", type=Path, help="Pasta dos resultados; padrão: saida (etapa 2) ou saida_etapa1")
    args = parser.parse_args()
    args.modelos = args.modelos.resolve()
    if args.saida is None:
        args.saida = BASE / ("saida" if args.analise_avancada else "saida_etapa1")
    if args.offline and args.modo == "coletar":
        parser.error("--modo coletar consulta a internet e não pode usar --offline. Use --modo cache.")
    if args.modo == "preparar":
        carregar_modelos(args.modelos, args.offline)
        print(f"Modelos prontos em {args.modelos}. Agora pode usar --modo cache --offline.")
        return 0
    if args.modo == "calculadora":
        print("Módulo herdado da etapa 1: a calculadora não executa análise textual.")
        calculadora()
        return 0
    args.saida.mkdir(parents=True, exist_ok=True)
    if args.modo == "coletar":
        registros = coletar_issues()
    elif args.modo == "cache":
        registros = snapshot_api()
    else:
        registros = exemplos_locais()
    if args.modo == "coletar":
        (args.saida / "issues_api.json").write_text(
            json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    if args.requisito.strip():
        registros.append({"origem": "usuario", "idioma": "pt", "titulo": "Pedido da empresa", "texto": args.requisito})
    resultados = analisar_textos(registros)
    if args.analise_avancada:
        embeddings, matriz = analisar_semanticamente(resultados, args.modelos, args.offline)
    else:
        print("ATENÇÃO: --somente-etapa1 desativa os modelos e não demonstra a etapa 2.")
    vendas = ler_vendas(BASE / "dados" / "vendas_ficticias.csv", args.produto)
    med = indicadores(vendas)
    grafico(vendas, args.produto, args.saida / "faturamento.png")
    grafico_categorias(resultados, args.saida / "categorias_issues.png")
    if args.analise_avancada:
        salvar_resultados_avancados(resultados, embeddings, matriz, args.saida)
    base = [r for r in resultados if r["origem"] != "usuario"]
    resumo = {
        "versao": VERSAO, "executado_em_utc": datetime.now(timezone.utc).isoformat(),
        "modo": args.modo, "etapa2_executada": args.analise_avancada,
        "offline": args.offline, "textos_corpus": len(base),
        "consultas_usuario": len(resultados) - len(base),
        "pipeline_spacy": {k: nlp.pipe_names for k, nlp in criar_analisadores().items()},
        "entrada_sha256": hashlib.sha256(json.dumps(registros, sort_keys=True,
                                                      ensure_ascii=False).encode()).hexdigest(),
        "sentimentos_corpus": dict(Counter(r["analise_semantica"]["sentimento"]["rotulo"] for r in base))
                              if args.analise_avancada else None,
        "vendas": {"natureza": "fictícia, separada das issues", "produto": args.produto, "indicadores": med},
        "limites_interpretacao": [
            "Cinco issues escolhidas não representam todos os usuários do ERPNext.",
            "Score agregado não mede acurácia nem urgência do requisito.",
            "Similaridade é um ranking relativo e não prova duplicidade.",
            "A agregação por fragmentos é uma aproximação da representação e do tom do documento.",
            "A consulta do usuário não altera as contagens nem os candidatos do corpus.",
        ],
    }
    (args.saida / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.saida / "analise.json").write_text(
        json.dumps(resultados, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
    )
    exibir(resultados, med, args.produto)
    print(f"\nArquivos gerados em: {args.saida}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, OSError, EOFError) as erro:
        print(f"\nERRO: {erro}", file=sys.stderr)
        raise SystemExit(2)
