# ============================================================
# IMPORTS E CONFIGURAÇÃO
# ------------------------------------------------------------
# Projeto: Risco de abandono escolar em Roraima
# Fase 1 : smoke test — 2025 apenas, base nova (recorte RR)
# ============================================================

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

# sklearn — pré-processamento
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder

# sklearn — modelo e avaliação
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
)
from sklearn.ensemble import (
    RandomForestRegressor, HistGradientBoostingRegressor,
)
from sklearn.linear_model import Ridge

# visualização
import matplotlib.pyplot as plt

# ============================================================
# CONFIGURAÇÃO
# ============================================================
RANDOM_STATE = 1
np.random.seed(RANDOM_STATE)

# Silenciar warnings comuns (pandas futuro, sklearn, openpyxl)
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning, module='sklearn')
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

# ============================================================
# CAMINHOS
# ------------------------------------------------------------
# O notebook roda em notebooks/. A raiz do repositório é um
# nível acima. Detecta isso automaticamente para funcionar
# também se for executado da raiz por engano.
# ============================================================
CWD = Path.cwd()
BASE = CWD.parent if CWD.name == 'notebooks' else CWD

DADOS        = BASE / 'dados'
INTERIM      = DADOS / 'interim' / 'indicadores_rr'
PROCESSADO   = DADOS / 'processado'

# Produto final do bootstrap
BASE_LONG = PROCESSADO / 'base_longitudinal_rr_2019_2025.parquet'

print('CWD        :', CWD)
print('BASE       :', BASE)
print('INTERIM    :', INTERIM, '→', INTERIM.exists())
print('PROCESSADO :', PROCESSADO, '→', PROCESSADO.exists())
print('Base long. :', BASE_LONG, '→', BASE_LONG.exists())
