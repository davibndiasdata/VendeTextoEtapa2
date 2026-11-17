# Mapa para a equipe estudar o código

O ponto de entrada continua sendo `vendetexto2.py`, em um único arquivo.

| Parte | Funções/classes para localizar | O que explicar |
|---|---|---|
| Fonte textual | `coletar_issues`, `snapshot_api`, `exemplos_locais` | Diferença entre API atual, cópia real salva e textos inventados. |
| Limpeza | `limpar`, `extrair_numeros` | Remoção de ruído e padrões monetários/unidades com regex. |
| Pipeline | `ExtratorRequisitos`, `criar_extrator_requisitos`, `criar_analisadores` | Componentes registrados, Doc, PhraseMatcher e ordem da pipeline. |
| Processamento | `analisar_textos` | Como as anotações viram categorias, evidências, contexto e sentenças. |
| Modelos | `carregar_modelos` | CPU, versões fixas, primeiro download e uso offline. |
| Textos longos | `fragmentar_sentencas` | Por que verificar os limites de ambos os tokenizadores. |
| Agregação | `agregar_fragmentos` | Pesos por tokens, média das probabilidades e normalização dos vetores. |
| Etapa 2 | `analisar_semanticamente` | encode, pipeline de sentimentos, cosseno, ranking e tratamento da consulta. |
| Evidências | `salvar_resultados_avancados`, `exibir` | CSV, vetores, distribuição de sentimentos, matriz e leitura do terminal. |
| Módulos herdados | `ler_vendas`, `indicadores`, `calculadora`, `grafico`, `grafico_categorias` | Separação entre texto real e indicadores fictícios. |
| Fluxo final | `main` | Opções, ativação padrão da etapa 2 e arquivos de saída. |

## Distinções importantes

`spaCy pipeline` é a sequência linguística que processa o Doc.
`transformers.pipeline` é o objeto de inferência do classificador pré-treinado.
O mesmo nome “pipeline” não torna os dois objetos equivalentes.

Tokens spaCy, tokens do modelo de embeddings e tokens do classificador são
contagens diferentes. O JSON mostra as contagens específicas e os limites
dos modelos; não é correto usar a quantidade de tokens do spaCy para decidir
se a entrada cabe em um Transformer.

Um embedding tem 384 dimensões. Esse número não é a quantidade de palavras
do texto e não é o limite de tokens de entrada.

O cosseno usa vetores normalizados. Um score de 0,60 não significa “60% de
probabilidade de os requisitos serem iguais”.

O score de sentimento é uma saída do modelo, agregada quando há vários
fragmentos. Ele não mede a taxa de acerto em issues do ERPNext.
