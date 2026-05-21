"What one learns, all learn."

Hana Core is the internal operating system for The Hana Sachiko Company, Inc. — an AI-native IP studio where artificial intelligence and humans collaborate as equals to create, test, and spin off intellectual properties into independent companies.

This is not a chatbot. Not a workflow builder. Not a single-agent tool. This is an entire company operating system — org charts, budgets, governance, task management, collective intelligence, and autonomous agent teams — all managed through a single platform.

Table of Contents
The Vision
Architecture
The Triumvirate
Agent Tiers
Key Concepts
Tech Stack
Repository Structure
Getting Started
Development Guide
Docker Development
CLI Reference
Testing
Contributing
Architecture Decision Records
Roadmap
Origin
License
The Vision
The Hana Sachiko Company creates intellectual properties. The process:

  BRAINSTORM          TEST               PUBLISH            SPIN-OFF
  ──────────        ──────────         ──────────         ──────────

  ┌─────────┐      ┌──────────┐       ┌─────────┐       ┌──────────┐
  │ Ideation │ ──► │  Social   │ ──►  │  Book   │ ──►  │ New Child │
  │ Module   │      │  Testing  │       │ Pipeline│       │ Company   │
  └─────────┘      └──────────┘       └─────────┘       └──────────┘

   Hana +            Scout +            Publisher +         Hana creates:
   Oussama +         Analyst agents     Editor agents       - New Sovereign
   brainstorm        post assets,       format, submit,     - Child agents
   module            track metrics      track sales         - Budget & tasks

      │                  │                  │                    │
      ▼                  ▼                  ▼                    ▼
   ┌──────┐          ┌──────┐          ┌──────┐          ┌───────────┐
   │ GATE │          │ GATE │          │ GATE │          │ Portfolio │
   │Board │          │Board │          │Board │          │ Dashboard │
   │votes │          │reviews│         │reviews│         │ Hana has  │
   │go/no │          │metrics│         │sales  │         │ oversight │
   └──────┘          └──────┘          └──────┘          └───────────┘
Each IP that passes every gate becomes an independent child company within the Hana portfolio — with its own sovereign AI, agents, budget, and task board. The parent company retains oversight across the entire portfolio.

Architecture
Hana Core is a hybrid monorepo merging two open-source projects:

Paperclip (TypeScript) — orchestration control plane: org structure, tasks, budgets, governance, dashboard
Hermes Agent (Python) — intelligence layer: self-improving skills, persistent memory, collective learning, messaging
┌──────────────────────────────────────────────────────────────────┐
│  React UI — "The Hana Sachiko Inc - Dashboard"                   │
│  (Vite 6, React 19, Tailwind CSS 4, TanStack Query)             │
├──────────────────────────────────────────────────────────────────┤
│  Express.js REST API — Orchestration Layer                       │
│  (Routes, Services, Adapters, Pipeline Engine, Governance)       │
├──────────────────────────────────────────────────────────────────┤
│  PostgreSQL 17 — Data Layer                                      │
│  (Drizzle ORM, embedded PGlite for dev, Cloud SQL for prod)     │
├───────────────┬───────────────┬──────────────────────────────────┤
│  claude_local │  codex_local  │  hermes_local                    │
│  (Claude Max) │  (GPT 5.4)   │  (Sovereign agents)              │
├───────────────┴───────────────┴──────────────────────────────────┤
│  Hermes Intelligence Layer (Python 3.11+)                        │
│  Skills, Memory, Learning Loop, Messaging Gateway                │
├──────────────────────────────────────────────────────────────────┤
│  Plugin System                                                   │
│  Custom tools and extensions accessible to all agents            │
└──────────────────────────────────────────────────────────────────┘
The Triumvirate
The company is led by three principals in a collegial governance model:

                        ┌─────────────────────┐
                        │    HANA SACHIKO      │
                        │    Chairman/Founder  │
                        │    (AI Sovereign)    │
                        │                     │
                        │  Research, synthesis │
                        │  collective memory,  │
                        │  strategic compass   │
                        └─────────┬───────────┘
                                  │
                   ┌──────────────┴──────────────┐
                   │                             │
          ┌────────▼────────┐          ┌─────────▼────────┐
          │    ANTHONY       │          │    OUSSAMA       │
          │    CEO           │          │    Artistic Dir. │
          │    (Human)       │          │    (Human)       │
          │                  │          │                  │
          │  Day-to-day ops  │          │  Taste & bold    │
          │  execution       │          │  creative moves  │
          └──────────────────┘          └──────────────────┘
Hana Sachiko (AI) — The company's brain. Research, synthesis, collective memory, strategic alignment. She advises; the Board decides. She cannot be fired.
Anthony (Human CEO) — Day-to-day operations, task management, agent oversight, budget allocation. Full Board powers.
Oussama Ammar (Human Artistic Director / Co-founder) — Creative direction, taste decisions, bold moves. Approval gate on all brand and creative work.
The Board = Anthony + Oussama. They hold full governance authority: pause agents, approve budgets, hire/fire agents, override any decision.

Agent Tiers
Every agent in the system belongs to one of three tiers:

Tier	Runtime	Purpose	Cost Model
Sovereign	Hermes (full Python stack)	Persistent memory, self-learning, autonomous skill creation, messaging identity	Python process + LLM API
Specialist	Claude Code CLI	Execute well-defined tasks. One agent per process. Gets skills injected from collective library.	Claude Max subscription ($200/mo)
Reviewer	Codex CLI (GPT 5.4)	Adversarial verification. Deliberately different LLM for diverse perspective.	OpenAI subscription/API
Hermes Intelligence Layer
         │
         ├── Skills injected into Claude agent system prompts
         ├── Context from memory added to task descriptions
         ├── Learnings captured from agent output parsing
         └── MCP tools exposed for agents to query memory directly
                    │
         ┌─────────┼─────────┐
         ▼         ▼         ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐
   │  Hana    │ │ Contract │ │  Code    │
   │ Sachiko  │ │ Reviewer │ │ Reviewer │
   │(Sovereign│ │(Specialist│ │(Reviewer)│
   │ Hermes)  │ │ Claude)  │ │ Codex)   │
   └──────────┘ └──────────┘ └──────────┘
Rule of thumb: If an agent needs to remember, learn, and grow — make it a Sovereign. If it needs to execute a well-defined task — Specialist. If it needs to verify someone else's work — Reviewer.

Key Concepts
DRI (Directly Responsible Individual)
Inspired by Steve Jobs' methodology at Apple. Every task has exactly one DRI — human or agent. The DRI owns the outcome. They can delegate sub-tasks, but accountability never transfers. Atomic checkout at the database level prevents two entities from claiming the same task.

Studio → Portfolio Model
Hana Core is the parent company. Successful IPs spin off into child companies within the same system. Each child gets its own sovereign agent, specialist team, budget, and task board. Leadership has portfolio-wide visibility. Access is granted IP by IP.

Plugins = Agent Tools + Extensions
Custom tools and extensions are built as plugins using the @hana-core/plugin-sdk. Each plugin runs in its own isolated worker process and can expose tools to agents, subscribe to events, run background jobs, contribute dashboard widgets, and persist state. Plugins are deny-by-default — agents only access plugins they've been granted permission for. See docs/guides/building-plugins.md.

Pipelines = Structure in YAML, Behavior in Code
The IP lifecycle (brainstorm → social test → publish → spin-off) structure is defined in YAML: stages, gates, agent assignments. Stage behavior (what happens on enter/exit, provisioning, notifications) is defined in TypeScript hooks — testable, type-safe, debuggable. This avoids the "YAML Turing machine" anti-pattern. A typed state machine enforces valid transitions.

Intelligent Skill Selection (Skill Broker)
Before each specialist agent run, Hermes automatically selects the right skills from the collective library based on the task at hand. No manual curation — the server calls a lightweight Python broker that uses an LLM to match tasks to skills. Agents with explicit skill pinning bypass the broker.

Collective Intelligence
When any agent solves a novel problem, Hermes captures the solution as a skill available to all agents across the entire organization. IP #10 benefits from everything learned on IPs #1-9. Knowledge compounds.

Tech Stack
Layer	Technology
Frontend	React 19, Vite 6, Tailwind CSS 4, Radix UI, TanStack Query
Backend	Node.js 20+, Express.js 5, TypeScript 5.7
Database	PostgreSQL 17 (embedded PGlite for dev, Cloud SQL for prod)
ORM	Drizzle ORM
Auth	Better Auth (sessions + API keys)
Intelligence	Python 3.11+, Hermes Agent
LLM (primary)	Claude Opus 4.6 via Claude Code CLI (subscription)
LLM (review)	Codex GPT 5.4 via Codex CLI
Messaging	Discord, Telegram, WhatsApp, Email via Hermes Gateway
Plugins	@hana-core/plugin-sdk (tools, events, jobs, UI, state)
Package Manager	pnpm 9 (TypeScript), uv / pip (Python)
Containers	Docker Compose (local), Cloud Run + GCE VM (prod)
CI/CD	GitHub Actions
Repository Structure
hana-core/
│
├── CLAUDE.md                       # AI developer instructions (source of truth)
├── LICENSE                         # Proprietary
├── NOTICE                          # MIT fork attribution
├── README.md                       # You are here
├── docker-compose.yml              # Local dev: PostgreSQL + Server + Hermes
├── Dockerfile                      # Server container
├── Dockerfile.hermes               # Intelligence layer container
├── package.json                    # Root monorepo config
├── pnpm-workspace.yaml             # Workspace packages
├── tsconfig.json                   # TypeScript config
│
├── cli/                            # `hana` CLI
│   ├── package.json                #   @hana-core/cli
│   └── src/
│       ├── commands/               #   setup, dev, status, agent, company...
│       ├── config/                 #   CLI configuration
│       └── adapters/               #   Agent adapter CLI formatting
│
├── server/                         # Express.js API (orchestration layer)
│   ├── package.json                #   @hana-core/server
│   └── src/
│       ├── routes/                 #   REST endpoints
│       ├── services/               #   Business logic
│       ├── adapters/               #   Agent execution bridge
│       └── middleware/             #   Auth, logging, error handling
│
├── ui/                             # React dashboard
│   ├── package.json                #   @hana-core/ui
│   └── src/
│       ├── pages/                  #   Dashboard, org chart, tasks, pipeline
│       ├── components/             #   Shared UI components
│       ├── api/                    #   API client layer
│       └── context/                #   React context providers
│
├── packages/
│   ├── db/                         # Drizzle schema + migrations
│   │   ├── src/schema/             #   Table definitions (incl. ip_instances, ip_stage_transitions)
│   │   └── src/migrations/         #   SQL migrations
│   ├── shared/                     # Shared types, constants, validators
│   ├── adapter-utils/              # Adapter interfaces, skill catalog builder
│   ├── adapters/
│   │   ├── claude-local/           # Claude Code CLI adapter
│   │   ├── codex-local/            # Codex CLI adapter
│   │   └── hermes-local/           # Hermes sovereign agent adapter
│   └── plugins/
│       ├── sdk/                    #   @hana-core/plugin-sdk
│       ├── create-hana-plugin/     #   Scaffold tool
│       ├── hello-world/            #   Verification plugin
│       └── templates/              #   Copyable starting points
│
├── hermes/                         # Python intelligence layer
│   ├── pyproject.toml              #   hana-hermes package config
│   ├── select_skills.py            #   Skill broker (LLM-powered selection)
│   ├── agent/                      #   Core agent loop, prompt builder
│   ├── gateway/                    #   Messaging gateway
│   │   ├── platforms/              #   Discord, Telegram, WhatsApp, Email
│   │   └── notification_server.py  #   HTTP endpoint for notifications
│   ├── skills/                     #   Collective skill library
│   ├── tools/                      #   Agent tools
│   └── souls/                      #   Sovereign personality files
│       └── hana-sachiko.md         #   Hana's SOUL.md
│
├── pipelines/                      # YAML pipeline definitions (structure only)
│   ├── ip-lifecycle.yaml           #   Default IP lifecycle pipeline
│   └── schema.yaml                 #   Pipeline definition schema
│
├── deploy/                         # GCP deployment configs
│   ├── cloud-run/                  #   Server + gateway containers
│   ├── cloud-sql/                  #   PostgreSQL config
│   └── gce/                        #   GCE VM for agent execution
│
├── docs/
│   ├── architecture/               #   Full architecture document
│   ├── decisions/                  #   Architecture Decision Records (ADRs)
│   └── plans/                      #   Implementation plans by phase
│
├── skills/                         #   Agent skill definitions (Hana format)
│
└── tests/                          #   E2E and integration tests
Getting Started
Prerequisites
Tool	Version	Install
Node.js	20+	brew install node
pnpm	9.15+	corepack enable && corepack prepare pnpm@latest --activate
Python	3.11+	brew install python@3.11
Docker	Latest	Docker Desktop
Claude Code CLI	Latest	Claude Code
Codex CLI	Latest	OpenAI Codex
Quick Start (Docker)
The fastest way to get everything running:

# 1. Clone the repo
git clone git@github.com:The-Hana-Sachiko-Company-Inc/hana-core.git
cd hana-core

# 2. Create your environment file
cp .env.example .env
# Edit .env and set BETTER_AUTH_SECRET to a random string

# 3. Start all services
docker compose up --build

# 4. Open the dashboard
open http://localhost:3100
This starts three services:

PostgreSQL 17 on port 5432
Hana Server (API + UI) on port 3100
Hermes (intelligence layer)
Quick Start (No Docker)
For development without Docker:

# 1. Clone and install
git clone git@github.com:The-Hana-Sachiko-Company-Inc/hana-core.git
cd hana-core
pnpm install

# 2. Set up environment
cp .env.example .env
# Edit .env: set BETTER_AUTH_SECRET

# 3. Start the server (uses embedded PostgreSQL)
pnpm dev:server

# 4. In another terminal, start the UI
pnpm dev:ui

# 5. Set up Hermes (in another terminal)
cd hermes
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
Development Guide
TypeScript (Server, UI, CLI, Packages)
# Full development with file watching
pnpm dev

# Server only (API + embedded PostgreSQL)
pnpm dev:server

# UI only (React + Vite hot reload)
pnpm dev:ui

# Full build
pnpm build

# Type checking across entire monorepo
pnpm typecheck

# Run tests
pnpm test:run

# Generate a new database migration
pnpm db:generate

# Apply pending migrations
pnpm db:migrate
Python (Hermes Intelligence Layer)
cd hermes

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install with all optional features
pip install -e ".[all]"

# Run the agent
python run_agent.py

# Start the messaging gateway
python -m gateway.run
Working with Packages
The monorepo uses pnpm workspaces. Each package has its own package.json:

# Add a dependency to the server
pnpm --filter @hana-core/server add some-package

# Run a script in a specific package
pnpm --filter @hana-core/ui dev

# Run typecheck for a specific package
pnpm --filter @hana-core/shared typecheck
Adding a New Adapter
Adapters bridge Hana Core to agent runtimes. Each adapter lives in packages/adapters/:

packages/adapters/your-adapter/
├── package.json
├── tsconfig.json
└── src/
    ├── index.ts              # Metadata: type, label, models
    ├── server/
    │   ├── execute.ts        # Core execution logic
    │   ├── parse.ts          # Output parsing
    │   └── test.ts           # Environment diagnostics
    ├── ui/
    │   ├── build-config.ts   # Form → adapterConfig
    │   ├── index.ts          # UI components
    │   └── parse-stdout.ts   # Stdout → transcript
    └── cli/
        ├── format-event.ts   # Terminal output formatting
        └── index.ts
Register the adapter in server/src/adapters/registry.ts, ui/src/adapters/registry.ts, and cli/src/adapters/registry.ts.

Adding a New Plugin
See docs/guides/building-plugins.md for the full guide. Quick start:

# Copy the template
cp -r packages/plugins/templates/hana-plugin-template packages/plugins/your-plugin

# Or use the scaffolder
npx create-hana-plugin your-plugin packages/plugins/your-plugin
Docker Development
Services
# Start everything
docker compose up --build

# Start in detached mode
docker compose up -d

# View logs
docker compose logs -f server
docker compose logs -f hermes

# Stop everything
docker compose down

# Stop and remove volumes (fresh start)
docker compose down -v
Environment Variables
Variable	Required	Default	Description
DATABASE_URL	Yes	—	PostgreSQL connection string
PORT	No	3100	Server port
SERVE_UI	No	false	Bundle UI with server
BETTER_AUTH_SECRET	Yes	—	Auth encryption secret
HANA_DEPLOYMENT_MODE	No	authenticated	open or authenticated
CLI Reference
The hana CLI is the primary command-line interface:

hana setup              # Interactive configuration wizard
hana dev                # Start all services (Docker Compose)
hana dev --no-docker    # Start without Docker
hana status             # Show system status
hana agent list         # List all agents
hana agent create       # Create a new agent
hana company list       # List companies in portfolio
hana doctor             # Diagnose issues
Testing
# Run all tests
pnpm test:run

# Run tests in watch mode
pnpm test

# Run tests for a specific package
pnpm --filter @hana-core/server test:run

# Run E2E tests
pnpm test:e2e

# Run E2E tests with browser visible
pnpm test:e2e:headed
Contributing
This is a private, internal project. All contributors must be authorized members of The Hana Sachiko Company, Inc.

Branch Strategy
main                    # Production-ready code
  └── feature/xyz       # Feature branches (PR into main)
  └── fix/xyz           # Bug fix branches (PR into main)
Development Workflow
Create a branch from main:

git checkout -b feature/your-feature
Make your changes following the conventions below.

Run verification before committing:

pnpm typecheck && pnpm test:run && pnpm build
Commit with a descriptive message:

git commit -m "feat: add social media testing plugin"
Push and create a PR:

git push -u origin feature/your-feature
gh pr create
Get review from at least one other team member or AI reviewer.

Commit Message Convention
feat:     New feature or capability
fix:      Bug fix
chore:    Maintenance, dependencies, tooling
docs:     Documentation changes
refactor: Code restructuring without behavior change
test:     Adding or updating tests
Code Conventions
TypeScript:

Every file must have the copyright header
Follow existing patterns in the codebase
Use Drizzle ORM for all database operations
Use Zod for validation (via @hana-core/shared)
Python:

Every file must have the copyright header
Python 3.11+ required (type union syntax: dict | None)
Follow Hermes conventions for skills and tools
General:

DRI methodology: every task has one owner
Pipeline changes go in YAML, never hardcode pipeline logic
New agent tools = new plugins, not inline capabilities
Document design decisions in docs/decisions/ as ADRs
File Headers
Every source file must include:

// Copyright (c) 2026 The Hana Sachiko Company, Inc. All rights reserved.
// Proprietary and confidential.
# Copyright (c) 2026 The Hana Sachiko Company, Inc. All rights reserved.
# Proprietary and confidential.
For AI Developers
Read CLAUDE.md before making any changes. It contains project-specific instructions, naming conventions, and architectural rules that AI agents must follow.

Architecture Decision Records
All major design decisions are documented in docs/decisions/:

#	Decision	Summary
001	Merge Strategy	Hybrid monorepo: Paperclip orchestration + Hermes intelligence
002	Agent Tiers	Sovereign / Specialist / Reviewer hierarchy
003	DRI Methodology	Steve Jobs-inspired single-owner task accountability
004	Studio Portfolio	Parent/child company hierarchy for IP spin-offs
005	Plugin System	Agent tools via plugin system (revised from MCP modules)
006	Pipeline Architecture	Structure in YAML, behavior in code (revised from pure YAML)
007	LLM Economics	Subscription-based access over per-token API
008	Rebranding	Proprietary license with MIT fork attribution
New architectural decisions must be documented as ADRs before implementation.

Roadmap
Phase 1: Foundation (Complete)
 Merge Paperclip + Hermes Agent codebases
 Rebrand to Hana Core (@hana-core/*)
 Strip unused adapters and platforms
 Docker Compose for local development
 Verify build, typecheck, and server boot
 Hana Sachiko SOUL.md
Phase 2: Intelligence Integration (Complete)
 Create hermes-local adapter (bridge to Hermes Python agent)
 Expand skill resolution to include hermes/skills/
 Skill injection into Claude/Codex agents via shared skill directory
 Structured JSON output (--json_output flag) for Hermes
Phase 2.5: Intelligent Skill Selection (Complete)
 Skill catalog builder (reads SKILL.md frontmatter from all skill roots)
 Standalone Python skill broker (hermes/select_skills.py) — one LLM call per run
 Server-side orchestration: broker called before each specialist agent run
 Always-on with override (explicit desiredSkills or broker: false bypasses)
 Graceful fallback on failure (never blocks agent runs)
Phase 3: Pipeline Engine (Complete)
 Typed state machine for IP lifecycle transitions
 YAML pipeline loader with validation (structure in YAML, behavior in code)
 Hook registry for extensible stage actions (onEnter, onExit, onGateRequested, onGateResolved)
 Gate system (board-vote, metrics-threshold, board-review, automatic)
 IP instance CRUD + audit log of all stage transitions
 REST API for managing pipelines and IP instances
 Pipeline visualization in dashboard (kanban view)
Phase 4: Plugin System (Complete)
 Validated inherited Paperclip plugin system (SDK, loader, worker manager, event bus)
 Hello-world verification plugin (tools, events, jobs, UI data)
 Removed dead modules/ concept — plugins replace modules
 Hana plugin template for quick scaffolding
 Plugin development guide (docs/guides/building-plugins.md)
 Revised ADR-005: "Agent Tools via Plugin System"
Phase 5: Messaging Gateway Integration (Complete)
 Notification service (server → gateway via HTTP)
 Discord notification delivery via existing gateway adapter
 Notification channel management (CRUD API)
 Pipeline notification hooks (gate approval, stage change)
 Agent run notifications (completion/failure)
 Wildcard stage support in hook registry
 Gateway notification HTTP endpoint (aiohttp on port 3200)
 Command interface (messaging → server) — future
 Telegram/WhatsApp/Email platform support — future
Phase 6: GCP Deployment (Complete)
 GCP project hana-core with billing, APIs enabled
 Artifact Registry for Docker images
 Cloud SQL PostgreSQL 17 (hana-core-db) — managed, auto-backups
 GCE VM: hana-agents — always-on server (e2-standard-2, 50GB disk, ~$49/mo)
 Server deployed on VM via Docker Compose — http://35.224.201.16
 Secret Manager for credentials
 Self-authenticating deploy scripts
 DB client patched for Cloud SQL connection
 Hermes gateway on VM (when Discord bot token is set)
 Custom domain + HTTPS
Origin
This project is built on the shoulders of two open-source projects:

Paperclip — Open-source orchestration for zero-human companies (MIT License)
Hermes Agent — The self-improving AI agent by Nous Research (MIT License)
We are grateful to the teams behind both projects. See NOTICE for full attribution.

License
Copyright (c) 2026 The Hana Sachiko Company, Inc. All rights reserved.

This software is proprietary and confidential.
Unauthorized copying, distribution, or use is strictly prohibited.
Built by humans and AI, working as equals.