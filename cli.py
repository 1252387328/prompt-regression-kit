#!/usr/bin/env python3
"""Evaluate saved model responses against explicit text assertions and compare results to a previous report. No model API or paid service is called."""

import argparse
import json
from pathlib import Path


def evaluate(cases):
    if not isinstance(cases, list) or not cases:
        raise ValueError("Cases must be a non-empty list")
    results, seen = [], set()
    allowed = {"id", "response", "contains", "excludes", "max_chars"}
    for case in cases:
        if not isinstance(case, dict) or set(case) - allowed:
            raise ValueError("Invalid case or unknown case fields")
        ident, response = case.get("id"), case.get("response")
        if not isinstance(ident, str) or not ident or ident in seen or not isinstance(response, str):
            raise ValueError("Each case needs a unique string id and string response")
        seen.add(ident)
        failures = []
        for field in ("contains", "excludes"):
            values = case.get(field, [])
            if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
                raise ValueError(f"{field} must be a list of strings")
            for index, value in enumerate(values):
                failed = value not in response if field == "contains" else value in response
                if failed:
                    failures.append(f"{field}[{index}]")
        if "max_chars" in case:
            limit = case["max_chars"]
            if type(limit) is not int or limit < 0:
                raise ValueError("max_chars must be a nonnegative integer")
            if len(response) > limit:
                failures.append("max_chars")
        results.append({"id": ident, "passed": not failures, "failed_assertions": failures})
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("cases", type=Path)
    p.add_argument("--baseline", type=Path, help="JSON report from a previous run")
    a = p.parse_args()
    try:
        results = evaluate(json.loads(a.cases.read_text(encoding="utf-8")))
        regressions = []
        if a.baseline:
            previous = json.loads(a.baseline.read_text(encoding="utf-8"))["results"]
            if not isinstance(previous, list) or not all(
                isinstance(row, dict) and isinstance(row.get("id"), str)
                and type(row.get("passed")) is bool for row in previous
            ):
                raise ValueError("Baseline results must contain string IDs and boolean passed values")
            old = {row["id"]: row["passed"] for row in previous}
            regressions = [row["id"] for row in results if old.get(row["id"]) and not row["passed"]]
        report = {"results": results, "regressions": regressions}
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        p.exit(2, f"Input error: {exc}\n")
    print(json.dumps(report, indent=2))
    return int(any(not r["passed"] for r in results))


if __name__ == "__main__":
    raise SystemExit(main())
