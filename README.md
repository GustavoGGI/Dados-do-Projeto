# Dados-do-Projeto

Risco de abandono escolar em Roraima (PIBIC/UERR + disciplina de mineração de dados).
Esta pasta é a raiz do repositório e reúne três frentes: o pipeline oficial do projeto
(`abandono-escolar/`), a extensão da série histórica e das features do Censo
(`gustavo/`) e a documentação de planejamento (`Relatórios do Projeto/`).

- Regras de trabalho do projeto: [`abandono-escolar/CLAUDE.md`](abandono-escolar/CLAUDE.md)
- Instalação e bootstrap do pipeline oficial: [`abandono-escolar/README.md`](abandono-escolar/README.md)
- Pipeline estendido (2007–2025): [`gustavo/README.md`](gustavo/README.md) e [`gustavo/COMO_RODAR.md`](gustavo/COMO_RODAR.md)

## Arquitetura de pastas

```
Projeto da Gabi/                       raiz do repositório
├── README.md                          este arquivo
├── Artigos/                           referências em PDF (ex.: Almeida & Mussato, 2023)
├── Relatórios do Projeto/             documentação de planejamento (00_LEIA_PRIMEIRO … 07_PLANOS)
│
├── abandono-escolar/                  pipeline oficial (repositório git próprio)
│   ├── CLAUDE.md                      fonte de verdade: contexto, dados e regras invioláveis
│   ├── README.md                      pré-requisitos, bootstrap e fontes
│   ├── requirements.txt · pytest.ini  dependências e configuração de testes
│   ├── src/                           módulos Python (python -m src.<módulo>)
│   │   ├── config.py                  caminhos e constantes
│   │   ├── aquisicao.py · fontes_inep.csv · certificados/   download do INEP e verificação TLS
│   │   ├── extrair_brutos_inep.py     extrai os .xlsx dos zips de indicadores
│   │   ├── integridade.py · manifesto.py                    sha256 e MANIFEST.csv
│   │   ├── indicadores_inep.py        detecção de cabeçalho e perfil das planilhas
│   │   ├── indicadores_rr.py          recorte de Roraima (um parquet por indicador e ano)
│   │   ├── base_longitudinal.py       regera a base escola-ano e compara com a v1.0
│   │   ├── analise_base_longitudinal.py · tabelas_metodologia.py   tabelas descritivas
│   │   ├── catalogo_microdados.py · relatorio_catalogo.py · leitura.py
│   │   ├── bootstrap.py               orquestra todas as etapas
│   │   └── migracao_estrutura.py      migração única para a estrutura de dados por estágio
│   ├── dados/                         fora do git, exceto MANIFEST.csv
│   │   ├── MANIFEST.csv               estágio, origem, arquivo e sha256 de cada arquivo
│   │   ├── origem/                    zips do INEP como vieram (somente leitura)
│   │   │   ├── censo/                 microdados do Censo Escolar
│   │   │   ├── indicadores/           indicadores educacionais (tx_rend, TDI, ATU, IED, HAD)
│   │   │   └── doc/                   PDFs de documentação
│   │   ├── bruto/                     extraído dos zips, nome original (somente leitura)
│   │   ├── interim/indicadores_rr/    recorte de RR em parquet ({tipo}_{ano}.parquet)
│   │   ├── processado/                base longitudinal regerada (.parquet + .csv)
│   │   └── cache_download/            downloads em andamento, páginas do INEP, certificado
│   ├── docs/                          tabelas geradas por código, metodologia e decisões
│   ├── tests/                         testes (sem rede, sem tocar em dados/) e fixtures
│   └── exploracao_colunas/            resumos exploratórios de colunas (censo, tx_rend)
│
├── gustavo/                           pipeline estendido: tx_rend 2007–2025 + features do Censo
│   ├── README.md                      visão geral, estado atual, validações e pendências
│   ├── COMO_RODAR.md                  ordem de execução, flags e dependências
│   ├── programas/                     scripts de produção, na ordem de execução
│   │   ├── 01_tx_rend_bruto.py                    zips do INEP → parquet bruto (RR, 3 gerações de layout)
│   │   ├── 02_tx_rend_selecionado_longitudinal.py bruto → 12 taxas harmonizadas → LAG1/DELTA1/T1
│   │   ├── 03_censo_features.py                   17 features de infraestrutura (Almeida & Mussato)
│   │   ├── 04_merge_features.py                   longitudinal + Censo → base_atual.parquet
│   │   ├── 99_pipeline.py                         roda 01 → 04 (--force, --from)
│   │   └── diagnostico/                           scripts pontuais, fora do pipeline
│   ├── testes/
│   │   └── 01_validar_base.py                     checagens automáticas da base final
│   ├── cache/                         cache por ano, apagável (regenera dos zips)
│   │   ├── tx_rend/{ano}.parquet
│   │   └── censo/{ano}.parquet
│   ├── docs/                          relatórios técnicos escritos à mão (01, 02, 03)
│   └── saida/
│       ├── README.md                  descrição de cada parquet
│       ├── base_atual.parquet         base consumida pelo modelo (cópia da etapa 04)
│       ├── etapas/                    01_bruto · 02a_selecionado · 02b_longitudinal ·
│       │                              03_censo_features · 04_base_com_censo
│       └── relatorios/                diagnósticos e validações geradas pelos scripts
│
└── old/                               material antigo, mantido só como histórico
    ├── v1.ipynb · v1_corrigido.ipynb  notebooks de análise anteriores
    ├── diagnosticos_plano.py · diagnosticos_saida/
    ├── testes/                        notebooks e scripts de teste descartados
    └── old/                           versão anterior de programas/, saida/ e testes/
```

## Fluxo dos dados

```
Pipeline oficial (abandono-escolar/)
  origem/ (zips) → bruto/ (planilhas) → interim/ (recorte RR) → processado/ (base 2019–2025)

Pipeline estendido (gustavo/)
  origem/indicadores (zips tx_rend 2007–2025) ──▶ 01 ─▶ 02 ─┐
                                                            ├─▶ 04 ─▶ saida/base_atual.parquet
  origem/censo + bruto/censo (zips 2007–2025) ───▶ 03 ──────┘
```

## Notas

- **`origem/`, `bruto/` e `externo/` são somente leitura** (regra 1 do CLAUDE.md). O `gustavo/`
  lê de `abandono-escolar/dados/` e escreve só dentro de `gustavo/`; não altera o pipeline oficial.
- **Como o `gustavo/` acha os dados:** os scripts sobem a árvore de pastas procurando
  `abandono-escolar/dados/`; podem ser rodados de qualquer pasta, mas o jeito canônico é
  `cd gustavo && python programas/99_pipeline.py`.
- **Dependências:** as do `abandono-escolar/requirements.txt`; os `.xls` de 2007–2011 também exigem `xlrd`.
- **Dois repositórios git:** a raiz (`GustavoGGI/Dados-do-Projeto`) e `abandono-escolar/`
  (`gabsma25/abandono-escolar`) têm `.git` próprio. Para o `gustavo/` rodar num clone novo, as duas
  pastas precisam estar lado a lado.
- **Dados não vão para o git:** `abandono-escolar/dados/` fica fora do versionamento (exceto
  `MANIFEST.csv`); os zips são obtidos pelo bootstrap ou colocados em `dados/origem/` manualmente.
- **Caminhos em transição:** scripts e documentos do `abandono-escolar/` que ainda citam o layout
  antigo (`src/abandono-escolar/…`) serão ajustados depois.
