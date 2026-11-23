# Streaming Data Ingestion API

A Django REST endpoint that receives JSON data, writes it to a file, and kicks off a background processing script — without blocking the HTTP response.

## How It Works

```
POST /api/ingest/  (JSON body)
        │
        ▼
  1. Parse JSON from request body
        │
        ▼
  2. Write to ingestion_data/<name>.json
     (uses "filename" from payload, or a random UUID)
        │
        ▼
  3. subprocess.Popen("python process.py <filepath>")
     Fire-and-forget — does NOT block the response
        │
        ▼
  4. Return 202 Accepted
```

## Project Structure

```
streamingAPI/
├── config/                # Django project settings
│   ├── settings.py
│   ├── urls.py            # Routes /api/ to ingestion app
│   ├── wsgi.py
│   └── asgi.py
├── ingestion/             # Ingestion app
│   ├── views.py           # The ingest endpoint
│   └── urls.py            # Maps /api/ingest/ to the view
├── process.py             # Background processing script
├── ingestion_data/        # Saved JSON files (auto-created)
├── logs/                  # Per-file processing logs (auto-created)
├── manage.py
└── venv/
```

## Setup

```powershell
# Clone the project and enter it
cd streamingAPI

# Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install Django
pip install django

# Run the server
python manage.py runserver
```

The server starts at `http://127.0.0.1:8000`.

## Usage

### Sending Data

**With a custom filename** — include a `"filename"` key in your JSON:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/ingest/" `
  -Method POST -ContentType "application/json" `
  -Body '[{"filename":"sensor-batch-01","sensor":"humidity-01","value":72.3},{"sensor":"pressure-01","value":1013.25}]'
```

→ Saves as `ingestion_data/sensor-batch-01.json`

**Without a filename** — a random UUID is used:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/ingest/" `
  -Method POST -ContentType "application/json" `
  -Body '[{"sensor":"co2-01","value":412},{"sensor":"light-01","value":540}]'
```

→ Saves as `ingestion_data/a3f7b2c1d4e5...json`

**From Python:**

```python
import requests

data = [
    {"filename": "my-readings", "sensor": "temp-01", "value": 23.5},
    {"sensor": "temp-02", "value": 18.1},
]
resp = requests.post("http://127.0.0.1:8000/api/ingest/", json=data)
print(resp.json())
```

### Response Format

```json
{
  "status": "accepted",
  "file": "sensor-batch-01.json",
  "processing": "started",
  "log": "sensor-batch-01.log"
}
```

| Field        | Description                                      |
|--------------|--------------------------------------------------|
| `status`     | `"accepted"` — data was saved to disk            |
| `file`       | Filename in `ingestion_data/`                    |
| `processing` | `"started"` or `"failed_to_start"`               |
| `log`        | Log filename in `logs/`                          |

### Checking Results

```powershell
# View saved data
Get-Content .\ingestion_data\sensor-batch-01.json

# View processing log
Get-Content .\logs\sensor-batch-01.log
```

Example log output:

```
2026-11-04 20:11:48 [INFO] Processing started for sensor-batch-01.json
2026-11-04 20:11:48 [INFO] Found 2 record(s) in sensor-batch-01.json
2026-11-04 20:11:48 [INFO]   Record 1: {"sensor": "humidity-01", "value": 72.3}
2026-11-04 20:11:49 [INFO]   Record 2: {"sensor": "pressure-01", "value": 1013.25}
2026-11-04 20:11:49 [INFO] Processing complete — 2 succeeded, 0 failed out of 2
```

## Adding Your Processing Logic

Edit `process.py` and replace the body of `process_record()` with your actual logic:

```python
def process_record(index: int, record: dict) -> None:
    # Your logic here: save to DB, call an API, transform, etc.
    ...
```

Each record is processed independently — one failing record does not stop the rest.

## Configuration

Override these in `config/settings.py` if needed:

| Setting                    | Default                     | Description                    |
|----------------------------|-----------------------------|--------------------------------|
| `INGESTION_DATA_DIR`       | `BASE_DIR / "ingestion_data"` | Where JSON files are saved   |
| `INGESTION_LOG_DIR`        | `BASE_DIR / "logs"`          | Where processing logs go      |
| `INGESTION_PROCESS_SCRIPT` | `BASE_DIR / "process.py"`    | Script to run on each file    |

