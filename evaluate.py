"""Generate all paired data or verify published JSONL traces offline."""
import argparse
import gzip
import json
from pathlib import Path
from study import baseline, generate, trial

ROOT = Path(__file__).resolve().parent / "evidence" / "v02"
SPLITS = {"dev": range(100), "holdout": range(10000, 11000)}


def compare(record, computed):
    for key in computed:
        if key not in ("elapsed_s", "model", "usage", "cost") and computed[key] != record[key]:
            raise ValueError(f"seed {record['seed']}, {key}: replay mismatch")


def offline(split, dest):
    with gzip.open(dest, "xt", encoding="utf-8") as out:
        for seed in SPLITS[split]:
            for name in ("fixed", "adaptive"):
                record = trial(generate(seed), name, baseline)
                out.write(json.dumps(record, separators=(",", ":")) + "\n")


def verify(split):
    with gzip.open(ROOT / (split + ".jsonl.gz"), "rt", encoding="utf-8") as stream:
        for seed in SPLITS[split]:
            for name in ("fixed", "adaptive"):
                record = json.loads(next(stream))
                compare(record, trial(generate(seed), name, baseline))
        if stream.read().strip():
            raise ValueError("extra results")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("split", choices=SPLITS)
    parser.add_argument("--generate", type=Path, help="new gzip JSONL path; refuses overwrite")
    args = parser.parse_args()
    if args.generate:
        offline(args.split, args.generate)
    else:
        verify(args.split)
        print("Verified all paired trajectories:", args.split)
