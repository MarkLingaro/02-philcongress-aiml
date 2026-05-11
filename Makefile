.PHONY: help up down restart logs ps \
        migrate migrate-down migrate-history db-shell \
        neo4j-browser qdrant-ui \
        pull-models download-bills \
        ingest ingest-dry status \
        api-dev dashboard-dev \
        test test-unit lint format typecheck check clean \
        setup seed

COMPOSE = docker compose -f docker/docker-compose.yml
CONGRESS ?= 20

# ─────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  PhilCongressAI"
	@echo "  ══════════════════════════════════════"
	@echo ""
	@echo "  First time:"
	@echo "    make setup            Full one-command setup"
	@echo "    make seed             Load sample data"
	@echo ""
	@echo "  Infrastructure:"
	@echo "    make up               Start all Docker services"
	@echo "    make down             Stop all services"
	@echo "    make logs             Tail all logs"
	@echo "    make logs s=postgres  Tail one service"
	@echo "    make ps               Show service status"
	@echo ""
	@echo "  Database:"
	@echo "    make migrate          Apply Alembic migrations"
	@echo "    make migrate-down     Rollback one migration"
	@echo "    make db-shell         Open psql prompt"
	@echo "    make neo4j-browser    Open Neo4j UI in browser"
	@echo "    make qdrant-ui        Open Qdrant dashboard"
	@echo ""
	@echo "  Data:"
	@echo "    make pull-models      Download Ollama models (~4 GB)"
	@echo "    make ingest           Run full ingestion pipeline"
	@echo "    make download-bills   Download PDFs  (CONGRESS=20)"
	@echo "    make status           Row/vector counts across all DBs"
	@echo ""
	@echo "  Dev:"
	@echo "    make api-dev          FastAPI with hot-reload"
	@echo "    make dashboard-dev    Streamlit locally"
	@echo "    make test             Run all tests"
	@echo "    make lint             Ruff linter"
	@echo "    make format           Auto-format"
	@echo "    make check            lint + typecheck + test"
	@echo ""

# ── Setup ─────────────────────────────────────────────────────────
setup:
	@echo ""
	@echo "╔══════════════════════════════════════╗"
	@echo "║  PhilCongressAI — First-time Setup   ║"
	@echo "╚══════════════════════════════════════╝"
	@echo ""
	@echo "1/6  Checking prerequisites..."
	@command -v docker  >/dev/null 2>&1 || (echo "❌ docker not found" && exit 1)
	@command -v uv      >/dev/null 2>&1 || (echo "❌ uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh" && exit 1)
	@echo "     ✅ OK"
	@echo ""
	@echo "2/6  Creating .env..."
	@if [ ! -f .env ]; then cp .env.example .env; echo "     ✅ Created from .env.example"; \
	else echo "     ⏭️  Already exists"; fi
	@echo ""
	@echo "3/6  Installing Python dependencies..."
	uv sync --extra dev
	@echo "     ✅ .venv/ ready"
	@echo ""
	@echo "4/6  Starting Docker services..."
	$(COMPOSE) up -d
	@echo "     Waiting 20s for services to initialise..."
	@sleep 20
	@echo "     ✅ Services running"
	@echo ""
	@echo "5/6  Applying database migrations..."
	.venv/bin/alembic upgrade head
	@echo "     ✅ PostgreSQL schema applied"
	@echo ""
	@echo "6/6  Installing pre-commit hooks..."
	.venv/bin/pre-commit install
	@echo "     ✅ Hooks installed"
	@echo ""
	@echo "╔══════════════════════════════════════╗"
	@echo "║  ✅ Setup complete                    ║"
	@echo "╚══════════════════════════════════════╝"
	@echo ""
	@echo "  Next: make seed            (quick demo data)"
	@echo "  Or:   make pull-models     (then make ingest)"
	@echo ""

seed:
	@echo "Loading seed data..."
	.venv/bin/python scripts/load_seed.py
	@echo "✅ Done. Run: make api-dev  and  make dashboard-dev"

# ── Infrastructure ────────────────────────────────────────────────
up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart

logs:
	@if [ -n "$(s)" ]; then $(COMPOSE) logs -f $(s); \
	else $(COMPOSE) logs -f; fi

ps:
	$(COMPOSE) ps

# ── Database ──────────────────────────────────────────────────────
migrate:
	.venv/bin/alembic upgrade head

migrate-down:
	.venv/bin/alembic downgrade -1

migrate-history:
	.venv/bin/alembic history --verbose

db-shell:
	docker exec -it philcongress_postgres \
		psql -U $${POSTGRES_USER:-philcongress} \
		     -d $${POSTGRES_DB:-philcongressai}

neo4j-browser:
	@open http://localhost:7474 2>/dev/null \
		|| xdg-open http://localhost:7474 2>/dev/null \
		|| echo "Open http://localhost:7474"

qdrant-ui:
	@open http://localhost:6333/dashboard 2>/dev/null \
		|| xdg-open http://localhost:6333/dashboard 2>/dev/null \
		|| echo "Open http://localhost:6333/dashboard"

# ── Data ──────────────────────────────────────────────────────────
pull-models:
	@echo "Pulling mistral (~4.1 GB)..."
	curl -s -X POST http://localhost:11434/api/pull \
		-d '{"name":"mistral","stream":false}' | \
		.venv/bin/python -c "import json,sys; d=json.load(sys.stdin); print('  ✅ mistral:', d.get('status','done'))"
	@echo "Pulling nomic-embed-text (~274 MB)..."
	curl -s -X POST http://localhost:11434/api/pull \
		-d '{"name":"nomic-embed-text","stream":false}' | \
		.venv/bin/python -c "import json,sys; d=json.load(sys.stdin); print('  ✅ nomic-embed-text:', d.get('status','done'))"

download-bills:
	.venv/bin/python -m src.ingestion.bill_downloader download-from-db \
		--congress $(CONGRESS) \
		--output $${BILL_PDF_DIR:-data/raw/bills} \
		--concurrent $${BILL_DOWNLOAD_CONCURRENCY:-5}

ingest:
	.venv/bin/python -m src.ingestion.ingest --all

ingest-dry:
	.venv/bin/python -m src.ingestion.ingest --all --dry-run

status:
	@echo ""
	@echo "── PostgreSQL ───────────────────────────────────"
	@docker exec philcongress_postgres \
		psql -U $${POSTGRES_USER:-philcongress} \
		     -d $${POSTGRES_DB:-philcongressai} \
		-c "SELECT tablename AS table, \
		    (SELECT COUNT(*) FROM information_schema.tables t2 \
		     WHERE t2.table_name = t.tablename) \
		    FROM information_schema.tables t \
		    WHERE table_schema = 'public' ORDER BY tablename;" \
		2>/dev/null || echo "  Not reachable — run: make up"
	@echo ""
	@echo "── Qdrant ───────────────────────────────────────"
	@curl -s http://localhost:6333/collections | \
		.venv/bin/python -c \
		"import json,sys; d=json.load(sys.stdin); \
		cols=d.get('result',{}).get('collections',[]); \
		[print(f'  {c[\"name\"]}') for c in cols] if cols else print('  (no collections yet)')" \
		2>/dev/null || echo "  Not reachable"
	@echo ""
	@echo "── Neo4j ────────────────────────────────────────"
	@curl -s -u $${NEO4J_USER:-neo4j}:$${NEO4J_PASSWORD:-changeme} \
		http://localhost:7474/db/neo4j/tx/commit \
		-H "Content-Type: application/json" \
		-d '{"statements":[{"statement":"MATCH (n) RETURN labels(n)[0] AS l, count(*) AS c ORDER BY l"}]}' | \
		.venv/bin/python -c \
		"import json,sys; d=json.load(sys.stdin); \
		rows=d.get('results',[{}])[0].get('data',[]); \
		[print(f'  {r[\"row\"][0]}: {r[\"row\"][1]}') for r in rows] if rows else print('  (empty graph)')" \
		2>/dev/null || echo "  Not reachable"
	@echo ""

# ── Dev servers ───────────────────────────────────────────────────
api-dev:
	.venv/bin/uvicorn src.api.main:app \
		--reload --host 0.0.0.0 --port 8000

dashboard-dev:
	.venv/bin/streamlit run src/dashboard/Home.py \
		--server.port 8501

# ── Quality ───────────────────────────────────────────────────────
test:
	.venv/bin/pytest

test-unit:
	.venv/bin/pytest tests/unit -v

lint:
	.venv/bin/ruff check src tests

format:
	.venv/bin/ruff format src tests
	.venv/bin/ruff check --fix src tests

typecheck:
	.venv/bin/mypy src

check: lint typecheck test

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleaned"
