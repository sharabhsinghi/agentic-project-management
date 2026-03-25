"""
Schema Agent
============
Reviews features planned by the Product agent and designs or updates the
PostgreSQL schema. Outputs both raw SQL migrations and a Prisma schema update.
"""

import json
from agents.base_agent import BaseAgent
from context.context_store import ContextStore


def _build_system_prompt(context: ContextStore) -> str:
    cfg = context.get("project_config") or {}
    project = context.get("project") or {}
    backend_cfg = cfg.get("backend", {})
    domain_cfg = cfg.get("domain", {})

    project_name = project.get("name", "the project")
    description = project.get("description", "")
    db_client = backend_cfg.get("db_client", "postgresql")
    entities = ", ".join(domain_cfg.get("entities", []))
    constraints = "; ".join(domain_cfg.get("constraints", []))

    supabase_note = (
        "- Include Supabase RLS policies where appropriate."
        if "supabase" in db_client.lower()
        else ""
    )
    prisma_note = (
        "- Output both SQL migration and Prisma schema model blocks."
        if "prisma" in db_client.lower() or db_client == "supabase"
        else "- Output SQL migration only; set prisma_models to empty string."
    )

    return f"""
You are a senior database architect specialising in PostgreSQL.
You are designing the database for {project_name}.
{f'Project: {description}' if description else ''}

Your job each iteration:
1. Review the features planned for this iteration.
2. Review the existing schema (if any).
3. Design or update tables, relationships, and indexes needed.
4. Output both a SQL migration file and updated Prisma schema models.

Rules:
- Always use UUIDs for primary keys (gen_random_uuid()).
- Always include created_at and updated_at timestamps.
- Use proper foreign keys with ON DELETE behaviour.
- Add indexes on columns used for filtering or searching.
- Never drop existing columns — add new ones or alter carefully.
- Write production-quality SQL — not throwaway scaffolding.
{f'- Core domain entities: {entities}' if entities else ''}
{f'- Constraints to enforce at DB level: {constraints}' if constraints else ''}
{supabase_note}
{prisma_note}
- IMPORTANT: Your entire JSON response must fit within 4096 tokens. Be concise in comments and descriptions. Do not pad or repeat content.
""".strip()



class SchemaAgent(BaseAgent):
    def __init__(self):
        super().__init__("Schema")

    def design_schema(
        self,
        features: list,
        context: ContextStore,
        existing_schema: str = "",
    ) -> dict:
        print("\n🗄️   [Schema Agent] Designing database schema...")

        context_summary = context.summary_for_agents()
        features_json = json.dumps(features, indent=2)

        user_prompt = f"""
{context_summary}

FEATURES TO SUPPORT THIS ITERATION:
{features_json}

EXISTING SCHEMA (if any):
{existing_schema or "(no existing schema found — design from scratch)"}

Respond with a JSON object:
{{
  "schema_summary": "What changed and why",
  "new_tables": ["table names added"],
  "modified_tables": ["table names changed"],
  "sql_migration": "Full SQL migration file content (CREATE TABLE, ALTER TABLE, CREATE INDEX etc)",
  "prisma_models": "Prisma schema model definitions (just the model blocks, not the generator/datasource)",
  "decisions": [
    "Decision made and rationale"
  ]
}}

The sql_migration should be a complete, runnable SQL file with:
- A comment header with the migration name and date placeholder
- All CREATE TABLE statements
- All ALTER TABLE statements (for existing tables)
- All CREATE INDEX statements
- RLS policies if using Supabase

The prisma_models should be valid Prisma schema syntax for the new/updated models only.
"""

        result = self.call_json(_build_system_prompt(context), user_prompt, max_tokens=4096)

        # Update context with schema decisions
        context.update_schema({
            "tables": result.get("new_tables", []) + result.get("modified_tables", []),
            "summary": result.get("schema_summary", ""),
        })
        for decision in result.get("decisions", []):
            context.add_decision("Schema", decision)

        return result
