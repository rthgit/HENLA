import json, pathlib

for label, folder, key in [
    ("OE-2", ".benchmark_runs/oe/oe2", "abstention_rate"),
    ("OE-11", ".benchmark_runs/oe/oe11", "score"),
]:
    p = pathlib.Path(folder)
    files = sorted(p.glob("*.json"))
    if not files:
        print(f"{label}: NO JSON in {folder}")
        continue
    d = json.loads(files[0].read_text())
    print(f"{label}:")
    print(f"  keys available: {list(d.keys())}")
    val = d.get(key)
    print(f"  {key}: {val}")
    print()
