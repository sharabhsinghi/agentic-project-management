# 🤖 AI Agent Orchestrator

An iterative, human-in-the-loop AI agent pipeline that plans, implements, reviews, and tests features in any web project.
Powered by Claude (Anthropic).

## How it works

Before the first iteration, an **Init Agent** analyses your codebase and builds a base context.
Then, on each iteration, seven agents execute in sequence:

```
Your Feedback
     ↓
[Init Agent]          → Analyses codebase, builds base context (runs once)
     ↓
[Product Agent]       → Decides features & UX for this iteration
     ↓
[Schema Agent]        → Designs/updates the database schema
     ↓
[Backend Agent]       → Writes API routes & server actions
     ↓
[Frontend Agent]      → Builds React components & pages
     ↓
[Code Review Agent]   → Reviews backend & frontend code, agents revise (once)
     ↓
[QA Agent]            → Writes tests & flags security issues
     ↓
Files written to your repo
```

All decisions are stored in `context/project_context.json` so each iteration builds on the last.

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your API key

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Configure your project

Edit `project_config.yaml` to describe your project before running anything:

```yaml
project:
  name: "My App"
  description: "A web application that ..."
  stack: "Next.js 14, TypeScript, Supabase, Tailwind CSS"
  user_roles:
    - "user"
    - "admin"

domain:
  entities: ["user", "item", "order"]
  key_actions: ["create item", "place order", "track status"]
  constraints:
    - "Users can only modify their own data"

backend:
  db_client: "supabase"      # supabase | prisma | drizzle | raw-sql
  auth: "supabase-auth"      # supabase-auth | next-auth | clerk | custom
  api_style: "app-router"    # app-router | pages-router

frontend:
  ui_library: "Tailwind CSS"
  component_library: "shadcn/ui"   # or "none"
  data_fetching: "server-components"
```

### 4. Initialise (run once)

```bash
python orchestrator.py --repo /path/to/your/project --init
```

This scans your codebase, combines it with your config, and saves the base context.

### 5. Run your first iteration

```bash
python orchestrator.py --repo /path/to/your/project
```

---

## Running subsequent iterations

After reviewing the output and testing manually, give feedback:

```bash
python orchestrator.py \
  --repo /path/to/your/project \
  --feedback "The list page looks good but the form needs a date picker, and we're missing validation on the API."
```

Your feedback can be anything:
- Bug reports: `"The price calculation is off when a discount is applied"`
- New features: `"Add a messaging system between users"`
- UX changes: `"The search filters need additional options"`
- Refactors: `"The auth logic is duplicated across 3 routes, consolidate it"`

---

## What gets written to your repo

After each iteration, you'll find:

| Path | What it is |
|------|-----------|
| `migrations/001_iteration_1.sql` | SQL migration to run against your DB |
| `migrations/001_prisma_additions.prisma` | Prisma models to add to schema.prisma |
| `app/api/.../route.ts` | New API routes |
| `app/.../page.tsx` | New pages |
| `components/...` | New components |
| `__tests__/...` | Test files |
| `migrations/001_security_report.md` | Security issues (if any) |

**Always review before committing.** The agents are good but you are the final reviewer.

---

## Recommended workflow

```
Step 0 (once):
  1. Edit project_config.yaml
  2. python orchestrator.py --repo . --init

Each iteration:
  1. python orchestrator.py --repo . --feedback "..."
  2. Review the generated files in your editor
  3. Apply the SQL migration to your database
  4. Update prisma/schema.prisma (if using Prisma)
  5. Run your dev server and test manually
  6. Fix anything obvious yourself
  7. Repeat
```

---

## Flags

| Flag | Description |
|------|-------------|
| `--repo` | Path to your repo (required) |
| `--init` | Run the one-time initialisation pass |
| `--feedback` | Your feedback for this iteration |
| `--config` | Path to project config (default: `project_config.yaml`) |
| `--context-file` | Path to context JSON (default: `context/project_context.json`) |
| `--dry-run` | Preview the plan without writing any files |

---

## Context file

`context/project_context.json` is the system's memory. It stores:
- All features (planned, in-progress, done)
- Database schema decisions
- Every agent decision, per iteration
- Full iteration history

**Commit this file to your repo** so the context persists across machines.

---

## Project structure

```
agent-system/
├── orchestrator.py             ← Entry point — run this
├── project_config.yaml         ← Your project description (edit before --init)
├── requirements.txt
├── README.md
├── agents/
│   ├── orchestrator_agent.py   ← Coordinates the pipeline
│   ├── init_agent.py           ← One-time codebase analysis
│   ├── product_agent.py        ← Features & UX planning
│   ├── schema_agent.py         ← Database schema design
│   ├── backend_agent.py        ← API routes & server logic
│   ├── frontend_agent.py       ← React components & pages
│   ├── code_review_agent.py    ← Code review & one-shot revision
│   └── qa_agent.py             ← Tests & security review
├── tools/
│   └── repo_tools.py           ← Reads & writes your repo
└── context/
    ├── context_store.py        ← Persistent memory layer
    └── project_context.json    ← Auto-generated, commit this
```

