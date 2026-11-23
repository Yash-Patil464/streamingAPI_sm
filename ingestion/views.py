import json
import subprocess
import sys
import uuid
import logging
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

# Directory where incoming data files are stored
DATA_DIR = getattr(settings, "INGESTION_DATA_DIR", settings.BASE_DIR / "ingestion_data")

# Directory where per-file processing logs are written
LOG_DIR = getattr(settings, "INGESTION_LOG_DIR", settings.BASE_DIR / "logs")

# Path to the processing script
PROCESS_SCRIPT = getattr(
    settings, "INGESTION_PROCESS_SCRIPT", settings.BASE_DIR / "process.py"
)

PYTHON = str(getattr(settings, "INGESTION_PYTHON", sys.executable))

@csrf_exempt
@require_POST
def ingest(request):
    """
    Receive a JSON payload, write it to a file, then kick off a
    fire-and-forget subprocess to process the file.

    POST /api/ingest/
    Content-Type: application/json
    Body: any valid JSON

    Response: 202 Accepted  { "status": "accepted", "file": "<filename>", "processing": "started" }
    """
    # --- 1. Parse the incoming JSON body --------------------------------
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, ValueError) as exc:
        return JsonResponse(
            {"status": "error", "message": f"Invalid JSON: {exc}"},
            status=400,
        )

    # --- 2. Write the payload to a file ---------------------------------
    #     If the payload (or a top-level item) contains a "filename" key,
    #     use that as the file name; otherwise fall back to a random UUID.
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

    # Extract a caller-supplied filename from the payload
    custom_name = None
    if isinstance(payload, dict):
        custom_name = payload.get("filename")
    elif isinstance(payload, list) and payload and isinstance(payload[0], dict):
        custom_name = payload[0].get("filename")

    if custom_name:
        # Sanitise: keep only the base name to prevent path traversal,
        # and ensure it ends with .json
        custom_name = Path(custom_name).name  # strips any directory parts
        if not custom_name.endswith(".json"):
            custom_name += ".json"
        filename = custom_name
        file_id = Path(custom_name).stem
    else:
        file_id = uuid.uuid4().hex
        filename = f"{file_id}.json"

    filepath = Path(DATA_DIR) / filename

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except OSError as exc:
        logger.exception("Failed to write ingestion file")
        return JsonResponse(
            {"status": "error", "message": f"File write failed: {exc}"},
            status=500,
        )

    # --- 3. Fire-and-forget: launch the processing script ---------------
    #     subprocess.Popen does NOT block the request; the child process
    #     runs independently.  We intentionally do not wait for it.
    #     Child stdout/stderr are directed to a log file so we can inspect
    #     what happened after the fact.
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
    log_path = Path(LOG_DIR) / f"{file_id}.log"

    processing_status = "started"
    try:
        log_file = open(log_path, "w", encoding="utf-8")
        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = (
                subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            )

        subprocess.Popen(
            [PYTHON, str(PROCESS_SCRIPT), str(filepath)],
            stdout=log_file,
            stderr=log_file,
            creationflags=creation_flags,
        )
        logger.info("Launched processing for %s (log: %s)", filepath, log_path)
    except Exception as exc:
        logger.exception("Failed to launch processing for %s", filepath)
        processing_status = "failed_to_start"

    # --- 4. Return immediately with 202 Accepted ------------------------
    return JsonResponse(
        {
            "status": "accepted",
            "file": filename,
            "processing": processing_status,
            "log": str(log_path.name),
        },
        status=202,
    )
