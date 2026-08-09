#!/usr/bin/env python3
"""nomic - play a game of Nomic on GenLayer from the terminal.

This wraps the official `genlayer` CLI rather than binding a client library,
so it keeps working across SDK releases and there is exactly one place where
command construction lives: build_command below.

Setup:

    npm install -g genlayer
    genlayer account import   # or genlayer account create
    genlayer network set <network>
    export NOMIC_ADDRESS=0x...

Usage:

    nomic state
    nomic rules
    nomic history
    nomic log
    nomic join "Alice"
    nomic move "I claim four points" --claim 4 \\
        --clarify "A claim of four points is legal."
    nomic propose enact "A player may not claim twice in a row."
    nomic propose setparam --param max_claim --value 20
    nomic vote 3 yes
    nomic resolve 3
    nomic win "I hold one hundred points."

Several players on one machine each need their own key. The genlayer CLI keeps
named accounts, so pass --account and this wrapper switches to it first:

    nomic --account alice move "..." --clarify "..."
    nomic --account bob vote 3 no

Or set NOMIC_ACCOUNT once per shell. Add --print to see the underlying
genlayer commands without running anything.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import textwrap

# The genlayer CLI takes `genlayer write [options] <address> <method>` and
# `genlayer call [options] <address> <method>`. Method arguments are appended
# after the method name. If a future CLI release moves them behind a flag,
# change ARG_STYLE to "flag" and nothing else needs touching.
ARG_STYLE = "positional"  # "positional" or "flag"

VERDICT_MARK = {
    "LEGAL": "legal",
    "ILLEGAL": "illegal",
    "UNDETERMINED": "UNDETERMINED",
}


class Failure(Exception):
    pass


def address() -> str:
    addr = os.environ.get("NOMIC_ADDRESS", "").strip()
    if not addr:
        raise Failure(
            "set NOMIC_ADDRESS to the deployed contract address, "
            "for example: export NOMIC_ADDRESS=0xabc..."
        )
    return addr


def build_command(mode: str, method: str, args: list) -> list:
    """The single point of contact with the genlayer CLI."""
    cmd = ["genlayer", mode]
    rpc = os.environ.get("NOMIC_RPC", "").strip()
    if rpc:
        cmd += ["--rpc", rpc]
    cmd += [address(), method]
    if args:
        if ARG_STYLE == "flag":
            cmd += ["--args"] + [str(a) for a in args]
        else:
            cmd += [str(a) for a in args]
    return cmd


def use_account(name: str, show: bool) -> None:
    """Make a named account active.

    `genlayer account use <name>` is the documented way to switch, and it is
    global state, which is exactly what several players sharing one machine
    need. It is a no-op when no account was asked for.
    """
    if not name:
        return
    cmd = ["genlayer", "account", "use", name]
    if show:
        print(" ".join(cmd))
        return
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise Failure(
            "could not switch to account " + name + ": "
            + (proc.stderr or proc.stdout).strip()
            + "\ncheck the name with: genlayer account list"
        )


def run(mode: str, method: str, args: list, show: bool) -> object:
    cmd = build_command(mode, method, args)
    if show:
        print(" ".join(json.dumps(c) if (" " in c or c == "") else c for c in cmd))
        return None
    if shutil.which("genlayer") is None:
        raise Failure(
            "the genlayer CLI is not on PATH. Install it with: "
            "npm install -g genlayer"
        )
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise Failure((proc.stderr or proc.stdout).strip())
    return parse_output(proc.stdout)


def parse_output(raw: str) -> object:
    """The CLI prints human readable text around any JSON payload."""
    text = raw.strip()
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    return text


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------


def wrap(text: str, indent: int = 6) -> str:
    return textwrap.fill(
        text, width=88, initial_indent=" " * indent, subsequent_indent=" " * indent
    )


def show_state(state: dict) -> None:
    print("rulebook   v" + str(state["rulebook_version"]))
    print("hash       " + state["rulebook_hash"])
    print("algorithm  " + state["hash_algo"])
    print("phase      " + state["phase"])
    if state["phase"] == "CLARIFY":
        print(
            "           clarification vote open as proposal "
            + str(state["open_clarification"])
        )
    if state["phase"] == "OVER":
        print("ending     " + state["ending"])
        print("winner     " + (state["winner_name"] or state["winner"]))
    else:
        print("to move    " + (state["turn"] or "nobody yet"))
    print(
        "rules      "
        + str(state["rules_in_force"])
        + " in force, "
        + str(state["params"]["max_rules"])
        + " allowed, "
        + str(state["limits"]["hard_max_rules"])
        + " is the machinery limit"
    )
    print(
        "rulebook   "
        + str(state["limits"]["rulebook_chars"])
        + " of "
        + str(state["limits"]["hard_max_rulebook_chars"])
        + " characters the judge can be given"
    )
    p = state["params"]
    print(
        "parameters victory "
        + str(p["victory_score"])
        + ", claim up to "
        + str(p["max_claim"])
        + ", threshold "
        + str(p["vote_threshold"])
        + "%"
    )
    print("moves      " + str(state["moves"]))


def show_rules(rules: list) -> None:
    for r in rules:
        tag = "immutable" if r["immutable"] else "mutable"
        if not r["in_force"]:
            print(str(r["id"]) + "  repealed at v" + str(r["since_version"]))
            continue
        print(str(r["id"]) + "  " + tag + ", since v" + str(r["since_version"]))
        print(wrap(r["text"]))
        print("")


def show_moves(moves: list) -> None:
    for m in moves:
        head = (
            "#"
            + str(m["id"])
            + "  "
            + (m["player_name"] or m["player"][:10])
            + "  "
            + m["action"]
            + "  "
            + VERDICT_MARK.get(m["verdict"], m["verdict"])
        )
        if m["rule_id"]:
            head += "  by rule " + str(m["rule_id"])
        else:
            head += "  no rule cited"
        print(head)
        print(wrap(m["text"]))
        print(
            "      judged against v"
            + str(m["rulebook_version"])
            + " "
            + m["rulebook_hash"][:16]
            + "  reasoning "
            + m["reasoning_hash"][:16]
        )
        if m["note"]:
            print("      " + m["note"])
        print("")


def show_proposals(props: list) -> None:
    for p in props:
        head = (
            "#"
            + str(p["id"])
            + "  "
            + p["kind"]
            + ("  clarification" if p["is_clarification"] else "")
            + "  "
            + p["status"]
            + "  "
            + str(p["yes"])
            + " for, "
            + str(p["no"])
            + " against"
        )
        print(head)
        if p["target"]:
            print("      on rule " + str(p["target"]))
        if p["param"]:
            print("      " + p["param"] + " to " + str(p["value"]))
        print(wrap(p["text"]))
        if p.get("ballots"):
            cast = ", ".join(b["name"] + " " + b["choice"] for b in p["ballots"])
            print("      ballots: " + cast)
        print("")


def show_history(versions: list) -> None:
    for v in versions:
        head = "v" + str(v["version"]) + "  " + v["at"]
        if v["by"]:
            head += "  by " + v["by"]
        print(head + "  " + v["hash"])
        for c in v["changes"]:
            if c["kind"] == "added":
                label = "rule " + str(c["rule"]) + " enacted" if c["rule"] else "genesis"
                print("      + " + label)
                print(wrap(c["after"], indent=8))
            elif c["kind"] == "removed":
                print("      - rule " + str(c["rule"]) + " repealed")
                print(wrap(c["before"], indent=8))
            else:
                print("      ~ rule " + str(c["rule"]) + " rewritten")
                print(wrap("was: " + c["before"], indent=8))
                print(wrap("now: " + c["after"], indent=8))
        print("")


def show_result(result: object) -> None:
    if not isinstance(result, dict):
        print(result)
        return
    if "verdict" in result:
        line = "verdict " + VERDICT_MARK.get(result["verdict"], result["verdict"])
        if result.get("rule_id"):
            line += ", by rule " + str(result["rule_id"])
        print(line)
        if result["verdict"] == "UNDETERMINED":
            print(
                "the rulebook does not settle this. A clarification vote is now "
                "open and the turn stays with you."
            )
    if result.get("note"):
        print(result["note"])
    if result.get("rulebook_hash") and "rulebook_version" in result:
        print(
            "rulebook now v"
            + str(result["rulebook_version"])
            + " "
            + str(result["rulebook_hash"])[:16]
        )


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(
        prog="nomic",
        description="Play Nomic on GenLayer.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Set NOMIC_ADDRESS to the deployed contract address first.",
    )
    parser.add_argument(
        "--print",
        dest="show",
        action="store_true",
        help="print the genlayer command instead of running it",
    )
    parser.add_argument(
        "--account",
        default=os.environ.get("NOMIC_ACCOUNT", ""),
        metavar="NAME",
        help="play as this named genlayer account, for several players on one machine",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("state", help="show version, hash, phase and whose turn it is")
    sub.add_parser("rules", help="print the rulebook as it stands")
    p_log = sub.add_parser("log", help="print recent moves with their verdicts")
    p_log.add_argument(
        "--older",
        action="store_true",
        help="the page before the most recent one",
    )
    p_log.add_argument(
        "--offset", type=int, default=0, metavar="N",
        help="skip N moves back from the newest",
    )
    sub.add_parser("proposals", help="print every proposal and its votes")
    sub.add_parser("history", help="print the amendment history, version by version")
    sub.add_parser("principle", help="print the equivalence principle in force")
    sub.add_parser("canonical", help="print the exact string that is hashed")

    p_join = sub.add_parser("join", help="join before the first move is made")
    p_join.add_argument("name")

    p_move = sub.add_parser("move", help="make a move")
    p_move.add_argument("text", help="what you are doing, in your own words")
    p_move.add_argument(
        "--claim", type=int, default=0, metavar="N", help="claim N points"
    )
    p_move.add_argument("--pass", dest="passing", action="store_true")
    p_move.add_argument(
        "--clarify",
        required=True,
        metavar="RULE",
        help="the rule you propose if the judge cannot settle this move",
    )

    p_prop = sub.add_parser("propose", help="propose an amendment")
    p_prop.add_argument(
        "kind", choices=["enact", "repeal", "amend", "transmute", "setparam"]
    )
    p_prop.add_argument("text", nargs="?", default="", help="the new rule, or a reason")
    p_prop.add_argument("--rule", type=int, default=0, help="the rule acted on")
    p_prop.add_argument(
        "--param",
        default="",
        choices=["", "victory_score", "max_claim", "vote_threshold", "max_rules"],
    )
    p_prop.add_argument("--value", type=int, default=0)

    p_vote = sub.add_parser("vote", help="vote on an open proposal")
    p_vote.add_argument("proposal_id", type=int)
    p_vote.add_argument("choice", choices=["yes", "no"])

    p_res = sub.add_parser("resolve", help="tally an open proposal and apply it")
    p_res.add_argument("proposal_id", type=int)

    p_win = sub.add_parser("win", help="claim the win")
    p_win.add_argument("statement")

    args = parser.parse_args(argv)
    cmd = args.command

    # views do not sign anything, so only switch when a write is coming
    if args.account and cmd not in (
        "state", "rules", "log", "proposals", "history", "principle", "canonical"
    ):
        use_account(args.account, args.show)

    if cmd == "state":
        out = run("call", "get_state", [], args.show)
        if out is not None:
            show_state(out)
    elif cmd == "rules":
        out = run("call", "get_rulebook", [], args.show)
        if out is not None:
            show_rules(out)
    elif cmd == "log":
        if args.older or args.offset:
            offset = args.offset or 50
            out = run("call", "get_moves_page", [offset, 50], args.show)
        else:
            out = run("call", "get_moves", [], args.show)
        if out is not None:
            show_moves(out)
    elif cmd == "proposals":
        out = run("call", "get_proposals", [], args.show)
        if out is not None:
            show_proposals(out)
    elif cmd == "history":
        out = run("call", "get_versions", [], args.show)
        if out is not None:
            show_history(out)
    elif cmd == "principle":
        out = run("call", "get_equivalence_principle", [], args.show)
        if out is not None:
            print(wrap(str(out), indent=0))
    elif cmd == "canonical":
        out = run("call", "get_canonical_rulebook", [], args.show)
        if out is not None:
            print(out)
    elif cmd == "join":
        run("write", "join", [args.name], args.show)
        if not args.show:
            print("joined as " + args.name)
    elif cmd == "move":
        if args.claim and args.passing:
            raise Failure("a move either claims points or passes, not both")
        if args.claim:
            kind, value = "CLAIM", args.claim
        elif args.passing:
            kind, value = "PASS", 0
        else:
            kind, value = "NOTE", 0
        out = run(
            "write", "submit_move", [args.text, kind, value, args.clarify], args.show
        )
        if out is not None:
            show_result(out)
    elif cmd == "propose":
        kind = args.kind.upper()
        if kind == "SETPARAM" and not args.param:
            raise Failure("setparam needs --param and --value")
        if kind != "SETPARAM" and not args.text:
            raise Failure(kind.lower() + " needs the proposal text")
        if kind in ("REPEAL", "AMEND", "TRANSMUTE") and not args.rule:
            raise Failure(kind.lower() + " needs --rule")
        target = args.rule
        if kind == "SETPARAM" and not target:
            target = {
                "max_claim": 202,
                "victory_score": 203,
                "vote_threshold": 204,
                "max_rules": 205,
            }[args.param]
        out = run(
            "write",
            "propose",
            [kind, target, args.text, args.param, args.value],
            args.show,
        )
        if out is not None:
            show_result(out)
    elif cmd == "vote":
        run(
            "write",
            "vote",
            [args.proposal_id, "true" if args.choice == "yes" else "false"],
            args.show,
        )
        if not args.show:
            print("voted " + args.choice + " on proposal " + str(args.proposal_id))
    elif cmd == "resolve":
        out = run("write", "resolve_proposal", [args.proposal_id], args.show)
        if out is not None:
            show_result(out)
    elif cmd == "win":
        out = run("write", "claim_victory", [args.statement], args.show)
        if out is not None:
            show_result(out)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Failure as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
