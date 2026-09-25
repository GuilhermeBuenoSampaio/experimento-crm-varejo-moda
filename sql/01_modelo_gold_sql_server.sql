/* Experimento CRM Varejo Moda: modelo Gold local, sem cliente_id.
   Executar no SSMS em uma consulta SQL Server; GO separa os lotes.
   Granularidade da fato: uma linha por registro experimental.
   Contrato: metadata/contrato_analitico.md.
*/
IF DB_ID(N'ExperimentoCRMVarejoModa') IS NULL
    CREATE DATABASE ExperimentoCRMVarejoModa;
GO
USE ExperimentoCRMVarejoModa;
GO
IF SCHEMA_ID(N'crm') IS NULL EXEC(N'CREATE SCHEMA crm');
GO
IF OBJECT_ID(N'crm.dim_grupo_experimental', N'U') IS NULL
BEGIN
    CREATE TABLE crm.dim_grupo_experimental (
        id_grupo_experimental tinyint NOT NULL PRIMARY KEY,
        grupo_experimental nvarchar(40) NOT NULL UNIQUE,
        recebeu_email bit NOT NULL,
        CONSTRAINT CK_dim_grupo_id CHECK (id_grupo_experimental IN (0, 1, 2))
    );
END;
GO
IF OBJECT_ID(N'crm.fato_resposta_experimental', N'U') IS NULL
BEGIN
    CREATE TABLE crm.fato_resposta_experimental (
        hash_arquivo_fonte char(64) NOT NULL,
        numero_linha_fonte int NOT NULL,
        id_grupo_experimental tinyint NOT NULL,
        meses_desde_ultima_compra smallint NOT NULL,
        faixa_gasto_12_meses_usd nvarchar(40) NOT NULL,
        gasto_12_meses_usd decimal(12,2) NOT NULL,
        comprou_masculino_12_meses tinyint NOT NULL,
        comprou_feminino_12_meses tinyint NOT NULL,
        zona_localizacao nvarchar(20) NOT NULL,
        cliente_novo_12_meses tinyint NOT NULL,
        canal_compra_historico nvarchar(20) NOT NULL,
        visitou_site_14_dias tinyint NOT NULL,
        comprou_14_dias tinyint NOT NULL,
        gasto_14_dias_usd decimal(12,2) NOT NULL,
        CONSTRAINT PK_fato_resposta_experimental PRIMARY KEY (hash_arquivo_fonte, numero_linha_fonte),
        CONSTRAINT FK_fato_grupo FOREIGN KEY (id_grupo_experimental)
            REFERENCES crm.dim_grupo_experimental(id_grupo_experimental),
        CONSTRAINT CK_fato_recencia CHECK (meses_desde_ultima_compra BETWEEN 1 AND 12),
        CONSTRAINT CK_fato_valores CHECK (gasto_12_meses_usd >= 0 AND gasto_14_dias_usd >= 0),
        CONSTRAINT CK_fato_flags CHECK (
            comprou_masculino_12_meses IN (0,1) AND comprou_feminino_12_meses IN (0,1)
            AND cliente_novo_12_meses IN (0,1) AND visitou_site_14_dias IN (0,1)
            AND comprou_14_dias IN (0,1)),
        CONSTRAINT CK_fato_resultado CHECK (
            (comprou_14_dias = 0 AND gasto_14_dias_usd = 0)
            OR (comprou_14_dias = 1 AND visitou_site_14_dias = 1 AND gasto_14_dias_usd > 0))
    );
    CREATE INDEX IX_fato_grupo ON crm.fato_resposta_experimental(id_grupo_experimental);
END;
GO
CREATE OR ALTER VIEW crm.vw_kpis_grupo AS
SELECT d.id_grupo_experimental,
       d.grupo_experimental,
       d.recebeu_email,
       COUNT_BIG(*) AS registros_atribuidos,
       SUM(CONVERT(bigint, f.visitou_site_14_dias)) AS visitas,
       SUM(CONVERT(bigint, f.comprou_14_dias)) AS compras,
       SUM(CONVERT(decimal(20,2), f.gasto_14_dias_usd)) AS gasto_total_usd,
       CAST(SUM(CONVERT(bigint, f.visitou_site_14_dias)) AS decimal(18,8))
           / NULLIF(COUNT_BIG(*), 0) AS taxa_visita,
       CAST(SUM(CONVERT(bigint, f.comprou_14_dias)) AS decimal(18,8))
           / NULLIF(COUNT_BIG(*), 0) AS taxa_conversao,
       SUM(CONVERT(decimal(20,2), f.gasto_14_dias_usd))
           / NULLIF(COUNT_BIG(*), 0) AS gasto_por_registro_usd
FROM crm.fato_resposta_experimental AS f
JOIN crm.dim_grupo_experimental AS d
  ON d.id_grupo_experimental = f.id_grupo_experimental
GROUP BY d.id_grupo_experimental, d.grupo_experimental, d.recebeu_email;
GO
