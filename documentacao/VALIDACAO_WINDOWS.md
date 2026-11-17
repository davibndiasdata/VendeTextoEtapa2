# Validação no Windows e organização para o GitHub

## Execução acompanhada pela equipe

Davi forneceu os registros do PowerShell e os resultados produzidos no
Windows com Python 3.12.10 em `.venv`, usando os modelos em CPU.

- `pip check`: `No broken requirements found.`
- Preparação dos dois modelos concluída.
- `cache --offline`: cinco relatos reais em onze fragmentos.
- `coletar`: cinco issues consultadas na API do GitHub.
- `demo --offline`: cinco exemplos e uma consulta em português, produto Caneca.
- `cache --somente-etapa1` e calculadora demonstrados na preparação.
- `VENDETEXTO_TESTAR_MODELOS=1`: 16 testes aprovados em 48,369 segundos,
  conforme a saída do terminal enviada pela equipe.

Esse registro descreve a execução no computador de Davi; não é um novo teste
dos modelos no ambiente que organizou a publicação.

## Arquivos preservados

| Pasta do repositório | Origem no ZIP enviado | Conteúdo |
|---|---|---|
| `resultados_windows/cache` | `saida` | Análise dos relatos salvos. |
| `resultados_windows/coleta` | `saida_colet` | Coleta real e análise. |
| `resultados_windows/demo` | `saida_demo` | Exemplos, consulta e produto Caneca. |
| `resultados_windows/etapa1` | `saida_etapa1` | Comparação sem sentimentos e embeddings. |

`saida_colet` e `saida_coleta` tinham as mesmas análises e diferiam apenas
no horário de `resumo.json`; foi mantida a execução mais recente, de
`saida_colet`. O mesmo ocorreu entre `saida_dem` e `saida_demo`; foi mantida
`saida_demo`. O ZIP enviado permanece como registro integral das execuções.

O código principal, os testes, os arquivos de requisitos e os atalhos `.bat`
foram mantidos byte a byte. O SHA-256 do código principal também confere com
o manifesto que acompanhava o projeto revisado. Não foi alterada a numeração
das linhas usadas na apresentação.

A apresentação incluída contém 13 slides, conforme a decisão final da equipe.
O roteiro de leitura da equipe não foi incluído no repositório.

## Limites das verificações da publicação

Foram conferidos sintaxe dos arquivos Python, leitura dos JSONs, referências
locais do README, integridade dos arquivos copiados e estrutura do pacote.
Uma tentativa de repetir os testes neste ambiente ficou limitada pela ausência
de spaCy: nove passaram, três não puderam completar e quatro testes de modelos
foram ignorados por padrão. Esse resultado não substitui os 16 testes aprovados
no Windows e não foi tratado como evidência de falha do código.
