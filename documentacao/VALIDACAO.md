# Registro de validação - 16/11/2026

## Ambiente e instalação

- Linux, Python 3.12, execução dos modelos em CPU.
- Criado um ambiente virtual novo, separado dos pacotes já existentes.
- Instalado PyTorch CPU por `requirements-torch-cpu.txt` e depois todas as
  dependências de `requirements.txt`.
- `pip check`: nenhum conflito de requisitos no ambiente novo.
- A lista completa dos pacotes instalados está em `AMBIENTE_TESTADO.txt`.
- Os dois modelos foram efetivamente baixados, salvos e carregados.
- Windows e execução dos `.bat` não foram testados em um computador Windows.
  O README usa Python 3.12 e um ambiente virtual, e a equipe deve conferir
  essa execução no computador que apresentará o trabalho.

## Testes automatizados

**16 testes aprovados**, incluindo os quatro que usam pesos reais. Os testes
de inferência foram executados com `VENDETEXTO_TESTAR_MODELOS=1`,
`HF_HUB_OFFLINE=1` e `TRANSFORMERS_OFFLINE=1`, após preparar os arquivos locais.

Cobertura:

- Componentes do spaCy executados, categorias e contexto no Doc.
- “Preconceito” não confundido com a categoria de preço.
- Falha clara quando spaCy não está disponível.
- Limpeza conserva o texto visível de links Markdown.
- Fragmentação conserva todas as palavras e respeita ambos os limites.
- Média ponderada, normalização e distribuições de probabilidades.
- Embeddings reais com dimensão 384 e norma unitária.
- Matriz simétrica, diagonal próxima de 1 e ranking ordenado sem autocomparação.
- Consultas do usuário excluídas dos candidatos do corpus.
- Casos de controle positivo em inglês e negativo em português.
- Regressão dos indicadores de Caderno/Caneca e preço sem variação.
- Calculadora com demanda, cruzada e oferta.
- Execução a partir de outra pasta com espaços no caminho.
- Rejeição de coleta com `--offline`.
- Nova tentativa após falha transitória da API, sem substituição por cache.

O teste de repetição da API usa respostas controladas para verificar o fluxo
de erro. Separadamente, a coleta real pela API também foi executada com
sucesso. Os casos de sentimento são controles de funcionamento, não uma
estimativa de acurácia no domínio de Engenharia de Software.

## Execuções completas

| Execução | Resultado |
|---|---|
| `cache --offline`, etapa 2 padrão | Cinco issues reais do snapshot, 11 fragmentos, embeddings de 384 dimensões e todos os nove arquivos de saída. |
| `demo --offline`, Caneca e consulta em português | Seis textos processados, cinco contados no corpus e uma consulta separada. |
| `coletar`, etapa 2 padrão | Cinco issues consultadas na API, coleta salva e análise avançada concluída. |
| `cache --somente-etapa1` | Categorias e indicadores herdados funcionando, com aviso de que não demonstra a etapa 2. |
| `calculadora` | Demanda 0,45, cruzada +0,75 e oferta +0,25 no caso reproduzível do README. |

A primeira tentativa de coleta desta revisão apresentou timeout. A versão
final informa o andamento, faz no máximo duas tentativas por issue em erros
transitórios e oferece uma mensagem clara caso a API permaneça indisponível.
Não há garantia de disponibilidade futura da rede ou da API pública.

## Resultados de exemplo do snapshot

| Issue | Classe prevista | Score agregado | Fragmentos | Vizinho mais próximo | Cosseno |
|---|---|---:|---:|---|---:|
| #40751 | Negativo | 0,4734 | 1 | #43935 | 0,5683 |
| #43635 | Positivo | 0,6074 | 1 | #7788 | 0,5863 |
| #7788 | Negativo | 0,4536 | 1 | #43635 | 0,5863 |
| #43935 | Negativo | 0,4354 | 2 | #40751 | 0,5683 |
| #53760 | Negativo | 0,4981 | 6 | #43635 | 0,4149 |

Os valores vêm de `resultados_exemplo/cache_real/analise.json`, com
arredondamento somente nesta tabela. A previsão agregada teve quatro
negativos e um positivo. Isso não significa quatro usuários insatisfeitos:
os relatos descrevem bugs e solicitações técnicas, com linguagem mista.

#43635 pede um filtro por marca e elogia o relatório existente, o que ajuda
a contextualizar a classe positiva. #7788 relata dificuldade para analisar
nomes de clientes por códigos. O par #43635/#7788 compartilha o tema de
melhorias no Sales Analytics Report, mas as funcionalidades pedidas são
diferentes. O ranking sugere relação temática, sem demonstrar duplicidade.

Os scores próximos de 0,45-0,50 reforçam a necessidade de consultar as três
probabilidades e ler o relato original. Não houve validação estatística de
acurácia, calibração ou limiar de duplicidade com uma base rotulada.

## Integridade e limites da entrega

- A cópia `original/vendetexto2_angelica.py` foi comparada por SHA-256 com o
  arquivo recebido e é idêntica byte a byte.
- O ZIP não inclui ambiente virtual, caches, credenciais ou pesos dos modelos.
  O instalador obtém bibliotecas e pesos no primeiro uso.
- As saídas salvas são resultados reais de exemplo; novas execuções têm
  seu próprio `resumo.json` e hash da entrada.
- O programa preserva o texto **após a limpeza de ruído**. Código em blocos,
  tags e URLs são removidos intencionalmente pelo pré-processamento.
- A agregação por fragmentos é uma aproximação documentada. Não equivale
  a treinar um classificador específico para documentos técnicos longos.
- O repositório remoto e o arquivo enviado pelo usuário não foram modificados.
