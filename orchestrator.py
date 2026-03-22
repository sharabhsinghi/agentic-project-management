#!/usr/bin/env python3
"""
AI Agent Orchestrator
=====================
First-time setup (run once before any iteration):
    python orchestrator.py --repo /path/to/your/repo --init

Run an iteration:
    python orchestrator.py --repo /path/to/your/repo --feedback "Add a booking calendar"

First iteration (after init, no specific feedback):
    python orchestrator.py --repo /path/to/your/repo
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime

from agents.orchestrator_agent import OrchestratorAgent
from tools.repo_tools import RepoTools
from context.context_store import ContextStore


def main():
    parser = argparse.ArgumentParser(description="AI Agent Orchestrator")
    parser.add_argument("--repo", required=True, help="Path to your local repo")
    parser.add_argument("--init", action="store_true", help="Analyse the codebase and build base context (run once before first iteration)")
    parser.add_argument("--feedback", default="", help="Your feedback / instructions for this iteration")
    parser.add_argument("--context-file", default="context/project_context.json", help="Path to context store file")
    parser.add_argument("--config", default="project_config.yaml", help="Path to project_config.yaml")
    parser.add_argument("--dry-run", action="store_true", help="Preview plan without writing files")
    args = parser.parse_args()

    repo_path = Path(args.repo).resolve()
    if not repo_path.exists():
        print(f"❌  Repo path not found: {repo_path}")
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌  ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)

    print("\n🤖  AI Agent Orchestrator")
    print("=" * 50)
    print(f"📁  Repo: {repo_path}")
    if args.init:
        print(f"🔧  Mode: Initialisation")
    else:
        print(f"💬  Feedback: {args.feedback or '(none — agents will decide)'}")
    print(f"🕐  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    context_store = ContextStore(args.context_file, config_path=args.config)
    repo_tools = RepoTools(repo_path)

    orchestrator = OrchestratorAgent(
        repo_tools=repo_tools,
        context_store=context_store,
        dry_run=args.dry_run,
    )

    # ── Initialisation mode ──────────────────────────────────────────────
    if args.init:
        if context_store.is_initialized():
            print("⚠️   Context already initialised. To re-run init, delete the context file:")
            print(f"    rm {args.context_file}")
            sys.exit(0)
        orchestrator.run_initialization()
        print(f"\n✅  Initialisation complete!")
        print(f"📋  Context saved to: {args.context_file}")
        print(f"\n   Next step:")
        print(f"   python orchestrator.py --repo {args.repo} --feedback \"<your first feature request>\"")
        sys.exit(0)

    # ── Iteration mode ───────────────────────────────────────────────────
    if not context_store.is_initialized():
        print("❌  Context not initialised. Run init first:")
        print(f"   python orchestrator.py --repo {args.repo} --init")
        sys.exit(1)

    orchestrator.run_iteration(feedback=args.feedback)

    print("\n✅  Iteration complete!")
    print(f"📋  Context saved to: {args.context_file}")
    if not args.dry_run:
        print(f"📝  Files written to repo. Review changes, then commit when ready.")


if __name__ == "__main__":
    main()
