# Relatório executivo final — experimento CRM em varejo de moda

**Fechamento de escopo:** 26/09/2026. O projeto termina neste recorte porque os dados, a análise A/B, a reconciliação e o painel já respondem à pergunta proposta. Não serão acrescentadas outras análises nesta versão.

## Pergunta e resultado

Em 64.000 registros experimentais, dois grupos receberam e-mail e um não recebeu. A taxa de compra foi de **0,57%** sem e-mail, **0,88%** com e-mail feminino e **1,25%** com e-mail masculino. Frente ao controle, as diferenças foram de **+0,31** e **+0,68 ponto percentual**, respectivamente. Ambas as comparações com o controle foram estatisticamente significativas após ajuste de Bonferroni para dois testes. Não foi realizado contraste estatístico direto entre os dois e-mails.

| Grupo | Registros | Compras | Conversão | Visitas | Vendas observadas USD |
|---|---:|---:|---:|---:|---:|
| Sem e-mail | 21.306 | 122 | 0,57% | 2.262 | 13.908,33 |
| E-mail feminino | 21.387 | 189 | 0,88% | 3.238 | 23.038,11 |
| E-mail masculino | 21.307 | 267 | 1,25% | 3.894 | 30.311,69 |
| **Total** | **64.000** | **578** | **0,90%** | **9.394** | **67.258,13** |

## Decisão e alcance

O achado apoia considerar campanhas de e-mail em um novo teste operacional, com medição de custo, margem e identificação de clientes. Os valores acima são vendas observadas, não lucro. Sem custo da campanha ou margem, não é possível afirmar rentabilidade; sem ID individual, a independência entre registros não pode ser auditada. O estudo também não mede aberturas nem cliques.

## Entrega do projeto

O percurso Bronze, Silver e Gold, a publicação no Azure, os indicadores no SQL Server e o painel Power BI foram documentados e reconciliados. O repositório inclui scripts Python, SQL, medidas DAX, captura do painel e arquivo `.pbix`. O executor final verifica as evidências acessíveis no ambiente local e registra pendências explicitamente. A análise técnica completa, inclusive fórmulas, intervalos de confiança e valores de p, consta em `docs/relatorio_tecnico_final.md`.

**Adendo de encerramento:** encerramos o projeto aqui por suficiência para a pergunta e para o objetivo de portfólio. Trabalhos futuros possíveis não são entregas pendentes deste escopo.
