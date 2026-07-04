"""Main Flask application entry point for gunicorn (dashboard:app)."""
from flask import Flask
from routes import register_blueprints, helpers
import os, sys

app = Flask(__name__, template_folder="templates")

# Minimal health check — no DB dependency, survives import failures
@app.route("/health")
def health():
    return {"status": "ok"}, 200

# Defensive startup: catch and log failures instead of hanging workers
try:
    helpers.ensure_db()
    print("[boot] ensure_db() OK", flush=True)
except Exception as e:
    print(f"[boot] ensure_db() FAILED: {e}", flush=True)

try:
    register_blueprints(app)
    print("[boot] blueprints registered OK", flush=True)
except Exception as e:
    print(f"[boot] register_blueprints() FAILED: {e}", flush=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5021))
    app.run(host="0.0.0.0", port=port, debug=True, threaded=True, use_reloader=False)
