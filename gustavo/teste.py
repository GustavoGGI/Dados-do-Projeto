def detectar_cabecalho(df_raw, max_rows=30):
    """
    Detecta geração e retorna (linha_inicio_cabecalho, n_linhas_cabecalho).

    - Geração nova/intermediária: 1 linha técnica (com tap_/1_CAT_/NU_ANO_CENSO).
    - Geração antiga (2007-2014): 2 linhas combinadas (nomes gerais + subtítulos).
    """
    padroes_tecnicos = (
        "tap_", "tre_", "tab_",
        "1_cat_", "2_cat_", "3_cat_",
        "nu_ano_censo", "co_entidade",
    )

    # Estratégia 1: linha técnica
    for i in range(min(max_rows, len(df_raw))):
        vals = [str(v).strip().lower() for v in df_raw.iloc[i] if pd.notna(v)]
        if len(vals) < 40:
            continue
        n_tec = sum(1 for p in padroes_tecnicos if any(p in v for v in vals))
        if n_tec >= 2:
            return i, 1

    # Estratégia 2: cabeçalho antigo em 2 linhas
    # Procura primeira linha "nome de coluna" (>=10 strings não vazias)
    # seguida de uma linha com muitas células preenchidas (sub-cabeçalho)
    for i in range(min(max_rows - 1, len(df_raw) - 1)):
        vals1 = [v for v in df_raw.iloc[i] if pd.notna(v)]
        if len(vals1) < 10:
            continue
        # primeira célula deve ser algo tipo "Ano" (não numérico)
        prim = str(vals1[0]).strip().lower()
        if prim in ("ano", "nu_ano_censo"):
            # confirma que linha i+1 tem pelo menos 40 preenchidas
            prox = [v for v in df_raw.iloc[i + 1] if pd.notna(v)]
            if len(prox) >= 40:
                return i, 2

    return None, 0


def construir_colunas(df_raw, linha, n_linhas):
    """Constrói lista de nomes de coluna, combinando 2 linhas se preciso."""
    l1 = df_raw.iloc[linha].tolist()
    if n_linhas == 1:
        return [str(v).strip() if pd.notna(v) else f"_col_{j}"
                for j, v in enumerate(l1)]

    l2 = df_raw.iloc[linha + 1].tolist()
    cols = []
    for j, v1 in enumerate(l1):
        s1 = str(v1).strip() if pd.notna(v1) else ""
        s2 = ""
        if j < len(l2) and pd.notna(l2[j]):
            s2 = str(l2[j]).strip()
        # ignora marcadores vazios
        if s1 in ("·", "--", "-", "nan"):
            s1 = ""
        if s2 in ("·", "--", "-", "nan"):
            s2 = ""
        if s1 and s2:
            cols.append(f"{s1} - {s2}")
        elif s1:
            cols.append(s1)
        elif s2:
            cols.append(s2)
        else:
            cols.append(f"_col_{j}")
    return cols


def ler_planilhas_do_zip(zip_path):
    with zipfile.ZipFile(zip_path) as zf:
        arquivos = [i for i in zf.infolist() if not i.is_dir()]
        xlsx = sorted([i for i in arquivos if i.filename.lower().endswith(".xlsx")],
                      key=lambda i: -i.file_size)
        xls = sorted([i for i in arquivos
                      if i.filename.lower().endswith(".xls")
                      and not i.filename.lower().endswith(".xlsx")],
                     key=lambda i: -i.file_size)
        if xlsx:
            escolhido = xlsx[0]
        elif xls:
            escolhido = xls[0]
        else:
            raise ValueError(f"Nenhum xls/xlsx em {zip_path.name}")
        conteudo = zf.read(escolhido.filename)
        nome_interno = escolhido.filename

    engine = "xlrd" if nome_interno.lower().endswith(".xls") else "openpyxl"
    try:
        sheets = pd.read_excel(io.BytesIO(conteudo), sheet_name=None,
                               header=None, engine=engine)
    except Exception as e:
        raise RuntimeError(f"Falha ao abrir {nome_interno}: {e}") from e

    resultados = []
    for nome_sheet, df_raw in sheets.items():
        linha, n_linhas = detectar_cabecalho(df_raw)
        if linha is None:
            continue
        colunas = construir_colunas(df_raw, linha, n_linhas)
        # dados começam após a última linha de cabeçalho
        primeira_dado = linha + n_linhas
        # pula linhas totalmente vazias
        while primeira_dado < len(df_raw) and df_raw.iloc[primeira_dado].notna().sum() == 0:
            primeira_dado += 1
        if primeira_dado >= len(df_raw):
            continue
        dados = df_raw.iloc[primeira_dado:].copy()
        dados.columns = colunas
        dados = dados.dropna(how="all")
        if len(dados) == 0:
            continue
        dados = dedup_cols(dados)
        resultados.append((nome_sheet, dados, linha, len(colunas)))
    return resultados, nome_interno