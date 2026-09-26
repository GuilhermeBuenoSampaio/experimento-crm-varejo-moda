# Relatório técnico final — experimento CRM em varejo de moda

**Data do fechamento:** 26/09/2026. **Escopo:** análise do experimento público MineThatData, pipeline Bronze/Silver/Gold, Azure, SQL Server, A/B e painel Power BI. Valores monetários em USD.

## Decisão de encerramento

O projeto foi encerrado neste recorte por decisão de escopo: as entregas atuais são suficientes para responder à pergunta de conversão de compra de cada e-mail frente ao grupo sem e-mail e demonstrar o fluxo de dados, reconciliação e comunicação executiva. Segmentação adicional, inferência entre os dois e-mails e modelos preditivos não fazem parte desta versão. Encerramento de escopo não equivale a dizer que a base suporta conclusões sobre lucro ou identidade de clientes.

## Fonte, granularidade e percurso

Fonte: desafio Email Analytics da MineThatData, de Kevin Hillstrom. O conjunto tem 64.000 registros experimentais, sem ID de cliente. A chave técnica `(source_sha256, source_row_number)` identifica a linha original. Os 6.562 registros com atributos idênticos aos de outra linha não foram eliminados, pois igualdade de atributos não prova repetição da pessoa. O CSV original foi preservado; a Silver aplica nomes em português e é armazenada em Parquet. A Gold contém uma dimensão de três grupos e uma fato de 64.000 registros. O projeto publicou as camadas no Azure e reconciliou Gold com SQL Server e Power BI. A verificação automatizada local e remota final é realizada por `src/finalizar_projeto.py`; seu resultado depende das evidências acessíveis no computador da execução.

## Definições e fórmulas

Para grupo `g`, `n_g` é o número de registros atribuídos; `v_g` soma `visit=1`; `c_g` soma `conversion=1`; `s_g` soma `spend` em USD. Taxa de visita = `v_g / n_g`. Taxa de conversão = `c_g / n_g` (intenção de tratar), nunca `c_g / v_g`. Vendas por registro = `s_g / n_g`. Para tratamento `t` e controle `c`, diferença em pontos percentuais = `100 × (c_t/n_t − c_c/n_c)`; uplift relativo = `((c_t/n_t)/(c_c/n_c) − 1) × 100%`, indefinido se a taxa do controle for zero. Os totais são recalculados pelas somas, não pela média simples das taxas de grupos.

| Grupo | Registros n | Visitas v | Compras c | Vendas USD s | Visitas / n | Compras / n | USD / n |
|---|---:|---:|---:|---:|---:|---:|---:|
| Sem e-mail | 21.306 | 2.262 | 122 | 13.908,33 | 10,6167% | 0,572609% | 0,652789 |
| E-mail feminino | 21.387 | 3.238 | 189 | 23.038,11 | 15,1400% | 0,883714% | 1,077201 |
| E-mail masculino | 21.307 | 3.894 | 267 | 30.311,69 | 18,2757% | 1,253109% | 1,422616 |
| **Total** | **64.000** | **9.394** | **578** | **67.258,13** | **14,678125%** | **0,903125%** | **1,050908** |

Exemplo feminino: `189 / 21.387 = 0,008837144`; controle: `122 / 21.306 = 0,005726087`. Logo, `(0,008837144 − 0,005726087) × 100 = 0,31110575 pp` e `(0,008837144 / 0,005726087 − 1) × 100 = 54,3313%`. Masculino: `267 / 21.307 = 0,012531093`; diferença `0,68050065 pp` e uplift `118,8422%`. O painel arredonda para 0,88%, 0,57%, 1,25%, +0,31 pp e +0,68 pp.

## Inferência A/B

O contrato analítico definiu duas comparações bilaterais, cada e-mail contra sem e-mail. Para cada uma, `H0: p_t = p_c`; `H1: p_t ≠ p_c`. O teste z usa a proporção combinada `p_pool=(c_t+c_c)/(n_t+n_c)`, erro sob H0 `sqrt[p_pool(1−p_pool)(1/n_t+1/n_c)]`, `z=(p_t−p_c)/EP_H0` e p bilateral `2 Φ(−|z|)`. Os dois p brutos foram multiplicados por 2 (Bonferroni, limitados a 1), com erro familiar de 5%. O IC normal de 97,5% usa erro não combinado `sqrt[p_t(1−p_t)/n_t+p_c(1−p_c)/n_c]` e crítico normal `Φ⁻¹(0,9875)`. Cada braço tem pelo menos cinco compras e cinco não compras. Valores abaixo foram reproduzidos do algoritmo de `src/06_analisar_ab.py` com as contagens reconciliadas.

| Comparação com controle | Diferença pp | Uplift relativo | z | IC 97,5% da diferença pp | p bruto | p Bonferroni |
|---|---:|---:|---:|---|---:|---:|
| E-mail feminino | +0,311106 | +54,3313% | 3,77956 | [+0,126715; +0,495496] | 0,000157105 | 0,000314210 |
| E-mail masculino | +0,680501 | +118,8422% | 7,38511 | [+0,474101; +0,886900] | 1,52322 × 10⁻¹³ | 3,04645 × 10⁻¹³ |

Ambos os p ajustados são menores que 0,05. Isto é evidência estatística nas duas comparações especificadas, sob a suposição de unidades independentes e atribuição adequada. Não houve teste masculino versus feminino. Visita e vendas por registro são descritivas; não se atribuiu significância a elas. O gasto representa vendas observadas, não custo, margem ou lucro.

## Reconciliação e evidências

A consulta `sql/02_reconciliar_kpis_power_bi.sql` produziu os grupos e totais acima. O documento `docs/validacoes/reconciliacao_sql_power_bi_2026-09-25.md` registra a comparação com a tabela e os cartões Power BI. `power_bi/medidas_crm.dax` documenta as fórmulas e `power_bi/experimento_crm_varejo_moda.pbix` contém o painel. `docs/visao_executiva_power_bi.png` é a captura publicada. Os números da interface foram conferidos pelo responsável; o relatório SQL/Power BI não substitui uma consulta automatizada em tempo real.

O executor `src/finalizar_projeto.py` verifica locais, tamanhos e SHA-256 de Silver/Gold, agregados da auditoria A/B, recibos Azure e SQL, arquivos finais e inventário Git. Quando a Azure CLI está acessível, confere presença e tamanho dos blobs Gold; os hashes remotos permanecem respaldados pelos recibos de publicação, não são baixados novamente pelo executor. Ele não consulta a visibilidade do repositório GitHub nem executa SQL ao vivo. Se alguma evidência faltar, registra `blocked`. Rodar `git fetch origin` antes da auditoria para atualizar a referência remota local. O recibo fica fora do Git em `docs/execucoes/FINAL01/finalizacao.json`.

## Limitações e interpretação

Não há identificador de pessoa, abertura, clique, custo de envio, margem nem data individual. Assim, não se consegue auditar recontatos ou independência entre linhas, atribuir mecanismo de resposta, estimar lucro/ROI ou fazer análise temporal individual. A fonte descreve um experimento, mas a atribuição individual não é verificável neste arquivo. A leitura se limita ao contraste observável entre os grupos e aos testes previamente especificados.

## Registro de tempo

O primeiro registro visual disponível desta sessão em 26/09/2026 tem carimbo de arquivo **17:16:22** (America/Sao_Paulo). Ele é um marco aproximado da retomada, não a hora exata de envio da primeira mensagem. Às **19:13** o responsável confirmou a visibilidade privada; às **19:17** confirmou a alteração para público, verificada separadamente pela API do GitHub. O intervalo entre o primeiro marco visual e a confirmação pública foi de aproximadamente **2h00min38s**. Pausas de hoje não foram informadas; horas efetivas não foram apuradas. O recibo `FINAL01` não testa a visibilidade e conserva `not_verified` nesse item. Ver `docs/registro_diario.md`.

## Referências internas

- `metadata/contrato_analitico.md`: hipóteses e denominadores.
- `src/06_analisar_ab.py`: cálculos inferenciais.
- `docs/validacoes/reconciliacao_sql_power_bi_2026-09-25.md`: totais e conferência.
- `power_bi/medidas_crm.dax`: medidas do painel.
- `docs/visao_executiva_power_bi.md`: narrativa do painel.
