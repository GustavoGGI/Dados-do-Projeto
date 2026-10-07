import pandas as pd
from pathlib import Path

# Configuração de caminhos
BASE_LONG = Path.cwd() / 'dados' / 'processado' / 'base_longitudinal_rr_2019_2025.parquet'
df = pd.read_parquet(BASE_LONG)

# 1. Separar a base de inferência futura (2025)
# O alvo ABANDONO_XXX_T1 (2026) não existe ainda. Usaremos isso apenas no final do projeto para prever o risco futuro.
df_inferencia = df[df['ANO_ALVO'].isna()].copy()

# 2. Separar a base de treino e validação (2019-2024)
df_treino_teste = df[df['ANO_ALVO'].notna()].copy()

# 3. Remover 2019 do treino (Tratamento de Lags)
# Como a base começa em 2019, as colunas '_LAG1' e '_DELTA1' são nulas. 
# Manter 2019 forçaria o modelo a imputar valores falsos para o passado de todas as escolas.
df_treino_teste = df_treino_teste[df_treino_teste['ANO'] > 2019].copy()

# 4. Definir colunas base de identificação que vão para todos os recortes
cols_base = [
    'ANO', 'ANO_ALVO', 'CO_ENTIDADE', 'NO_ENTIDADE', 'CO_MUNICIPIO', 
    'LOCALIZACAO', 'DEPENDENCIA', 'REDE_PUBLICA'
]

# 5. Criar dataset específico para Anos Finais (Foco 9º ano)
# Filtra apenas linhas que possuem a variável alvo preenchida para os Anos Finais
df_af = df_treino_teste[df_treino_teste['ABANDONO_FUN_AF_T1'].notna()].copy()

# Seleciona as colunas de identificação + todas que contêm '_AF' ou '_FUN' (ignorando '_AI' que são Anos Iniciais)
cols_af = [c for c in df.columns if ('_AF' in c or '_FUN' in c) and ('_AI' not in c)]
df_af = df_af[cols_base + cols_af]

# 6. Criar dataset específico para Ensino Médio (1º ao 3º ano)
# Filtra apenas linhas que possuem a variável alvo preenchida para o Ensino Médio
df_med = df_treino_teste[df_treino_teste['ABANDONO_MED_T1'].notna()].copy()

# Seleciona as colunas de identificação + todas que contêm '_MED'
cols_med = [c for c in df.columns if '_MED' in c]
df_med = df_med[cols_base + cols_med]

print(f"Total original: {df.shape[0]} linhas\n")
print(f"Base Treino/Teste - Anos Finais (2020-2024): {df_af.shape[0]} linhas, {df_af.shape[1]} colunas")
print(f"Base Treino/Teste - Ensino Médio (2020-2024): {df_med.shape[0]} linhas, {df_med.shape[1]} colunas")
print(f"Base de Inferência para uso futuro (2025): {df_inferencia.shape[0]} linhas")