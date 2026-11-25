# The first experiment
Can a model reserve five eligible units for a single order when inventory changes between observation and action? We use SQLite and synthetic lots. Observations, writes and transaction rejection come from the database-backed environment. The competing sale is a deterministic test intervention.

## Operational definition
A policy maps a goal and observations to an action. The environment changes state and returns an observation. That observation can change the next decision. A model, bounded action interface and repeated feedback suffice for this experiment. A grader, trace and stop budget make its outcome inspectable. This is a working definition for this project, not a universal definition of agency.

## Sources and decisions
- ReAct studies interleaved reasoning and environment actions. We keep the action/observation interface and record externally observable decisions. Private reasoning transcripts are unnecessary for a state-based grader. [Authors' paper and examples](https://react-lm.github.io/)
- SWE-agent treats the agent-computer interface as a design choice. A reservation capability gives us atomic quantity checks and a small permission boundary. Shell access would add irrelevant actions for this task. [Official ACI documentation](https://swe-agent.com/latest/background/aci/)
- Mini-SWE-Agent's DefaultAgent separates model query, environment execution and observation formatting. We adopt that separation conceptually and implement our own loop. [Upstream source](https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/agents/default.py)
- SWE-bench separates patch generation from evaluation. Our analogous test reads committed inventory with a separate reference allocator. Passing one fixture measures only this task. [SWE-bench](https://www.swebench.com/SWE-bench/)
- Anthropic describes context as a finite inference resource. The whole short trajectory fits a fixed step budget, so we retain it. Longer tasks would require measuring information loss before adding compression. [Engineering article](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- Codex supports noninteractive inference through its CLI. The adapter asks for one JSON action per invocation. Authentication and inference belong to the external client. Dispatch, transaction handling, history, grading and stopping belong here. [Official CLI guide](https://developers.openai.com/codex/noninteractive/)

## Simpler baseline
A deterministic first-expiry-first-out allocator is preferable for this fixed business rule in production. We use the rule as an independent oracle for studying feedback. This release does not establish that a model improves warehouse operations. A later experiment could vary the natural-language request and the inventory independently, with held-out cases and a symbolic baseline.

