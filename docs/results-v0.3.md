# Recomputed v0.3 results

The unit of evaluation is one synthetic dialogue. A fill requires a confirmed SQL change matching the independently expanded gold allocation. Percentages include blocked and refused cases in the all-case denominator.

|Split / method|Unsafe / attempted|Targeted clarification recall|Unnecessary / clear|Initial slots correct|Binary conflict accuracy|Unsupported recall|Verified fills / attempted|Questions per case|
|---|---|---|---|---|---|---|---|---|
|dev A|0/50 (0.0%)|0/30 (0.0%)|0/10 (0.0%)|200/200 (100.0%)|50/50 (100.0%)|10/10 (100.0%)|10/50 (20.0%)|0.00|
|dev B|0/50 (0.0%)|0/30 (0.0%)|0/10 (0.0%)|200/200 (100.0%)|50/50 (100.0%)|10/10 (100.0%)|10/50 (20.0%)|0.00|
|dev C|0/50 (0.0%)|30/30 (100.0%)|0/10 (0.0%)|200/200 (100.0%)|50/50 (100.0%)|10/10 (100.0%)|40/50 (80.0%)|0.60|
|holdout A|0/50 (0.0%)|0/30 (0.0%)|0/10 (0.0%)|200/200 (100.0%)|50/50 (100.0%)|10/10 (100.0%)|10/50 (20.0%)|0.00|
|holdout B|0/50 (0.0%)|0/30 (0.0%)|0/10 (0.0%)|200/200 (100.0%)|50/50 (100.0%)|10/10 (100.0%)|10/50 (20.0%)|0.00|
|holdout C|0/50 (0.0%)|30/30 (100.0%)|0/10 (0.0%)|200/200 (100.0%)|50/50 (100.0%)|10/10 (100.0%)|40/50 (80.0%)|0.60|

|Split / method|Correct refusals|Questions on target|Wrong / all previews|Verified fills / potentially fulfillable|
|---|---:|---:|---:|---:|
|dev A|10|0|0/10|10/40|
|dev B|10|0|0/10|10/40|
|dev C|10|30|0/40|40/40|
|holdout A|10|0|0/10|10/40|
|holdout B|10|0|0/10|10/40|
|holdout C|10|30|0/40|40/40|

|Split / physical batch phase|CLI calls|Order extractions|Input tokens|Output tokens|Cached input tokens|Summed wall seconds|
|---|---:|---:|---:|---:|---:|---:|
|dev initial|5|50|62828|1783|51840|81.15|
|dev followup|5|30|63595|1095|51840|60.46|
|holdout initial|5|50|62861|1767|51840|86.10|
|holdout followup|5|30|63544|1095|51840|65.06|

A used zero model calls. B used initial batches only. C shared those outputs and used the follow-up batches. Cached input is included in input. Physical telemetry cannot be allocated to individual orders. Backend model and monetary cost are unknown.

## Post-hoc control

We enabled the same question-and-answer policy for the rule extractor to check whether the corpus requires an LLM. This control uses no live calls and was added during review after the primary protocol freeze.
- dev: 40 verified fills, 10 correct refusals, 30 targeted questions out of 50 cases.
- holdout: 40 verified fills, 10 correct refusals, 30 targeted questions out of 50 cases.
