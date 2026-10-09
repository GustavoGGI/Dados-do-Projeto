# Como rodar o pipeline

Tudo é rodado da pasta `gustavo/`. Os scripts funcionam de qualquer CWD
(auto-discovery de pasta), mas rodar daqui é o "jeito canônico".

---

## Pipeline completo (reconstruir tudo)

```bash
python programas/99_pipeline.py
```

Roda os 4 scripts em ordem:

1. `01_tx_rend_bruto.py`                    → `etapas/01_tx_rend_bruto.parquet`
2. `02_tx_rend_selecionado_longitudinal.py` → `etapas/02a_*.parquet` e `etapas/02b_*.parquet`
3. `03_censo_features.py`                   → `etapas/03_censo_features.parquet`
4. `04_merge_features.py`                   → `etapas/04_base_com_censo.parquet` + `base_atual.parquet`

**Tempo:** ~8 s com cache quente. ~10 min do zero (primeira vez, ou após
apagar cache).

**Flags:**

```bash
# Ignorar todo o cache (reprocessa dos zips originais)
python programas/99_pipeline.py --force

# Começar de uma etapa específica (útil quando 01 e 02 já estão ok)
python programas/99_pipeline.py --from 03

# Combinar
python programas/99_pipeline.py --force --from 03
```

---

## Rodar uma etapa só

### Etapas 01 e 03 (aceitam `--force`)

```bash
# 01 — reprocessa dos zips (ignora cache dos anos)
python programas/01_tx_rend_bruto.py --force

# 01 — só um ano específico (reprocessa só aquele, útil para debug)
python programas/01_tx_rend_bruto.py --force-year 2010

# 03 — reprocessa dos zips do Censo (ignora cache dos anos)
python programas/03_censo_features.py --force
```

### Etapas 02 e 04 (não aceitam flag)

```bash
# 02 — lê cache quente de 01, sempre regenera 02a e 02b (rápido: ~3 s)
python programas/02_tx_rend_selecionado_longitudinal.py

# 04 — lê 02b + 03, sempre regenera 04 e base_atual (rápido: ~1 s)
python programas/04_merge_features.py
```

**Por que 02 e 04 não têm `--force`:**

- **02** — só trabalha em cima do cache, que já é o produto final do 01.
  Não existe "versão antiga" do 02 para descartar; regenerar é sempre barato.
- **04** — só faz merge; não tem cache próprio. Se 02b ou 03 estiverem
  desatualizados, o 04 vai refletir isso. Para forçar, refaça 02b e/ou 03 antes.

**Quando o 02 não acha o cache do 01:** ele para com erro claro
("cache não encontrado"). Rode o 01 antes.

---

## Testes

```bash
# Validar a base final (29 checks)
python testes/01_validar_base.py
```

Saída em `saida/relatorios/validacao_base.txt`. Se algum check falhar,
o relatório aponta qual.

---

## Scripts de diagnóstico (não entram no pipeline)

Ficam em `programas/diagnostico/`. Não são chamados pelo 99_pipeline.

```bash
# Ver quais colunas do Censo existem em RR por ano
python programas/diagnostico/explorar_colunas_censo.py

# Filtrar por ano ou por padrão de coluna
python programas/diagnostico/explorar_colunas_censo.py --anos 2019 2020
python programas/diagnostico/explorar_colunas_censo.py --buscar AGUA BIBLIOTECA

# Inspecionar o conteúdo bruto dos zips antigos do INEP (para debug de layout)
python programas/diagnostico/inspecionar_zips_antigos.py
```

---

## Limpar cache

Cache é só otimização. Apagar é seguro:

```bash
Remove-Item cache\tx_rend\* -Force
Remove-Item cache\censo\* -Force
```

Depois de apagar, a próxima execução reprocessa os zips (~10 min).

---

## Dependências

- `pandas`, `pyarrow` (parquets)
- `openpyxl` (xlsx do INEP)
- `xlrd` (xls antigos de 2007–2011)
- `numpy`

Já estão no ambiente. Se algum der ImportError, avise antes de instalar
(fora da política do CLAUDE.md).