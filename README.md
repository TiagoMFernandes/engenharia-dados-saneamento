# 💧 Engenharia de Dados — Saneamento Básico Brasil

Pipeline de engenharia de dados para ingestão, tratamento e análise de indicadores públicos de saneamento básico no Brasil, com foco em abastecimento de água por município.

Utiliza dados oficiais do **SINISA/SNIS** (Sistema Nacional de Informações sobre Saneamento) e do **IBGE** (dados territoriais) para construir uma base analítica pronta para consumo em dashboards e consultas SQL.

---

## O que este projeto faz

O projeto resolve um problema real: os dados públicos de saneamento do governo são disponibilizados em planilhas Excel com formatação irregular e cabeçalhos inconsistentes. Este pipeline automatiza o processo de:

1. **Ingerir** os dados brutos do IBGE (via API) e do SINISA (via arquivo Excel)
2. **Limpar e padronizar** os dados, removendo inconsistências, nulos e valores fora do padrão
3. **Integrar** as duas fontes usando o código oficial IBGE do município
4. **Validar** a qualidade dos dados em cada etapa
5. **Disponibilizar** os dados em um dashboard interativo

---

## Arquitetura — Medallion

O pipeline segue a **Medallion Architecture**, um padrão amplamente adotado em projetos de engenharia de dados:

```
Fontes Públicas → Raw → Bronze → Silver → Gold → Dashboard
```

| Camada   | O que contém                                                              |
|----------|---------------------------------------------------------------------------|
| Raw      | Arquivos originais baixados das fontes, sem nenhuma modificação           |
| Bronze   | Dados convertidos para Parquet, com metadados de ingestão adicionados     |
| Silver   | Dados limpos, padronizados, tipos corrigidos e nulos tratados             |
| Gold     | Base analítica final: SINISA + IBGE integrados, prontos para consumo      |

O formato **Parquet** foi escolhido por ser colunar (ideal para análises), comprimido e muito mais rápido que CSV para leitura.

---

## Estrutura do projeto

```
engenharia-dados-saneamento/
│
├── src/
│   ├── ingestion/
│   │   ├── ibge_localidades.py    # Consome API do IBGE (regiões, estados, municípios)
│   │   ├── sinisa.py              # Lê planilhas do SINISA com detecção automática de cabeçalho
│   │   └── sinisa_download.py     # Tenta download automático; exibe instruções se falhar
│   │
│   ├── transformations/
│   │   ├── bronze_to_silver.py    # Orquestra todas as transformações
│   │   ├── ibge_localidades.py    # Limpeza e padronização dos dados IBGE
│   │   ├── sinisa.py              # Limpeza e padronização dos dados SINISA
│   │   └── build_gold.py          # Integra IBGE + SINISA e gera camada Gold
│   │
│   ├── quality/
│   │   └── validators.py          # Validação de qualidade em cada camada (Bronze/Silver/Gold)
│   │
│   ├── query/
│   │   └── duck.py                # Consultas SQL via DuckDB diretamente nos arquivos Parquet
│   │
│   └── utils/
│       ├── cleaning.py            # Funções de limpeza: nulos, UFs, códigos IBGE
│       ├── columns.py             # Padronização de nomes de colunas
│       ├── io.py                  # Leitura e escrita de arquivos Parquet
│       ├── paths.py               # Caminhos centralizados do projeto
│       └── sinisa_labels.py       # Dicionário de rótulos dos indicadores SINISA
│
├── dashboard/
│   └── app.py                     # Dashboard interativo em Streamlit
│
├── data/
│   ├── raw/sinisa/                # Planilha SINISA (não versionada — baixar manualmente)
│   ├── bronze/                    # Gerado pelo pipeline
│   ├── silver/                    # Gerado pelo pipeline
│   └── gold/                      # Gerado pelo pipeline
│
├── tests/
│   ├── test_ingestion.py          # Testes de ingestão e padronização
│   ├── test_quality.py            # Testes do módulo de qualidade de dados
│   └── test_transformations.py    # Testes das transformações e limpeza
│
├── .github/workflows/ci.yml       # CI automático: testes + linting a cada push
├── Dockerfile                     # Containerização do projeto
├── docker-compose.yml             # Orquestra dashboard e pipeline via Docker
├── requirements.txt               # Dependências de produção (versões fixadas)
├── requirements-dev.txt           # Dependências de desenvolvimento (testes, linting)
└── pytest.ini                     # Configuração dos testes
```

---

## Fontes de dados

### IBGE — API Localidades

Disponível gratuitamente, sem autenticação, em tempo real. O pipeline consome três endpoints:

- `GET /regioes` — 5 macrorregiões brasileiras
- `GET /estados` — 27 estados + DF
- `GET /municipios` — 5.570 municípios com dados geográficos completos

Documentação: https://servicodados.ibge.gov.br/docs/localidades

### SINISA — Sistema Nacional de Informações sobre Saneamento

Planilhas Excel com indicadores de saneamento básico por município. O pipeline detecta automaticamente a linha de cabeçalho real (as planilhas do SINISA possuem linhas institucionais no topo antes da tabela de dados).

Download manual: https://www.gov.br/mdr/pt-br/assuntos/saneamento/sinisa

A integração entre SINISA e IBGE é feita pelo **código do município** (`cod_IBGE`), que é a chave oficial utilizada em todos os sistemas públicos brasileiros.

---

## Como executar

### Opção 1 — Localmente (Python)

**1. Clonar o repositório**
```bash
git clone https://github.com/TiagoMFernandes/engenharia-dados-saneamento.git
cd engenharia-dados-saneamento
```

**2. Criar e ativar ambiente virtual**
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

**3. Instalar dependências**
```bash
pip install -r requirements.txt
```

**4. Baixar a planilha do SINISA**

Tente o download automático:
```bash
python -m src.ingestion.sinisa_download
```

Se não funcionar, baixe manualmente em https://www.gov.br/mdr/pt-br/assuntos/saneamento/sinisa e salve o arquivo `.xlsx` em `data/raw/sinisa/`.

**5. Executar o pipeline**
```bash
# Passo 1: Ingestão do IBGE (automático via API)
python -m src.ingestion.ibge_localidades

# Passo 2: Ingestão do SINISA
python -m src.ingestion.sinisa

# Passo 3: Transformação Bronze → Silver
python -m src.transformations.bronze_to_silver

# Passo 4: Construção da camada Gold
python -m src.transformations.build_gold
```

**6. Abrir o dashboard**
```bash
streamlit run dashboard/app.py
```

Acesse: http://localhost:8501

---

### Opção 2 — Docker

Com Docker instalado, suba tudo com um comando:

```bash
# Executa o pipeline completo
docker-compose run pipeline

# Sobe o dashboard
docker-compose up dashboard
```

O dashboard estará disponível em http://localhost:8501.

---

## Consultas SQL com DuckDB

Após gerar a camada Gold, você pode fazer consultas SQL diretamente nos arquivos Parquet, sem banco de dados:

```python
from src.query.duck import query_gold, top_municipios_agua, resumo_por_uf

# Consulta livre
df = query_gold("SELECT uf, AVG(iag0001) as media FROM gold GROUP BY uf ORDER BY media DESC")

# Funções prontas
top10_sp = top_municipios_agua(uf="SP", limit=10)
resumo = resumo_por_uf(indicador="iag0001")
criticos = municipios_sem_atendimento(threshold=50.0)
```

---

## Indicadores disponíveis (SINISA)

Os principais indicadores de abastecimento de água disponíveis na camada Gold:

| Código   | Descrição                                                            |
|----------|----------------------------------------------------------------------|
| IAG0001  | Atendimento da população total com rede de abastecimento de água     |
| IAG0002  | Atendimento da população urbana com rede de abastecimento de água    |
| IAG0003  | Atendimento da população rural com rede de abastecimento de água     |
| IAG0004  | Atendimento dos domicílios totais com rede de abastecimento de água  |
| IAG0005  | Atendimento dos domicílios urbanos com rede de abastecimento de água |
| IAG0006  | Atendimento dos domicílios rurais com rede de abastecimento de água  |
| IAG2012  | Perdas de faturamento de água                                        |
| IAG2013  | Perdas totais de água na distribuição                                |

O dicionário completo está em `src/utils/sinisa_labels.py`.

---

## Testes

```bash
# Instalar dependências de desenvolvimento
pip install -r requirements-dev.txt

# Executar todos os testes
pytest tests/

# Com relatório de cobertura
pytest tests/ --cov=src --cov-report=term-missing
```

Os testes cobrem: ingestão, limpeza, transformações, validação de qualidade e conversões numéricas.

---

## Melhorias implementadas

Este projeto incorpora práticas de engenharia de dados de produção:

- **Error handling robusto**: falhas em arquivos individuais são registradas em log e o pipeline continua processando os demais arquivos
- **Módulo de qualidade de dados**: validações automáticas de nulos, duplicatas, UFs inválidas, códigos IBGE e intervalos de indicadores percentuais
- **DuckDB**: consultas SQL diretamente em Parquet, sem necessidade de banco de dados
- **Docker**: containerização completa com `Dockerfile` e `docker-compose`
- **Dependências fixadas**: `requirements.txt` com versões exatas para reprodutibilidade total
- **CI/CD**: pipeline de integração contínua via GitHub Actions (testes + linting a cada push)
- **`save_parquet` corrigido**: agora retorna o caminho do arquivo salvo, permitindo encadeamento
- **Testes abrangentes**: 30+ casos de teste cobrindo as partes mais críticas do pipeline

---

## Tecnologias

- **Python 3.11**
- **Pandas** — manipulação de dados
- **PyArrow** — leitura/escrita de Parquet
- **DuckDB** — consultas SQL em Parquet
- **Streamlit** — dashboard interativo
- **Plotly** — visualizações no dashboard
- **Requests** — consumo da API do IBGE
- **OpenPyXL** — leitura de planilhas Excel
- **Pytest** — testes automatizados
- **Docker** — containerização
- **GitHub Actions** — integração contínua

---

## Próximas evoluções

- [ ] Adicionar dados da ANEEL (energia elétrica)
- [ ] Adicionar dados do PNCP (licitações públicas)
- [ ] Testes de qualidade de dados mais avançados com Great Expectations
- [ ] Orquestração com Apache Airflow ou Prefect
- [ ] Modelagem analítica com dbt
- [ ] Deploy do dashboard no Streamlit Cloud
- [ ] Diagrama de arquitetura interativo

---

## Autor

**Tiago Fernandes**
GitHub: [@TiagoMFernandes](https://github.com/TiagoMFernandes)

Projeto desenvolvido para portfólio em Engenharia de Dados, com foco em dados públicos brasileiros de saneamento básico.
