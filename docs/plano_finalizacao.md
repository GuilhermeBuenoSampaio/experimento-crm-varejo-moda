# Plano da etapa final — `src/finalizar_projeto.py`

**Estado:** executada em 26/09/2026 como `FINAL01`. Conferências locais, dados, recibos, Azure, SQL e Git local aprovadas. Após a execução, o responsável tornou o repositório público; a visibilidade pública foi verificada separadamente pela API do GitHub às 19:17 (America/Sao_Paulo). O resultado histórico `github_visibilidade: not_verified` no recibo `FINAL01` permanece correto para o escopo do executor, que não consulta a API do GitHub. Ver `docs/registro_diario.md` e recibo local fora do Git.

## Objetivo e comportamento

O finalizador reunirá as evidências de cada etapa, fará uma última reconciliação e atualizará os documentos de encerramento com resultados efetivamente validados. Sua execução padrão será somente leitura e produzirá um plano de pendências. A opção explícita de finalização escreverá um novo relatório de auditoria e a versão final dos documentos, sem sobrescrever execuções anteriores. Falha ou evidência indisponível resultará em `blocked`, nunca em aprovação presumida.

## Critérios obrigatórios

| Área | Verificação exigida | Evidência |
|---|---|---|
| Fonte e camadas | SHA-256 da fonte; 64.000 registros reconciliados; Bronze preservada; Silver Parquet e Gold aprovadas conforme contratos. | Manifestos, validações e relatórios por execução. |
| Experimento | Grupos, denominadores, métricas, comparações, testes, incerteza, multiplicidade e limitações coerentes com o contrato analítico. | Saídas aprovadas dos cálculos e relatório técnico. |
| Consistência | Indicadores Python, SQL Server e Power BI usam a mesma definição; diferenças numéricas dentro de tolerância documentada. | Reconciliação versionada; nenhuma métrica é declarada conferida sem evidência acessível. |
| Azure | Contêiner esperado acessível; objetos obrigatórios presentes; tamanho e SHA-256 remoto conferidos; acesso público desabilitado quando verificável. | Recibos de publicação e verificações de leitura no Azure. |
| GitHub | Repositório e branch esperados, visibilidade privada durante desenvolvimento, commit remoto sincronizado e lista de arquivos permitidos. | Metadados autenticados do repositório, estado Git e inventário do commit. |
| Proteção | CSV, Parquets, `.env`, segredos, tokens e recibos detalhados ausentes do histórico versionado; destinos dos artefatos conferidos; nenhum valor sensível impresso no relatório. | Inventário de caminhos rastreados e checagens de padrões, com revisão humana de falsos positivos. |
| Documentação | Registro diário, decisões, limitações, relatório técnico e resumo executivo completos e alinhados com a execução aprovada. | Versões finais e identificadores das execuções citadas. |

O escaneamento de padrões não prova ausência absoluta de segredos. A visibilidade do GitHub e a política de acesso do Azure exigem consultas autenticadas; se essas consultas falharem, o resultado fica `blocked`. Não se infere privacidade a partir de `git remote` ou de um arquivo `.gitignore`.

## Saídas previstas

- `docs/execucoes/<id>/finalizacao.json`: resultado por critério, horários UTC, hashes, caminhos de evidência e pendências; sem credenciais ou conteúdo bruto.
- `docs/execucoes/<id>/finalizacao.md`: relatório técnico da conferência e limitações remanescentes.
- README e relatórios finais atualizados somente com fatos conferidos. Uma síntese pública pode ser versionada; detalhes de execução permanecem fora do GitHub.

## Regras de execução

1. Verificar pré-requisitos e dependências de acesso antes de modificar documentos.
2. Não alterar dados Bronze/Silver/Gold nem apagar artefatos como efeito da finalização.
3. Não sobrescrever um ID de execução. Falha parcial permanece auditável e pode ser retomada com novo ID.
4. Exigir reconciliação remota após eventual publicação final; somente então registrar `approved`.
5. Qualquer critério obrigatório não verificado impede declarar o projeto concluído. A revisão humana aprova a interpretação de negócio e a publicação do resumo executivo.

**Implementação:** `src/finalizar_projeto.py`. A auditoria não executa SQL ao vivo, não baixa novamente os blobs Azure para recalcular SHA-256 e não consulta a API autenticada do GitHub. Essas limitações permanecem explícitas no recibo. O encerramento do recorte foi decidido pela suficiência da análise e dos artefatos, sem novas análises planejadas.
