# Stockroom Loop

A small AI agent that reserves inventory, observes the result of each transaction and decides what to do next. A separate grader reads every lot when the policy signals completion. The experiment asks whether a language model can finish an order when its first view of stock becomes stale.

[简体中文与源码阅读指南](README.zh-CN.md) · [Design and sources](docs/design.md) · [Experiment log](docs/experiments.md)

## v0.3 Chinese orders, clarification and consent

Try `python order_demo.py` for an offline Chinese dialogue. Enter `请预留茶，有效期不早于2026-12-01，优先早到期。`, answer the quantity question with `要3件`, then inspect the exact preview before entering its confirmation code. Add `--model` for real language extraction with your existing ChatGPT login. The default interactive rules mode can ask questions. Benchmark A deliberately uses those rules in single-pass mode.

The language interface supports one product, an integer quantity, a minimum expiry date and an expiry priority. It accepts known Chinese clause forms. Unknown clauses block execution. Each session has a fresh SQLite fixture. The extractor can propose fields or select a clarification target. Only a separate user confirmation can cause a reservation. A revised order invalidates the previous preview. The transaction checks actual database rows using the v0.2 grader before commit.

[Architecture and frozen protocol](docs/protocol-v0.3.md) · [Study findings and limitations](docs/clarification-v0.3.md) · [Recomputed metrics](docs/results-v0.3.md) · [Synthetic inputs, model replies and traces](evidence/v03) · [Chinese tutorial](docs/learning/clarification-from-zero.md)

## v0.2 reliability study

On 1,000 paired held-out synthetic orders, a fixed initial plan reached 561 correct terminal states. The same allocator with reobservation reached 1,000, including 539 correct shortage declarations. Three exploratory live Codex runs matched the adaptive allocator on the same three orders. One recovered from a rejected stale reservation. [Results, failure cases and limits](docs/reliability-v0.2.md) · [Frozen protocol](docs/protocol-v0.2.md) · [Audit of v0.1](docs/audit-v0.1.0.md).

The v0.2 study uses atomic in-memory order submission. Separate independent-connection tests exercise the original SQLite statement. The original demo and evidence remain available below. [Read the Codex client source](docs/learning/codex-source-map.md) · [Beginner guide](docs/learning/agent-from-zero.md) · [Handwriting exercises](exercises/README.md).

## Reproduce in a minute

With Git and Python 3.11+ installed, run:

```sh
git clone https://github.com/qwsvd/stockroom-loop.git
cd stockroom-loop
git checkout v0.3.0
python -m unittest -v
python replay.py
python evaluate.py dev
python evaluate.py holdout
python report.py
python order_eval.py
python order_report.py
```

The tests include scripted policies and independent SQLite connections. Legacy replay applies saved decisions to new databases. The two evaluate commands reproduce the v0.2 paired trials. Its report checks trajectories and usage totals. The two order commands replay v0.3 against fresh databases and calculate its metrics. All checks work offline after cloning with standard Python.

To run fresh inference, use a compatible Codex CLI (tested with 0.144.6) already signed in with ChatGPT. Check your quota in the client before running. This adapter uses the existing login and requires its English login-status confirmation. It starts a fresh ephemeral CLI process for each action and sends the goal and public trajectory.

```sh
codex login status
python demo.py --policy codex
```

For a human-operated demonstration, run `python demo.py --policy stdio` and enter one action per line. Start with `{"op":"inspect"}`. Use `--steady` to remove the competing sale or `--steps 1` to exercise budget exhaustion. The final JSON goes to stdout. Exit code 0 means verified success. Code 1 indicates an unsuccessful run. Argument or login errors can also terminate the CLI before a trace is produced.

## What executes in the original SQLite demo

1. `agent.run` sends the task and previous actions/observations to a policy.
2. `demo.codex` obtains a single proposed JSON action via the external Codex client. The policy sees a textual tool protocol, without native provider function calling.
3. `Stockroom.act` accepts inspect or a bounded, parameterized reservation. On the first well-formed reservation in race mode, a separate transaction consumes three units of the earliest lot. The triggering reservation then succeeds or fails against current stock.
4. A rejected action returns feedback. A finish action invokes `verified`, which reconstructs the correct allocation from initial supply and the recorded sale. It compares every row, including untouched lots. Invalid output consumes a step. Provider failure and budget exhaustion stop the run.

## Scope and trust

The demonstration uses fictional lots and a real, ephemeral SQLite database. The order rule is earliest valid expiry first. Changes disappear when the process exits. This is a single-order research fixture with a scheduled external sale, without independent warehouse clients or durable inventory. A mistaken eligible reservation can make the goal unreachable because this interface has no undo.

A policy can inspect only the fixture or request a reservation through the application. The CLI adapter runs in a temporary directory, requests read-only sandboxing, ignores user configuration and disables shell, web search, plugins, apps and multi-agent capabilities. It relies on the installed client and host security. Use synthetic data with this adapter. A separate OS sandbox would be appropriate before connecting sensitive sources. The application allows 9 decisions by default, at most 12, a 120-second subprocess timeout per decision and 1,024 characters per accepted reply. Interactive stdin waits for its operator. Provider-side token usage and remaining subscription allowance are outside the harness.

The runtime uses Python's standard library. GitHub Actions uses commit-pinned official actions and read-only repository permissions. CI performs offline tests without model credentials. The MIT license covers this repository. Python, SQLite, Codex and hosted inference are provided separately. The published traces contain synthetic task data.

## Attribution and research

The project owner defined the research brief, constraints and acceptance criteria. Codex researched, designed, implemented, tested and documented this release. Independent execution or mastery by the owner has not been established. Report a reproducible problem in GitHub Issues with the version, policy, scenario, status and a sanitized trace.
