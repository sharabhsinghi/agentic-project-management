"""
Context Store
=============
Persists all agent decisions, schemas, and iteration history across runs.
This is the shared memory that lets agents build on previous work.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # graceful fallback if PyYAML not installed

# Default location of the project config, relative to cwd
DEFAULT_CONFIG_PATH = "project_config.yaml"


class ContextStore:
    def __init__(self, path: str = "context/project_context.json",
                 config_path: str = DEFAULT_CONFIG_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._config = self._load_config(config_path)
        self._data = self._load()

    def _load_config(self, config_path: str) -> dict:
        """Load project_config.yaml if present, else return empty dict."""
        p = Path(config_path)
        if p.exists() and yaml is not None:
            with open(p) as f:
                return yaml.safe_load(f) or {}
        return {}

    @property
    def project_config(self) -> dict:
        """The raw project_config.yaml contents for agents to use."""
        return self._config

    def _load(self) -> dict:
        if self.path.exists():
            with open(self.path) as f:
                return json.load(f)
        # Seed defaults from config if available
        project_cfg = self._config.get("project", {})
        return {
            "project": {
                "name": project_cfg.get("name", "My Project"),
                "stack": project_cfg.get("stack", ""),
                "description": project_cfg.get("description", ""),
                "created_at": datetime.now().isoformat(),
            },
            "iterations": [],
            "features": [],
            "schema": {},
            "decisions": [],
            "current_iteration": 0,
        }

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        self._data[key] = value
        self.save()

    def increment_iteration(self) -> int:
        self._data["current_iteration"] += 1
        self.save()
        return self._data["current_iteration"]

    def add_iteration(self, iteration: dict):
        self._data["iterations"].append({
            **iteration,
            "timestamp": datetime.now().isoformat(),
            "iteration_number": self._data["current_iteration"],
        })
        self.save()

    def update_schema(self, schema: dict):
        self._data["schema"] = schema
        self.save()

    def add_features(self, features: list):
        existing_ids = {f.get("id") for f in self._data["features"]}
        for feature in features:
            if feature.get("id") not in existing_ids:
                self._data["features"].append(feature)
        self.save()

    def update_features(self, features: list):
        self._data["features"] = features
        self.save()

    def add_decision(self, agent: str, decision: str):
        self._data["decisions"].append({
            "agent": agent,
            "decision": decision,
            "iteration": self._data["current_iteration"],
            "timestamp": datetime.now().isoformat(),
        })
        self.save()

    def is_initialized(self) -> bool:
        """Returns True if the init pass has already been run for this context."""
        return bool(self._data.get("initialized", False))

    def summary_for_agents(self) -> str:
        """Returns a compact context summary to inject into agent prompts."""
        features = self._data.get("features", [])
        schema = self._data.get("schema", {})
        decisions = self._data.get("decisions", [])[-10:]  # last 10
        iteration = self._data.get("current_iteration", 0)
        project = self._data.get("project", {})

        feature_list = "\n".join(
            f"  - [{f.get('status','planned')}] {f.get('name','')}: {f.get('description','')}"
            for f in features
        )
        schema_summary = json.dumps(schema, indent=2) if schema else "  (not yet defined)"
        decision_list = "\n".join(
            f"  - [{d['agent']}] {d['decision']}" for d in decisions
        )

        return f"""
=== PROJECT CONTEXT (Iteration {iteration}) ===

PROJECT: {project.get('name', '')}
DESCRIPTION: {project.get('description', '')}
STACK: {project.get('stack', '')}

FEATURES:
{feature_list or '  (none yet)'}

DATABASE SCHEMA:
{schema_summary}

RECENT DECISIONS:
{decision_list or '  (none yet)'}
""".strip()
