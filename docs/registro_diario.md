# Registro de tempo e entregas

| Data | Início | Fim | Pausas (min) | Horas efetivas | Horas previstas | Diferença | Entrega validada | Bloqueios e decisões | Próximo passo |
|---|---|---|---:|---:|---:|---:|---|---|---|
| 2026-09-23 | 20:26 | 22:25 | Não registradas | 1h59* | 3h | -1h01* | Perfil da fonte, Bronze e Silver aprovadas; documentação gerada; publicação Azure informada como concluída | Azure CLI instalado; login Entra ID e permissão de dados ajustados; chamada do `az.cmd` corrigida no script Python. Não deduplicar registros idênticos sem ID de cliente. | Confirmar recibo `publicacao_azure.json` com 12 arquivos aprovados; iniciar EDA da Silver. |
| 2026-09-24 | 19:30:16 (marco de controle) | 23:43 (informado) | 0 (confirmado) | 4h12min44s desde o marco** | 3h | +1h12min44s desde o marco** | EDA Silver e A/B revisadas; Gold publicada no Azure; SQL reconciliado (64.000 fatos, 3 grupos); Power BI conectado, relacionamento 1:* e KPIs por grupo conferidos, incluindo uplift e diferença em pp. | Início real anterior ao marco não foi cronometrado; resultados inferenciais comparam cada e-mail ao controle. | Confirmar PBIX salvo e excluir medidas antigas com erro; versionar DAX e evidências; seguir com relatórios técnico e executivo. |
| 2026-09-25 | 22:00 (informado) | 23:31 (informado) | A confirmar | Até 1h31min*** | 3h | Até -1h29min*** | Reconciliação SQL × Power BI dos totais e grupos; cartões, tabela e página de comparação de grupos montados no PBIX segundo confirmação do responsável. | Uplift na linha Total corrigido; gastos representam vendas, sem custos/margem; comparação direta entre e-mails não foi testada. Encerramento por cansaço. | Salvar evidências do painel; concluir documentação e preparação para fechamento. |
| 2026-09-26 | ~17:16:22 (primeira imagem disponível) | A registrar ao encerrar a sessão | Não informadas | A apurar | 8h (planejamento antigo) | A apurar | Painel finalizado; PBIX, captura, DAX e reconciliação enviados ao GitHub; relatórios finais e executor preparados para versionamento | Encerramento por suficiência do escopo acordado, sem novas análises; auditoria final depende de execução no ambiente local | Executar finalizador, registrar resultado, publicar arquivos finais e preencher horário de término. |
| 2026-09-27 |  |  |  |  | 8 |  |  |  |  |

Diferença = horas efetivas menos horas previstas. Registrar valores positivos e negativos e explicar desvios relevantes.

\* Cálculo provisório com base no intervalo de 20:26 a 22:25 (1h59). Como não foram informadas pausas, ajustar horas efetivas e diferença caso alguma pausa tenha ocorrido. A publicação foi informada como concluída; a conferência do recibo permanece como validação documental.

** Em 2026-09-24, o intervalo de 19:30:16 a 23:43:00 soma 4h12min44s, sem pausas, conforme confirmação do responsável. Trabalho anterior ao marco não está incluído.

*** Em 2026-09-25, de 22:00 a 23:31 decorreram 1h31min. As pausas não foram informadas; ajustar horas efetivas e diferença quando confirmadas.

**Adendo 26/09:** o horário 17:16:22 foi inferido do carimbo do primeiro arquivo de imagem disponível da conversa de hoje. A interface não forneceu o instante exato da primeira mensagem; portanto este é um marco aproximado. O horário de término e as pausas de hoje devem ser informados pelo responsável ao encerrar. O projeto termina neste recorte porque foi considerado suficiente para a pergunta de negócio e o portfólio, sem expansão adicional.
