from flask import Flask

from . import auth, deals, main, reports
from .config import Config
from .db import db, migrate
from .integrations import youtube


def create_app(config: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config)

    db.init_app(app)
    migrate.init_app(app, db)
    auth.init_oauth(app)

    app.before_request(auth.load_current_user)

    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(deals.bp)
    app.register_blueprint(reports.bp)
    app.register_blueprint(youtube.bp)

    @app.template_filter("num")
    def _num(v):
        if v is None:
            return "—"
        return f"{int(v):,}"

    @app.template_filter("money")
    def _money(v, currency="USD"):
        if v is None:
            return "—"
        return f"{currency} {v:,.2f}"

    from . import models  # noqa: F401 — register models with SQLAlchemy metadata

    return app
