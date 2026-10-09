# -*- coding: utf-8 -*-
"""
Diagnósticos de apoio ao plano avançado do projeto "Risco de abandono escolar em Roraima".

Uso (na raiz do repositório, com o bootstrap já executado):

    python diagnosticos_plano.py --dados dados --saida diagnosticos_saida

Lê (não altera nada em dados/):
    dados/processado/base_longitudinal_rr_2019_2025.csv
    dados/interim/indicadores_rr/{tx_rend,TDI,ATU}_AAAA.parquet
    dados/bruto/censo/microdados_ed_basica_AAAA.csv (2019-2024) e Tabela_*_2025_V2.csv
    dados/bruto/indicadores/tx_rend/AAAA/tx_rend_brasil_regioes_ufs_AAAA.xlsx   (opcional, só para conferência)

Grava em --saida: um CSV por tabela e o painel enriquecido (painel_diagnostico.parquet).

IMPORTANTE
- Tudo aqui é EXPLORATÓRIO. Os números servem para orientar o plano, não são resultado de artigo.
- O script usa a transição 2024->2025, que a proposta do orientador reservava como teste bloqueado.
  Essa transição já havia sido usada nos notebooks v1, v1_old e v1_corrigido. O plano propõe
  tratá-la como validação e reservar 2025->2026 como teste prospectivo.
- "Contagem" de abandonos é reconstruída: taxa publicada x denominador compatível com as três
  taxas (aprovação, reprovação, abandono) mais próximo da matrícula do Censo. É aproximação.
"""
import argparse
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

warnings.filterwarnings("ignore")
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 100)
pd.set_option("display.max_rows", 300)

RS = 1
K = 30
ANOS = list(range(2019, 2026))
FOLDS = (2021, 2022, 2023, 2024)          # ano t das features; alvo em t+1
ETAPAS = {
    "AF": dict(y="ABANDONO_FUN_AF", ap="APROVACAO_FUN_AF", rp="REPROVACAO_FUN_AF", n="QT_MAT_FUND_AF", tdi="TDI_FUN_AF", tur="QT_TUR_FUND_AF"),
    "EM": dict(y="ABANDONO_MED", ap="APROVACAO_MED", rp="REPROVACAO_MED", n="QT_MAT_MED", tdi="TDI_MED_TOTAL", tur="QT_TUR_MED"),
}
CAT = ["LOCALIZACAO", "DEPENDENCIA", "CO_MUNICIPIO"]
FLAG = ["DISP_ATU", "DISP_TDI", "DISP_IED", "DISP_REND"]
NUM = {
    "AF": ["ATU_FUN_AF", "ATU_FUN_TOTAL", "TDI_FUN_AF", "TDI_FUN_TOTAL", "APROVACAO_FUN_AF", "REPROVACAO_FUN_AF", "ABANDONO_FUN_AF",
           "APROVACAO_FUN", "REPROVACAO_FUN", "ABANDONO_FUN", "ABANDONO_FUN_AF_LAG1", "ABANDONO_FUN_LAG1", "ABANDONO_FUN_AF_DELTA1",
           "TDI_FUN_AF_DELTA1", "ATU_FUN_AF_DELTA1", "IED_FUN_N1", "IED_FUN_N2", "IED_FUN_N3", "IED_FUN_N4", "IED_FUN_N5", "IED_FUN_N6",
           "IED_FUN_ALTO", "ATU_FUN_AI", "TDI_FUN_AI", "APROVACAO_FUN_AI", "REPROVACAO_FUN_AI", "ABANDONO_FUN_AI"],
    "EM": ["ATU_MED_TOTAL", "TDI_MED_TOTAL", "APROVACAO_MED", "REPROVACAO_MED", "ABANDONO_MED", "ABANDONO_MED_LAG1", "ABANDONO_MED_DELTA1",
           "TDI_MED_TOTAL_DELTA1", "ATU_MED_TOTAL_DELTA1", "IED_MED_N1", "IED_MED_N2", "IED_MED_N3", "IED_MED_N4", "IED_MED_N5",
           "IED_MED_N6", "IED_MED_ALTO"],
}
SERIES = ["FUN_06", "FUN_07", "FUN_08", "FUN_09", "MED_01", "MED_02", "MED_03", "MED_04"]
NOVO = ["FUN", "FUN_AI", "FUN_AF", "FUN_01", "FUN_02", "FUN_03", "FUN_04", "FUN_05", "FUN_06", "FUN_07", "FUN_08", "FUN_09",
        "MED", "MED_01", "MED_02", "MED_03", "MED_04", "MED_NS"]
# 2019-2020: o mapeamento é POSICIONAL (P009/P014): F04 = anos finais, F58 = 1º ano, F00..F08 = 2º..9º
VELHO = ["FUN", "F14", "F04", "F58", "F00", "F01", "F02", "F03", "F05", "F06", "F07", "F08", "MED", "M01", "M02", "M03", "M04", "MNS"]
COLS_CENSO = [
    "QT_MAT_BAS", "QT_MAT_FUND", "QT_MAT_FUND_AF", "QT_MAT_MED", "QT_MAT_EJA", "QT_MAT_BAS_N", "QT_MAT_BAS_INDIGENA", "QT_MAT_BAS_15_17",
    "QT_MAT_BAS_18_MAIS", "QT_TUR_FUND_AF", "QT_TUR_MED", "IN_EDUCACAO_INDIGENA", "TP_LOCALIZACAO_DIFERENCIADA", "TP_LOCALIZACAO",
    "TP_DEPENDENCIA", "QT_MAT_FUND_AF_6", "QT_MAT_FUND_AF_7", "QT_MAT_FUND_AF_8", "QT_MAT_FUND_AF_9", "QT_MAT_MED_1", "QT_MAT_MED_2",
    "QT_MAT_MED_3", "QT_MAT_MED_PROP_1", "QT_MAT_MED_PROP_2", "QT_MAT_MED_PROP_3", "QT_MAT_MED_CT_1", "QT_MAT_MED_CT_2", "QT_MAT_MED_CT_3",
    "QT_MAT_MED_NM_1", "QT_MAT_MED_NM_2", "QT_MAT_MED_NM_3",
]


def titulo(t):
    print(f"\n{'=' * 118}\n{t}\n{'=' * 118}")


# --------------------------------------------------------------------------------------------------------------
# 1. Leitura
# --------------------------------------------------------------------------------------------------------------
def censo_rr(dados: Path, cache: Path) -> pd.DataFrame:
    """Recorte de Roraima dos microdados (uma linha por escola-ano), só com as colunas usadas aqui."""
    alvo = cache / "censo_rr.parquet"
    if alvo.exists():
        return pd.read_parquet(alvo)
    bruto = dados / "bruto" / "censo"

    def ler(caminho):
        partes = []
        for ch in pd.read_csv(caminho, sep=";", encoding="cp1252", dtype=str, chunksize=40000):
            partes.append(ch[ch["SG_UF"] == "RR"])
        return pd.concat(partes, ignore_index=True)

    saida = []
    for ano in ANOS:
        if ano == 2025:
            e = ler(bruto / "Tabela_Escola_2025_V2.csv")
            for tb in ("Matricula", "Turma"):          # em 2025 as contagens saíram da tabela Escola (P003)
                x = ler(bruto / f"Tabela_{tb}_2025_V2.csv")
                novas = ["CO_ENTIDADE"] + [c for c in x.columns if c not in e.columns]
                e = e.merge(x[novas], on="CO_ENTIDADE", how="left", validate="1:1")
        else:
            cand = [p for p in bruto.iterdir() if p.name.lower() == f"microdados_ed_basica_{ano}.csv"]
            e = ler(cand[0])
        o = pd.DataFrame({"ANO": ano, "CO_ENTIDADE": e["CO_ENTIDADE"].astype(str)})
        for c in COLS_CENSO:
            o[c] = pd.to_numeric(e[c], errors="coerce").values if c in e.columns else np.nan
        saida.append(o)
        print(f"   censo {ano}: {len(o)} escolas de RR")
    out = pd.concat(saida, ignore_index=True)
    out.to_parquet(alvo, index=False)
    return out


def montar_painel(dados: Path, cache: Path) -> pd.DataFrame:
    base = pd.read_csv(dados / "processado" / "base_longitudinal_rr_2019_2025.csv", sep=";", dtype={"CO_ENTIDADE": str, "CO_MUNICIPIO": str})
    rr = dados / "interim" / "indicadores_rr"
    tx, tdi, atu = [], [], []
    for a in ANOS:
        t = pd.read_parquet(rr / f"tx_rend_{a}.parquet")
        o = pd.DataFrame({"ANO": a, "CO_ENTIDADE": t["CO_ENTIDADE"].astype(str)})
        for pn, pv, rot in (("1_CAT_", "tap_", "AP"), ("2_CAT_", "tre_", "RP"), ("3_CAT_", "tab_", "AB")):
            for n, v in zip(NOVO, VELHO):
                col = pn + n if a >= 2021 else pv + v
                o[f"{rot}_{n}"] = pd.to_numeric(t[col], errors="coerce").astype(float).values
        tx.append(o)
        t = pd.read_parquet(rr / f"TDI_{a}.parquet")
        o = pd.DataFrame({"ANO": a, "CO_ENTIDADE": t["CO_ENTIDADE"].astype(str)})
        for s in SERIES[:-1]:
            o[f"TDI_{s}"] = pd.to_numeric(t[f"{s}_CAT_0"], errors="coerce").astype(float).values
        tdi.append(o)
        t = pd.read_parquet(rr / f"ATU_{a}.parquet")
        o = pd.DataFrame({"ANO": a, "CO_ENTIDADE": t["CO_ENTIDADE"].astype(str)})
        for s in ("FUN_09", "MED_01", "MED_02", "MED_03", "MULT_ETA"):
            o[f"ATU_{s}"] = pd.to_numeric(t[f"{s}_CAT_0"], errors="coerce").astype(float).values
        atu.append(o)
    p = base
    for bloco in (pd.concat(tx), pd.concat(tdi), pd.concat(atu), censo_rr(dados, cache)):
        p = p.merge(bloco, on=["ANO", "CO_ENTIDADE"], how="left", validate="1:1")
    # conferência do mapeamento posicional contra a base
    for a_, b_ in (("ABANDONO_FUN_AF", "AB_FUN_AF"), ("ABANDONO_MED", "AB_MED"), ("REPROVACAO_MED", "RP_MED")):
        assert (p[a_] - p[b_]).abs().max() < 1e-9 and (p[a_].isna() != p[b_].isna()).sum() == 0, f"mapeamento divergente: {a_}"
    capital = p.CO_MUNICIPIO == "1400100"
    urb = p.LOCALIZACAO == "Urbana"
    indig = ((p.IN_EDUCACAO_INDIGENA == 1) | (p.TP_LOCALIZACAO_DIFERENCIADA == 2)).astype(float).where(p.IN_EDUCACAO_INDIGENA.notna())
    p["INDIG_E"] = p.CO_ENTIDADE.map(indig.groupby(p.CO_ENTIDADE).max())       # indígena se marcada em algum ano
    p["ESTRATO"] = np.where(p.INDIG_E == 1, "4-Indígena", np.where(capital & urb, "1-Capital urbana",
                            np.where(urb, "2-Interior urbano", "3-Rural não indígena")))
    return p


# --------------------------------------------------------------------------------------------------------------
# 2. Utilitários
# --------------------------------------------------------------------------------------------------------------
def n_compat(ap, rp, ab, n0, janela=0.35, tol=0.051):
    """Denominador (aprovados+reprovados+abandonos) compatível com as 3 taxas de 1 casa decimal, mais próximo da matrícula."""
    if np.isnan(ab) or np.isnan(n0) or n0 <= 0:
        return np.nan
    lo, hi = max(1, int(np.floor(n0 * (1 - janela))) - 2), int(np.ceil(n0 * (1 + janela))) + 2
    ok = []
    for n in range(lo, hi + 1):
        b = round(ab * n / 100)
        r = round(rp * n / 100)
        a = n - b - r
        if a >= 0 and abs(100 * b / n - ab) <= tol and abs(100 * r / n - rp) <= tol and abs(100 * a / n - ap) <= tol:
            ok.append(n)
    return min(ok, key=lambda n: abs(n - n0)) if ok else np.nan


def contagens(pub, c):
    d = pub[pub[c["y"]].notna()].copy()
    d["n_rend"] = [n_compat(a, r, b, n0) for a, r, b, n0 in zip(d[c["ap"]], d[c["rp"]], d[c["y"]], d[c["n"]])]
    d["n_use"] = d.n_rend.fillna(d[c["n"]])
    d["B"] = (d[c["y"]] * d.n_use / 100).round()
    d["R"] = (d[c["rp"]] * d.n_use / 100).round()
    return d.sort_values(["CO_ENTIDADE", "ANO"]).reset_index(drop=True)


def prior_eb(hist):
    """Prior beta por momentos sobre as taxas acumuladas das escolas: devolve (p0, m) com m = 'alunos equivalentes' do prior."""
    h = hist.groupby("CO_ENTIDADE").agg(B=("B", "sum"), n=("n_use", "sum"))
    p0 = h.B.sum() / h.n.sum()
    ph = h.B / h.n
    tau2 = max(np.average((ph - p0) ** 2, weights=h.n) - p0 * (1 - p0) * (1 / h.n).mean(), 1e-6)
    return p0, p0 * (1 - p0) / tau2


def icc_anova(yc, grupo):
    k = yc.groupby(grupo).size()
    G, N = len(k), len(yc)
    em = yc.groupby(grupo).transform("mean")
    msb = (em ** 2).sum() / (G - 1)
    msw = ((yc - em) ** 2).sum() / (N - G)
    k0 = (N - (k ** 2).sum() / N) / (G - 1)
    return (msb - msw) / (msb + (k0 - 1) * msw)


def pre(num, cat):
    return ColumnTransformer([
        ("n", Pipeline([("i", SimpleImputer(strategy="median")), ("s", StandardScaler())]), num),
        ("c", Pipeline([("i", SimpleImputer(strategy="constant", fill_value="NA")), ("o", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]), cat),
    ])


# --------------------------------------------------------------------------------------------------------------
# 3. Blocos de diagnóstico
# --------------------------------------------------------------------------------------------------------------
def bloco_porte(d, et, c, saida):
    titulo(f"A. PORTE, DENOMINADOR E SÉRIE PONDERADA — {et}")
    n = d[c["n"]]
    print("Matrícula na etapa por escola-ano — quantis:", n.quantile([.1, .25, .5, .75, .9]).round(0).to_dict())
    print("   escolas-ano com até 30 / 50 / 100 alunos:", [f"{(n <= k).mean():.1%}" for k in (30, 50, 100)])
    x = d[d.ANO == 2025]
    g = x.groupby("ESTRATO").agg(escolas=(c["n"], "size"), matriculas=("n_use", "sum"), mediana=(c["n"], "median"), abandonos=("B", "sum"))
    g["%escolas"] = g.escolas / g.escolas.sum()
    g["%matriculas"] = g.matriculas / g.matriculas.sum()
    g["%abandonos"] = g.abandonos / g.abandonos.sum()
    g["taxa"] = 100 * g.abandonos / g.matriculas
    print("\n2025 por estrato:\n", g.round(3).to_string())
    g.to_csv(saida / f"A_estrato_2025_{et}.csv")
    ok = d.n_rend.notna()
    r = (d.n_rend / d[c["n"]])[ok]
    print(f"\nDenominador reconstruído em {ok.mean():.1%} das linhas; n_rend/matrícula: P5 {r.quantile(.05):.3f}, mediana {r.median():.3f}, P95 {r.quantile(.95):.3f}")
    s = d.groupby("ANO").apply(lambda z: pd.Series({"escolas": len(z), "matriculas": z.n_use.sum(), "abandonos": z.B.sum(),
                                                    "taxa_ponderada": 100 * z.B.sum() / z.n_use.sum(), "media_simples": z[c["y"]].mean()}))
    print("\nSérie anual, rede pública (taxa ponderada ≈ taxa oficial da UF):\n", s.round(2).to_string())
    s2 = d.groupby(["ESTRATO", "ANO"]).apply(lambda z: 100 * z.B.sum() / z.n_use.sum()).unstack("ANO")
    print("\nTaxa ponderada por estrato:\n", s2.round(2).to_string())
    s.to_csv(saida / f"A_serie_{et}.csv")
    s2.to_csv(saida / f"A_serie_estrato_{et}.csv")
    tr_, tc_ = x.nlargest(K, c["y"]), x.nlargest(K, "B")
    print(f"\n2025: top-{K} por TAXA soma {tr_.B.sum():.0f} abandonos ({tr_.B.sum() / x.B.sum():.1%}); matrícula mediana {tr_.n_use.median():.0f}; indígenas {int((tr_.INDIG_E == 1).sum())}")
    print(f"2025: top-{K} por CONTAGEM soma {tc_.B.sum():.0f} abandonos ({tc_.B.sum() / x.B.sum():.1%}); matrícula mediana {tc_.n_use.median():.0f}; indígenas {int((tc_.INDIG_E == 1).sum())}")
    cum = x.sort_values("B", ascending=False).B.cumsum() / x.B.sum()
    print(f"   sobreposição das duas listas: {len(set(tr_.CO_ENTIDADE) & set(tc_.CO_ENTIDADE))}/{K} | total {x.B.sum():.0f} abandonos em {len(x)} escolas | "
          f"{int((cum < .5).sum() + 1)} escolas somam 50% e {int((cum < .8).sum() + 1)} somam 80%")


def bloco_estrutura(d, et, c, saida):
    titulo(f"B. ESTRUTURA DA VARIAÇÃO — {et}")
    w = d.pivot(index="CO_ENTIDADE", columns="ANO", values=c["y"])
    cm = w.corr(method="spearman", min_periods=30)
    wt = d.pivot(index="CO_ENTIDADE", columns="ANO", values=c["tdi"]).corr(method="spearman", min_periods=30)
    print("Spearman entre anos — abandono da mesma escola:\n", cm.round(2).to_string())
    for nome, m in (("abandono", cm), ("TDI", wt)):
        lag = {k: round(float(np.mean([m.loc[a, a + k] for a in range(2022, 2026 - k)])), 2) for k in (1, 2, 3)}
        print(f"   Spearman médio por defasagem, 2022+ ({nome}): {lag}")
    z = d[d.ANO >= 2022].copy()
    yc = z[c["y"]] - z.groupby("ANO")[c["y"]].transform("mean")
    vt = yc.var()
    icc = icc_anova(yc, z.CO_ENTIDADE)
    pe = z.groupby("CO_ENTIDADE").apply(lambda g: g.B.sum() / g.n_use.sum())
    pg = z.B.sum() / z.n_use.sum()
    p_use = 0.5 * z.CO_ENTIDADE.map(pe) + 0.5 * pg
    vb = (p_use * (1 - p_use) / z.n_use * 1e4)
    print(f"\n2022-2025, dentro do ano: variância {vt:.1f} p.p.² = persistente da escola {icc:.0%} (ICC) + ruído binomial {vb.mean() / vt:.0%} "
          f"+ transitória restante {1 - icc - vb.mean() / vt:.0%}")
    print(f"   desvio-padrão do ruído binomial na escola mediana: {np.sqrt(vb.median()):.2f} p.p. | 1 aluno na escola mediana = {100 / z.n_use.median():.2f} p.p.")
    print(f"   zeros observados {(z[c['y']] == 0).mean():.1%} | esperados sob binomial {((1 - p_use) ** z.n_use).mean():.1%}")
    g4 = z.groupby("CO_ENTIDADE").agg(anos=(c["y"], "size"), zeros=(c["y"], lambda s: (s == 0).sum()))
    g4 = g4[g4.anos == 4]
    pz = (z[c["y"]] == 0).mean()
    print(f"   escolas com os 4 anos de 2022-2025: {len(g4)} | abandono zero nos 4 anos: {(g4.zeros == 4).sum()} "
          f"(seriam {len(g4) * pz ** 4:.1f} se os zeros fossem independentes entre anos)")
    pd.DataFrame([dict(etapa=et, var_dentro_ano=vt, icc=icc, binomial=vb.mean() / vt)]).to_csv(saida / f"B_variancia_{et}.csv", index=False)
    return dict(vt=vt, icc=icc)


def bloco_previsao(d, et, c, saida):
    titulo(f"C/D. PREVISÃO E PRIORIZAÇÃO — {et}  (walk-forward; alvo em t+1; K = {K})")
    y = c["y"]
    g = d.groupby("CO_ENTIDADE")
    for h in (1, 2):
        ok = g["ANO"].shift(-h) == d.ANO + h
        for col, novo in ((y, f"y{h}"), ("B", f"B{h}"), ("n_use", f"n{h}")):
            d[novo] = g[col].shift(-h).where(ok)
    d["ylag1"], d["ylag2"] = g[y].shift(1), g[y].shift(2)
    d["m3"] = d[[y, "ylag1", "ylag2"]].mean(axis=1)
    d["mexp"] = g[y].transform(lambda s: s.expanding().mean())
    d["cumB"], d["cumN"] = g["B"].cumsum(), g["n_use"].cumsum()
    d["pool"] = 100 * d.cumB / d.cumN
    linhas, fron, h2 = [], [], []
    for ano in FOLDS:
        tr = d[(d.ANO < ano) & (d.ANO > 2019) & d.y1.notna()]
        te = d[(d.ANO == ano) & d.y1.notna()].copy()
        p0, m = prior_eb(d[d.ANO < ano])
        te["eb"] = 100 * (te.cumB + m * p0) / (te.cumN + m)
        ytr = tr.y1.to_numpy(float)
        ols = Pipeline([("i", SimpleImputer(strategy="median")), ("m", LinearRegression())]).fit(tr[["mexp", c["tdi"]]].to_numpy(float), ytr)
        te["ols2"] = ols.predict(te[["mexp", c["tdi"]]].to_numpy(float))
        num = NUM[et] + FLAG
        for nome, mod in (("ridge", Ridge(alpha=1.0, random_state=RS)),
                          ("rf", RandomForestRegressor(n_estimators=300, max_depth=10, min_samples_leaf=3, random_state=RS, n_jobs=-1))):
            te[nome] = Pipeline([("p", pre(num, CAT)), ("m", mod)]).fit(tr[num + CAT], ytr).predict(te[num + CAT])
        med = np.nanmedian(tr[y])
        y1, B1, n1 = te.y1.to_numpy(float), te.B1.to_numpy(float), te.n1.to_numpy(float)
        top_t, top_c = set(np.argsort(-y1, kind="stable")[:K]), set(np.argsort(-B1, kind="stable")[:K])
        escores = {
            "T0 média do treino": np.full(len(te), ytr.mean()), "T1 persistência: taxa(t)": te[y], "T2 média de 3 anos": te.m3,
            "T3 taxa acumulada (ΣB/Σn)": te.pool, "T4 taxa acumulada encolhida (EB)": te.eb, "T5 OLS: média histórica + TDI": te.ols2,
            "T6 Ridge (todas as features)": te.ridge, "T7 RandomForest (todas as features)": te.rf,
            "C0 só o porte: matrícula(t)": te.n_use, "C1 persistência: contagem(t)": te.B, "C3 taxa acumulada × matrícula": te.pool * te.n_use,
            "C4 EB × matrícula": te.eb * te.n_use, "C5 OLS × matrícula": te.ols2 * te.n_use, "C7 RandomForest × matrícula": te.rf * te.n_use,
        }
        for nome, s in escores.items():
            s = np.where(np.isfinite(s), s, med if nome.startswith("T") else 0.0).astype(float)
            sel = np.argsort(-s, kind="stable")[:K]
            L = dict(fold=f"{ano}->{ano + 1}", estrategia=nome, sobrep_taxa=len(top_t & set(sel)) / K, sobrep_cont=len(top_c & set(sel)) / K,
                     captura_alunos=B1[sel].sum() / B1.sum(), matr_mediana=np.median(n1[sel]), n_indig=float((te.INDIG_E.to_numpy()[sel] == 1).sum()),
                     spearman=spearmanr(s, y1).statistic if len(np.unique(s)) > 1 else np.nan)
            if nome.startswith("T"):
                e = s - y1
                L.update(MAE=np.abs(e).mean(), MAE_pond=np.average(np.abs(e), weights=n1), R2=r2_score(y1, s), R2c=1 - np.var(e) / np.var(y1), vies=e.mean())
            linhas.append(L)
        for nome, selo in (("ORÁCULO por taxa", list(top_t)), ("ORÁCULO por contagem", list(top_c))):
            linhas.append(dict(fold=f"{ano}->{ano + 1}", estrategia=nome, captura_alunos=B1[selo].sum() / B1.sum(), matr_mediana=np.median(n1[selo]),
                               n_indig=float((te.INDIG_E.to_numpy()[selo] == 1).sum())))
        linhas.append(dict(fold=f"{ano}->{ano + 1}", estrategia="ACASO (K/N)", captura_alunos=K / len(te), sobrep_taxa=K / len(te), sobrep_cont=K / len(te)))
        # fronteira taxa x contagem e cotas por estrato
        te["esp"] = te.eb * te.n_use
        tot, tot_i = te.B1.sum(), te.loc[te.INDIG_E == 1, "B1"].sum()
        def resumo(sel, rot):
            return dict(fold=ano, regra=rot, captura=sel.B1.sum() / tot, captura_em_escolas_indigenas=sel.loc[sel.INDIG_E == 1, "B1"].sum() / tot_i,
                        n_indig=int((sel.INDIG_E == 1).sum()), n_capital=int((sel.ESTRATO == "1-Capital urbana").sum()), matr_mediana=sel.n1.median())
        for lam in (0, 0.25, 0.5, 0.75, 1.0):
            fron.append(resumo(te.assign(s=te.eb * te.n_use ** lam).nlargest(K, "s"), f"EB × matrícula^{lam}"))
        tam, esp = te.groupby("ESTRATO").size(), te.groupby("ESTRATO").esp.sum()
        for rot, peso in (("cota ∝ nº de escolas", tam), ("cota ∝ abandonos esperados", esp), ("cota ∝ √(escolas × abandonos esperados)", np.sqrt(tam * esp))):
            q = peso / peso.sum() * K
            ks = np.floor(q).astype(int)
            for e_ in (q - ks).sort_values(ascending=False).index[: K - ks.sum()]:
                ks[e_] += 1
            fron.append(resumo(pd.concat([te[te.ESTRATO == e_].nlargest(int(k_), "esp") for e_, k_ in ks.items()]), rot))
        # horizonte de dois anos (o que o dado público permite planejar): features de t, alvo em t+2
        t2 = d[(d.ANO == ano - 1) & d.y2.notna()].copy()
        if len(t2) > 50:
            p0b, mb = prior_eb(d[d.ANO < ano - 1])
            t2["eb"] = 100 * (t2.cumB + mb * p0b) / (t2.cumN + mb)
            yy, BB = t2.y2.to_numpy(float), t2.B2.to_numpy(float)
            for nome, s in (("persistência", t2[y].fillna(med)), ("EB", t2.eb), ("EB × matrícula", t2.eb * t2.n_use)):
                sel = np.argsort(-s.to_numpy(float), kind="stable")[:K]
                h2.append(dict(alvo=ano + 1, estrategia=nome, spearman_taxa=spearmanr(s, yy).statistic, captura_alunos=BB[sel].sum() / BB.sum(),
                               MAE=np.abs(s.to_numpy(float) - yy).mean() if nome != "EB × matrícula" else np.nan))
    r = pd.DataFrame(linhas)
    r.to_csv(saida / f"CD_estrategias_{et}.csv", index=False)
    cols = ["MAE", "MAE_pond", "R2", "R2c", "spearman", "sobrep_taxa", "sobrep_cont", "captura_alunos", "matr_mediana", "n_indig"]
    print("Média dos 4 folds:\n", r.groupby("estrategia", sort=False)[cols].mean().round(3).to_string())
    print("\nR² por fold (previsores de taxa):\n", r[r.R2.notna()].pivot_table(index="estrategia", columns="fold", values="R2", sort=False).round(3).to_string())
    print("\nCaptura de alunos por fold:\n", r.pivot_table(index="estrategia", columns="fold", values="captura_alunos", sort=False).round(3).to_string())
    f = pd.DataFrame(fron)
    f.to_csv(saida / f"D_fronteira_{et}.csv", index=False)
    print(f"\nFronteira taxa × contagem e cotas por estrato (média dos 4 folds, K={K}):\n",
          f.groupby("regra", sort=False).mean(numeric_only=True).drop(columns="fold").round(3).to_string())
    if h2:
        hh = pd.DataFrame(h2)
        hh.to_csv(saida / f"C_horizonte2_{et}.csv", index=False)
        print("\nHorizonte de 2 anos (features de t, alvo em t+2), média dos alvos disponíveis:\n", hh.groupby("estrategia", sort=False)[["spearman_taxa", "captura_alunos", "MAE"]].mean().round(3).to_string())
    # regressão à média: o que acontece com o top-K por taxa no ano seguinte, sem nenhuma intervenção
    print("\nRegressão à média do top-30 por taxa (nenhuma intervenção do projeto):")
    for ano in (2022, 2023, 2024):
        x = d[(d.ANO == ano) & d.y1.notna()]
        top = x.nlargest(K, y)
        print(f"   top-{K} de {ano}: taxa média {top[y].mean():.1f} p.p. em {ano} -> {top.y1.mean():.1f} p.p. em {ano + 1} "
              f"(rede toda: {x[y].mean():.1f} -> {x.y1.mean():.1f}); {int((top.y1 < top[y]).sum())} das {K} caíram")
    return d


def bloco_series(p, saida):
    titulo("E. RECORTE 9º ANO – 3ª SÉRIE")
    pub = p[p.REDE_PUBLICA == 1].copy().sort_values(["CO_ENTIDADE", "ANO"])
    print("Abandono por série — média simples das escolas (p.p.):\n", pub.groupby("ANO")[[f"AB_{s}" for s in SERIES[:-1]]].mean().round(2).to_string())
    pub["M_F9"] = pub.QT_MAT_FUND_AF_9
    for k in (1, 2, 3):
        pub[f"M_M{k}"] = np.where(pub.ANO == 2025, pub[f"QT_MAT_MED_{k}"],
                                  pub[[f"QT_MAT_MED_PROP_{k}", f"QT_MAT_MED_CT_{k}", f"QT_MAT_MED_NM_{k}"]].sum(axis=1, min_count=1))
    x = pub[pub.ANO >= 2023]
    par = (("FUN_09", "M_F9"), ("MED_01", "M_M1"), ("MED_02", "M_M2"), ("MED_03", "M_M3"))
    linhas = []
    for a in (2023, 2024, 2025):
        z = x[x.ANO == a]
        L = dict(ano=a)
        for s, m in par:
            L[f"abandono_{s}"] = np.nansum(z[f"AB_{s}"] * z[m]) / z.loc[z[f"AB_{s}"].notna(), m].sum()
            L[f"matricula_{s}"] = z[m].sum()
        linhas.append(L)
    t = pd.DataFrame(linhas).set_index("ano")
    print("\nMatrícula e abandono ponderado por série, rede pública (matrícula por série só existe de 2023 em diante):\n", t.round(2).to_string())
    t.to_csv(saida / "E_series.csv")
    z = x[x.ANO == 2025]
    print("   tamanho da série por escola em 2025 (mediana, P25):", {m: (float(z.loc[z[m] > 0, m].median()), float(z.loc[z[m] > 0, m].quantile(.25))) for _, m in par})
    tot = x.groupby("ANO")[["QT_MAT_FUND_AF_8", "M_F9", "M_M1", "M_M2", "M_M3"]].sum()
    for a in (2023, 2024):
        print(f"   progressão aparente da coorte {a}->{a + 1}: 8º->9º {tot.loc[a + 1, 'M_F9'] / tot.loc[a, 'QT_MAT_FUND_AF_8']:.3f} | 9º->1ª {tot.loc[a + 1, 'M_M1'] / tot.loc[a, 'M_F9']:.3f} "
              f"| 1ª->2ª {tot.loc[a + 1, 'M_M2'] / tot.loc[a, 'M_M1']:.3f} | 2ª->3ª {tot.loc[a + 1, 'M_M3'] / tot.loc[a, 'M_M2']:.3f}")
    g = pub.groupby("CO_ENTIDADE")
    prox = g["ANO"].shift(-1)
    print("\nO abandono da série s em t+1 se parece mais com a mesma série em t (horizontal), com a série s-1 em t (diagonal = mesma coorte) ou com a etapa inteira em t?")
    for s, ant in (("FUN_09", "FUN_08"), ("MED_01", "FUN_09"), ("MED_02", "MED_01"), ("MED_03", "MED_02")):
        alvo = g[f"AB_{s}"].shift(-1)
        etapa = "ABANDONO_MED" if s.startswith("MED") else "ABANDONO_FUN_AF"
        res = []
        for a in FOLDS:
            m = (pub.ANO == a) & (prox == pub.ANO + 1) & alvo.notna() & pub[f"AB_{s}"].notna() & pub[f"AB_{ant}"].notna()
            if m.sum() >= 30:
                res.append([spearmanr(pub.loc[m, col], alvo[m]).statistic for col in (f"AB_{s}", f"AB_{ant}", etapa)])
        r = np.mean(res, axis=0)
        print(f"   alvo {s}: horizontal {r[0]:.2f} | diagonal {r[1]:.2f} | etapa inteira {r[2]:.2f}")
    b = pub[pub.ABANDONO_FUN_AF.notna() & pub.ABANDONO_MED.notna()]
    print(f"\nEscolas-ano de EM que também têm anos finais: {len(b) / pub.ABANDONO_MED.notna().sum():.1%} | Spearman(AF, EM) na mesma escola-ano, por ano:",
          {int(a): round(float(spearmanr(z.ABANDONO_FUN_AF, z.ABANDONO_MED).statistic), 2) for a, z in b.groupby("ANO")})


def bloco_teto(d, et, c, info, saida, S=3000):
    titulo(f"F. TETO DE PREVISIBILIDADE POR SIMULAÇÃO — {et}  (ilustrativo)")
    rng = np.random.default_rng(RS)
    z = d[d.ANO >= 2022]
    x = z[z.ANO == 2025]
    h = z.groupby("CO_ENTIDADE").agg(B=("B", "sum"), n=("n_use", "sum"))
    p0 = h.B.sum() / h.n.sum()
    eb = ((h.B + 60 * p0) / (h.n + 60)).reindex(x.CO_ENTIDADE).to_numpy()
    tau = np.sqrt(info["icc"] * info["vt"]) / 100
    p_true = np.clip(eb.mean() + (eb - eb.mean()) * tau / eb.std(), 0.0005, 0.6)       # risco persistente "verdadeiro" com a variância estimada
    n = x.n_use.to_numpy().astype(int)
    vbin = (p_true * (1 - p_true) / n * 1e4).mean()
    v_extra = max(info["vt"] * (1 - info["icc"]) - vbin, 0.0)
    out = {}
    for nome, ve in (("só ruído binomial", 0.0), ("binomial + choques transitórios", v_extra)):
        ov, cap, orc, sp = [], [], [], []
        for _ in range(S):
            if ve > 0:
                v = np.minimum(ve / 1e4, p_true * (1 - p_true) * 0.95)
                kap = p_true * (1 - p_true) / v - 1
                pt = rng.beta(p_true * kap, (1 - p_true) * kap)
            else:
                pt = p_true
            B = rng.binomial(n, pt)
            taxa = B / n
            top_t = set(np.argsort(-(taxa + rng.uniform(0, 1e-9, len(n))))[:K])
            top_c = np.argsort(-(B + rng.uniform(0, 1e-6, len(n))))[:K]
            ov.append(len(top_t & set(np.argsort(-p_true)[:K])) / K)
            cap.append(B[np.argsort(-(p_true * n))[:K]].sum() / max(B.sum(), 1))
            orc.append(B[top_c].sum() / max(B.sum(), 1))
            sp.append(spearmanr(taxa, p_true).statistic)
        out[nome] = dict(sobreposicao_top30_por_taxa=np.mean(ov), spearman_taxa=np.mean(sp), captura_lista_por_contagem=np.mean(cap), captura_do_oraculo=np.mean(orc))
    t = pd.DataFrame(out).T
    print("Desempenho que se teria CONHECENDO o risco persistente verdadeiro de cada escola:\n", t.round(3).to_string())
    t.to_csv(saida / f"F_teto_{et}.csv")


def conferencia_uf(dados):
    """Compara com a taxa oficial da UF (rede pública), se as planilhas estiverem no disco."""
    try:
        import openpyxl
    except ImportError:
        return
    titulo("Conferência: taxas oficiais (INEP, nível UF, rede pública) — abandono AF e EM")
    for a in range(2019, 2026):
        f = dados / "bruto" / "indicadores" / "tx_rend" / str(a) / f"tx_rend_brasil_regioes_ufs_{a}.xlsx"
        if not f.exists():
            print(f"   {a}: planilha de UF ausente (em 2025 a ausência é deliberada no projeto)")
            continue
        ws = openpyxl.load_workbook(f, read_only=True, data_only=True).worksheets[0]
        tec = None
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i < 12 and row and row[0] is not None and str(row[0]).strip() in ("NU_ANO_CENSO", "Ano", "ano") and tec is None and any(str(c).startswith(("tab_", "3_CAT")) for c in row if c):
                tec = [str(c) for c in row]
            if tec and row and len(row) > 3 and str(row[1]).strip() in ("Brasil", "Roraima") and str(row[2]).strip() == "Total" and str(row[3]).strip() == "Pública":
                af = tec.index("3_CAT_FUN_AF") if "3_CAT_FUN_AF" in tec else tec.index("tab_F04")
                em = tec.index("3_CAT_MED") if "3_CAT_MED" in tec else tec.index("tab_MED")
                print(f"   {a} {str(row[1]):<8} AF {row[af]} | EM {row[em]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dados", default="dados")
    ap.add_argument("--saida", default="diagnosticos_saida")
    a = ap.parse_args()
    dados, saida = Path(a.dados), Path(a.saida)
    cache = saida / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    p = montar_painel(dados, cache)
    p.to_parquet(saida / "painel_diagnostico.parquet", index=False)
    pub = p[p.REDE_PUBLICA == 1].copy()
    print(f"Painel: {p.shape} | escolas públicas: {pub.CO_ENTIDADE.nunique()} | estrato em 2025: {pub[pub.ANO == 2025].ESTRATO.value_counts().to_dict()}")
    for et, c in ETAPAS.items():
        d = contagens(pub, c)
        bloco_porte(d, et, c, saida)
        info = bloco_estrutura(d, et, c, saida)
        d = bloco_previsao(d, et, c, saida)
        bloco_teto(d, et, c, info, saida)
    bloco_series(p, saida)
    conferencia_uf(dados)


if __name__ == "__main__":
    main()
