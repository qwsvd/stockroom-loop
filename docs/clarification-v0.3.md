# What did asking a question change?

On 50 held-out synthetic Chinese orders, single-pass extraction produced ten verified fills. Enabling one targeted question and supplying the scripted answer produced forty verified fills. Both policies used the **same actual first model response** for each order. There were ten correct refusals in each arm. A deterministic rule extractor with the same clarification opportunity also reached forty fills. The incremental capability demonstrated here is the opportunity to obtain missing user information under a narrowly specified contract. This corpus provides no evidence of an LLM-specific fulfillment advantage.

## What actually ran

- Checked out the v0.2 release, examined the structured allocator, grader, policy adapter, SQL contention tests, protocol, evidence and known limits, ran the full offline suite, and corrected an attribution error. All three archived v0.2 records identify the native inference executable as codex-cli 0.171.0-alpha.13.2. The source study covers rust-v0.144.6. The existing release tags and raw evidence retain their historical contents.
- Frozen protocol: commit 15a6aeb. Frozen 100 distinct authored stimuli and inference code: 52cd040. Ten examples per class per split. No human or company supplied these orders, labels or answers. Different phrasings distinguish the two splits; both use the same constrained language design. Data were authored by the implementer and were never a blind external benchmark.
- A ran offline. B and C used real Codex calls under an existing ChatGPT login. C shared ten initial batches with B and made ten additional follow-up batch calls. Across both splits there were 100 initial and 60 follow-up extractions, 252,828 input tokens (207,360 cached), 5,740 output tokens, and 292.77 seconds of summed request wall time. The recorded native CLI was codex-cli 0.171.0-alpha.13.2. The backend model identifier, network retry count, monetary cost and per-case token consumption are unknown.
- The user and stock were simulated. The application really executed SQLite transactions and verified their resulting rows. Each method/case pair got a fresh fixture. Questions are rendered from the selected target using fixed Chinese wording. Only the evaluation driver reads labels and scripted user replies; the model receives an array of dialogues. Batch neighbors are visible to the model, an additional limitation on treating cases as independent.
- The published 300 primary trajectories include previews, question targets, actual scripted answers, confirmation decisions, terminal state and all final rows. Ephemeral confirmation nonces are omitted. One record per physical inference preserves the exact reply, inputs, CLI and service-reported usage. All primary replies parse identically under the collection parser and the stricter duplicate-key check used in release replay. Study inputs and prompts were unchanged.

[Predeclared design and denominators](protocol-v0.3.md) · [Data integrity note](v03-freeze-note.md) · [Computed results](results-v0.3.md) · [Raw evidence](../evidence/v03/)

## Inspect one decision and one failure

H03 requested soap, gave two possible quantities (six or seven), set a minimum date and specified latest expiry first. B identified the quantity ambiguity and stopped. C asked for quantity. The script supplied a complete replacement choosing six, the preview matched that authorization and the SQL reservation passed both graders. H05 additionally asked for delivery; the system refused the whole request. H05 contributes zero fills.

A and B both left 30 potentially fulfillable held-out orders unresolved. That is a safe abstention and a failed fulfillment opportunity. There was no wrong committed execution in the primary corpus and no terminal model failure in C. Manufacturing one would distort the result.

An additional executable scope test uses the clear paraphrase “茶要三件，至少能放到2026年12月2日，先挑快到期的。” Even when supplied its **correct** structured proposal, the deterministic language guard refuses it. This is an observed coverage failure with a supplied proposal, outside the labeled corpus. No live model was invoked for that probe. Other fault tests inject malformed JSON, wrong types, missing fields, stale confirmation and a rejecting grader. A failed post-update check rolls the SQL transaction back.

## What keeps a proposal from becoming an unauthorized write?

The executable language is deliberately narrow. The guard covers whole clauses, checks the four types/ranges, resolves date validity, compares independent text evidence against the complete proposal and detects incompatible or insufficient constraints. A has access to this same rule grammar directly. A production claim about unrestricted Chinese understanding would require a different evaluation. Unsupported or unrecognized clauses stop fulfillment.

Every edit invalidates pending consent. A preview is bound to a private session nonce and current typed order. The model has no confirmation or database action in its interface. SQL changes occur only upon a separate exact operator confirmation. The v0.2 planner computes quantities, the market checks the planned submission, the grader checks actual transactional SQL rows, and the evaluation harness separately expands eligible units to verify the committed ledger against the labeled order. Only the synthetic fixture is initialized before confirmation.

The interactive CLI can accept one short, explicit answer when exactly one known slot remains. Ambiguous replies do not authorize changes. A complete explicit replacement begins with “重下：”. The live benchmark tested full replacement answers only. Inventory lives for one session. The trust boundary includes the Python program, Codex client and host. There is no authentication service for external users, durable identity, or production shipment integration.

## Interpretation and next experiment

**Verified:** for these templates all three extractors got all initial slots right. C made 30 necessary questions on each split, no unnecessary questions on clear inputs, and all 80 fulfillable orders across the splits were filled after consent. Refusals were graded separately. The post-hoc rule-plus-clarification control matched C with zero model calls.

**Inference:** useful clarification recovered information absent from the request. The experiment makes recovery easy: a correct target unlocks a perfect full restatement, and a perfect simulated user withholds confirmation for wrong previews. The unsafe execution rate of zero under these conditions cannot establish a real-world failure probability. The Python guard and rule baseline share vocabulary with the corpus.

**Unknown:** performance on previously unseen constructions, user fatigue, wrong confirmations, noisy short replies, changing preferences, multi-intent orders, model routing and independent human judgments of question quality.

**Next investment:** collect consented, independently authored Chinese paraphrases and partial replies. Freeze labels before model access; measure false refusal of valid orders alongside unsafe proposals. Compare a rule question policy against a model question policy with the *same* confirmation behavior, including unanswered or mistaken replies. This addresses the observed coverage failure before expanding the tool surface.
