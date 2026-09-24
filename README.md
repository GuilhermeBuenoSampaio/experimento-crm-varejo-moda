# Experimento de CRM em Varejo de Moda

Estudo independente do experimento público de Kevin Hillstrom (MineThatData) para comparar dois e-mails com o grupo de controle sem e-mail. Projeto de portfólio em desenvolvimento; as conclusões A/B serão publicadas após análise exploratória, definição e validação dos indicadores e testes de hipótese.

O CSV original permanece em inglês na Landing e na Bronze. O projeto usa português na documentação e aplicará os nomes e categorias aprovados em `metadata/dicionario_traducao.md` somente na Silver, mantendo os valores originais rastreáveis. Valores monetários permanecem em USD; não há conversão para reais.

## Primeira execução (Python 3.12)

1. Coloque o CSV original em `data/00_landing/` sem editar o conteúdo.
2. Na raiz do projeto, execute:

```powershell
python src/01_perfil_fonte.py
```

O script cria uma cópia intacta em `data/01_bronze_raw/`, um manifesto em `metadata/`, e relatórios JSON e Markdown em `quality/`. A execução não sobrescreve saídas existentes: use `--run-id` novo para uma nova tentativa. O CSV original e os dados derivados permanecem fora do GitHub por padrão.

## Preparação da Silver

Após revisar `metadata/dicionario_traducao.md`, valide a Bronze sem escrever a Silver:

```powershell
python src/02_materializar_silver.py --bronze-run-id SEU_ID --validate-only
```

Se a validação passar, instale a dependência no ambiente Python do projeto e crie uma execução Silver identificada:

```powershell
python -m pip install -r requirements.txt
python src/02_materializar_silver.py --bronze-run-id SEU_ID --silver-run-id SILVER01
```

Troque `SEU_ID` pelo nome da pasta existente em `metadata/runs/`. O Parquet e o relatório de qualidade serão criados somente com um `silver-run-id` ainda não usado.

## Orquestração e publicação

`src/run_pipeline.py` confere Bronze e Silver existentes ou cria uma nova execução, gera a documentação de cada etapa e só aprova a execução quando as validações passarem. Para ver os parâmetros disponíveis:

```powershell
python src/run_pipeline.py --help
```

`src/03_publicar_azure.py` publica uma execução aprovada no contêiner dedicado do Azure Storage, usando Azure CLI e autenticação Microsoft Entra ID. Sem `--execute`, exibe apenas o plano. Com `--execute`, impede sobrescrita, confere tamanho e SHA-256 de cada arquivo remoto e cria `docs/execucoes/<ID>/publicacao_azure.json` com o resultado. Não inclua chaves nem tokens no repositório.

```powershell
python src/03_publicar_azure.py --help
```

Os recibos de execução e os dados locais ficam fora do Git. A confirmação da publicação exige o recibo com `status: approved`; a aprovação local Bronze/Silver, sozinha, não confirma upload.

## Estrutura

- `data/00_landing`: arquivo recebido.
- `data/01_bronze_raw`: cópia imutável por execução.
- `data/02_silver` e `data/03_gold`: Parquet nas próximas etapas.
- `src`: scripts Python; `sql`: consultas SQL Server; `power_bi`: medidas DAX e Power Query.
- `metadata`: manifesto, contrato de métricas e decisões.
- `quality`: resultados de validações.
- `docs`: rastreabilidade e relatórios.

## Granularidade e limites

Cada linha representa um registro experimental. A chave técnica `(source_sha256, source_row_number)` identifica o registro recebido, não uma pessoa. Linhas com valores idênticos não são removidas sem evidência de que representam a mesma pessoa. A Silver está em Parquet.

O conjunto não contém abertura, clique, custo de campanha ou margem. O contrato em `metadata/contrato_analitico.md` define a métrica principal e as comparações antes da análise de resultados. SQL Server, Power Query e DAX usarão essas mesmas definições nas próximas etapas. O processamento local em batch atende ao volume atual e evita custo de computação em nuvem; a adaptação a volumes maiores será tratada separadamente.

Fonte do experimento: https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html

O arquivo recebido é identificado por SHA-256 no manifesto. A linha da fonte não é uma identidade de cliente; `source_row_number` identifica somente a posição do registro dentro desta versão do arquivo.
