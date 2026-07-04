from flask import Flask
from routes import register_blueprints, helpers
import os

app = Flask(__name__, template_folder="templates")

# Initialize database tables on startup (gunicorn imports this module)
helpers.ensure_db()

register_blueprints(app)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5021))
    app.run(host="0.0.0.0", port=port, debug=True, threaded=True, use_reloader=False)
