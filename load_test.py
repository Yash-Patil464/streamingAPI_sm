import statistics, sys, time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = "https://smdata1.smartex.me/api/ingest/"
total, workers = int(sys.argv[1]), int(sys.argv[2])
RUN = int(time.time())


def send(i):
    body = [
        {"filename": f"loadtest_{RUN}_{i}", "sensor": "humidity-01", "value": 72.3},
        {"sensor": "pressure-01", "value": 1013.25},
        {"sensor": "wind-01", "value": 8.4},
    ]
    start = time.perf_counter()
    try:
        r = requests.post(URL, json=body, timeout=30, verify=False)  # add verify=False only if you get a certificate error
        proc = r.json().get("processing") if r.ok else None
        return r.status_code, time.perf_counter() - start, proc
    except Exception as exc:
        return type(exc).__name__, time.perf_counter() - start, None


t0 = time.perf_counter()
with ThreadPoolExecutor(max_workers=workers) as pool:
    results = list(pool.map(send, range(total)))
elapsed = time.perf_counter() - t0

lat = sorted(t for _, t, _ in results)
print(f"requests: {total}  concurrency: {workers}  time: {elapsed:.1f}s  throughput: {total / elapsed:.1f} req/s")
print("status codes:", dict(Counter(c for c, _, _ in results)))
print("processing:  ", dict(Counter(p for _, _, p in results)))
print(f"latency avg {statistics.mean(lat)*1000:.0f} ms | p95 {lat[max(int(len(lat)*0.95)-1, 0)]*1000:.0f} ms | max {lat[-1]*1000:.0f} ms")