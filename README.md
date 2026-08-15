# ETIS Engineering Studio

A browser-based engineering judgment environment for COMP 330 that turns phase-gate evidence into interactive, multi-perspective engineering reviews.

The Studio is intentionally **not** a grading bot, passive dashboard, generic chatbot, or artifact generator. It is a structured practice environment in which students must make and defend engineering decisions against evidence, tradeoffs, uncertainty, business constraints, and professional accountability.

## Wave 1

Wave 1 is production-oriented around **Assignment 1 (Project Launch)** and **Assignment 2 (Planning & Estimation)**, while preserving extension contracts for A3-A6.

Implemented in this package:

- A1-A6 machine-readable phase contracts, with detailed A1/A2 review logic.
- Evidence-quality model and repository snapshot analyzer.
- Multi-lens reviewer architecture with deterministic challenge selection.
- Optional OpenAI Responses API follow-up generation behind a provider interface.
- A sophisticated student Engineering Review Room UI.
- Instructor Command Center UI.
- GitHub OAuth login flow plus explicit course/team access model.
- GitHub repository evidence provider with read-only access design.
- SQLite local development and PostgreSQL-compatible persistence.
- Docker Compose local environment.
- Azure Container Apps / PostgreSQL / Key Vault architecture specification and starter Bicep.
- GitHub Actions CI and Azure deployment workflow starter.
- Automated backend tests.
- Seed/demo mode so the product can be demonstrated before GitHub/App credentials are configured.

## Core design principle

> AI may challenge, critique, synthesize, and ask for evidence. Engineers decide, defend, and own the consequences.

## Quick start (demo mode)

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt
uvicorn apps.api.app.main:app --reload --port 8000
```

Open `http://localhost:8000`.

For a full split frontend/backend developer workflow, see `docs/LOCAL_DEVELOPMENT.md`.

## Repository structure

```text
apps/api/                 FastAPI application and agent orchestration
apps/web/                 React/Vite student + instructor UI
course-model/             Machine-readable COMP 330 phase contracts
infra/azure/              Azure deployment starter (Bicep + notes)
docs/                     Architecture, security, product, operations, source model
scripts/                  Development and validation helpers
tests/                    Backend contract and challenge-engine tests
```

## Status

This is a **professional Wave 1 foundation**, not a finished SaaS release. The core product model, server, demo experience, API contracts, repository/evidence abstraction, agent orchestration, access model, and deployment architecture are implemented. Production rollout still requires GitHub OAuth/App registration, Azure resource creation, secrets, DNS, and an OpenAI API key/model selection.
