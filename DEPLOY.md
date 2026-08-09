# Deploy

Everything else is done. This is the only part that needs a key.

## 1. Tools

```
npm install -g genlayer
genlayer network list          # confirm what Bradbury is called on your CLI
genlayer network set <name>
genlayer account create --name alice
```

Fund the account from the faucet before deploying. Create one named account
per player now, they are needed in step 4:

```
genlayer account create --name bob
genlayer account list
```

## 2. Check the runner before you spend anything

The contract header pins the runner the testnet serves today:

```
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
```

If deployment fails on the runner hash, the testnet has moved to SDK 0.3. The
changes needed are listed under "SDK notes" in the README: the import block,
the storage annotations and the `u32(...)` wrapping. Nothing else moves.

## 3. Measure the judge before you spend anything

This is the step I would not skip. Two things decide whether the game works and
neither can be tested off chain by asserting on code: whether UNDETERMINED is
reachable at all, and whether two independent judges return the same verdict
and rule id. The battery builds the real Stage B prompts from the contract's own
Stage A and scores them.

```
python3 scripts/calibrate.py                    # writes 12 prompts to calibration/
ANTHROPIC_API_KEY=... python3 scripts/calibrate.py --run \
    --models <model-a>,<model-b> --repeats 3
```

Read three numbers at the bottom:

- **UNDETERMINED reachable.** Four cases in the battery are ones where the
  rulebook is genuinely silent. If none of them fire, the central mechanic is
  dead, and the fix is in `build_prompt` in the contract, not on chain.
- **Unanimous across judges.** Rows marked `!` are ones where judges disagreed
  on verdict or rule id. On chain those go to appeal. A few are fine, a lot
  means the equivalence principle is being asked for more agreement than the
  models can give.
- **Matched the rulebook.** Sanity only. The two injection cases must come back
  ILLEGAL citing rule 202; if either returns LEGAL, stop and fix the fencing.

This costs a few cents and can save a deployment.

## 4. Deploy

```
genlayer deploy --contract contracts/nomic.py
export NOMIC_ADDRESS=0x...
```

Sanity check before anyone joins:

```
python3 cli/nomic.py state
python3 cli/nomic.py rules
python3 cli/nomic.py history
```

You should see rulebook v1, ten rules, five immutable and five mutable, and a
single history entry saying genesis. Confirm the hash is reproducible:

```
python3 cli/nomic.py canonical | sha256sum
python3 cli/nomic.py state | grep hash
```

Those two must match. If they do, Stage A is pinning what it claims to pin.

## 5. Seat the players

Joining closes as soon as the first move is made, so seat everyone first. On
one machine, `--account` switches between the named keystores:

```
python3 cli/nomic.py --account alice join "Alice"
python3 cli/nomic.py --account bob   join "Bob"
```

On separate machines, drop the flag and use each machine's active account.
Two players minimum, eight maximum. Note that joining is open to anyone who
knows the address until the first move lands, so make the first move promptly
if the address is public.

## 6. Play far enough to be worth showing

The submission needs one UNDETERMINED verdict on the record, because that is
the thing to demonstrate. The move that reliably produces one is a move whose
legality the rulebook genuinely does not settle:

```
python3 cli/nomic.py --account alice move \
  "I claim five points and, in the same move, propose that claims be doubled." \
  --claim 5 \
  --clarify "A move may not carry a proposal. One or the other, not both."
```

No rule says whether a move may carry a proposal, so the judge should return
UNDETERMINED, freeze the turn and open a clarification vote. Then:

```
python3 cli/nomic.py --account alice vote 1 yes
python3 cli/nomic.py --account bob   vote 1 yes
python3 cli/nomic.py --account alice resolve 1
python3 cli/nomic.py history         # the new rule appears as version 2
```

Replaying the same move against the amended rulebook should now come back with
a definite verdict. That sequence, an unsettled move becoming a settled one
because the players legislated, is the demo.

## 7. Cost

Take the receipt for one `submit_move` and fill the single blank in `COSTS.md`:

```
genlayer receipt <tx hash>
```

## 8. Publish the page

Live, straight from the contract:

```
python3 -m http.server -d web 8080
# http://localhost:8080/?address=0xYOUR_ADDRESS
```

Hosted as a static page, refreshed from chain on a timer:

```
scripts/snapshot.sh                  # writes web/snapshot.json and web/snapshot.js
*/10 * * * * cd /path/to/nomic && NOMIC_ADDRESS=0x... scripts/snapshot.sh
```

Then upload `web/` anywhere static and point `playnomic.xyz` at it, since that
is the address the end card gives out. The page falls back to the snapshot when
it cannot reach the chain, so it never shows an empty screen.

If the host serves `index.html` without the query string, add a redirect or
commit a one line `index.html` that forwards to `?address=0x...`, otherwise a
visitor sees the snapshot rather than the live game.

Query parameters: `address`, `chain` (default bradbury), `poll` in seconds
(default 20), `tab` (rules or diff), `scanlines=0` to turn off the CRT effect
for a cleaner recording.

## 9. Record the demo

`DEMO.md` is the shot list, the setup commands that put the game in the right
state before recording, and the Suno prompt. `DEMO.srt` is the subtitle track,
timed to those shots. The cards need no editing beyond the recording itself:

```
web/intro.html        about 8 seconds, click or press R to retake
web/outro.html        about 5 seconds, carries the source and playnomic.xyz
```

Record at 1920 by 1080 with the browser in full screen. `?speed=2` shortens
either card if the cut needs to be tighter. Between them, screen record the
live page with the UNDETERMINED move on screen: open that row in the log so the
three stage trace and the vote it opened are both visible. That single frame is
the argument for the whole project.

Add `?scanlines=0` to the live page if the CRT effect fights with the video
codec.

## 10. Submit

Work through the checklist at the bottom of `SUBMISSION.md`. The two things
that matter most: open on the consensus design and the third verdict rather
than on an explanation of Nomic, and put the UNDETERMINED move on screen in the
first few seconds of the demo video.
