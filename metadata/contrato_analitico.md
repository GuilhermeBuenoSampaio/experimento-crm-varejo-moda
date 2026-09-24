# Contrato analítico — rascunho para aprovação

**Pergunta:** qual e-mail produz compras incrementais em relação a não enviar e-mail?

- População: todos os registros sorteados no arquivo; a fonte declara clientes com compra nos doze meses anteriores.
- Grupos: `Mens E-Mail` e `Womens E-Mail`, cada um comparado a `No E-Mail`.
- Janela de resultado: duas semanas após o envio, conforme descrição da fonte.
- Métrica principal: soma de `conversion` dividida pelo número de registros do grupo.
- Comparações planejadas: cada grupo de e-mail versus controle; diferença absoluta em pontos percentuais e relativa ao controle.
- Métricas secundárias: proporção com `visit=1` e soma de `spend` dividida por todos os registros sorteados do grupo.
- Inferência planejada: intervalo de confiança e teste de duas proporções para as duas comparações primárias; documentar multiplicidade. Receita por registro será analisada separadamente, com incerteza apropriada para muitos zeros.
- Critério de interpretação: magnitude, incerteza e coerência comercial; sem custo e margem não há conclusão sobre lucro.

**Limites:** não há cliente_id, data individual, abertura, clique, custo de campanha ou margem. Nenhuma dessas medidas será inventada.

Este documento antecede a abertura das métricas de resultado por grupo. Revisões terão versão, data e justificativa.

Na Silver, os nomes e categorias em português seguirão `metadata/dicionario_traducao.md`. Valores financeiros continuarão expressos em USD.
