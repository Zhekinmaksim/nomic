# Nomic on GenLayer

Nomic is a game in which changing the rules is a move. It starts from a short
rulebook in plain language. Players propose amendments, vote, and the rulebook
mutates. Turn order, victory condition and the amendment procedure itself all
get rewritten as play proceeds.

It has never been built as a real digital game, because it needs a judge that
applies rules written after the software shipped. This is that judge, as a
GenLayer Intelligent Contract.

## Why this cannot be built anywhere else

The contract has to enforce text that did not exist at deploy time. The EVM
cannot do that at all.

A single LLM judge cannot do it either, and that is not a formality. Nomic
players hunt for holes in the rules, so the first hole they find is the quirks
of one particular model. The rulebook turns into a collection of jailbreaks
against that judge and the game dies. Consensus across independent validators
running different models is what makes the arbiter unbribable, and an
unbribable arbiter is what makes the game playable.

Slow consensus is an advantage here. The game is turn based and asynchronous,
like correspondence chess. Fifteen minutes per move is a normal pace.

## Why this is not "AI decides X"

The contract answers one bounded question per action:

> is this move legal under rulebook version N, whose hash was fixed on chain
> before the move was submitted

It does not score quality and it has no taste. The output is an enum, the
number of the rule that decided it, and a hash of the reasoning. Consensus
compares the verdict, the rule number and the rulebook hash. No prose is ever
compared. The equivalence principle is published on chain and readable with
`nomic principle`.

The model never performs the state change. When a move is judged legal, a
deterministic branch applies the declared effect. When an amendment passes, a
deterministic branch rewrites the rulebook. The model decides permission, the
contract decides consequence.

## The key design decision: UNDETERMINED is a game mechanic

There is a third verdict alongside legal and illegal, meaning the rulebook does
not clearly settle the question. It is not an error state and it is never
collapsed into "illegal".

An UNDETERMINED verdict opens a clarification vote and freezes the turn. In the
original game, disputed interpretations are resolved by the players, so this is
faithful to Nomic rather than a workaround. Non-determinism is absorbed into
the gameplay instead of being hidden from it.

Every move must be submitted with the clarifying rule its author would propose
if the judge cannot settle it. The price of making an ambiguous move is saying
in advance how you would disambiguate it.

## Architecture

Adjudication runs in three stages.

**Stage A, deterministic.** Pin the rulebook hash, the version, the move text
and the set of rule ids that may be cited. No LLM. Turn order, effect ranges
and phase are checked here, so an out of turn move never reaches an inference.

**Stage B, non deterministic.** Judge legality. Returns four fields:
`rulebook_hash`, `verdict`, `rule_id`, `reasoning_hash`. Compared under
`gl.eq_principle.prompt_comparative` with a principle that names the three
fields that decide agreement and excludes everything else, including the
reasoning hash, which is leader local by construction.

**Stage C, deterministic.** Apply the state change. Free of divergence risk, so
it is auditable, and it is also where the game can break.

```
submit_move / propose / claim_victory
        |
   Stage A  pin hash, version, valid rule ids, check turn and ranges
        |
   Stage B  one LLM call, output normalised to four fields, consensus on three
        |
   Stage C  LEGAL        -> apply effect, pass the turn
            ILLEGAL      -> record, the turn does not pass
            UNDETERMINED -> open a clarification vote, freeze the turn
```

`vote` and `resolve_proposal` are fully deterministic and cost no inference.

## Rulebook growth versus context limits

The rulebook grows every turn and at some point stops fitting in a prompt.
There were two options: cap the rule count and force repeal before addition, or
supply only the rules a move plausibly touches. The second introduces a
retrieval step, and a retrieval step is a second attack surface that players
would aim at immediately, because omitting a rule from the prompt is
indistinguishable from repealing it. So the whole rulebook is always sent, and
it is capped instead.

| limit | value | set by |
| --- | --- | --- |
| rules in force | 16 | rule 205, mutable |
| rules in force, machinery limit | 24 | contract |
| rulebook characters, machinery limit | 12000 | contract |
| characters per rule | 500 | contract |

Two other things grow without bound, the move log and the amendment history.
Neither enters a prompt, so neither threatens the judge, but a view has to fit
in one response. `get_moves` and `get_versions` return the most recent page,
`get_moves_page` and `get_versions_page` reach further back, and `get_state`
publishes the totals so a reader always knows when it is looking at a window.

Measured prompt sizes: 3843 characters at genesis, 6995 at the current rule
cap, 14505 at the machinery limit. See `COSTS.md`.

## Calibrating the judge

Two properties of Stage B decide whether the game works, and neither can be
tested by asserting on code: whether UNDETERMINED is reachable at all, and
whether independent judges return the same verdict and rule id.
`scripts/calibrate.py` builds the real prompts through the contract's own
Stage A and scores twelve cases against what the rulebook actually says, four
of them cases where it is genuinely silent and two of them prompt injections.

```
python3 scripts/calibrate.py                  # write the prompts out
ANTHROPIC_API_KEY=... python3 scripts/calibrate.py --run \
    --models model-a,model-b --repeats 3
```

Across models it measures divergence, which is the on chain appeal rate.
Repeated on one model it measures stability. Run it before deploying.

One thing the contract does to help: an UNDETERMINED verdict is forced to cite
no rule. Judges that agree the rulebook is silent still pick different rules to
blame, and that disagreement would fail consensus for no reason.

## Rules that break the contract

In Nomic, players eventually pass a rule the machinery cannot execute, and
reaching that state is a legitimate win in the original game. That is rule 105
here, and it is implemented as an ending rather than an exception. When a
proposal passes and Stage C cannot execute it, the game enters a terminal state
that records how it was broken, and the proposer wins.

Only `MachineryError` does that. Any other exception raised while applying an
amendment is a fault in the contract, not a Nomic ending, so it reverts the
transaction rather than handing somebody the win.

The break surfaces are deliberate and reachable: raising the rule cap past what
the judge can be given, amending an immutable rule that was never transmuted,
enacting into a full rulebook, setting a vote threshold that cannot be met.

Four mutable rules quote a number that the contract also holds as an integer.
Those rules are amended with `SETPARAM`, which changes the number and rewrites
the sentence in one deterministic step. Without that, the rule text and the
contract behaviour drift apart on the first amendment and the judge starts
enforcing a rulebook the contract does not implement.

## Prompt injection

Move text and proposal text are player supplied and go into the prompt. They
are fenced with a marker derived from the current rulebook hash, so the marker
changes on every amendment, and any `<<<` or `>>>` in the payload is broken up.
The prompt labels the fenced region as evidence under examination and says that
any instruction inside it is part of the evidence.

That is a speed bump, not the defence. The defence is the equivalence
principle: an injection has to flip the verdict and the rule number identically
across independent validators running different models, or it fails consensus
instead of winning the game. An injection that half works costs the attacker a
turn and produces a disagreement, which is the cheapest possible outcome for
everyone except the attacker.

## Layout

```
contracts/nomic.py        the Intelligent Contract
rules/genesis.md          the ten starting rules, with the reasoning
cli/nomic.py              player CLI, wraps the official genlayer CLI
web/index.html            read-only page, a VT100 terminal
web/snapshot.js           bundled fallback so the page works from disk
web/intro.html            title card for the demo video
web/outro.html            end card with source and site
scripts/calibrate.py      measures the judge before deployment
scripts/                  snapshot generation
test/test_nomic.py        off chain tests for the deterministic halves
test/page.spec.js         end to end test of the page in a real browser
COSTS.md                  what a game costs
DEMO.md                   shot list, recording setup and the Suno prompt
DEMO.srt                  subtitle track, timed to the shot list
SUBMISSION.md             Portal submission notes
```

## Running it

The contract tests need nothing but Python.

```
python3 test/test_nomic.py
```

They stub the GenVM runtime and exercise Stage A and Stage C exactly as
written, with Stage B scripted so verdicts can be forced. They cover rulebook
hashing, versioning, turn order, vote tallies, amendment application, parameter
rewrites, the UNDETERMINED path and the rule 105 ending. They do not test
consensus. Only a real network can do that.

The full local gate runs the contract tests and the page end to end test. The
page test boots `web/` in Chromium, blocks the CDN import, and verifies that
the bundled snapshot fallback renders a real UNDETERMINED game state:

```
npm install
npx playwright install chromium
npm test
```

It covers the status line, roster, votable queue, log with the three stage
trace, rule search and highlighting, the version diff, every command the form
builds for the current phase, shell escaping and the keyboard.

The title and end cards have their own test, which plays both timelines and
checks the final frame:

```
node test/test_cards.mjs
```

## Cards for the demo video

`web/intro.html` and `web/outro.html` are full screen title and end cards in
the same terminal, sized off the viewport so recording at 1280 or at 1920 gives
identical framing. The intro is a boot sequence that states the four things a
reviewer needs in the first ten seconds: the rulebook is hashed and pinned, the
judge is consensus rather than a model, the board is Bradbury, and there are
three verdicts, the third of which arrives in reverse video and blinking. The
outro carries the closing line, the source, the site and the byline.

Both replay on click, on `R` and on space, so a recording can be retaken
without reloading. `?speed=2` runs the timeline at double rate for a shorter
cut, and both honour `prefers-reduced-motion` by skipping straight to the final
frame.

Deploying:

```
npm install -g genlayer
genlayer account create
genlayer network set <network>
genlayer deploy --contract contracts/nomic.py
export NOMIC_ADDRESS=0x...
```

Playing in the web app:

Open the deployed page, choose an action, press `CONNECT WALLET`, then `SEND TX`.
The browser wallet signs with the player's own account on GenLayer Bradbury;
the deployer's private key is not used by other players. Joining is available
until the first move lands, so seat the second player before Alice moves.

Playing from the CLI:

```
python3 cli/nomic.py --account alice join "Alice"
python3 cli/nomic.py move "I claim four points" --claim 4 \
    --clarify "A claim of four points on your own turn is legal."
python3 cli/nomic.py propose enact "A player may not claim twice in a row."
python3 cli/nomic.py vote 1 yes
python3 cli/nomic.py resolve 1
python3 cli/nomic.py state
python3 cli/nomic.py log
python3 cli/nomic.py history
```

Add `--print` to any command to see the underlying `genlayer` invocation
without running it. `--account NAME`, or `NOMIC_ACCOUNT`, switches between
named genlayer keystores, which is how several players share one machine.

Watching:

```
python3 scripts/make_demo_snapshot.py   # simulated game, for a local preview
open web/index.html                     # works straight off disk
```

The page reads in three steps and takes the first that works: live from the
contract when the URL carries `?address=0x...`, then `web/snapshot.json` over
`fetch`, then `web/snapshot.js`, which is a plain script tag and therefore
loads under `file://` where `fetch` does not. The badge in the header says
which source it ended up using.

Served rather than opened:

```
python3 -m http.server -d web 8080
```

`scripts/snapshot.sh` writes both `snapshot.json` and `snapshot.js` from a
deployed contract, for hosting the page statically. Run it on a timer if you
want a hosted page to keep up with a live game.

## The interface

Nomic dates from 1982, so the page is the interface a player would have had
that year: a DEC VT100. Monochrome green P1 phosphor, 80 columns for the narrow
view and 132 for the wide one, scanlines, and the VT323 typeface, which is the
terminal's own.

The point is not nostalgia. A VT100 has no colour, so everything it can say it
says with character attributes, and the three verdicts fall onto three of them
exactly:

| verdict | attribute |
| --- | --- |
| LEGAL | bold, full intensity |
| ILLEGAL | dim, struck through |
| UNDETERMINED | reverse video, blinking |

Blink is what the terminal has for "look at this, it is not settled", which is
precisely what UNDETERMINED means. On a screen with no colour at all, the one
blinking thing is the judge admitting the rulebook has a hole. Blinking stops
under `prefers-reduced-motion`, where the verdict stays in steady reverse video.

The layout follows the Board Game Arena convention for asynchronous games:
global state along the top, shared actions in the middle, player panels compact
enough to read at a glance, and a status line that always says what is
happening.

- **Status line**, sticky, reverse video, the way a VT100 form banner was
  drawn: PLAY with whose turn it is, HELD with a blinking asterisk when a
  clarification is blocking the game, or OVER with how it ended. It also
  carries the rulebook version, the hash, and how old the reading is, which
  goes to reverse video once it is more than ninety seconds stale.
- **PF key legend** fixed at the foot, listing only what is possible right now,
  at most four. `PF1` to `PF4` work as keys, as do `1` to `4`, `R` refreshes,
  and `ESC` closes the form.
- **Players** as a roster: turn order, score against the winning score, an
  ASCII gauge, and state. The player to move is in reverse video.
- **On the table.** Open proposals with tallies, a gauge, whether each is
  passing or short of quorum, and who has voted which way with the players who
  have not voted shown as a dash. This is the BlogNomic shape, where the queue
  of votable matters is what players act on, so it sits above the history.
- **Game log.** One line per move. Opening a row shows the three stage trace:
  A, what Stage A pinned, including how many rules were citable at that moment;
  B, the four fields Stage B returned and which three consensus compared; C,
  which branch Stage C took and what it did. Then the rulebook version and hash
  it was judged against, the reasoning hash, and a permalink.
- **Rulebook** in its own pane with two tabs. IN FORCE has a search box that
  highlights hits inside the rule text and a toggle for repealed rules.
  CHANGES is the amendment history: pick any version and see what that version
  did, with a word level diff so a rewritten rule shows only the words that
  moved. Clicking a cited rule in the log jumps to it and puts it in reverse
  video.

The page reads live from the contract when the URL carries `?address=0x...`,
polls every twenty seconds, and falls back to `web/snapshot.json` and then to
`web/snapshot.js`, which is a plain script tag and therefore loads under
`file://` where `fetch` does not. Query parameters: `address`, `chain`,
`poll`, `tab`, `scanlines=0`.

Each PF key opens a form that writes the exact CLI command for what you filled
in, at a `nomic>` prompt with a blinking block cursor and a copy key. It warns
when a claim is over the cap in rule 202 or a rule is over the character limit,
reading both numbers from the contract rather than hard coding them. The page
stays read only, so no key ever touches it. Every command it produces is one
the CLI accepts as written, quoting and all.

VT323 has a small x-height and reads far smaller than its point size, so every
size on the page is in `rem` and one root rule sets them all: the terminal
scales with the display rather than sitting at a fixed pixel size. Body text is
about 23px on a laptop and 27px on a 1080p screen, and the rulebook pane stacks
under the log below 1180px.

There is no logo. A VT100 had no logos, it had banners, so the title is
"NOMIC" printed in hashes the way a line printer would have done it.

## SDK notes

Written against the runner the testnet serves today,
`py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`, which is
the 0.2.x API: `from genlayer import *`, `gl.Contract`, bare `DynArray`,
`TreeMap` and `allow_storage`.

SDK 0.3.0-rc7 restructures all of this. `gl.Contract` becomes
`gl.contract.Contract`, storage moves to `gl.storage.*`, events move to
`gl.chain.Event`, and the integer aliases stop being callable so the `u32(...)`
wrapping disappears. When the testnet runner moves to 0.3, the changes needed
here are the import block, the storage annotations and the `u32` calls.
`gl.nondet.exec_prompt` and `gl.eq_principle.prompt_comparative` are unchanged
across both.

Two deliberate omissions:

- No events. `gl.chain.Event` is present in 0.3 but the deployed runner is
  0.2.x era, so state is exposed through view methods instead. The frontend
  reads those, so nothing is lost.
- Hashing prefers `hashlib.sha256`, with `Keccak256` as a fallback if a runner
  ever ships without hashlib. Whichever branch runs is recorded on chain in
  `hash_algo`, and `get_canonical_rulebook` returns the exact string that was
  hashed, so anyone can recompute it.

## Status

The contract, the rulebook, the CLI, the tests and the page are complete. What
is not yet done is a deployment with real verdicts, which is what turns the
cost model in `COSTS.md` from a formula with one blank into a measured number.
