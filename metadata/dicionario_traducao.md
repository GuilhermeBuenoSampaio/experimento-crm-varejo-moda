# Dicionário de tradução — versão 0.1 (para revisão)

**Regra:** manter o CSV de origem byte a byte na Landing e na Bronze. Aplicar as traduções à Silver em Parquet após aprovação da qualidade. Guardar este mapeamento para rastrear cada transformação. Não traduzir unidades, moeda nem inferir informação ausente.

| Coluna original | Nome proposto na Silver | Significado e tipo esperado |
|---|---|---|
| `recency` | `meses_desde_ultima_compra` | Meses desde a última compra; inteiro |
| `history_segment` | `faixa_gasto_12_meses_usd` | Faixa de gasto histórico em dólares; texto ordenado |
| `history` | `gasto_12_meses_usd` | Gasto nos 12 meses anteriores em dólares; decimal |
| `mens` | `comprou_masculino_12_meses` | Indicador 0/1 de compra anterior; inteiro ou booleano |
| `womens` | `comprou_feminino_12_meses` | Indicador 0/1 de compra anterior; inteiro ou booleano |
| `zip_code` | `zona_localizacao` | Categoria Rural, Suburbana ou Urbana; **não é CEP numérico** |
| `newbie` | `cliente_novo_12_meses` | Indicador 0/1 de novo cliente nos 12 meses anteriores |
| `channel` | `canal_compra_historico` | Canal de compras anteriores |
| `segment` | `grupo_experimental` | Grupo sorteado; três valores |
| `visit` | `visitou_site_14_dias` | Indicador 0/1 de visita no período observado |
| `conversion` | `comprou_14_dias` | Indicador 0/1 de compra no período observado |
| `spend` | `gasto_14_dias_usd` | Valor gasto após a campanha em dólares; decimal |

## Categorias

| Coluna | Valor original | Valor em português |
|---|---|---|
| `segment` | `Mens E-Mail` | `E-mail masculino` |
| `segment` | `Womens E-Mail` | `E-mail feminino` |
| `segment` | `No E-Mail` | `Sem e-mail` |
| `channel` | `Phone` | `Telefone` |
| `channel` | `Web` | `Internet` |
| `channel` | `Multichannel` | `Multicanal` |
| `zip_code` | `Rural` | `Rural` |
| `zip_code` | `Surburban` | `Suburbana` |
| `zip_code` | `Urban` | `Urbana` |

`Surburban` está grafado assim na fonte. A correção será uma transformação documentada da Silver, preservando a forma recebida na Bronze. As sete faixas de `history_segment` manterão número e limites monetários originais; apenas a descrição poderá ser traduzida, após validar sua coerência com `history`. O símbolo `$` significa USD. Não assumir limites inclusivos ou exclusivos que a fonte não especificou.

## Metadados técnicos

`source_sha256` e `source_row_number` identificam o arquivo e a posição do registro. Na Silver, poderão ser expostos como `hash_arquivo_fonte` e `numero_linha_fonte`, mantendo nomes originais no manifesto de ingestão. Nenhum deles é um `id_cliente` real.
