# Ajustes da revisão da etapa 2

## Autoria e continuidade

A base da etapa 2 foi recebida de **Angélica Maria da Silva**. Ela já
acrescentava a análise semântica, os embeddings e a classificação de
sentimentos ao VendeTexto da primeira etapa. Esta revisão parte desse
trabalho e conserva os dois modelos escolhidos, o corpus, as categorias,
as opções de coleta e a calculadora.

A equipe é composta por **Angélica Maria da Silva, Leonardo Pessoa de Souza
e Davi Batista Nóbrega Dias**. Os ajustes técnicos e a organização deste
pacote tiveram apoio do ChatGPT. A cópia exata do arquivo recebido está em
`original/vendetexto2_angelica.py`, para comparar sem perder a versão inicial.

## O que foi corrigido

| Ponto | Versão recebida | Versão revisada |
|---|---|---|
| Pipeline do spaCy | Tokenização e chamada externa do PhraseMatcher; `pipe_names` vazio. | Pipeline com `sentencizer` e componente próprio `requisitos_vendetexto`, usando PhraseMatcher e contexto das sentenças. |
| Participação da pipeline | Categorias extraídas fora dos componentes. | Requisitos anotados no Doc e sentenças usadas na divisão dos textos para os modelos. |
| Falta do spaCy | Busca silenciosa por substrings, com saída chamada “spaCy”. | Erro claro com instrução de instalação; não apresenta outro mecanismo como se fosse spaCy. |
| Textos longos | Cada modelo podia cortar a entrada de forma diferente. | Fragmentos que cabem nos dois modelos, com cobertura completa do texto limpo e verificação nos testes. |
| Resultado por documento | Inferência de uma entrada possivelmente truncada. | Agregação documentada dos embeddings e probabilidades dos fragmentos. |
| Sentimentos | Apenas classe e score vencedor. | Três probabilidades por fragmento e por documento; classe e score agregado. |
| Similaridade | Vizinho identificado pelo índice. | Vizinho com ID, título, URL e cosseno; exclusão do próprio texto. |
| Consulta do usuário | Entrava na lista geral de candidatos. | Busca no corpus sem alterar os candidatos e contagens das issues. |
| Ativação | Exigia lembrar `--analise-avancada`. | Etapa 2 habilitada por padrão; opção antiga preservada e `--somente-etapa1` explícito. |
| Dependências | Novo arquivo de instalação mencionado, mas ausente. | Requisitos com versões fixadas, instalação de PyTorch para CPU e ambiente virtual. |
| Primeiro download | Dependia do primeiro uso durante a análise. | Modo `preparar` salva os modelos; `--offline` exige arquivos locais e impede nova coleta. |
| Evidência de resultados | Gráficos de categorias e faturamento da etapa 1. | Acrescentados CSVs, embeddings, gráfico de sentimentos e matriz de similaridade reais. |
| Entrega | Um arquivo Python separado dos dados. | ZIP com dados, código, instalador, testes, documentação, original e exemplos de saída. |

## Decisões técnicas

- A pipeline spaCy é por regras. Não foi acrescentada uma etapa estatística
  apenas para exibir nomes de componentes. Cada componente é utilizado.
- Os Transformers continuam pré-treinados. O grupo faz inferência, não
  treinamento ou fine-tuning.
- As revisões dos modelos são fixas. O preparo acontece uma vez e os pesos
  ficam locais; não é necessário criar conta ou chave de API para estes modelos públicos.
- A representação de documentos longos usa uma média ponderada seguida
  de normalização. É uma aproximação explicitada no README e na saída.
- O score agregado de sentimentos não foi chamado de acurácia. Não há
  prioridade automática de requisitos ou conclusão comercial baseada nele.
- Os modos da etapa 1 continuam disponíveis, inclusive calculadora com
  demanda, elasticidade cruzada e oferta. O CSV continua identificado como fictício.
- As fontes e o repositório remoto não foram alterados. A revisão é uma
  nova entrega, pronta para a equipe conferir e integrar ao seu repositório.

## Como conferir rapidamente

1. Execute a instalação e depois `--modo cache --offline`.
2. Veja `Pipeline spaCy: sentencizer, requisitos_vendetexto` no terminal.
3. Abra `analise.json` e confira contexto, fragmentos, três probabilidades,
   dimensões do embedding e identificação dos vizinhos.
4. Veja `sentimentos.png` e `similaridade.png`.
5. Consulte `VALIDACAO.md` e execute os testes descritos no README.

O parecer anterior avaliava a versão recebida. As pendências de código
apontadas nele foram tratadas nesta nova versão; o registro atual de
execução e limitações é `VALIDACAO.md`. O planejamento da apresentação,
slides e roteiro será feito sobre esta versão revisada, com os três integrantes.
