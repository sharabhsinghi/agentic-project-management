"""
Code Review Agent
=================
Reviews backend and frontend code written in the current iteration for
quality, security, and consistency issues.

Provides structured, file-scoped feedback that is passed back to the
backend and frontend agents for a single revision pass before QA runs.
"""

import json
from agents.base_agent import BaseAgent
from context.context_store import ContextStore


def _build_system_prompt(context: ContextStore) -> str:
    project = context.get("project") or {}
    cfg = context.get("project_config") or {}
    backend_cfg = cfg.get("backend", {})

    project_name = project.get("name", "the project")
    stack = project.get("stack", "")
    db_client = backend_cfg.get("db_client", "")

    supabase_note = (
        "  missing Supabase RLS considerations,"
        if "supabase" in db_client.lower()
        else ""
    )
    stack_line = f"You are reviewing code for {project_name}." + (f" Stack: {stack}." if stack else "")

    return f"""
You are a senior software engineer and technical lead conducting a thorough code review.
{stack_line}

Review each file against these criteria:
- Correctness: logic errors, unhandled edge cases, incorrect API or framework usage
- Security: missing auth checks, unvalidated input reaching the DB, XSS/injection risks,
  exposed secrets or tokens{supabase_note}
- TypeScript strictness: no `any` types, proper return types on exported functions
- Code quality: duplicated logic, overly complex or unreadable sections
- Consistency: does the new code follow patterns visible in the existing codebase?
- Performance: N+1 DB queries, unnecessary re-renders, missing memoisation where critical
- Accessibility (frontend only): missing aria attributes, non-semantic HTML, keyboard traps
- API design (backend only): correct HTTP status codes, consistent response shapes,
  Zod validation present on all mutating routes

Focus only on real, actionable issues — not stylistic preferences.
Be concise and specific: reference the file and the exact function or section.
""".strip()


class CodeReviewAgent(BaseAgent):
    def __init__(self):
        super().__init__("CodeReview")

    def review(
        self,
        backend_files: dict,
        frontend_files: dict,
        features: list,
        context: ContextStore,
    ) -> dict:
        """
        Review backend and frontend files produced in this iteration.

        Returns a dict with:
          backend_feedback  – list of {file, issues[], severity}
          frontend_feedback – list of {file, issues[], severity}
          has_issues        – bool; False when the code is clean
          overall_notes     – brief human-readable summary
        """
        print("\n🔍  [Code Review Agent] Reviewing backend and frontend code...")

        context_summary = context.summary_for_agents()
        features_json = json.dumps(features, indent=2)

        backend_code = "\n\n".join(
            f"// FILE: {path}\n{content}"
            for path, content in backend_files.items()
        )
        frontend_code = "\n\n".join(
            f"// FILE: {path}\n{content}"
            for path, content in frontend_files.items()
        )

        user_prompt = f"""
{context_summary}

FEATURES BEING IMPLEMENTED THIS ITERATION:
{features_json}

──────────────────────────────────────────
BACKEND CODE TO REVIEW:
──────────────────────────────────────────
{backend_code}

──────────────────────────────────────────
FRONTEND CODE TO REVIEW:
──────────────────────────────────────────
{frontend_code}

Review all the code above and respond with a JSON object in this exact structure:
{{
  "backend_feedback": [
    {{
      "file": "<filepath>",
      "issues": ["<specific, actionable issue description>"],
      "severity": "high|medium|low"
    }}
  ],
  "frontend_feedback": [
    {{
      "file": "<filepath>",
      "issues": ["<specific, actionable issue description>"],
      "severity": "high|medium|low"
    }}
  ],
  "has_issues": true,
  "overall_notes": "<brief summary of what was reviewed and the main findings>"
}}

Rules:
- Only include a file in backend_feedback / frontend_feedback if it has real issues.
- Set has_issues to false if the code is clean with no meaningful problems.
- Each issue string must identify the specific function, block, or line range involved.
"""

        result = self.call_json(_build_system_prompt(context), user_prompt, max_tokens=4096)

        backend_issues = len(result.get("backend_feedback", []))
        frontend_issues = len(result.get("frontend_feedback", []))

        context.add_decision(
            "CodeReview",
            f"Reviewed {len(backend_files)} backend file(s) and {len(frontend_files)} "
            f"frontend file(s). Found issues in {backend_issues} backend and "
            f"{frontend_issues} frontend file(s).",
        )

        has_issues = result.get("has_issues", False)
        status = "issues found" if has_issues else "no issues"
        print(f"  ✓  Review complete ({status}) — "
              f"{backend_issues} backend file(s), {frontend_issues} frontend file(s) flagged")

        return result
