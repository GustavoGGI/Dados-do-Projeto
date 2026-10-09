# `gustavo/` — extensão de tx_rend (2007–2025) + features do Censo

Pipeline paralelo ao `src/` do projeto principal. Constrói uma base
estendida para Roraima que:

- estende a série de tx_rend de 7 para **19 anos** (2007–2025)
- adiciona **17 features de infraestrutura** do Censo Escolar
  (Almeida & Mussato, 2023)

**Não modifica nada em `src/` nem em `dados/`** — todo o output fica em
`gustavo/saida/`.

## Como usar

- Para rodar o pipeline: veja `COMO_RODAR.md`
- Para entender os parquets de saída: veja `saida/README.md`
- Para entender o que cada script faz: docstring no topo de cada `.py`

## Estrutura

- `programas/` — scripts de produção (`01_` a `04_`, + `99_pipeline.py`)
- `programas/diagnostico/` — scripts pontuais (não entram no pipeline)
- `testes/` — validação dos parquets (`01_validar_base.py`)
- `cache/` — cache por ano, apagável (regenera dos zips em ~10 min)
  - `cache/tx_rend/{ano}.parquet`
  - `cache/censo/{ano}.parquet`
- `docs/` — relatórios longos em markdown
- `saida/` — parquets e relatórios finais (ver `saida/README.md`)

## Pipeline em 4 etapas

| Etapa | Script | Lê de | Escreve em |
|---|---|---|---|
| 01 | `01_tx_rend_bruto.py` | zips INEP (`dados/origem/indicadores/`) | `etapas/01_tx_rend_bruto.parquet` (12.597 × 238) |
| 02 | `02_tx_rend_selecionado_longitudinal.py` | cache `tx_rend/` + `01` | `etapas/02a_*.parquet` (19 col) + `etapas/02b_*.parquet` (30 col) |
| 03 | `03_censo_features.py` | zips Censo (`dados/bruto/censo/`, `dados/origem/censo/`) | `etapas/03_censo_features.parquet` (16.449 × 19) |
| 04 | `04_merge_features.py` | `02b` + `03` | `etapas/04_base_com_censo.parquet` (12.597 × 47) + `base_atual.parquet` |

O `99_pipeline.py` roda os 4 em ordem, com `--force` e `--from`.
Detalhes e flags por etapa: ver `COMO_RODAR.md`.

## Estado atual

Última execução completa: **09/10/2026**. `testes/01_validar_base.py`
rodou com **29 checks / 0 falhas**.

- **`saida/base_atual.parquet`** — 12.597 × 47
  - É a base pronta para o modelo: **30 colunas do tx_rend longitudinal
    + 17 features do Censo**, com as chaves `ANO + CO_ENTIDADE` compartilhadas.
  - É uma cópia fiel do `saida/etapas/04_base_com_censo.parquet`.

## Validações já executadas

- **Contra a base da Gabi (2019–2025):** 4.733 linhas em comum, zero
  diferenças de valor em todas as colunas comparadas. Única divergência
  de ausência: `ANO_ALVO` em 25 linhas (esperado — universos diferentes).
  Ver `saida/relatorios/validacao_longitudinal.txt`.
- **Base final:** 29 checks automáticos, 0 falhas. Cobre tipagem
  (regra 6 do CLAUDE.md), chave única, ausência de `'--'`, taxas em
  [0, 100], coerência de LAG1/DELTA1/T1, `ANO_ALVO`, 17 features
  binárias e cobertura do Censo. Ver `saida/relatorios/validacao_base.txt`.
- **Censo:** 17 features binárias, cobertura >99% em 18 dos 19 anos
  (só 2007 fica em 76,5%).

## Pendências documentadas

- **2007 tem 4 features do Censo 100% vazias** em todo o Brasil (lacuna
  real do INEP — colunas existem no schema mas não foram coletadas):
  `IDA_despensa`, `IDA_secretaria`, `IDA_refeitorio`, `IDP_patio_coberto`.
- **`out of memory` em 2010** quando o cache é apagado — investigar antes
  de reconstruir o pipeline inteiro sem cache.
- **TDI, ATU e IED** ainda não construídos — decisão do orientador se
  prioriza antes do modelo A/B.
- **17 vs 18 variáveis do artigo** — falta `IDP_patio_descoberto` (o artigo
  trata "pátio coberto ou descoberto" como uma variável só; temos só a
  versão "coberto").

## Próximo passo proposto

**Modelo A/B** — as 17 features do Censo melhoram a previsão de abandono?

| Config | Features |
|---|---|
| A (baseline) | só tx_rend (12 taxas + 3 LAG + 2 DELTA) |
| B (enriquecido) | tx_rend + 17 features do Censo |

Mesmo walk-forward, mesmos modelos, mesmos folds. Comparar R²/MAE por ano.
Implementação sugerida: `programas/05_modelo.py` (script Python puro,
consumindo `saida/base_atual.parquet`).