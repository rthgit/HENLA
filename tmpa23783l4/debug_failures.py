import traceback
import sys

sys.path.insert(0, ".")

for label, fn_name, mod_name in [
    ("OE-2", "run_cold_start_learning_without_priors", "benchmarks.open_ended_cold_start"),
    ("OE-4", "run_long_horizon_goal_pursuit",          "benchmarks.open_ended_long_horizon"),
    ("OE-9", "run_self_curriculum_generation",         "benchmarks.open_ended_self_curriculum"),
]:
    print(f"\n{'='*60}\n{label}  ({fn_name})\n{'='*60}")
    try:
        import importlib
        mod = importlib.import_module(mod_name)
        fn  = getattr(mod, fn_name)
        result = fn(f".benchmark_runs/oe/debug_{label.lower().replace('-','')}")
        print(f"  status : {result.get('status')}")
        print(f"  passed : {result.get('passed')}")
        for k, v in result.items():
            if k not in ("name","status","passed","policy","workspace_summaries","packets","packet_results"):
                print(f"  {k}: {v}")
    except Exception:
        traceback.print_exc()
