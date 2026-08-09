#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB="$ROOT/web"

if [[ -z "${NOMIC_ADDRESS:-}" ]]; then
  echo "set NOMIC_ADDRESS to the deployed contract address" >&2
  exit 1
fi

python3 - "$WEB" "$NOMIC_ADDRESS" <<'PY'
import json
import pathlib
import subprocess
import sys

web = pathlib.Path(sys.argv[1])
address = sys.argv[2]


def parse_output(raw):
    text = raw.strip()
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
    raise SystemExit("genlayer output did not contain JSON: " + text[:200])


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
