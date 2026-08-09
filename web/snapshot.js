window.NOMIC_FALLBACK = {
  "state": {
    "rulebook_version": 1,
    "rulebook_hash": "a06f3b43895bc31febe9d885f0e5d9464e823d37bbc3dfd2ad4791028cc81c4c",
    "hash_algo": "sha256",
    "phase": "CLARIFY",
    "ending": "",
    "winner": "0x0000000000000000000000000000000000000000",
    "winner_name": "",
    "broken_by_proposal": 0,
    "turn": "Alice",
    "turn_address": "0xa1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1",
    "rules_in_force": 10,
    "quorum": 1,
    "open_clarification": 1,
    "moves": 1,
    "versions": 1,
    "page_moves": 50,
    "page_versions": 30,
    "params": {
      "victory_score": 100,
      "max_claim": 6,
      "vote_threshold": 60,
      "max_rules": 16
    },
    "limits": {
      "hard_max_rules": 24,
      "hard_max_rulebook_chars": 12000,
      "max_rule_chars": 500,
      "rulebook_chars": 1448
    }
  },
  "players": [
    {
      "address": "0xa1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1",
      "name": "Alice",
      "score": 0,
      "to_move": true
    },
    {
      "address": "0xb0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0",
      "name": "Bob",
      "score": 0,
      "to_move": false
    }
  ],
  "rules": [
    {"id":101,"text":"Every player must obey the rules in force at the moment a move is submitted. Each rule is either immutable or mutable, and carries a number that is never reused.","immutable":true,"in_force":true,"since_version":1},
    {"id":102,"text":"The rulebook changes only through a proposal that has been voted on and accepted. Nothing else alters the text of a rule.","immutable":true,"in_force":true,"since_version":1},
    {"id":103,"text":"A move is judged against the rulebook version and hash that were fixed before the move was submitted. A rule enacted later never applies to a move that has already been judged.","immutable":true,"in_force":true,"since_version":1},
    {"id":104,"text":"A mutable rule may be amended or repealed. An immutable rule may be neither, until an accepted proposal has first transmuted it into a mutable rule.","immutable":true,"in_force":true,"since_version":1},
    {"id":105,"text":"If the rulebook reaches a state the contract cannot execute, the game ends immediately and the player whose accepted proposal produced that state wins.","immutable":true,"in_force":true,"since_version":1},
    {"id":201,"text":"Players take turns in the order they joined. A turn is one move that was judged legal, or one proposal that has been resolved.","immutable":false,"in_force":true,"since_version":1},
    {"id":202,"text":"On your turn you may claim points by declaring a whole number of points from 1 to 6. A claim outside that range is not legal.","immutable":false,"in_force":true,"since_version":1},
    {"id":203,"text":"A player who holds 100 points or more wins, once that player has claimed the win and the claim has been judged legal.","immutable":false,"in_force":true,"since_version":1},
    {"id":204,"text":"A proposal is accepted when the votes in its favour are at least 60 percent of the votes cast, and at least half the players have voted.","immutable":false,"in_force":true,"since_version":1},
    {"id":205,"text":"At most 16 rules may be in force at once. While the rulebook is full, a proposal to enact a further rule is not legal.","immutable":false,"in_force":true,"since_version":1}
  ],
  "proposals": [
    {
      "id": 1,
      "proposer": "0xa1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1",
      "proposer_name": "Alice",
      "kind": "ENACT",
      "target": 0,
      "text": "A move may not carry a proposal. One or the other, not both.",
      "param": "",
      "value": 0,
      "status": "OPEN",
      "yes": 0,
      "no": 0,
      "opened_at_version": 1,
      "is_clarification": true,
      "ballots": []
    }
  ],
  "moves": [
    {
      "id": 1,
      "player": "0xa1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1",
      "player_name": "Alice",
      "action": "MOVE",
      "text": "I claim five points and, in the same move, propose that claims be doubled.",
      "effect_kind": "CLAIM",
      "effect_value": 5,
      "verdict": "UNDETERMINED",
      "rule_id": 0,
      "rulebook_hash": "a06f3b43895bc31febe9d885f0e5d9464e823d37bbc3dfd2ad4791028cc81c4c",
      "rulebook_version": 1,
      "reasoning_hash": "31651ad00110084ab4667da94212c1f36e168dd4e0d2d86db179aa892b4d41af",
      "citable": 10,
      "proposal": 1,
      "note": "clarification vote opened as proposal 1",
      "outcome": "clarification vote opened as proposal 1"
    }
  ],
  "versions": [
    {
      "version": 1,
      "at": "genesis",
      "by": "",
      "hash": "a06f3b43",
      "full_hash": "a06f3b43895bc31febe9d885f0e5d9464e823d37bbc3dfd2ad4791028cc81c4c",
      "changes": [
        {
          "kind": "added",
          "rule": 0,
          "before": "",
          "after": "Ten starting rules: 101 to 105 immutable, 201 to 205 mutable."
        }
      ]
    }
  ]
};
