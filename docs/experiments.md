# Experiment record · 2026-11-25

Windows, Python 3.14.3, Codex CLI 0.144.6, ChatGPT login. All public task inputs are synthetic. The CLI selected its default model. We did not record a backend model identifier, seed, sampling settings, account balance or token count. Source commit feeb034 contains the original prompt. The release changes the reservation grammar and batching guidance.

|Run |Policy |Budget |Observed result |
|---|---|---:|---|
|[Short run](../evidence/live-short.json) |Live Codex, original prompt |1 |Inspected the lots and stopped at the limit. Zero units held. |
|[First full run](../evidence/live-race-original.json) |Live Codex, original prompt |9 |Alternated unit reservations and inspections. Held four units when the budget expired. |
|[Revised full run](../evidence/live-race.json) |Live Codex, revised prompt |9 |Seven decisions. A stale four-unit reservation failed. A new inspection revealed one unit left in H4. Reserved one there and four in B7. The grader accepted finish. |
|Fixed-plan control, steady |Scripted |3 |H4 × 4 then B7 × 1 passed. |
|Same fixed plan, race |Scripted |3 |H4 × 4 failed. B7 × 1 succeeded. Finish failed state verification. |

The two full live runs share stock, external sale, goal quantity and decision budget. The original example gave a quantity of 1. The revision names the legal range and asks for batching. We observed different decisions on two samples. Stochastic inference and unpinned backend routing confound causal attribution. Neither a general success rate nor a prompt improvement estimate follows from these runs.

## Recheck the evidence

Run `python -m unittest -v` for eight deterministic test methods, including paired scenarios, failed updates, wrong SKU, expiry, malformed requests, fractional and boolean quantities, budget enforcement, timed-out policy and corruption of an unrelated row. The scripted feedback case checks the observation received by the next policy invocation.

Run `python replay.py` to execute the saved decisions and compare the observations, status, sale and final rows against each live trace. Replay verifies consistency with the environment; it cannot independently authenticate the provider or reproduce stochastic choices. Running `python demo.py --policy codex` obtains a new trajectory. The fixture and traces are public, so they cannot serve as a blind capability benchmark.

## Open questions

- Does batching guidance reduce calls across unseen stock levels and order sizes? Randomize instances, assign prompts in randomized order, publish all attempts and compare with a rule-based allocator.
- Can the grader catch errors it shares with the environment? Both depend on the same seed and date. Add externally reviewed golden fixtures, including ties and impossible orders, before broadening scope.
- What happens after an ambiguous write timeout in a persistent store? Study idempotent reservation IDs and reconciliation before attaching real services. This release has one process, one order and no crash recovery.
- Would reduced context help? Compare full history with the current snapshot plus the last failed action under identical budgets. Track decision count, success and invalid operations, including the cost of obtaining each snapshot.
