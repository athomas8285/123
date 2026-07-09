"""Auto-generated route file."""
from flask import jsonify, request, send_from_directory
from .helpers import db_get, load_json, _build_result_cache, _RESULT_CACHE, _console_log
from .helpers import BASE, APP_DATA, WEEKDAY_CN, parse_weekday, get_today_cn
from .helpers import enrich_row_with_results, get_results_for
from . import plans_bp as bp
import os


@bp.route('/api/dashboard/featured')
def dashboard_featured():
    return send_from_directory('static', 'featured.html')

