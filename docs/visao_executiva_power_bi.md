# Visão Executiva — experimento CRM em varejo de moda

## Pergunta e desenho

Qual foi a diferença na taxa de compra entre cada grupo que recebeu e-mail e o grupo sem e-mail nos 14 dias observados? A unidade da base é o registro experimental. A chave técnica identifica uma linha do arquivo, não um cliente conhecido. Os dois e-mails são comparados separadamente ao controle; não foi realizado teste direto entre eles.

## Indicadores do painel

| Indicador | Definição | Total |
|---|---|---:|
| Registros atribuídos | Linhas da fato, incluindo todos os grupos | 64.000 |
| Visitas válidas | Soma do indicador de visita em 14 dias | 9.394 |
| Compras válidas | Soma do indicador de compra em 14 dias | 578 |
| Gasto total | Soma do gasto observado em 14 dias, em USD | US$ 67.258,13 |
| Taxa de visita | Visitas / registros atribuídos | 14,68% |
| Taxa de conversão | Compras / registros atribuídos | 0,90% |

As taxas não usam visitas como denominador. Gasto é valor de vendas observado, não lucro.

## Comparação por grupo

| Grupo | Registros | Visitas | Compras | Conversão | Gasto por registro (USD) | Diferença vs. controle | Uplift relativo |
|---|---:|---:|---:|---:|---:|---:|---:|
| Sem e-mail | 21.306 | 2.262 | 122 | 0,57% | 0,65 | — | — |
| E-mail feminino | 21.387 | 3.238 | 189 | 0,88% | 1,08 | +0,31 ponto percentual | +54,33% |
| E-mail masculino | 21.307 | 3.894 | 267 | 1,25% | 1,42 | +0,68 ponto percentual | +118,84% |

Os resultados arredondados acima são para apresentação. Os cálculos e a reconciliação com SQL Server estão em `metadata/contrato_analitico.md`, `power_bi/medidas_crm.dax` e `docs/validacoes/reconciliacao_sql_power_bi_2026-09-25.md`. As duas comparações com o controle foram classificadas como estatisticamente significativas na análise A/B, com ajuste de Bonferroni; intervalos de confiança e valores de p pertencem à saída Python, não aos cartões DAX.

## Leitura executiva e limites

Ambos os grupos de e-mail apresentaram conversão maior que o controle nesta base. O painel não estabelece superioridade estatística do e-mail masculino sobre o feminino, pois esse contraste não foi testado. A interpretação do experimento depende de tratar cada registro como unidade sorteada independente; sem ID de cliente não é possível auditar recontatos ou independência entre linhas. A base não informa abertura, clique, custo da campanha ou margem, portanto não permite estimar lucro ou retorno sobre investimento.

## Evidência visual e status

O responsável confirmou a reconciliação dos cartões e da tabela no Power BI Desktop em 26/09/2026 e salvou o `.pbix`. Os números exibidos coincidem com os totais documentados. Uma captura limpa do painel e o caminho do arquivo `.pbix` ainda devem ser registrados antes da publicação do projeto. O relatório de finalização fará a conferência de GitHub, Azure e proteção dos artefatos.
