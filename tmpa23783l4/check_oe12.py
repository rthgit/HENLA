import json, pathlib

p = pathlib.Path(".benchmark_runs/oe/oe12")
files = sorted(p.glob("*.json"))
if files:
    d = json.loads(files[0].read_text())
    print(f"verdict: {d['verdict']}")
    print(f"criteria_met: {d['criteria_met']}/{d['criteria_total']}\n")
    for c in d["criteria"]:
        mark = "OK " if c["met"] else "FAIL"
        print(f"  [{mark}] {c['criterion']}  (source={c['source']})")
