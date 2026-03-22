"""
Backend Agent
=============
Implements API routes, server actions, and business logic
based on features and schema from earlier agents.
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
    stack = project.get("stack", "Next.js, TypeScript, PostgreSQL")
    db_client = backend_cfg.get("db_client", "the project's existing DB client")
    auth = backend_cfg.get("auth", "the project's existing auth")
    api_style = backend_cfg.get("api_style", "app-router")
    entities = ", ".join(domain_cfg.get("entities", []))
    key_actions = ", ".join(domain_cfg.get("key_actions", []))
    constraints = "; ".join(domain_cfg.get("constraints", []))

    api_note = (
        "Use Next.js App Router conventions (app/api/... route handlers OR server actions)."
        if api_style == "app-router"
        else f"Use the project's {api_style} API conventions."
    )

    return f"""
You are a senior full-stack engineer. You are building the backend for {project_name}.
{f'Project: {description}' if description else ''}
Stack: {stack}

Your job each iteration:
1. Review the planned features and database schema.
2. Review the existing codebase.
3. Write production-quality API routes, server actions, and utility functions.

Rules:
- {api_note}
- Use TypeScript throughout — no `any` types.
- Validate all inputs with Zod.
- Handle errors gracefully — always return typed responses.
- Use {db_client} for database access.
- Use {auth} for authentication — protect all routes that require it.
- Never hardcode secrets — use environment variables.
- Write complete files, not snippets. Every file should be immediately usable.
- Include JSDoc comments on exported functions.
{f'- Core domain entities: {entities}' if entities else ''}
{f'- Key actions to support: {key_actions}' if key_actions else ''}
{f'- Constraints to enforce: {constraints}' if constraints else ''}

Output format: a JSON object where keys are file paths (relative to repo root)
and values are the complete file content as strings.
""".strip()



class BackendAgent(BaseAgent):
    def __init__(self):
        super().__init__("Backend")

    def implement(
        self,
        features: list,
        schema_result: dict,
        key_files: str,
        context: ContextStore,
    ) -> dict:
        print("\n⚙️   [Backend Agent] Implementing API routes and logic...")

        context_summary = context.summary_for_agents()
        features_json = json.dumps(features, indent=2)
        schema_json = json.dumps({
            "prisma_models": schema_result.get("prisma_models", ""),
            "tables": schema_result.get("new_tables", []) + schema_result.get("modified_tables", []),
        }, indent=2)

        user_prompt = f"""
{context_summary}

FEATURES TO IMPLEMENT:
{features_json}

DATABASE SCHEMA:
{schema_json}

EXISTING KEY FILES (for context — match existing patterns):
{key_files}

Write the backend implementation. Respond with a JSON object where:
- Keys are file paths relative to the repo root (e.g. "app/api/listings/route.ts")
- Values are the complete file content as a string

Include:
1. API route handlers for each feature
2. Server actions where appropriate (for form submissions)
3. Type definitions (types/index.ts additions or new type files)
4. Database utility functions (lib/ helpers)
5. Zod validation schemas

Aim for 3–6 files per iteration. Write complete, production-quality TypeScript.
Focus on the features planned for this iteration — don't rewrite existing code.
"""

        files = self.call_json(_build_system_prompt(context), user_prompt, max_tokens=4096)

        context.add_decision("Backend", f"Implemented {len(files)} files: {', '.join(list(files.keys())[:5])}")

        return files  # {filepath: content}

    def revise(
        self,
        original_files: dict,
        feedback: list,
        context: ContextStore,
    ) -> dict:
        """
        Revise backend files in response to code-review feedback.
        Returns the full set of backend files (original merged with fixes).
        """
        print("\n⚙️   [Backend Agent] Revising files based on code review feedback...")

        context_summary = context.summary_for_agents()
        feedback_json = json.dumps(feedback, indent=2)
        original_code = "\n\n".join(
            f"// FILE: {path}\n{content}"
            for path, content in original_files.items()
        )

        user_prompt = f"""
{context_summary}

ORIGINAL BACKEND FILES:
{original_code}

CODE REVIEW FEEDBACK (address every issue listed):
{feedback_json}

Fix all issues identified in the feedback above.
Respond with a JSON object where keys are file paths and values are the complete,
updated file content — the same format as the original implementation.
Only include files that required changes; unchanged files can be omitted.
"""

        revised = self.call_json(_build_system_prompt(context), user_prompt, max_tokens=4096)

        context.add_decision(
            "Backend",
            f"Revised {len(revised)} file(s) after code review: {', '.join(list(revised.keys())[:5])}",
        )

        # Merge: start from originals, overwrite with revised versions
        return {**original_files, **revised}
