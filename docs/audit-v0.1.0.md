# Independent re-examination of v0.1.0

Reviewed the complete tree at 4910573a272a5870fcd6501be449f3e75b28a77b before designing the successor. Re-ran all eight tests and all three replays on Python 3.14.3. The two failures still end at their step limit, the seven-step trace still passes. This is a fresh technical review by the original AI implementer. It has no independent human reviewer.

| Component | What inspection and replay establish | Boundary or defect |
|---|---|---|
| agent.py | One policy call per step, textual JSON, retained history, validated finish and a step limit. | No observation freshness guarantee. A repeated valid reserve can apply twice. A bad earlier choice may be irreversible. A supplied Python policy is trusted code. |
| stockroom.py | A conditional SQL update changes available and held together. Eligibility and aggregate order capacity are predicates in that statement. | A synchronous sale commits on the very same in-memory connection before reservation. There is no overlapping transaction, competing process or lock contention here. |
| verified | Recomputes an expected allocation independently of SQL dispatch and checks untouched rows too. | Both sides trust SEED, ORDER, DATE, the sale field and snapshot reader. A common misinterpretation of eligibility or a defective snapshot can hide errors. Tests rarely vary the business rule. |
| demo.py | The model receives goal and history in a fresh CLI process. Tool use is textual. Exit and timeout can become provider_error. | stdout and stderr are discarded. No observed backend identity, usage, rate-limit signal or retry count is retained. A subprocess timeout on Windows wrappers does not establish descendant termination. Read-only mode and disabled features rely on the external client. |
| replay.py and evidence | Reapplies the three saved action streams and compares every recorded outcome. | Assumes an action at every step, so malformed replies and provider errors cannot generally be replayed. Replay authenticates neither origin nor inference. A requested model name would establish only requested identity. |
| test_agent.py | Covers malformed actions, policy timeout, fixed plans, grading and delivery of observations. | The feedback test uses a predetermined script. No unknown instance, genuinely adaptive baseline, independent connection or adversarial grader mutation is exercised. |
| CI, docs, license | Commit-pinned read-only CI runs offline on two OSes. README discloses synthetic data and AI authorship. MIT covers the repository. | CI replays a few historical decisions. It measures neither live provider reliability nor production suitability. |

**Observed.** The first nine-step trace held four units. The second held five after a rejected stale request. The revised prompt and a fresh model draw changed together. No matched live open-loop arm exists.

**Inference.** These results support existence of feedback-based recovery on this fixture. They cannot isolate the effect of prompt wording, model randomness or the loop. SQLite serializes writers by design, but the existing tests give no evidence about the particular statement across connections. [SQLite isolation](https://sqlite.org/isolation.html)

**Hypothesis.** Atomic whole-order submission could avoid irreversible partial holds and reduce inference calls. It changes the action space, so old and new step counts would not measure a pure algorithm improvement.

**Unknown.** Model weights, server routing, retry behavior in these historical trials, transfer to unseen tasks, effects of compaction and production contention. Keep the legacy fixture, evidence and replay as historical controls. Introduce a separate paired experiment and an actual connection-contention test. Retain standard-library dependencies and the existing two-platform CI.
