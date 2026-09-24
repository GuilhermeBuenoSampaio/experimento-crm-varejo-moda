# Contrato analítico — versão 1.0 (definições da análise A/B)

**Pergunta:** qual e-mail produz compras incrementais em relação a não enviar e-mail?

- População: todos os registros sorteados no arquivo; a fonte declara clientes com compra nos doze meses anteriores.
- Grupos: `Mens E-Mail` e `Womens E-Mail`, cada um comparado a `No E-Mail`.
- Janela de resultado: duas semanas após o envio, conforme descrição da fonte.
- Métrica principal: soma de `conversion` dividida pelo número de registros do grupo.
- Comparações planejadas: cada grupo de e-mail versus controle; diferença absoluta em pontos percentuais e relativa ao controle.
- Métricas secundárias: proporção com `visit=1` e soma de `spend` dividida por todos os registros sorteados do grupo.
- Inferência planejada: intervalo de confiança e teste de duas proporções para as duas comparações primárias; documentar multiplicidade. Receita por registro será analisada separadamente, com incerteza apropriada para muitos zeros.
- Hipótese primária bilateral em cada comparação: H0, taxa de compra do e-mail igual à taxa do controle; H1, taxas diferentes. Teste z de duas proporções com variância combinada sob H0.
- Família de dois testes primários: controle de erro familiar de 5% pelo ajuste de Bonferroni. Reportar p bruto e p ajustado (mínimo entre 1 e 2 × p bruto), além de intervalo normal não combinado de 97,5% para a diferença absoluta. A aproximação normal só é aplicada se houver pelo menos cinco compras e cinco não compras em cada braço; caso contrário, interromper a inferência e revisar o método.
- Efeito relativo = (taxa do e-mail − taxa do controle) / taxa do controle. Se a taxa controle for zero, registrar como indefinido. Visitas e receita por registro são descritivas nesta etapa, sem afirmação de significância estatística ou lucro.
- Critério de interpretação: magnitude, incerteza e coerência comercial; sem custo e margem não há conclusão sobre lucro.

**Limites:** não há cliente_id, data individual, abertura, clique, custo de campanha ou margem. Nenhuma dessas medidas será inventada.

Estas definições antecedem a abertura das métricas de resultado por grupo. Revisões terão versão, data e justificativa. A ausência de ID individual impede verificar independência entre linhas ou recontato; os resultados dependem da interpretação da fonte de que cada registro representa uma unidade sorteada.

Na Silver, os nomes e categorias em português seguirão `metadata/dicionario_traducao.md`. Valores financeiros continuarão expressos em USD.
