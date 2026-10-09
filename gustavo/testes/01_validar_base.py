# -*- coding: utf-8 -*-
"""
01 — Valida a base completa (todas as etapas do pipeline).

Lê os parquets de saida/etapas/ e roda ~30 checks:
  - selecionado (02a)  : tipagem, chave única, taxas em [0,100], sem '--'
  - longitudinal (02b) : LAG/DELTA/T1 coerentes escola a escola, ANO_ALVO
  - censo (03)         : 17 features binárias, cobertura por ano
  - base final (04)    : cobertura no universo tx_rend, chaves únicas
  - base_atual.parquet : idêntica ao 04

Saída:
    gustavo/saida/relatorios/validacao_base.txt

Uso:  python testes/01_validar_base.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ------------------------------------------------------------------
# Descoberta das pastas
# ------------------------------------------------------------------
def achar_base_projeto():
    here = Path(__file__).resolve().parent
    for p in [here, *here.parents]:
        for nome in ("abandono-escolar", "abandono_escolar"):
            cand = p / nome
            if cand.is_dir() and (cand / "dados").is_dir():
                return cand
    for p in [here, *here.parents]:
        for nome in ("abandono-escolar", "abandono_escolar"):
            cand = p.parent / nome
            if cand.is_dir() and (cand / "dados").is_dir():
                return cand
    return None


BASE_PROJETO = achar_base_projeto()
if BASE_PROJETO is None:
    raise SystemExit("[ERRO] não achei 'abandono-escolar/dados/'")

GUSTAVO = Path(__file__).resolve().parent.parent
SAIDA_ETAPAS = GUSTAVO / "saida" / "etapas"
SAIDA_REL = GUSTAVO / "saida" / "relatorios"
SAIDA_REL.mkdir(parents=True, exist_ok=True)

P_SEL = SAIDA_ETAPAS / "02a_tx_rend_selecionado.parquet"
P_LONG = SAIDA_ETAPAS / "02b_tx_rend_longitudinal.parquet"
P_CENSO = SAIDA_ETAPAS / "03_censo_features.parquet"
P_FINAL = SAIDA_ETAPAS / "04_base_com_censo.parquet"
P_ATUAL = GUSTAVO / "saida" / "base_atual.parquet"

REPORT = SAIDA_REL / "validacao_base.txt"

# ------------------------------------------------------------------
# Acumuladores
# ------------------------------------------------------------------
log = []
n_ok = n_warn = n_fail = 0


def secao(t):
    log.append("")
    log.append("=" * 78)
    log.append(t)
    log.append("=" * 78)


def ok(msg):
    global n_ok
    n_ok += 1
    log.append(f"  ✅ {msg}")


def warn(msg):
    global n_warn
    n_warn += 1
    log.append(f"  ⚠️  {msg}")


def fail(msg):
    global n_fail
    n_fail += 1
    log.append(f"  ❌ {msg}")


def info(msg):
    log.append(f"     {msg}")


def normalizar_id(serie):
    return pd.to_numeric(serie, errors="coerce").dropna().astype("Int64").astype("string")


# ==================================================================
# Carregamento
# ==================================================================
secao("0. CARREGAMENTO")

paths_obrigatorios = {
    "02a selecionado": P_SEL,
    "02b longitudinal": P_LONG,
    "03 censo": P_CENSO,
    "04 base final": P_FINAL,
    "base_atual": P_ATUAL,
}
for nome, p in paths_obrigatorios.items():
    if not p.exists():
        print(f"[ERRO] falta {nome}: {p}")
        sys.exit(1)

sel = pd.read_parquet(P_SEL)
lon = pd.read_parquet(P_LONG)
censo = pd.read_parquet(P_CENSO)
base = pd.read_parquet(P_FINAL)
atual = pd.read_parquet(P_ATUAL)

ok(f"02a selecionado:    {sel.shape[0]:>7,} × {sel.shape[1]:>3}")
ok(f"02b longitudinal:   {lon.shape[0]:>7,} × {lon.shape[1]:>3}")
ok(f"03 censo features:  {censo.shape[0]:>7,} × {censo.shape[1]:>3}")
ok(f"04 base final:      {base.shape[0]:>7,} × {base.shape[1]:>3}")
ok(f"base_atual:         {atual.shape[0]:>7,} × {atual.shape[1]:>3}")

anos = sorted(base["ANO"].dropna().unique().tolist())
info(f"anos: {anos}")


# ==================================================================
# 1. Tipagem (regra 6)
# ==================================================================
secao("1. TIPAGEM (regra 6 do CLAUDE.md)")

if str(sel["CO_ENTIDADE"].dtype) == "string":
    ok("CO_ENTIDADE é string")
else:
    fail(f"CO_ENTIDADE é {sel['CO_ENTIDADE'].dtype}")

if str(sel["CO_MUNICIPIO"].dtype) == "string":
    ok("CO_MUNICIPIO é string")
else:
    warn(f"CO_MUNICIPIO é {sel['CO_MUNICIPIO'].dtype}")

if "int" in str(sel["ANO"].dtype).lower():
    ok(f"ANO é inteiro ({sel['ANO'].dtype})")
else:
    fail(f"ANO é {sel['ANO'].dtype}")

TAXAS = [c for c in sel.columns
         if c.startswith(("APROVACAO_", "REPROVACAO_", "ABANDONO_"))]
nao_float = [c for c in TAXAS if str(sel[c].dtype) != "Float64"]
if not nao_float:
    ok(f"todas as {len(TAXAS)} taxas são Float64 nullable")
else:
    fail(f"taxas não-Float64: {nao_float}")


# ==================================================================
# 2. Chave composta única
# ==================================================================
secao("2. CHAVE (ANO, CO_ENTIDADE)")

for nome, df in [("02a", sel), ("02b", lon), ("04", base), ("atual", atual)]:
    n_max = df.groupby(["ANO", "CO_ENTIDADE"]).size().max()
    if n_max == 1:
        ok(f"{nome}: chave única")
    else:
        fail(f"{nome}: chave não única (máx {n_max})")


# ==================================================================
# 3. '--' residual
# ==================================================================
secao("3. VALORES '--' RESIDUAIS (regra 5)")

for nome, df in [("02a", sel), ("02b", lon), ("04", base)]:
    encontrados = 0
    for c in df.columns:
        if df[c].dtype == object or "string" in str(df[c].dtype):
            encontrados += int((df[c].astype(str).str.strip() == "--").sum())
    if encontrados == 0:
        ok(f"{nome}: nenhum '--'")
    else:
        fail(f"{nome}: {encontrados} '--' residuais")


# ==================================================================
# 4. Cobertura de escolas por ano
# ==================================================================
secao("4. COBERTURA POR ANO")

por_ano = sel.groupby("ANO").agg(
    linhas=("CO_ENTIDADE", "size"),
    escolas=("CO_ENTIDADE", "nunique"),
)
if (por_ano["linhas"] == por_ano["escolas"]).all():
    ok("todos os anos: linhas == escolas únicas")
else:
    fail("há duplicatas em algum ano")

if len(por_ano) == 19:
    ok("19 anos cobertos (2007-2025)")
else:
    fail(f"esperado 19 anos, obtido {len(por_ano)}")


# ==================================================================
# 5. Taxas em [0, 100]
# ==================================================================
secao("5. TAXAS EM [0, 100]")

for c in TAXAS:
    v = pd.to_numeric(sel[c], errors="coerce")
    fora = int(((v < 0) | (v > 100)).sum())
    if fora > 0:
        fail(f"{c}: {fora} valores fora de [0, 100]")
if all((pd.to_numeric(sel[c], errors="coerce").between(0, 100) |
        pd.to_numeric(sel[c], errors="coerce").isna()).all() for c in TAXAS):
    ok(f"todas as {len(TAXAS)} taxas dentro de [0, 100]")


# ==================================================================
# 6. Curva temporal — 2020 é a anomalia
# ==================================================================
secao("6. CURVA TEMPORAL")

curva = sel.groupby("ANO")["ABANDONO_FUN_AF"].mean().round(2)
log.append(curva.to_string())

if curva.get(2020, 99) < curva.get(2019, 0):
    ok(f"2020 ({curva.get(2020):.2f}) < 2019 ({curva.get(2019):.2f})")
else:
    fail("2020 não é vale")

if curva.get(2022, 0) > curva.get(2021, 0):
    ok(f"2022 ({curva.get(2022):.2f}) > 2021 ({curva.get(2021):.2f})")
else:
    warn("2022 não é maior que 2021")


# ==================================================================
# 7. LAG1 = valor do ano anterior
# ==================================================================
secao("7. LAG1 COERENTE")

lon_ord = lon.sort_values(["CO_ENTIDADE", "ANO"]).reset_index(drop=True)
lon_ord["_esp"] = lon_ord.groupby("CO_ENTIDADE")["ABANDONO_FUN_AF"].shift(1)
mask = lon_ord["ABANDONO_FUN_AF_LAG1"].notna()
esperado = lon_ord.loc[mask, "_esp"]
obtido = lon_ord.loc[mask, "ABANDONO_FUN_AF_LAG1"]
comparaveis = esperado.notna() & obtido.notna()
diff = (esperado[comparaveis].astype(float) - obtido[comparaveis].astype(float)).abs()
n_diff = int((diff > 0.01).sum())
if n_diff == 0:
    ok(f"ABANDONO_FUN_AF_LAG1 = ABANDONO_FUN_AF[t-1] em {comparaveis.sum()} linhas")
else:
    fail(f"LAG1 divergente em {n_diff} linhas")


# ==================================================================
# 8. DELTA1 = valor - LAG1
# ==================================================================
secao("8. DELTA1 COERENTE")

mask = lon["ABANDONO_FUN_AF_DELTA1"].notna() & lon["ABANDONO_FUN_AF_LAG1"].notna()
esp = lon.loc[mask, "ABANDONO_FUN_AF"].astype(float) - lon.loc[mask, "ABANDONO_FUN_AF_LAG1"].astype(float)
obt = lon.loc[mask, "ABANDONO_FUN_AF_DELTA1"].astype(float)
n_diff = int(((esp - obt).abs() > 0.01).sum())
if n_diff == 0:
    ok(f"DELTA1 = valor - LAG1 em {mask.sum()} linhas")
else:
    fail(f"DELTA1 divergente em {n_diff}")


# ==================================================================
# 9. T1 = valor do ano seguinte
# ==================================================================
secao("9. T1 COERENTE")

lon_ord["_esp_t1"] = lon_ord.groupby("CO_ENTIDADE")["ABANDONO_FUN_AF"].shift(-1)
mask = lon_ord["ABANDONO_FUN_AF_T1"].notna()
esp = lon_ord.loc[mask, "_esp_t1"]
obt = lon_ord.loc[mask, "ABANDONO_FUN_AF_T1"]
comp = esp.notna() & obt.notna()
n_diff = int(((esp[comp].astype(float) - obt[comp].astype(float)).abs() > 0.01).sum())
if n_diff == 0:
    ok(f"ABANDONO_FUN_AF_T1 = ABANDONO_FUN_AF[t+1] em {comp.sum()} linhas")
else:
    fail(f"T1 divergente em {n_diff}")


# ==================================================================
# 10. ANO_ALVO
# ==================================================================
secao("10. ANO_ALVO")

sem_alvo = lon[lon["ANO_ALVO"].isna()]
n_2025 = int((sem_alvo["ANO"] == 2025).sum())
if n_2025 == 687:
    ok(f"2025: {n_2025} sem alvo (esperado — último ano)")
else:
    warn(f"2025: {n_2025} sem alvo (esperado 687)")

# confirmar hipótese: sem alvo (2007-2024) => escola ausente em t+1
ids_sel = set(zip(sel["ANO"].tolist(), sel["CO_ENTIDADE"].tolist()))
suspeitas = sem_alvo[sem_alvo["ANO"] < 2025]
nao_conf = sum(1 for a, e in zip(suspeitas["ANO"], suspeitas["CO_ENTIDADE"])
               if (a + 1, e) in ids_sel)
if nao_conf == 0:
    ok(f"todas as {len(suspeitas)} linhas sem alvo (2007-2024) confirmam escola ausente em t+1")
else:
    fail(f"{nao_conf} linhas sem alvo têm escola presente em t+1")


# ==================================================================
# 11. Features do Censo — binárias
# ==================================================================
secao("11. CENSO — BINÁRIAS")

vars_censo = [c for c in base.columns
              if c.startswith(("IIB_", "IDA_", "IDP_", "IEP_"))]
for c in vars_censo:
    uniq = set(base[c].dropna().unique().tolist())
    if uniq <= {0.0, 1.0}:
        continue
    fail(f"{c}: valores fora de {{0, 1}}: {sorted(uniq)[:5]}")
else:
    ok(f"{len(vars_censo)} features do Censo são binárias (0/1)")


# ==================================================================
# 12. Cobertura do Censo no universo tx_rend
# ==================================================================
secao("12. COBERTURA DO CENSO NA BASE FINAL")

cob_por_ano = []
for ano in sorted(base["ANO"].unique()):
    sub = base[base["ANO"] == ano]
    cob = sub[vars_censo].notna().mean().mean() * 100
    cob_por_ano.append((ano, len(sub), round(cob, 1)))
    info(f"{ano}: n={len(sub):>4}, cobertura={cob:.1f}%")

anos_ok = [a for a, _, c in cob_por_ano if c > 99]
anos_ruim = [a for a, _, c in cob_por_ano if c < 50]
if len(anos_ok) >= 18:
    ok(f"{len(anos_ok)}/19 anos com cobertura >99%")
if anos_ruim == [2007]:
    ok("só 2007 tem cobertura baixa (lacuna real do INEP)")
elif anos_ruim:
    warn(f"anos com cobertura <50%: {anos_ruim}")


# ==================================================================
# 13. base_atual idêntica ao 04
# ==================================================================
secao("13. base_atual = 04_base_com_censo")

if base.equals(atual):
    ok("base_atual.parquet é idêntico ao 04_base_com_censo.parquet")
else:
    fail("base_atual e 04 divergem")


# ==================================================================
# RESUMO
# ==================================================================
secao("RESUMO")
log.append(f"  ✅ OK:      {n_ok}")
log.append(f"  ⚠️  Warn:   {n_warn}")
log.append(f"  ❌ Falhas:  {n_fail}")
log.append("")
if n_fail == 0:
    log.append("  🎉 BASE VALIDADA — nenhuma falha crítica")
elif n_fail <= 2:
    log.append(f"  ⚠️  {n_fail} falhas — revisar antes de usar")
else:
    log.append(f"  ❌ {n_fail} falhas — base precisa correção")

texto = "\n".join(log)
print(texto)
REPORT.write_text(texto, encoding="utf-8")
print(f"\n>>> Relatório: {REPORT}")