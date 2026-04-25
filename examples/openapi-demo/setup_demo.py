"""Setup script to create demo snapshots for the OpenAPI demo."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from driftguard.collectors.json_collector import OpenApiCollector
from driftguard.schema.models import ContractSnapshot
from driftguard.store.local import LocalStore


def main() -> None:
    demo_dir = Path(__file__).parent
    store = LocalStore(demo_dir / ".driftguard/snapshots")

    # Baseline
    baseline_collector = OpenApiCollector(demo_dir / "baseline-spec.yaml")
    baseline_resources = baseline_collector.collect()
    baseline = ContractSnapshot(name="baseline", resources=baseline_resources)
    store.save(baseline)
    print(f"Saved baseline: {len(baseline_resources)} resources")

    # Current
    current_collector = OpenApiCollector(demo_dir / "current-spec.yaml")
    current_resources = current_collector.collect()
    current = ContractSnapshot(name="current", resources=current_resources)
    store.save(current)
    print(f"Saved current: {len(current_resources)} resources")

    print("\nRun: driftguard diff --baseline baseline --current current --config driftguard.yaml")


if __name__ == "__main__":
    main()
