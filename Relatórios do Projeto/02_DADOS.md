# 02 — Dados

Tudo sobre os dados: fontes, repositório, base longitudinal,
qualidade, limites e enriquecimento planejado.

---

# Parte A — Fontes

## 1. INEP

Toda a matéria-prima vem do INEP.

### 1.1 Microdados do Censo Escolar (2019–2025)

- Base anual com uma linha por escola.
- Contém infraestrutura, dependências, equipamentos, profissionais,
  oferta, acessibilidade, escola indígena, terra indígena,
  assentamento.
- Formato original: um zip por ano, contendo um CSV grande.
- **Uso no projeto:** espinha dorsal da base longitudinal + material
  para enriquecimento futuro.
- **Zips:** 7. O de 2025 tem ~537 MB.

### 1.2 Indicadores Educacionais (2019–2025)

- Planilhas `.xlsx` por indicador e por ano, em três níveis (escola,
  município, Brasil/UF).
- **Indicadores usados:** tx_rend, TDI, ATU, IED, HAD.
- **Uso no projeto:** apenas nível escola.
- **Zips:** 103.

## 2. Manifesto

- **Arquivo:** `dados/MANIFEST.csv`. Versionado no git.
- **Colunas:** `estagio, origem, arquivo, sha256, data_download`.
- **Função:** reprodutibilidade. O bootstrap confere cada arquivo
  obtido contra o sha256 registrado.

## 3. Revisão de arquivos pelo INEP

- O INEP **substitui arquivos depois de publicar**, nem sempre com
  aviso.
- Exemplo: zip de microdados de 2024 é uma versão revisada em
  julho/2026, sem nota na página.
- Exemplo: em seis planilhas de indicadores, o md5 publicado pelo INEP
  não confere com o arquivo do zip (P007 e P020).
- **Consequência:** a referência é o sha256 do manifesto, não o hash
  publicado.

## 4. Certificado do servidor

- `download.inep.gov.br` não envia a cadeia completa do certificado
  TLS.
- **Solução:** o repositório traz o certificado que falta em
  `src/certificados/`, conferido por fingerprint.
- Se o INEP trocar o certificado, o download para com mensagem
  indicando o que atualizar.

## 5. Citação

> BRASIL. Instituto Nacional de Estudos e Pesquisas Educacionais
> Anísio Teixeira (Inep). **Microdados do Censo Escolar da Educação
> Básica 2019–2025.** Brasília: Inep. Acesso em 2 a 15 set. 2026.

> BRASIL. Inep. **Indicadores Educacionais: Taxas de Rendimento,
> Distorção Idade-série, Alunos por Turma, Esforço Docente e Horas-
> aula diária, 2019–2025.** Brasília: Inep. Acesso em 9 a 17 set.
> 2026.

## 6. Fontes alternativas

- **Base dos Dados** (basedosdados.org): sugerida no grupo.
  **Descartada** para o alvo porque não contém a taxa de rendimento
  escolar (tx_rend). Pode ser útil para outras variáveis.

---

# Parte B — Repositório e bootstrap

## 7. Estrutura do repositório

```text
abandono-escolar/
├── dados/
│   ├── origem/                  zips do INEP (~2,9 GB)
│   │   ├── censo/               7 zips de microdados 2019–2025
│   │   ├── indicadores/         103 zips
│   │   └── doc/
│   ├── bruto/                   extraído dos zips (~3,0 GB)
│   ├── interim/indicadores_rr/  recorte de Roraima em Parquet
│   ├── processado/              base longitudinal final
│   ├── externo/                 arquivos do orientador (ausente)
│   ├── cache_download/          descartável
│   └── MANIFEST.csv             lista mestre com sha256 (versionado)
├── docs/
│   ├── metodologia_variaveis.md
│   ├── DECISOES.md
│   ├── problemas.csv
│   ├── inventarios/
│   └── catalogo_variaveis.html
├── src/
│   ├── bootstrap.py             pipeline completo
│   ├── base_longitudinal.py     gera a base final
│   ├── certificados/            certificado do INEP
│   └── fontes_inep.csv          URLs dos zips
├── tests/
├── notebooks/
└── CLAUDE.md
```

## 8. Pré-requisitos

- Python 3.12+ (numpy fixado exige 3.12).
- ~6 GB livres (2,9 GB de zips + 3,0 GB extraídos).
- Git.
- Tempo: ~44 min num SSD; na prática, medido ~3h52min com
  sincronização de nuvem ativa na pasta `dados/`.

## 9. Comandos

```bash
git clone <url> abandono-escolar
cd abandono-escolar
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Obter os dados
python -m src.bootstrap --baixar
# ou
python -m src.bootstrap --origem-local C:\caminho\para\zips
# ou
python -m src.bootstrap --baixar --so-aquisicao
```

## 10. O que o bootstrap faz

1. Estimativa de espaço e tempo.
2. Aquisição — baixa 110 zips ou copia de pasta local.
3. Extração em `dados/bruto/`.
4. Conferência sha256 contra o manifesto.
5. Inventário de microdados.
6. Catálogo de variáveis.
7. Inventário de indicadores.
8. Recorte RR → `dados/interim/indicadores_rr/`.
9. Base longitudinal → `dados/processado/`.
10. Análise base v1 do orientador (se presente).
11. Catálogo HTML.
12. Conferência final: `git status docs/` limpo.

## 11. Reprodutibilidade

- Rodar de novo é seguro: o que existe e confere não é refeito.
- Arquivo divergente vai para `cache_download/divergente/` e o
  bootstrap para.
- Nada divergente entra nas pastas de dados.

## 12. Limitação conhecida

A base do orientador (`base_longitudinal_v1/`) foi entregue pronta e
não é reproduzível só a partir deste repositório. É necessária para
comparação. **Ação:** pedir ao orientador.

---

# Parte C — Base longitudinal

## 13. Visão geral

- **Arquivo:** `dados/processado/base_longitudinal_rr_2019_2025.parquet`
  (também em `.csv`).
- **Dimensões:** 6.054 linhas × 59 colunas.
- **Cobertura:** 2019 a 2025, Roraima, escola-ano.
- **Escolas únicas:** 934.
- **Unidade:** uma escola em um ano (`ANO`), com alvo em t+1
  (`ANO_ALVO`).

## 14. As 59 colunas

### 14.1 Identificação e metadados (8)

| Coluna | Tipo | Descrição |
|---|---|---|
| `ANO` | Int16 | Ano de referência. 2019–2025. |
| `ANO_ALVO` | Int16 | Ano do alvo. Sempre `ANO + 1`. Nulo em 2025. |
| `CO_ENTIDADE` | string | Código INEP da escola. Chave para join. |
| `NO_ENTIDADE` | string | Nome da escola. 105 escolas mudam de nome. |
| `CO_MUNICIPIO` | string | Código INEP do município. 15 em RR. |
| `NO_MUNICIPIO` | string | Nome do município. 16 valores (um muda). |
| `LOCALIZACAO` | string | Urbana ou Rural. |
| `DEPENDENCIA` | string | Municipal, Estadual, Privada, Federal. |

### 14.2 Flags (5)

| Coluna | Descrição |
|---|---|
| `REDE_PUBLICA` | 1 = pública, 0 = privada. |
| `DISP_ATU` | 1 = tem dado de ATU. |
| `DISP_TDI` | 1 = tem dado de TDI. |
| `DISP_IED` | 1 = tem dado de IED. |
| `DISP_REND` | 1 = tem dado de rendimento. |

Permitem distinguir "escola sem indicador" de "indicador = zero".

### 14.3 ATU — Média de Alunos por Turma (4)

| Coluna | Etapa |
|---|---|
| `ATU_FUN_TOTAL` | Todo o fundamental. |
| `ATU_FUN_AI` | Anos iniciais. |
| `ATU_FUN_AF` | Anos finais. |
| `ATU_MED_TOTAL` | Ensino médio. |

### 14.4 TDI — Distorção Idade-Série (4)

`TDI_FUN_TOTAL`, `TDI_FUN_AI`, `TDI_FUN_AF`, `TDI_MED_TOTAL`.

### 14.5 IED — Esforço Docente (14)

`IED_FUN_N1` a `IED_FUN_N6`, `IED_FUN_ALTO`.
`IED_MED_N1` a `IED_MED_N6`, `IED_MED_ALTO`.

Só existe a partir de 2021.

### 14.6 Aprovação (4)

`APROVACAO_FUN`, `APROVACAO_FUN_AI`, `APROVACAO_FUN_AF`, `APROVACAO_MED`.

### 14.7 Reprovação (4)

`REPROVACAO_FUN`, `REPROVACAO_FUN_AI`, `REPROVACAO_FUN_AF`,
`REPROVACAO_MED`.

### 14.8 Abandono contemporâneo (4)

`ABANDONO_FUN`, `ABANDONO_FUN_AI`, `ABANDONO_FUN_AF`, `ABANDONO_MED`.

São features legítimas: abandono em t, alvo é em t+1.

### 14.9 Abandono defasado — `_LAG1` (3)

`ABANDONO_FUN_LAG1`, `ABANDONO_FUN_AF_LAG1`, `ABANDONO_MED_LAG1`.

Em 2019 são nulas — não há 2018.

### 14.10 Variação anual — `_DELTA1` (6)

`TDI_FUN_AF_DELTA1`, `TDI_MED_TOTAL_DELTA1`,
`ATU_FUN_AF_DELTA1`, `ATU_MED_TOTAL_DELTA1`,
`ABANDONO_FUN_AF_DELTA1`, `ABANDONO_MED_DELTA1`.

### 14.11 Alvos — `_T1` (3)

| Coluna | Etapa |
|---|---|
| `ABANDONO_FUN_T1` | Fundamental. Alvo auxiliar. |
| `ABANDONO_FUN_AF_T1` | Anos finais. Alvo principal AF. |
| `ABANDONO_MED_T1` | Ensino médio. Alvo principal EM. |

Nulas no último ano.

### 14.12 Contagem final

| Grupo | Nº |
|---|---|
| Identificação | 8 |
| Flags | 5 |
| ATU | 4 |
| TDI | 4 |
| IED | 14 |
| Aprovação | 4 |
| Reprovação | 4 |
| Abandono em t | 4 |
| `_LAG1` | 3 |
| `_DELTA1` | 6 |
| `_T1` | 3 |
| **Total** | **59** |

## 15. Convenções de nomenclatura

- `_AI` — anos iniciais.
- `_AF` — anos finais.
- `_MED` — ensino médio.
- `_FUN` — fundamental inteiro.
- `_LAG1` — ano anterior.
- `_DELTA1` — diferença anual.
- `_T1` — target do ano seguinte.

---

# Parte D — Qualidade e limites

## 16. Missing estrutural

Os nulos não são aleatórios. Refletem o que a escola oferece.

| Grupo | % nulos | Por quê |
|---|---|---|
| `*_MED*` | ~80–85% | Só escolas com EM. |
| `*_FUN_AF*` | ~71–76% | Só escolas com anos finais. |
| `*_FUN_AI*` | ~38–69% | Só escolas com anos iniciais. |
| `*_FUN` | ~24% | Só escolas com fundamental. |
| IDs, localização, `DISP_*` | 0% | Sempre presentes. |

**Consequência:** não dá para rodar um modelo único misturando tudo.
Confirma a decisão de separar em dois conjuntos.

## 17. Zeros no alvo

| Alvo | % zeros |
|---|---|
| `ABANDONO_FUN_T1` | 66,1% |
| `ABANDONO_FUN_AF_T1` | 44,1% |
| `ABANDONO_MED_T1` | 32,3% |

**Implicações:**

- Métricas lineares dominadas por "acertar o zero".
- R² pode ser enganoso.
- Talvez valha uma abordagem em duas etapas: (a) classificar se há
  abandono, (b) se sim, estimar quanto.

## 18. Distribuição temporal do alvo

| ANO_ALVO | AF | EM |
|---|---|---|
| 2020 | 0,99 | 1,60 |
| 2021 | 2,96 | 5,54 |
| 2022 | 4,94 | 11,41 |
| 2023 | 3,00 | 7,18 |
| 2024 | 2,63 | 5,42 |
| 2025 | 2,42 | 5,91 |

**Pico em 2022**

- Corresponde ao retorno pós-pandemia.
- Abandono do EM triplicou entre 2020 e 2022.
- Contamina qualquer split temporal. Treinar em 2020–2022 e testar
  em 2023–2025 vê distribuições muito diferentes.

## 19. Painel não balanceado

- 934 escolas em 7 anos.
- Nem toda escola aparece em todos os anos.
- 6 escolas mudam de localização.
- 105 mudam de nome.

## 20. Cobertura do IED

Só existe a partir de 2021. Em 2019 e 2020, `IED_FUN_*` e `IED_MED_*`
são nulos. Ver problema P019.

## 21. INSE

- Existe apenas em 2019, 2021 e 2023.
- Depende da participação no Saeb.
- ~Metade das escolas públicas (a confirmar para Roraima).
- Ausência concentra-se em escolas pequenas e rurais.
- **Decisão:** usar só para comparar grupos, não como feature.

## 22. Duplicatas e outliers

- Nenhuma duplicata completa.
- Nenhuma duplicata por (`CO_ENTIDADE`, `ANO`).
- Outliers presentes em `TDI_*`, `IED_FUN_N1`, `ABANDONO_*`.
- RMSE > MAE indica erros muito grandes em algumas escolas.

## 23. Defasagem do desfecho

- Abandono de t+1 só é conhecido bem depois do fim de t+1.
- Segunda etapa do Censo é coletada no ano seguinte.
- Em outubro/2026, último ano com alvo é 2025.

## 24. Resumo de limitações

| # | Limitação | Consequência |
|---|---|---|
| 1 | Missing estrutural | Separar por etapa. |
| 2 | Muitos zeros no alvo | Métricas dominadas por acertos triviais. |
| 3 | Pico de 2022 | Split temporal precisa tratar. |
| 4 | IED só a partir de 2021 | Perde 2019–2020. |
| 5 | INSE esparso e enviesado | Só para análise de grupos. |
| 6 | Outliers no alvo | RMSE > MAE. |
| 7 | Defasagem do desfecho | Um ano atrás do presente. |

---

# Parte E — Enriquecimento futuro

Variáveis discutidas e priorizadas para inclusão.

## 25. Escola indígena e localização diferenciada

- Do Censo Escolar: `IN_ESCOLA_INDIGENA`, terra indígena,
  assentamento.
- Hoje a base só distingue Urbana / Rural.
- **Por que incluir:** Roraima tem muitas escolas indígenas; sem isso
  não se avalia desempenho por grupo.
- **Como:** extrair, adicionar como colunas. Não necessariamente como
  features — usar para avaliar por grupo.

## 26. Flag de elegibilidade

- `elegivel_analise` (0/1): 1 se oferece AF ou EM; 0 se só educação
  infantil.
- Não excluir fisicamente da base — manter e filtrar só na hora de
  treinar.

## 27. Multisseriadas

- Flag `multisseriada`.
- Onde não houver média dos anos finais, usar a do fundamental como
  aproximação.
- Criar coluna indicadora de substituição.

## 28. Esforço docente 2019–2020 (IED)

- Só existe a partir de 2021 na base atual.
- 2019 e 2020 estão disponíveis no INEP.
- Pendente de confirmação da consistência metodológica.

## 29. Horas-aula diárias (HAD)

- Disponível em todos os anos.
- Pode representar diferenças de organização e jornada.
- Pendente de decisão com o orientador. Ver P019.

## 30. Pé-de-Meia

- Vigente desde 2024. Foca permanência no EM público.
- Afeta validação (2023→2024) e teste (2024→2025) do desenho.
- Se houver dados por escola: nº de beneficiários, % de alunos
  atendidos.
- Se não: variável indicando pré/pós-2024, análises separadas.
- **Cuidado com leakage:** não usar informação que dependa da
  frequência do aluno para prever abandono no mesmo período.

## 31. INSE

Só para comparação de grupos, não como feature.

## 32. Censo — infraestrutura e dependências

- Água, energia, esgoto, internet, acessibilidade.
- Biblioteca, quadra, laboratório.
- Computador, impressora, projetor.
- Nos microdados, mas não na base atual.
- **Cuidado:** muitas variáveis, risco de inflar o modelo.

## 33. Priorização

1. Escola indígena e localização diferenciada.
2. Flag de elegibilidade.
3. Flag de multisseriada.
4. Pé-de-Meia.
5. IED 2019–2020 e HAD.
6. INSE (só avaliação).
7. Infraestrutura do Censo (se houver tempo).

## 34. Princípio geral

Colocar as informações na base agora, documentar bem de onde cada
uma veio, e decidir depois, por meio dos experimentos, quais entram
no modelo final.