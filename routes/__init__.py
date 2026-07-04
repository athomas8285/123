from flask import Blueprint

overview_bp = Blueprint("overview", __name__)
console_bp = Blueprint("console", __name__)
matches_bp = Blueprint("matches", __name__)
fundamental_bp = Blueprint("fundamental", __name__)
plans_bp = Blueprint("plans", __name__)
review_bp = Blueprint("review", __name__)

def register_blueprints(app):
    # Import route modules so @bp.route() decorators execute
    from . import overview_routes
    from . import console_routes
    from . import matches_routes
    from . import fundamental_routes
    from . import plans_routes
    from . import review_routes

    app.register_blueprint(overview_bp)
    app.register_blueprint(console_bp)
    app.register_blueprint(matches_bp)
    app.register_blueprint(fundamental_bp)
    app.register_blueprint(plans_bp)
    app.register_blueprint(review_bp)
