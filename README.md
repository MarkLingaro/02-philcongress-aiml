# 🏛️ PhilCongressAI

Philippine Congress Analytics & RAG Chatbot — bill survival rates,
voting networks, party coalitions, and an LLM chatbot over Philippine
legislation. All models run locally via Ollama. All services via Docker.

**Primary data source:** `api.congress.gov.ph` — the REST API behind the
Philippine House of Representatives LEGIS system (8th–19th Congress).

---

## Requirements

| Tool | Install |
|------|---------|
| Git ≥ 2.40 | https://git-scm.com |
| Docker Desktop ≥ 24 | https://docs.docker.com/get-docker/ |
| Python ≥ 3.11 | https://www.python.org/downloads/ |
| `uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

Hardware: 16 GB RAM minimum, 20 GB free disk, 4 CPU cores.

---

## Quickstart

```bash
git clone https://github.com/<you>/philcongressai.git
cd philcongressai
make setup
```

`make setup` does in order:
1. Checks Docker and `uv` are installed
2. Copies `.env.example` → `.env`
3. Installs Python dependencies into `.venv/`
4. Starts all Docker services
5. Applies PostgreSQL schema
6. Installs pre-commit hooks

Then load data:

```bash
make pull-models   # ~4 GB Ollama models — do once
make ingest        # fetch from api.congress.gov.ph + Wikidata
```

Start the app:

```bash
make api-dev        # http://localhost:8000/docs
make dashboard-dev  # http://localhost:8501
```

---

## Services

| Service | URL |
|---------|-----|
| API (Swagger) | http://localhost:8000/docs |
| Dashboard | http://localhost:8501 |
| Neo4j Browser | http://localhost:7474 |
| Qdrant | http://localhost:6333/dashboard |

```bash
make status   # row/vector counts across all databases
make ps       # Docker service health
make help     # full command list
```

---

## Branch Workflow

Work on feature branches — direct commits to `main` are blocked.

```bash
git checkout -b sprint-1/hrep-api-client
# ... do work, commit ...
git checkout main
git merge sprint-1/hrep-api-client
```

Branch naming: `sprint-{N}/{what-youre-building}`

---

## Data Sources

| Source | Provides | Role |
|--------|----------|------|
| [api.congress.gov.ph](https://api.congress.gov.ph/hrep/api-v1/) | Bills (8th–19th), legislators, PDF URLs | **Primary** |
| [Wikidata](https://www.wikidata.org) | Biographical data, party history | Enrichment |
| [BetterGov HuggingFace](https://huggingface.co/datasets/bettergov) | Bulk persons + memberships | Supplementary |
| [hrep.online](https://docs.congress.hrep.online) | Full bill text PDFs | Phase 2 only |

---

## Sprint Progress

- [x] Sprint 0 — Foundation & DevEnv
- [ ] Sprint 1 — Data Ingestion
- [ ] Sprint 2 — Core Analytics
- [ ] Sprint 3 — Network Analysis
- [ ] Sprint 4 — RAG Chatbot
- [ ] Sprint 5 — Dashboard
- [ ] Sprint 6 — Productionization

## License

MIT
