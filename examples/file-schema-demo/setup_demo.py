"""Setup script to create demo snapshots for the file schema demo."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from driftguard.collectors.csv_collector import CsvCollector
from driftguard.schema.models import ContractSnapshot
from driftguard.store.local import LocalStore


def main() -> None:
    demo_dir = Path(__file__).parent
    store = LocalStore(demo_dir / ".driftguard/snapshots")

    baseline_collector = CsvCollector(demo_dir / "baseline-data.csv", "export-data")
    baseline = ContractSnapshot(name="baseline", resources=baseline_collector.collect())
    store.save(baseline)
    print(f"Saved baseline: {len(baseline.resources[0].fields)} fields")

    current_collector = CsvCollector(demo_dir / "current-data.csv", "export-data")
    current = ContractSnapshot(name="current", resources=current_collector.collect())
    store.save(current)
    print(f"Saved current: {len(current.resources[0].fields)} fields")

    print("\nRun: driftguard diff --baseline baseline --current current --config driftguard.yaml")


if __name__ == "__main__":
    main()
