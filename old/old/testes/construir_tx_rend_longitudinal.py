# -*- coding: utf-8 -*-
"""
bruto (tx_rend RR 2007-2025)  ->  selecionado  ->  longitudinal (escola-ano, t -> t+1)

Escopo: SÓ tx_rend (conjunto "Core" do CLAUDE.md). Segue o desenho da base da Gabi
(src/base_longitudinal.py): 12 taxas = {APROVACAO, REPROVACAO, ABANDONO} x {FUN, FUN_AI,
FUN_AF, MED}, mais REDE_PUBLICA, DISP_REND, LAG1, DELTA1, T1 e ANO_ALVO.
Não altera nada em src/ nem em dados/. Só escreve em gustavo/saida/.

Etapas (cada uma é uma função):
  1. harmonizar_ano(): por ano, escolhe as 12 taxas POR POSIÇÃO e TRAVA com o rótulo do
     cabeçalho (armadilha P009/P014). Converte '--' em NA e tipa (regra 5 e 6).
  2. montar_selecionado(): empilha os 19 anos e confere contra o bruto.
  3. derivar_longitudinal(): REDE_PUBLICA, DISP_REND, LAG1, DELTA1, T1 por junção em ANO+-1.
  4. relatorio(): tabela por ano + comparação com a base da Gabi (2019-2025).

Por que lê gustavo/saida/cache/{ano}.parquet e não o bruto direto: o bruto empilha as 3
gerações pelo NOME da coluna e perde a ORDEM original; a posição é a única coisa confiável
(o nome técnico muda de significado entre anos). O cache é exatamente a tabela de cada ano,
na ordem original, e o bruto é a concatenação dele (a etapa 2 confere as contagens).

Uso:  python gustavo/construir_tx_rend_longitudinal.py
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = Path(__file__).resolve().parent / "saida"
CACHE = SAIDA / "cache"
BRUTO = SAIDA / "tx_rend_rr_2007_2025_bruto.parquet"
OUT_SEL = SAIDA / "tx_rend_rr_2007_2025_selecionado.parquet"
OUT_LONG = SAIDA / "tx_rend_rr_2007_2025_longitudinal.parquet"
OUT_REL = SAIDA / "validacao_longitudinal.txt"
BASE_GABI = RAIZ / "dados" / "processado" / "base_longitudinal_rr_2019_2025.parquet"

ANOS = range(2007, 2026)
CHAVE = ["ANO", "CO_ENTIDADE"]
IDENTIDADE = ["NO_ENTIDADE", "CO_MUNICIPIO", "NO_MUNICIPIO", "LOCALIZACAO", "DEPENDENCIA"]
MEDIDAS = {"APROVACAO": ("Aprovação", 0), "REPROVACAO": ("Reprovação", 18), "ABANDONO": ("Abandono", 36)}
ETAPAS = ["FUN", "FUN_AI", "FUN_AF", "MED"]
TAXAS = [f"{m}_{e}" for m in MEDIDAS for e in ETAPAS]          # as 12 colunas de taxa

# ---------------------------------------------------------------------------
# Posições (1-based) na planilha de 63 colunas. O bloco de Reprovação começa 18
# colunas depois do de Aprovação, e o de Abandono 36 depois (ver MEDIDAS).
#   Leiaute "A" (2007-2010): totais ficam no FIM de cada grupo (ordem antiga).
#   Leiaute "B" (2011-2025): totais ficam no INÍCIO (FUN, AI, AF, 1º..9º, MED, 1ª..4ª, NS).
# ---------------------------------------------------------------------------
POS_A = {"FUN": 21, "FUN_AI": 19, "FUN_AF": 20, "MED": 27}
POS_B = {"FUN": 10, "FUN_AI": 11, "FUN_AF": 12, "MED": 22}
# Posições das séries que COMPÕEM cada total (usadas só na checagem de consistência):
COMP_A = {"FUN": range(10, 19), "FUN_AI": range(10, 15), "FUN_AF": range(15, 19), "MED": range(22, 27)}
COMP_B = {"FUN": range(13, 22), "FUN_AI": range(13, 18), "FUN_AF": range(18, 22), "MED": range(23, 28)}


def leiaute(ano):
    return "A" if ano <= 2010 else "B"


def nomes_identidade(ano):
    """Colunas de identificação: aqui o NOME é confiável (rótulo literal), a ordem muda."""
    if ano <= 2014:
        dep = "Rede" if ano <= 2012 else "Dependência Administrativa"
        return dict(id="Código da Escola", nome="Nome da Escola", mun="Código do Município",
                    nmun="Nome do Município", loc="Localização", dep=dep)
    if ano <= 2020:
        return dict(id="CO_ENTIDADE", nome="NO_ENTIDADE", mun="CO_MUNICIPIO",
                    nmun="NO_MUNICIPIO", loc="TIPOLOCA", dep="Dependad")
    return dict(id="CO_ENTIDADE", nome="NO_ENTIDADE", mun="CO_MUNICIPIO",
                nmun="NO_MUNICIPIO", loc="NO_CATEGORIA", dep="NO_DEPENDENCIA")


def cabecalho_esperado(ano, medida, etapa):
    """Regex que o cabeçalho da posição escolhida PRECISA satisfazer. É a trava P009/P014:
    se o INEP reordenar colunas, o script para em vez de trocar taxas em silêncio."""
    nome, _ = MEDIDAS[medida]
    if ano <= 2010:                                    # rótulos humanos, ordem antiga
        return {"FUN": rf"^Total {nome} Fundamental$",
                "FUN_AI": rf"^{nome} 1ª a 4ª",
                "FUN_AF": rf"^{nome} 5ª a 8ª",
                "MED": rf"^Total {nome}\s*-?\s*Médio$"}[etapa]
    if ano <= 2014:                                    # rótulos humanos, ordem nova
        return {"FUN": rf"Total {nome}.*Ens\. Fundamental$",
                "FUN_AI": rf"^{nome} - Anos Iniciais",
                "FUN_AF": rf"^{nome} - Anos Finais",
                "MED": rf"Total {nome}.*Ens\. Médio$"}[etapa]
    if ano <= 2020:                                    # nomes técnicos tap_/tre_/tab_
        p = {"APROVACAO": "tap", "REPROVACAO": "tre", "ABANDONO": "tab"}[medida]
        # O nome do 3º item ESCORREGA: em 2015-2017 Anos Finais é *_F58; em 2018-2020 é *_F04
        # (e *_F58 passa a ser o 1º ano). Conferido nas linhas de rótulo humano dos zips.
        af = "F58" if ano <= 2017 else "F04"
        return {"FUN": rf"^{p}_FUN$", "FUN_AI": rf"^{p}_F14$", "FUN_AF": rf"^{p}_{af}$",
                "MED": rf"^{p}_MED$"}[etapa]
    k = {"APROVACAO": 1, "REPROVACAO": 2, "ABANDONO": 3}[medida]   # 2021+
    return {"FUN": rf"^{k}_CAT_FUN$", "FUN_AI": rf"^{k}_CAT_FUN_AI$",
            "FUN_AF": rf"^{k}_CAT_FUN_AF$", "MED": rf"^{k}_CAT_MED$"}[etapa]


def para_float(serie):
    """'--' = ausência estrutural -> NA (regra 5). Qualquer outro texto não numérico dá erro."""
    return pd.to_numeric(serie.where(serie != "--"), errors="raise").astype("Float64")


# ---------------------------------------------------------------------------
# Etapa 1 - um ano
# ---------------------------------------------------------------------------
def harmonizar_ano(ano):
    df = pd.read_parquet(CACHE / f"{ano}.parquet")
    assert df.shape[1] == 64, f"{ano}: esperado 63 colunas + ANO, veio {df.shape[1]}"
    assert (df["ANO"] == ano).all()
    cols = [re.sub(r"\s+", " ", str(c)).strip() for c in df.columns]
    pos = POS_A if leiaute(ano) == "A" else POS_B
    comp = COMP_A if leiaute(ano) == "A" else COMP_B

    ident = nomes_identidade(ano)
    out = pd.DataFrame({
        "ANO": np.int16(ano),
        "CO_ENTIDADE": df[ident["id"]].astype("int64").astype("string"),
        "NO_ENTIDADE": df[ident["nome"]].astype("string").str.strip(),
        "CO_MUNICIPIO": df[ident["mun"]].astype("int64").astype("string"),
        "NO_MUNICIPIO": df[ident["nmun"]].astype("string").str.strip(),
        "LOCALIZACAO": df[ident["loc"]].astype("string").str.strip(),
        # 'Particular' (2007-11, 2014, 2015) e 'Privada' (demais) são a mesma rede.
        "DEPENDENCIA": df[ident["dep"]].astype("string").str.strip().replace({"Particular": "Privada"}),
    })

    faixas_fora = 0                                   # componentes vs. total (ver abaixo)
    for medida, (_, desloc) in MEDIDAS.items():
        for etapa in ETAPAS:
            p = pos[etapa] + desloc
            rotulo = cols[p - 1]
            assert re.search(cabecalho_esperado(ano, medida, etapa), rotulo), (
                f"{ano}: posição {p} deveria ser {medida}_{etapa}, mas o cabeçalho é {rotulo!r}")
            out[f"{medida}_{etapa}"] = para_float(df.iloc[:, p - 1])
            # Consistência: uma taxa total é média ponderada das séries -> fica entre o mín e o
            # máx delas. Pega troca de coluna que o cabeçalho sozinho não pegaria (ex.: nos
            # anos com nomes técnicos). Tolerância 0,15 = arredondamento de 1 casa.
            partes = pd.concat([para_float(df.iloc[:, q + desloc - 1]) for q in comp[etapa]], axis=1)
            mn, mx = partes.min(axis=1, skipna=True), partes.max(axis=1, skipna=True)
            tot = out[f"{medida}_{etapa}"]
            ok = tot.notna() & mn.notna()
            faixas_fora += int(((tot[ok] < mn[ok] - 0.15) | (tot[ok] > mx[ok] + 0.15)).sum())
    out.attrs["faixas_fora"] = faixas_fora
    return out


# ---------------------------------------------------------------------------
# Etapa 2 - selecionado
# ---------------------------------------------------------------------------
def montar_selecionado():
    partes = [harmonizar_ano(a) for a in ANOS]
    faixas = {a: p.attrs["faixas_fora"] for a, p in zip(ANOS, partes)}
    sel = pd.concat(partes, ignore_index=True)
    sel = sel[CHAVE + IDENTIDADE + TAXAS].sort_values(CHAVE).reset_index(drop=True)

    assert not sel.duplicated(CHAVE).any(), "chave ANO+CO_ENTIDADE repetida"
    bruto = pd.read_parquet(BRUTO, columns=["ANO"])
    assert sel.groupby("ANO").size().to_dict() == bruto.groupby("ANO").size().to_dict(), \
        "linhas por ano diferem do bruto"
    for c in TAXAS:
        assert sel[c].dropna().between(0, 100).all(), f"{c} fora de [0,100]"
    sel.to_parquet(OUT_SEL, index=False)
    return sel, faixas


# ---------------------------------------------------------------------------
# Etapa 3 - longitudinal (mesma lógica da Gabi: junção em ANO+-1, nunca shift())
# ---------------------------------------------------------------------------
LAG1 = ["ABANDONO_FUN", "ABANDONO_FUN_AF", "ABANDONO_MED"]
DELTA1 = ["ABANDONO_FUN_AF", "ABANDONO_MED"]
T1 = ["ABANDONO_FUN", "ABANDONO_FUN_AF", "ABANDONO_MED"]


def derivar_longitudinal(sel):
    base = sel.copy()
    base["REDE_PUBLICA"] = (base["DEPENDENCIA"] != "Privada").astype("Int8")
    base["DISP_REND"] = base[TAXAS].notna().any(axis=1).astype("Int8")

    def valores_em(delta, cols, sufixo):
        """Valores da MESMA escola em ANO+delta, alinhados à linha de ANO.
        Se a escola não tem linha nesse ano, fica NA (shift() ligaria 2019 a 2021)."""
        outro = base[CHAVE + cols].assign(ANO=lambda d: (d["ANO"] - delta).astype("int16"))
        outro = outro.rename(columns={c: f"{c}{sufixo}" for c in cols})
        return base[CHAVE].merge(outro, on=CHAVE, how="left", validate="1:1")

    ant = valores_em(-1, sorted(set(LAG1) | set(DELTA1)), "__t-1")
    seg = valores_em(+1, T1, "__t+1")
    for x in LAG1:
        base[f"{x}_LAG1"] = pd.array(ant[f"{x}__t-1"], dtype="Float64")
    for x in DELTA1:
        base[f"{x}_DELTA1"] = base[x] - pd.array(ant[f"{x}__t-1"], dtype="Float64")
    for x in T1:
        base[f"{x}_T1"] = pd.array(seg[f"{x}__t+1"], dtype="Float64")

    existe = base[CHAVE].assign(ANO=lambda d: (d["ANO"] - 1).astype("int16"), _e=True)
    tem_seg = base[CHAVE].merge(existe, on=CHAVE, how="left", validate="1:1")["_e"].notna()
    base["ANO_ALVO"] = pd.array(np.where(tem_seg, base["ANO"] + 1, pd.NA), dtype="Int16")

    ordem = (["ANO", "ANO_ALVO", "CO_ENTIDADE"] + IDENTIDADE + ["REDE_PUBLICA", "DISP_REND"] + TAXAS
             + [f"{x}_LAG1" for x in LAG1] + [f"{x}_DELTA1" for x in DELTA1] + [f"{x}_T1" for x in T1])
    base = base[ordem].astype({"ANO": "Int16"})
    # o T1 só pode ser lido do ano seguinte: se ANO_ALVO é NA, T1 tem que ser NA
    assert base.loc[base["ANO_ALVO"].isna(), [f"{x}_T1" for x in T1]].isna().all().all()
    base.to_parquet(OUT_LONG, index=False)
    return base


# ---------------------------------------------------------------------------
# Etapa 4 - relatório e comparação com a base da Gabi
# ---------------------------------------------------------------------------
def relatorio(sel, base, faixas):
    L = ["VALIDAÇÃO - tx_rend RR 2007-2025 (selecionado + longitudinal)", "=" * 70, ""]
    L.append(f"selecionado: {sel.shape[0]} linhas x {sel.shape[1]} colunas | "
             f"longitudinal: {base.shape[0]} x {base.shape[1]}")
    L.append("")
    L.append("Por ano (médias só das escolas com valor; compare 2010->2011 e 2014->2015):")
    L.append(f"{'ano':>5}{'linhas':>8}{'c/AF':>6}{'c/MED':>6}{'abandAF':>9}{'abandMED':>10}"
             f"{'T1_AF':>7}{'soma≠100':>9}{'compFora':>9}")
    for a, g in base.groupby("ANO"):
        soma = 0
        for e in ETAPAS:
            t = g[f"APROVACAO_{e}"] + g[f"REPROVACAO_{e}"] + g[f"ABANDONO_{e}"]
            soma += int(((t - 100).abs() > 0.2).sum())
        L.append(f"{a:>5}{len(g):>8}{int(g['ABANDONO_FUN_AF'].notna().sum()):>6}"
                 f"{int(g['ABANDONO_MED'].notna().sum()):>6}"
                 f"{g['ABANDONO_FUN_AF'].mean():>9.2f}{g['ABANDONO_MED'].mean():>10.2f}"
                 f"{int(g['ABANDONO_FUN_AF_T1'].notna().sum()):>7}{soma:>9}{faixas[int(a)]:>9}")
    L.append("")
    L.append("Dependência (após Particular->Privada): " + str(sel["DEPENDENCIA"].value_counts().to_dict()))

    if BASE_GABI.exists():
        g = pd.read_parquet(BASE_GABI)
        g["ANO"] = g["ANO"].astype("Int16")
        cols = (TAXAS + [f"{x}_LAG1" for x in LAG1] + [f"{x}_DELTA1" for x in DELTA1]
                + [f"{x}_T1" for x in T1] + ["REDE_PUBLICA", "DISP_REND", "DEPENDENCIA", "ANO_ALVO"])
        m = base[base["ANO"] >= 2019][CHAVE + cols].merge(
            g[CHAVE + cols], on=CHAVE, how="inner", suffixes=("", "__g"), validate="1:1")
        L += ["", f"Comparação com a base da Gabi (2019-2025): {len(m)} linhas em comum "
                  f"de {int((base['ANO'] >= 2019).sum())} minhas e {len(g)} dela"]
        # LAG1/DELTA1 de 2019 dependem de 2018, que a base da Gabi não tem: só 2020+ é comparável.
        # ANO_ALVO depende do universo (a dela inclui escolas só de TDI/ATU): mostrado à parte.
        for c in cols:
            mm = m[m["ANO"] >= 2020] if c.endswith(("_LAG1", "_DELTA1")) else m
            x, y = mm[c], mm[f"{c}__g"]
            na_dif = int((x.isna() != y.isna()).sum())
            ambos = x.notna() & y.notna()
            if pd.api.types.is_numeric_dtype(x):
                dif = int(((x[ambos].astype("float64") - y[ambos].astype("float64")).abs() > 1e-9).sum())
            else:
                dif = int((x[ambos] != y[ambos]).sum())
            if na_dif or dif:
                L.append(f"  [DIF] {c}: ausência diverge em {na_dif}, valor diverge em {dif}")
        n2019 = m[m["ANO"] == 2019]
        L.append(f"  (LAG1/DELTA1 comparados só de 2020 em diante; em 2019 eu tenho LAG de 2018 e ela não: "
                 f"{int(n2019['ABANDONO_FUN_AF_LAG1'].notna().sum())} escolas)")
        L.append("  (colunas não listadas: idênticas, inclusive onde é ausente)")
    else:
        L.append(f"\nBase da Gabi não encontrada em {BASE_GABI}; comparação pulada.")

    texto = "\n".join(L)
    OUT_REL.write_text(texto, encoding="utf-8")
    print(texto)


def main():
    sel, faixas = montar_selecionado()
    print(f"selecionado gravado: {OUT_SEL.name} {sel.shape}")
    base = derivar_longitudinal(sel)
    print(f"longitudinal gravado: {OUT_LONG.name} {base.shape}\n")
    relatorio(sel, base, faixas)


if __name__ == "__main__":
    sys.exit(main())
