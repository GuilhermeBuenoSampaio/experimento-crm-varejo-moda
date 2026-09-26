# Registro de tempo e entregas

| Data | Início | Fim | Pausas (min) | Horas efetivas | Horas previstas | Diferença | Entrega validada | Bloqueios e decisões | Próximo passo |
|---|---|---|---:|---:|---:|---:|---|---|---|
| 2026-09-23 | 20:26 | 22:25 | Não registradas | 1h59* | 3h | -1h01* | Perfil da fonte, Bronze e Silver aprovadas; documentação gerada; publicação Azure informada como concluída | Azure CLI instalado; login Entra ID e permissão de dados ajustados; chamada do `az.cmd` corrigida no script Python. Não deduplicar registros idênticos sem ID de cliente. | Confirmar recibo `publicacao_azure.json` com 12 arquivos aprovados; iniciar EDA da Silver. |
| 2026-09-24 | 19:30:16 (marco de controle) | 23:43 (informado) | Não registradas | Até 4h12min44s** | 3h | Até +1h12min44s** | EDA Silver e A/B revisadas; Gold publicada no Azure; SQL reconciliado (64.000 fatos, 3 grupos); Power BI conectado, relacionamento 1:* e KPIs por grupo conferidos, incluindo uplift e diferença em pp. | Início real anterior ao marco não foi cronometrado; pausas não informadas. Resultados inferenciais comparam cada e-mail ao controle. | Confirmar PBIX salvo e excluir medidas antigas com erro; versionar DAX e evidências; seguir com relatórios técnico e executivo. |
| 2026-09-25 |  |  |  |  | 3 |  |  |  |  |
| 2026-09-26 |  |  |  |  | 8 |  |  |  |  |
| 2026-09-27 |  |  |  |  | 8 |  |  |  |  |

Diferença = horas efetivas menos horas previstas. Registrar valores positivos e negativos e explicar desvios relevantes.

\* Cálculo provisório com base no intervalo de 20:26 a 22:25 (1h59). Como não foram informadas pausas, ajustar horas efetivas e diferença caso alguma pausa tenha ocorrido. A publicação foi informada como concluída; a conferência do recibo permanece como validação documental.

\*\* Em 2026-09-24, o intervalo de 19:30:16 a 23:43:00 soma 4h12min44s. É tempo decorrido desde o marco anotado, não horas efetivas confirmadas: subtrair eventuais pausas. Trabalho anterior ao marco não está incluído.
