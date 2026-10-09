# Saída do pipeline `gustavo/`

Cada arquivo aqui é uma etapa do pipeline de construção da base.
A ordem numérica reflete a sequência de execução.

Para reconstruir tudo: `python programas/99_pipeline.py --force`

---

## `base_atual.parquet`

**Cópia da última etapa pronta.** É o arquivo que o notebook de modelo
consome.

- Dimensões: 12.597 × 47
- Conteúdo: idêntico ao `etapas/04_base_com_censo.parquet`
- Como trocar a base do modelo: substitua este arquivo por qualquer
  `.parquet` de `etapas/` (a maioria dos scripts usa as mesmas chaves
  `ANO + CO_ENTIDADE`, então o merge continua funcionando)

**Quando ele é atualizado:** pelo `04_merge_features.py` (última etapa).
Se você rodar as etapas individualmente, o `base_atual.parquet` não muda
até o `04` rodar de novo.

---

## Etapas (em `etapas/`)

### `01_tx_rend_bruto.parquet`
- **Dimensões:** 12.597 × 238
- **O que tem:** taxas de rendimento (aprovação, reprovação, abandono) para
  Roraima, 2007–2025, com as 3 gerações de layout do INEP empilhadas
  (2007–2011 `.xls`, 2012–2020 `tap_/tre_/tab_`, 2021–2025 `1_CAT_/2_CAT_/3_CAT_`).
- **Gerado por:** `01_tx_rend_bruto.py`
- **Uso:** auditoria. Não é consumido por modelos.

### `02a_tx_rend_selecionado.parquet`
- **Dimensões:** 12.597 × 19
- **O que tem:** 12 taxas (4 etapas × 3 tipos: FUN, FUN_AI, FUN_AF, MED) com
  nomes unificados + chaves (`ANO`, `CO_ENTIDADE`) + descrição (nome, município,
  localização, dependência).
- **Gerado por:** `02_tx_rend_selecionado_longitudinal.py`
- **Uso:** base mínima do modelo (só o alvo, sem features derivadas).

### `02b_tx_rend_longitudinal.parquet`
- **Dimensões:** 12.597 × 30
- **O que tem:** `02a` + `REDE_PUBLICA`, `DISP_REND` + `_LAG1` (valor do ano
  anterior), `_DELTA1` (variação anual) + `_T1` (valor do ano seguinte = alvo
  do modelo) + `ANO_ALVO`.
- **Gerado por:** `02_tx_rend_selecionado_longitudinal.py`
- **Uso:** base preditiva só com tx_rend. É a entrada do `04`.

### `03_censo_features.parquet`
- **Dimensões:** 16.449 × 19
- **O que tem:** 17 features de infraestrutura do Censo Escolar
  (Almeida & Mussato, 2023) + chaves (`ANO`, `CO_ENTIDADE`):
  - `IIB_*` (4): água potável, energia de rede, coleta de lixo, banheiro
  - `IDA_*` (5): despensa, refeitório, sala de diretoria, sala de professores, secretaria
  - `IDP_*` (4): biblioteca, lab. de informática, pátio coberto, quadra
  - `IEP_*` (4): computador, impressora, projetor, internet
- **Cobertura:** 100% em 2008–2025, 76,5% em 2007 (4 features do IDA + pátio
  são lacuna real do INEP — colunas existem no schema mas não foram coletadas
  no Brasil inteiro em 2007).
- **Gerado por:** `03_censo_features.py`
- **Uso:** enriquecimento. Não é consumido sozinho.

### `04_base_com_censo.parquet`
- **Dimensões:** 12.597 × 47
- **O que tem:** `02b` + as 17 features do Censo (merge `LEFT` por
  `ANO + CO_ENTIDADE`). 30 colunas do longitudinal + 17 do Censo (chaves
  compartilhadas).
- **Gerado por:** `04_merge_features.py`
- **Uso:** modelo com `tx_rend` + infraestrutura. É a base recomendada.

---

## Por que o script `02` gera dois parquets (02a e 02b)

O script `02_tx_rend_selecionado_longitudinal.py` produz dois arquivos:

- **`02a`** — base limpa, sem features derivadas
- **`02b`** — `02a` + LAG1/DELTA1/T1 + ANO_ALVO

**Motivo de serem um só script:** a lógica de harmonização das 3 gerações de
layout do INEP (armadilha P009/P014) precisa ler o cache anual, aplicar a
trava com o rótulo humano do cabeçalho e só então montar o longitudinal.
Separar em dois scripts exigiria duplicar essa lógica ou gravar um parquet
intermediário que perderia a informação de posição — que é a única confiável
entre gerações.

**Uso prático:** se você quer só o alvo (sem lags), use `02a`. Se quer o
dataset preditivo, use `02b`.

---

## Relatórios (em `relatorios/`)

- `diagnostico_bruto.txt` — resumo do `01`: por ano, escolas únicas, colunas
- `validacao_longitudinal.txt` — validação do `02b` contra a base da Gabi (2019–2025)
- `diagnostico_features_censo.txt` — cobertura das 17 features por ano, no universo do Censo
- `merge_features.txt` — cobertura do Censo no universo tx_rend (após o merge)
- `validacao_base.txt` — 29 checks de integridade da base final

## Relatório de diagnóstico (na raiz de `saida/`)

- `relatorio_colunas_censo.csv` — inventário das colunas do Censo por ano,
  gerado pelo script `programas/diagnostico/explorar_colunas_censo.py`.
  Não faz parte do pipeline; é só material de investigação.

---

## Como reconstruir

```bash
# Reconstruir tudo (com cache quente: ~8 s)
python programas/99_pipeline.py

# Reconstruir tudo do zero (~10 min)
python programas/99_pipeline.py --force

# Só uma etapa (útil durante desenvolvimento)
python programas/04_merge_features.py

# Validar a base final
python testes/01_validar_base.py