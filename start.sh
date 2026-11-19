#!/usr/bin/env bash
set -euo pipefail

LAYANAN="${LAYANAN:-ui}"
PORT="${PORT:-7860}"

# Tunggu /health memakai Python yang sudah ada di image (tanpa curl/netcat)
tunggu_api() {
  python - "$1" <<'PY'
import json, sys, time, urllib.request

url = sys.argv[1].rstrip("/") + "/health"
for _ in range(60):
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            if r.status == 200 and json.loads(r.read()).get("status") == "ok":
                sys.exit(0)
    except Exception:
        pass
    time.sleep(2)
sys.exit(f"API tidak siap: {url}")
PY
}

if [ "$LAYANAN" = "api" ]; then
  exec python -m uvicorn app.api.main:app --host 0.0.0.0 --port "$PORT"
fi

if [ "$LAYANAN" = "ui" ]; then
  python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000 &
  tunggu_api "http://127.0.0.1:8000"
  export PM25_API_URL="${PM25_API_URL:-http://127.0.0.1:8000}"
  exec python -m streamlit run app/ui/streamlit_app.py \
       --server.port "$PORT" \
       --server.address 0.0.0.0 \
       --server.headless true \
       --browser.gatherUsageStats false
fi

echo "LAYANAN harus 'ui' atau 'api' (sekarang: $LAYANAN)" >&2
exit 2
