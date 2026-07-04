"""Auto-generated route file."""
from flask import jsonify, request, send_from_directory
from .helpers import db_get, load_json, _build_result_cache, _RESULT_CACHE, _console_log
from .helpers import BASE, APP_DATA, WEEKDAY_CN, parse_weekday, get_today_cn
from .helpers import enrich_row_with_results, get_results_for
from . import plans_bp as bp
import os

@bp.route("/api/dashboard/plan")
def plan_data():
    """Return plan_data.json for the dashboard plans panel."""
    import json, os
    plan_path = os.path.join(BASE, "data", "plan_data.json")
    if os.path.exists(plan_path):
        with open(plan_path, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify({})


@bp.route('/api/dashboard/featured')
def dashboard_featured():
    return send_from_directory('static', 'featured.html')

