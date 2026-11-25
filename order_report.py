"""Render the v0.3 study tables from archived replies, authoritative labels and SQL replays."""
from order_eval import ROOT, evidence, metrics, paired, read, replay


def ratio(a,b):
    return f"{a}/{b} ({100*a/b:.1f}%)" if b else "0/0 (undefined)"


def render():
    cases=read(ROOT/"orders.jsonl")
    calls=read(ROOT/"calls.jsonl")
    rows=replay(cases,calls)
    lookup={c["id"]:c for c in cases}
    lines=["# Recomputed v0.3 results", "",
           "The unit of evaluation is one synthetic dialogue. A fill requires a confirmed SQL change matching the independently expanded gold allocation. Percentages include blocked and refused cases in the all-case denominator.","",
           "|Split / method|Unsafe / attempted|Targeted clarification recall|Unnecessary / clear|Initial slots correct|Binary conflict accuracy|Unsupported recall|Verified fills / attempted|Questions per case|",
           "|---|---|---|---|---|---|---|---|---|"]
    for split in ("dev","holdout"):
        for method in "ABC":
            m=metrics([r for r in rows if (r["split"],r["method"])==(split,method)],lookup)
            fields=[ratio(m["unsafe"],m["n"]),ratio(m["right_questions"],m["needs"]),
                    ratio(m["unnecessary"],m["clear"]),ratio(m["slots"],4*m["n"]),
                    ratio(m["conflict_correct"],m["n"]),ratio(m["unsupported_tp"],m["unsupported"]),
                    ratio(m["fills"],m["n"]),f'{m["questions"]/m["n"]:.2f}']
            lines.append("|"+"|".join([split+" "+method,*fields])+"|")
    lines+=["","|Split / method|Correct refusals|Questions on target|Wrong / all previews|Verified fills / potentially fulfillable|",
            "|---|---:|---:|---:|---:|"]
    for split in ("dev","holdout"):
        for method in "ABC":
            m=metrics([r for r in rows if (r["split"],r["method"])==(split,method)],lookup)
            lines.append(f'|{split} {method}|{m["correct_refusals"]}|{m["right_questions"]}|{m["wrong_previews"]}/{m["previews"]}|{m["fills"]}/{m["n"]-m["unsupported"]}|')
    lines+=["","|Split / physical batch phase|CLI calls|Order extractions|Input tokens|Output tokens|Cached input tokens|Summed wall seconds|",
            "|---|---:|---:|---:|---:|---:|---:|"]
    for split in ("dev","holdout"):
        for phase in ("initial","followup"):
            selected=[r for r in calls if lookup[r["ids"][0]]["split"]==split and r["phase"]==phase]
            usage=[]
            for key in ("input_tokens","output_tokens","cached_input_tokens"):
                counts=[(r["usage"] or {}).get(key) for r in selected]
                usage.append(str(sum(counts)) if all(type(x) is int for x in counts) else "unknown")
            lines.append("|"+"|".join([split+" "+phase,str(len(selected)),str(sum(len(r["ids"]) for r in selected)),
                                       *usage,f'{sum(r["wall_s"] for r in selected):.2f}'])+"|")
    lines+=["","A used zero model calls. B used initial batches only. C shared those outputs and used the follow-up batches. Cached input is included in input. Physical telemetry cannot be allocated to individual orders. Backend model and monetary cost are unknown.","",
            "## Post-hoc control", "",
            "We enabled the same question-and-answer policy for the rule extractor to check whether the corpus requires an LLM. This control uses no live calls and was added during review after the primary protocol freeze."]
    for split in ("dev","holdout"):
        selected=[c for c in cases if c["split"]==split]
        control=[paired(c,"C",evidence(c["text"]),evidence(c["answer"]) if c["answer"] else None) for c in selected]
        lines.append(f'- {split}: {sum(r["filled"] for r in control)} verified fills, {sum(r["correct_refusal"] for r in control)} correct refusals, {sum(r["targeted"] for r in control)} targeted questions out of {len(control)} cases.')
    return "\n".join(lines)+"\n"


if __name__=="__main__":
    print(render(),end="")
