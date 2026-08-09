#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB="$ROOT/web"

if [[ -f "$ROOT/.env.local" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env.local"
  set +a
fi

if [[ -z "${NOMIC_ADDRESS:-}" ]]; then
  echo "set NOMIC_ADDRESS to the deployed contract address" >&2
  exit 1
fi

python3 - "$WEB" "$NOMIC_ADDRESS" <<'PY'
import json
import pathlib
import ast
import re
import subprocess
import sys

web = pathlib.Path(sys.argv[1])
address = sys.argv[2]


def parse_output(raw):
    text = raw.strip()
    payload = extract_payload(text)
    if payload:
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return parse_relaxed_object(payload)
    raise SystemExit("genlayer output did not contain JSON: " + text[:200])


def extract_payload(text):
    marker = text.find("Result:")
    haystack = text[marker + len("Result:") :] if marker != -1 else text
    for idx, ch in enumerate(haystack):
        if ch == "{":
            end = haystack.rfind("}")
            return haystack[idx : end + 1] if end > idx else ""
        if ch == "[":
            end = haystack.rfind("]")
            return haystack[idx : end + 1] if end > idx else ""
    return ""


def parse_relaxed_object(payload):
    quoted = re.sub(
        r"([{\[,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:",
        r'\1"\2":',
        payload,
    )
    return ast.literal_eval(replace_js_atoms(quoted))


def replace_js_atoms(source):
    out = []
    i = 0
    quote = ""
    escaped = False
    while i < len(source):
        ch = source[i]
        if quote:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = ""
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            out.append(ch)
            i += 1
            continue
        replaced = False
        for word, value in (("true", "True"), ("false", "False"), ("null", "None")):
            end = i + len(word)
            before = source[i - 1] if i else ""
            after = source[end] if end < len(source) else ""
            if (
                source.startswith(word, i)
                and not (before.isalnum() or before == "_")
                and not (after.isalnum() or after == "_")
            ):
                out.append(value)
                i = end
                replaced = True
                break
        if replaced:
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def call(name):
    out = subprocess.check_output(["genlayer", "call", address, name], text=True)
    return parse_output(out)


snapshot = {
    "state": call("get_state"),
    "players": call("get_players"),
    "rules": call("get_rulebook"),
    "proposals": call("get_proposals"),
    "moves": call("get_moves"),
    "versions": call("get_versions"),
}

data = json.dumps(snapshot, indent=2)
(web / "snapshot.json").write_text(data + "\n")
(web / "snapshot.js").write_text("window.NOMIC_FALLBACK = " + data + ";\n")
PY
