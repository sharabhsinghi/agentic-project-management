"""
Base Agent
==========
All agents inherit from this. Handles Claude API calls, retries, and JSON parsing.
"""

import json
import os
import re
import time
from typing import Optional
import anthropic


class BaseAgent:
    MODEL = "claude-opus-4-5"
    MAX_TOKENS = 4096

    def __init__(self, name: str):
        self.name = name
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    def call(self, system: str, user: str, max_tokens: Optional[int] = None) -> str:
        """Make a Claude API call and return the text response."""
        print(f"  🤖  [{self.name}] thinking...")
        for attempt in range(3):
            try:
                response = self.client.messages.create(
                    model=self.MODEL,
                    max_tokens=max_tokens or self.MAX_TOKENS,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                return response.content[0].text
            except anthropic.RateLimitError:
                wait = 2 ** attempt * 5
                print(f"  ⏳  Rate limited. Waiting {wait}s...")
                time.sleep(wait)
            except Exception as e:
                print(f"  ❌  [{self.name}] API error: {e}")
                raise
        raise RuntimeError(f"[{self.name}] Failed after 3 attempts")

    def call_json(self, system: str, user: str, max_tokens: Optional[int] = None) -> dict | list:
        """Make a Claude API call expecting a JSON response."""
        system_with_json = system + "\n\nRespond ONLY with valid JSON. No markdown fences, no preamble."
        raw = self.call(system_with_json, user, max_tokens)
        return self._parse_json(raw)

    def _parse_json(self, raw: str) -> dict | list:
        """Parse JSON, stripping any markdown fences if present."""
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"  ⚠️  [{self.name}] JSON parse error: {e}")
            print(f"  Raw response (first 500 chars): {raw[:500]}")
            # Response may be truncated due to token limits — attempt recovery
            recovered = self._recover_truncated_json(cleaned)
            if recovered is not None:
                print(f"  🔧  [{self.name}] Recovered truncated JSON response.")
                return recovered
            raise

    def _recover_truncated_json(self, text: str) -> dict | list | None:
        """Attempt to recover a truncated JSON object by trimming to the last complete key."""
        # Walk backwards through the text to find the last position where JSON is valid
        # Strategy: remove the last incomplete key-value pair by finding the last comma
        # at the top level and closing the object/array there.
        depth_map = {'{': '}', '[': ']'}
        close_map = {'}': '{', ']': '['}
        stack = []
        in_string = False
        escape_next = False
        last_top_level_comma = -1
        first_open = None

        for i, ch in enumerate(text):
            if escape_next:
                escape_next = False
                continue
            if ch == '\\' and in_string:
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch in depth_map:
                if first_open is None:
                    first_open = ch
                stack.append(ch)
            elif ch in close_map:
                if stack and stack[-1] == close_map[ch]:
                    stack.pop()
            elif ch == ',' and len(stack) == 1:
                last_top_level_comma = i

        if first_open is None or last_top_level_comma == -1:
            return None

        closer = depth_map[first_open]
        truncated = text[:last_top_level_comma] + closer
        try:
            return json.loads(truncated)
        except json.JSONDecodeError:
            return None
