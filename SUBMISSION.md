# Submission notes

Category: **Projects**. This is a complete application with a user facing flow,
not a contract on its own.

---

## Opening

This contract enforces rule text that did not exist when it was deployed, and
it does so without trusting any one model to be the judge. Nomic players hunt
for holes in the rules, so a single LLM arbiter becomes the hole: the rulebook
turns into a collection of jailbreaks against that model and the game dies.
Consensus across independent validators is the only thing that makes the
arbiter unbribable, and an unbribable arbiter is the only thing that makes this
game playable.

The design decision I would lead with is the third verdict. Alongside legal and
illegal there is **UNDETERMINED**, meaning the rulebook does not settle the
question. It is not an error state and it is never collapsed into illegal. It
opens a clarification vote and freezes the turn, which is how disputed
interpretations get resolved in the paper game too. Non-determinism is absorbed
into the gameplay instead of being hidden from it.

## Why it is not a thin wrapper

The contract answers one bounded question: is this move legal under rulebook
version N, whose hash was fixed on chain before the move was submitted. It does
not score quality and it has no taste.

- The output is an enum, the number of the rule that decided it, and a hash of
  the reasoning. Consensus compares the verdict, the rule number and the
  rulebook hash. No prose is ever compared, so the equivalence principle is a
  real one rather than a decorative one. It is published on chain and readable
  with `nomic principle`.
- The model never performs a state change. A legal verdict hands off to a
  deterministic branch that applies the declared effect; a passed amendment
  hands off to a deterministic branch that rewrites the rulebook. The model
  decides permission, the contract decides consequence.
- Turn order, effect ranges, vote tallies and the terminal states are all
  deterministic. Roughly half the transactions in a game cost no inference at
  all.

## Three stages

| stage | kind | does |
| --- | --- | --- |
| A | deterministic | pins the rulebook hash, version, move text and the rule ids that may be cited; checks turn and ranges before any inference |
| B | non deterministic | one judge call, output normalised to four fields, compared under `prompt_comparative` on three of them |
| C | deterministic | applies the effect, or opens the clarification vote, or ends the game |

## What is built

- Intelligent Contract with rulebook, versioning, proposals, votes, three stage
  adjudication and two terminal states
- Ten starting rules, five immutable and five mutable, with the reasoning for
  each written up in `rules/genesis.md`
- CLI for moves, proposals, votes and reading state
- Read only page built as the terminal a 1982 game would have been played on,
  a DEC VT100: player roster, queue of votable proposals, move log, and the
  rulebook. Monochrome, so the three verdicts use the three character
  attributes the terminal actually had, and UNDETERMINED is the one blinking
  thing on the screen
- Amendment history on chain, so any past version of the rulebook can be read
  back and diffed, and the page can show what each version actually changed
- 34 off chain tests covering both deterministic stages, with Stage B scripted
  so verdicts can be forced, plus an end to end test of the page in a real DOM

## Three problems and what was done about them

**The rulebook outgrows the prompt.** Two options: cap and force repeal, or
retrieve only the rules a move plausibly touches. Retrieval was rejected
because omitting a rule from the prompt is indistinguishable from repealing it,
which would make the retriever the most attractive target in the game. So the
whole rulebook always goes in and it is capped instead: 16 rules by rule 205,
24 as the machinery limit. Measured prompt sizes are 3843 characters at
genesis, 6995 at the rule cap, 14505 at the machinery limit.

**A rule the machinery cannot execute.** In Nomic this is a legitimate win, so
it is rule 105 and it is implemented as an ending rather than an exception.
When a proposal passes and Stage C cannot execute it, the game enters a
terminal state recording how it broke, and the proposer wins. The break
surfaces are deliberate and reachable: raising the rule cap past what the judge
can be given, amending an untransmuted immutable rule, enacting into a full
rulebook.

**Prompt injection through player text.** Fenced with a marker derived from the
current rulebook hash, labelled as evidence under examination. That is a speed
bump. The defence is the equivalence principle: an injection has to flip the
verdict and the rule number identically across validators running different
models, or it fails consensus instead of winning the game.

## Judged behaviour, measured before deployment

`scripts/calibrate.py` builds the real Stage B prompts from the contract's own
Stage A and scores twelve cases: four where the rulebook is genuinely silent,
two prompt injections, and six with a clear answer. Run across two models it
gives the divergence rate, which is the on chain appeal rate, and it answers
the question that decides the project, which is whether UNDETERMINED fires at
all rather than being a verdict the judge never reaches for.

## Cost

Roughly 54 adjudicated actions in a full game, about 450,000 prompt tokens at a
validator set of five, spread across days of asynchronous play. Full working in
`COSTS.md`, including which actions cost nothing and three optimisations that
were considered and rejected.

## Slow consensus is not a cost here

The game is turn based and asynchronous, like correspondence chess. Fifteen
minutes per move is a normal pace. This is the rare project where the latency
needs no excuse.

## Status and what is next

The contract, rulebook, CLI, tests and page are complete. Not yet done: a
deployment with real verdicts, which is what turns the cost model from a
formula with one blank into a measured number, and a recorded game to use as
the demo.

Next, in order: deploy, play a three player game to a rule 105 ending, record
it, fill the cost table from the receipts.

---

## Checklist before posting

- [ ] Deploy and put the address in the submission
- [ ] Play a game far enough to produce at least one UNDETERMINED verdict and
      one clarification vote, since that is the thing to demonstrate
- [ ] Record a demo video, opening on the move log rather than on an
      explanation of Nomic
- [ ] Host the read only page and link it with `?address=`
- [ ] Fill the cost table from a real receipt
- [ ] Run `scripts/snapshot.sh` on a timer so the hosted page keeps up
- [ ] Confirm the submission opens on the consensus design and the third
      verdict, not on a description of Nomic
