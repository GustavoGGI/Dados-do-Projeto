import pandas as pd
base = pd.read_parquet("../saida/base_completa.parquet")
print(base[base["ANO"] == 2010]["IIB_agua_potavel"].notna().sum())  # deve ser ~632


features = [c for c in base.columns if c.startswith(("IIB_","IDA_","IDP_","IEP_"))]
for c in features:
    print(c, sorted(base[c].dropna().unique()))