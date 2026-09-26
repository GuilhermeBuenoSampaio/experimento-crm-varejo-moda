/* Executar no SSMS. Conferir contra a tabela por grupo do Power BI.
   Taxas são frações: 0,00903125 = 0,903125%. Diferenca_pp já está em pp.
   Os testes A/B e seus p-valores permanecem no resultado Python AB01.
*/
USE ExperimentoCRMVarejoModa;
GO
SELECT
    k.grupo_experimental,
    k.registros_atribuidos,
    k.visitas,
    k.compras,
    k.gasto_total_usd,
    k.taxa_visita,
    k.taxa_conversao,
    k.gasto_por_registro_usd,
    CASE WHEN k.recebeu_email = 1
         THEN CONVERT(decimal(18,8), 100 * (k.taxa_conversao - c.taxa_conversao))
         END AS diferenca_conversao_pp,
    CASE WHEN k.recebeu_email = 1
         THEN CONVERT(decimal(18,8), (k.taxa_conversao - c.taxa_conversao)
              / NULLIF(c.taxa_conversao, 0))
         END AS uplift_conversao_fracao
FROM crm.vw_kpis_grupo AS k
CROSS JOIN (
    SELECT taxa_conversao
    FROM crm.vw_kpis_grupo
    WHERE grupo_experimental = N'Sem e-mail'
) AS c
ORDER BY k.id_grupo_experimental;
GO

SELECT
    SUM(registros_atribuidos) AS registros_total,
    SUM(visitas) AS visitas_total,
    SUM(compras) AS compras_total,
    SUM(gasto_total_usd) AS gasto_total_usd
FROM crm.vw_kpis_grupo;
GO
