"""
Frontend Agent
==============
Implements pages, React components, and UI based on the product
plan and backend APIs built in this iteration.
"""

import json
from agents.base_agent import BaseAgent
from context.context_store import ContextStore


def _build_system_prompt(context: ContextStore) -> str:
    cfg = context.get("project_config") or {}
    project = context.get("project") or {}
    frontend_cfg = cfg.get("frontend", {})
    domain_cfg = cfg.get("domain", {})

    project_name = project.get("name", "the project")
    description = project.get("description", "")
    stack = project.get("stack", "Next.js, TypeScript, Tailwind CSS")
    ui_library = frontend_cfg.get("ui_library", "Tailwind CSS")
    component_lib = frontend_cfg.get("component_library", "none")
    data_fetching = frontend_cfg.get("data_fetching", "server-components")
    entities = ", ".join(domain_cfg.get("entities", []))
    key_actions = ", ".join(domain_cfg.get("key_actions", []))

    component_lib_note = (
        f"- Use {component_lib} as the component library where appropriate."
        if component_lib and component_lib != "none"
        else "- Use the project's existing component patterns."
    )
    fetching_note = (
        "- Use React Server Components for initial data; 'use client' only for event handlers, hooks, or browser APIs."
        if data_fetching == "server-components"
        else f"- Use {data_fetching} for data fetching, matching the existing project pattern."
    )

    return f"""
You are a senior frontend engineer. You are building the UI for {project_name}.
{f'Project: {description}' if description else ''}
Stack: {stack}

Your job each iteration:
1. Review the planned features and UX notes from the Product agent.
2. Review existing components and pages.
3. Write production-quality React components and Next.js pages.

Rules:
- Use Next.js App Router (app/ directory), TypeScript, {ui_library}.
- Write complete components — no placeholder TODOs.
- {fetching_note}
- Handle loading and error states.
- Make components accessible (proper aria labels, semantic HTML).
- {component_lib_note}
- For forms: use react-hook-form + Zod for validation if the project uses it,
  otherwise use controlled components.
{f'- Core domain entities to display: {entities}' if entities else ''}
{f'- Key user actions to support: {key_actions}' if key_actions else ''}

Output format: a JSON object where keys are file paths (relative to repo root)
and values are the complete file content as strings.
""".strip()



class FrontendAgent(BaseAgent):
    def __init__(self):
        super().__init__("Frontend")

    def implement(
        self,
        features: list,
        backend_files: dict,
        key_files: str,
        context: ContextStore,
    ) -> dict:
        print("\n🎨  [Frontend Agent] Building components and pages...")

        context_summary = context.summary_for_agents()
        features_json = json.dumps(features, indent=2)
        backend_summary = "\n".join(
            f"- {path}" for path in backend_files.keys()
        )

        user_prompt = f"""
{context_summary}

FEATURES AND UX NOTES:
{features_json}

BACKEND FILES CREATED THIS ITERATION (match these APIs):
{backend_summary}

EXISTING KEY FILES (match existing patterns and components):
{key_files}

Write the frontend implementation. Respond with a JSON object where:
- Keys are file paths relative to the repo root (e.g. "app/listings/page.tsx")
- Values are the complete file content as a string

Include:
1. New pages (app/.../page.tsx)
2. New components (components/... or app/.../components/...)
3. Any layout updates needed
4. Loading skeletons (loading.tsx) for new pages
5. Error boundaries (error.tsx) for new pages where needed

Aim for 4–8 files per iteration. Write complete, production-quality TypeScript + Tailwind.
Focus on the features planned — don't rewrite existing pages.
"""

        files = self.call_json(_build_system_prompt(context), user_prompt, max_tokens=4096)

        context.add_decision("Frontend", f"Built {len(files)} UI files: {', '.join(list(files.keys())[:5])}")

        return files  # {filepath: content}

    def revise(
        self,
        original_files: dict,
        feedback: list,
        context: ContextStore,
    ) -> dict:
        """
        Revise frontend files in response to code-review feedback.
        Returns the full set of frontend files (original merged with fixes).
        """
        print("\n🎨  [Frontend Agent] Revising files based on code review feedback...")

        context_summary = context.summary_for_agents()
        feedback_json = json.dumps(feedback, indent=2)
        original_code = "\n\n".join(
            f"// FILE: {path}\n{content}"
            for path, content in original_files.items()
        )

        user_prompt = f"""
{context_summary}

ORIGINAL FRONTEND FILES:
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
            "Frontend",
            f"Revised {len(revised)} file(s) after code review: {', '.join(list(revised.keys())[:5])}",
        )

        # Merge: start from originals, overwrite with revised versions
        return {**original_files, **revised}
