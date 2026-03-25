"""
QA & Security Agent
===================
Reviews the code produced this iteration and writes tests.
Also flags security concerns relevant to the project.
"""

import json
from agents.base_agent import BaseAgent
from context.context_store import ContextStore


def _build_system_prompt(context: ContextStore) -> str:
    cfg = context.get("project_config") or {}
    project = context.get("project") or {}
    backend_cfg = cfg.get("backend", {})
    domain_cfg = cfg.get("domain", {})
    project_cfg = cfg.get("project", {})

    project_name = project.get("name", "the project")
    description = project.get("description", "")
    db_client = backend_cfg.get("db_client", "postgresql")
    auth = backend_cfg.get("auth", "the project's auth")
    user_roles = ", ".join(project_cfg.get("user_roles", ["user"]))
    constraints = "; ".join(domain_cfg.get("constraints", []))
    key_actions = ", ".join(domain_cfg.get("key_actions", []))

    supabase_note = (
        "- Verify Supabase RLS policies exist for all tables with user-scoped data."
        if "supabase" in db_client.lower()
        else ""
    )

    return f"""
You are a senior QA engineer and security reviewer.
You are reviewing code for {project_name}.
{f'Project: {description}' if description else ''}
User roles: {user_roles}

Your job each iteration:
1. Review the backend and frontend code produced.
2. Write meaningful tests (unit + integration where possible).
3. Flag any security issues.

Testing rules:
- Use Jest + React Testing Library for component tests.
- Use Jest for API route/utility unit tests.
- Write tests that test behaviour, not implementation details.
- Cover happy paths AND error cases.
- Mock DB/external calls appropriately.

Security checklist:
- Auth required on every protected route/action (users can only access their own data).
- Input validation against injection, XSS, and price/value manipulation.
- No secrets or tokens in client-side code.
- Rate limiting on high-volume endpoints.
- PII handling: sensitive data must not leak across user boundaries.
{f'- Constraints to verify: {constraints}' if constraints else ''}
{f'- Critical user actions to test: {key_actions}' if key_actions else ''}
{supabase_note}

Output format: a JSON object with:
- "test_files": {{ filepath: content }} — test files to write
- "security_issues": [ {{ severity, location, description, recommendation }} ]
- "qa_notes": "Summary of what was tested and any gaps"
- IMPORTANT: Your entire JSON response must fit within 4096 tokens. Be concise; omit boilerplate. Do not pad or repeat content.
""".strip()



class QAAgent(BaseAgent):
    def __init__(self):
        super().__init__("QA")

    def review_and_test(
        self,
        backend_files: dict,
        frontend_files: dict,
        features: list,
        context: ContextStore,
    ) -> dict:
        print("\n🔒  [QA Agent] Writing tests and reviewing security...")

        context_summary = context.summary_for_agents()
        features_json = json.dumps(features, indent=2)

        # Give the QA agent the actual code to review
        all_files = {**backend_files, **frontend_files}
        code_review_input = "\n\n".join(
            f"=== {path} ===\n{content[:3000]}"
            for path, content in list(all_files.items())[:8]  # cap to avoid token limit
        )

        user_prompt = f"""
{context_summary}

FEATURES THIS ITERATION:
{features_json}

CODE TO REVIEW AND TEST:
{code_review_input}

Write tests for the most critical paths and flag any security issues.
"""

        result = self.call_json(_build_system_prompt(context), user_prompt, max_tokens=4096)

        # Log security issues
        issues = result.get("security_issues", [])
        if issues:
            high = [i for i in issues if i.get("severity") == "high"]
            context.add_decision("QA", f"Found {len(issues)} security issues ({len(high)} high severity)")
        else:
            context.add_decision("QA", "No security issues found this iteration")

        return result
