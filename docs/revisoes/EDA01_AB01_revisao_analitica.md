# Revisão analítica — EDA01 e AB01

Data da revisão: 24/09/2026 (horário de Brasília). Escopo: conferência dos relatórios apresentados pelo responsável pelo projeto, com análise aritmética e metodológica. A revisão não substitui a auditoria técnica automática nem uma inspeção independente de todos os registros da Silver.

## Evidências recebidas

- Relatório EDA: `docs/execucoes/EDA01/04_eda_silver.md`, SHA-256 da cópia examinada: `d30d34c255832de0322f1d2ad76a204df019e305d2bf4a0912e5bfa4d7c03535`.
- Relatório A/B: `docs/execucoes/AB01/06_analise_ab.md`, SHA-256 da cópia examinada: `064893da5625e36ba5b4e3eb452ce1269f4608d1326269da76d91f8bd500c5da`.
- Parquet Silver referenciado na EDA: SHA-256 `c1e5f9d82b2557faae0dc4d915779ed5c2cd85435bff042b72a7cecaa75186b4`.

## Conferências

| Critério | Resultado |
|---|---|
| Registros por grupo | 21.306 + 21.307 + 21.387 = 64.000 |
| Compras por grupo | 122 + 267 + 189 = 578 |
| Visitas por grupo | 2.262 + 3.894 + 3.238 = 9.394 |
| Gasto por grupo | US$ 13.908,33 + US$ 30.311,69 + US$ 23.038,11 = US$ 67.258,13 |
| EDA | 64.000 chaves técnicas distintas; grafias previstas; SMD numéricas e binárias inferiores a 0,01 em módulo |
| Comparações planejadas | E-mail masculino × controle; e-mail feminino × controle; ambas com p ajustado de Bonferroni inferior a 0,05 |

## Leitura dos resultados

- Controle: 122/21.306 = 0,573% de conversão.
- E-mail masculino: 267/21.307 = 1,253%; diferença de +0,6805 ponto percentual (IC simultâneo aproximado de 97,5%: +0,4741 a +0,8869 pp); uplift relativo de 118,84%.
- E-mail feminino: 189/21.387 = 0,884%; diferença de +0,3111 ponto percentual (IC de 97,5%: +0,1267 a +0,4955 pp); uplift relativo de 54,33%.
- Os dois contrastes contra controle são estatisticamente significativos segundo o método pré-definido. A magnitude comercial ainda depende de custo de envio e margem. O relatório não testa diretamente masculino contra feminino.

## Decisão de revisão

**Aprovado para continuidade da análise**, com os limites abaixo. Este registro complementa os JSONs imutáveis das execuções, cujos campos `analytic_review` permanecem `pending`; o estado conjunto passa a ser interpretado pela existência deste documento de revisão, sem alterar retroativamente a saída da execução.

## Limitações e pendências

1. Não existe ID de cliente: a chave técnica identifica registro. A independência entre registros e a ausência de recontato não são verificáveis nesta fonte.
2. As diferenças padronizadas de atributos históricos numéricos e binários são pequenas, mas o relatório EDA remete as distribuições categóricas por grupo ao JSON local, que não foi apresentado nesta revisão.
3. Não há abertura, clique, custo de campanha ou margem; visitas e receita por registro são descritivas, sem teste de hipótese nesta versão.
4. Não concluir que o e-mail masculino supera o feminino sem comparação direta planejada e respectivo controle de multiplicidade.
5. Antes de uma recomendação comercial, documentar cenário de custo e margem como hipótese externa ou solicitar dados reais; não atribuir valores hipotéticos à fonte.
