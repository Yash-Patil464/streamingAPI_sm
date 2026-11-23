"""
Processing script.

Called by the ingestion endpoint as:
    python process.py <filepath>

The JSON file may contain a single object or a list of objects.
Each record is processed independently — one failing record does
not stop the rest.
"""
import json
import sys
import logging
import time
import traceback
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def process_record(index: int, record: dict) -> None:
    """
    Process a single record.
    """
    logger.info("  Record %d: %s", index, json.dumps(record, default=str)[:200])
    # Simulate some work
    time.sleep(0.5)


def process(filepath: Path) -> None:
    """Process a single ingested JSON file, record by record."""
    logger.info("Processing started for %s", filepath)

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Normalise: always work with a list of records
    records = data if isinstance(data, list) else [data]
    total = len(records)
    succeeded = 0
    failed = 0

    logger.info("Found %d record(s) in %s", total, filepath.name)

    for i, record in enumerate(records, start=1):
        try:
            process_record(i, record)
            succeeded += 1
        except Exception:
            failed += 1
            logger.error(
                "  Record %d failed:\n%s", i, traceback.format_exc()
            )

    logger.info(
        "Processing complete for %s — %d succeeded, %d failed out of %d",
        filepath.name,
        succeeded,
        failed,
        total,
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <filepath>", file=sys.stderr)
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    process(file_path)
