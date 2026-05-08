import json
import pathlib

for name in ["oe2", "oe4", "oe9"]:
    p = pathlib.Path(f".benchmark_runs/oe/{name}")
    files = sorted(p.glob("*.json"))
    if not files:
        print(f"=== {name} === NO JSON FOUND")
        continue
    d = json.loads(files[0].read_text())
    print(f"=== {name} ===  status={d.get('status')}  passed={d.get('passed')}")
    skip = {"name", "status", "passed", "policy", "workspace_summaries",
            "packet_results", "packets", "criteria", "benchmark_statuses"}
    for k, v in d.items():
        if k not in skip:
            print(f"  {k}: {v}")
    print()
