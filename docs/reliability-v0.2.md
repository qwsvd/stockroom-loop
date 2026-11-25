# When does feedback pay for itself?

**Finding.** When a legal allocation failed because its observation was stale, one new observation let the same deterministic allocator reach a verified terminal state on every such held-out case. In this generator there is exactly one opportunity for supply to decrease. The result measures the benefit of observing after rejection under that specific intervention.

## Evidence and reproducibility

Protocol commit fc808d6 precedes the experiment. Generator, prompt and policy freeze dcc2df9 precedes the held-out run. Development comprised 100 separate seeds; the final paired study used 1,000 new seeds. One run per policy per seed, same snapshot and depletion. The model got the first three preselected held-out cases. No additional model runs or prompt revisions followed. Data cover synthetic integer expiry days, 3–8 lots, four target products, variable quantities, earliest/latest priority, equal-expiry ties, ineligible supply and shortages. Generated combinations are new to this experiment; model pretraining exposure is unknowable.

Run `python evaluate.py dev`, `python evaluate.py holdout`, `python replay.py` and `python report.py` offline. The two gzip JSONL files store every A/B action, observation, terminal ledger, counters and original run time. Regenerate with `python evaluate.py holdout --generate fresh.jsonl.gz`; compare outcomes, excluding timestamps and elapsed times. Live records contain the replies and CLI usage fields. The code can start a new live campaign with `python live_study.py NEW.jsonl` under an existing authorized ChatGPT login. The published data suffice for all offline checks.

## Verified observations

| Holdout policy | Correct / failed | Filled / correct shortage | Wrong or rejected actions / illegal | Recovered | Decisions / tools | Mean steps among successes | Sum of task seconds |
|---|---:|---:|---:|---:|---:|---:|---:|
| Initial fixed plan | 561 / 439 | 311 / 250 | 439 / 0 | 0 | 2000 / 1750 | 2.000 | 0.026 |
| Same planner with feedback | 1000 / 0 | 461 / 539 | 439 / 0 | 439 | 2878 / 2339 | 2.878 | 0.041 |

A/B success rates were 56.1% and 100%; failure rates were 43.9% and 0%. Both used zero model decisions. The extra 439 successes comprised 150 additional fills and 289 correct shortage declarations. Every additional success required two extra decisions, an inspection and a terminal decision. A well-formed but stale request counts as a rejected action. It counts toward errors without implying irrational planning. A terminal shortage declaration has no tool call. Timings measure the in-process loop, exclude case generation and disk I/O, and depend on this Windows host.

| Preassigned intervention (250 cases each) | Fixed successes | Adaptive successes |
|---|---:|---:|
| Steady and feasible | 250 | 250 |
| First two priority lots depleted | 0 | 250 |
| Steady and insufficient | 250 | 250 |
| Random quantities lost across lots | 61 | 250 |

The development sample gave 60/100 and 100/100 respectively. The four equal-sized strata were designed, not sampled from warehouse traffic. The overall percentages depend on that weighting. The two policies used identical initial planning and terminal grading. Returning a legal allocation is guarded by an atomic in-memory check. This study does not use its synthetic sale as evidence of threaded concurrency.

### Three live tasks, retained in order

| Seed | Fixed / adaptive / Codex | Codex decisions / tools | Errors / illegal / recoveries | Input / cached input / output tokens | Seconds |
|---|---|---|---|---|---:|
| 10000 | filled / filled / filled | 2 / 2 | 0 / 0 / 0 | 24501 / 20736 / 25 | 41.44 |
| 10001 | rejected / shortage / shortage | 4 / 3 | 1 / 0 / 1 | 49048 / 41472 / 44 | 89.44 |
| 10002 | shortage / shortage / shortage | 2 / 1 | 0 / 0 / 0 | 24436 / 20736 / 19 | 39.88 |

The model's submission on seed 10001 selected one unit of rice from L0. After rejection it inspected both eligible lots, observed zero remaining and declared shortage. Seed 10009 gives a different offline recovery: the fixed plan failed, the adaptive plan filled the order. Inspect the full compressed rows by loading the file with Python's gzip.open and filtering the JSON seed. All 439 fixed-policy failures remain available.

Live task success was 3/3, failure 0/3, mean 2.67 decisions, 170.76 total seconds. This is exploratory. The deterministic policy reached the same three outcomes. The CLI reported 97,985 input tokens (82,944 cached, included in input), 88 output tokens and zero reported reasoning tokens. Monetary cost, remaining subscription capacity, backend identity and internal request count are unknown. Erratum after release: all three archived rows record codex-cli 0.171.0-alpha.13.2 from the native executable used for inference under ChatGPT login. The 0.144.6 figure was the separately inspected CLI/source tag. Neither version identifies the hosted model. The adapter captured numeric usage and final replies but did not persist model routing notifications. A review after collection tightened provider-error stopping and distinguished HTTP 429 from a token count ending in 429. These changes did not trigger additional trials. Reported token counts include client context.

### Independent verification and contention

The planner sorts lots and greedily fills. The grader instead checks per-lot conservation, eligibility, total and the absence of a better unused unit when a worse unit was reserved. A hand-authored fixture has opposite answers for earliest/latest and ties resolved by ID. Tests enumerate all candidate allocations for this fixture and compare acceptance with the lexicographically maximal feasible count vector. Another reference expands individual units for 100 development seeds. Mutating an untouched row invalidates a correct outcome. The generator, policy and grader still share field meanings and a definition of valid dates. External domain review remains valuable.

Two separate SQLite tests use the original v0.1 conditional UPDATE on one file. Two independent connections in separate threads first see the same stock, synchronize, then compete for the same lot or for the order-wide capacity on different lots. Each case has one winner and four total held. A second test deliberately holds an uncommitted write transaction. An independent reader still sees committed stock, its zero-timeout write raises SQLITE_BUSY, and after the first writer commits the stale reservation fails. This demonstrates observable lock contention and the need to distinguish transient locks from business rejection. The evidence covers one SQLite configuration, a single order and same-host connections. It does not establish crash safety, fairness or multi-order correctness. [SQLite isolation](https://sqlite.org/isolation.html)

## Inferences, hypotheses and unknowns

**Inference.** With explicit structured rules and monotone depletion, checking again only after rejection saves inspections on steady cases. Once the single shock has happened, B sees final supply. It can either compute a valid allocation or establish shortage. The problem construction makes that strategy unusually favorable. A policy that blindly retries identical rejected quantities would lack that information.

**Hypothesis.** Natural-language ambiguity is a more credible role for a model here than exact arithmetic. Next compare a deterministic parser and a model constraint extractor on human-authored ambiguous orders under a fixed downstream allocator. Prelabel which orders need clarification, split by template family, count unsafe fills and unnecessary questions. Freeze before sampling and match the inference budget. Stage this before testing a general hybrid architecture.

**Unknown.** Generalization to new rules, repeated shocks, additions, ambiguous instructions, write timeouts with unknown commit status, and environments where observation is expensive. Unknown whether a new model sample would reproduce these trajectories. The live arm changes policy type and cannot isolate a model-only feedback effect.

## Architecture decisions

| Decision | Evidence and boundary |
|---|---|
| Keep a task-specific loop and explicit tool schemas | Three operations sufficed here. The old fixture stays runnable for historical comparisons. No demonstrated requirement for a generic runtime, registry or MCP transport. |
| Use structured orders, atomic submission and a separate evaluator | Pairing needs a precise contract. Atomicity avoids partial holds. The legacy and new task interfaces differ; their step counts cannot be directly attributed to better reasoning. |
| Keep the deterministic planner as a baseline | It passed all 1,000 held-out cases. A separate learned planner or multi-agent coordination would need a new task with a measurable deficit. |
| Keep short histories | At most nine decisions. No measured information loss or need for persistent memory or context compression. Token usage suggests testing smaller context and fewer CLI invocations before adding machinery. |
| Defer a hybrid | These orders already encode the rules. Ambiguity, clarification and refusal need their own labeled benchmark before building a language front end. |
| Stop or ask | Within this contract: stop on verified completion, budget exhaustion or provider stop. Decline malformed/unauthorized actions before changing stock. In a future interface, ask the owner when priority or substitution is unspecified; no user clarification action was evaluated here. |
| Duplicate writes | A successful atomic submission terminates this in-memory run. Durable retries after ambiguous timeouts require idempotency and reconciliation. This release does not establish them. |
