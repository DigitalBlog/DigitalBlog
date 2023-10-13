from flask import Flask, request, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_babel import Babel, lazy_gettext as _l
from config import Config
import os
from flask_bcrypt import Bcrypt


def get_locale():
    return "ru"
    # return request.accept_languages.best_match(current_app.config['LANGUAGES'])


# sentry_sdk.init(
#     dsn="https://2358793f94946e3634df18442fab0861@o4506003987955712.ingest.sentry.io/4506003991166976",
#     # Set traces_sample_rate to 1.0 to capture 100%
#     # of transactions for performance monitoring.
#     traces_sample_rate=0.01,
#     # Set profiles_sample_rate to 1.0 to profile 100%
#     # of sampled transactions.
#     # We recommend adjusting this value in production.
#     profiles_sample_rate=1,
# )

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
bcrypt = Bcrypt()
login.login_view = "auth.login"
login.login_message = _l("Войдите в аккаунт, для получения доступа к этой странице!")
login.login_message_category = "danger"
login.session_protection = "basic"
bootstrap = Bootstrap()
moment = Moment()
babel = Babel()


def create_app(config_class=Config):
    app = Flask(
        __name__,
        template_folder=os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "templates"
        ),
        static_url_path="",
        static_folder="static",
    )
    app.config.from_object(config_class)
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    bootstrap.init_app(app)
    moment.init_app(app)
    babel.init_app(app, locale_selector=get_locale)

    from app.errors import bp as errors_bp

    app.register_blueprint(errors_bp)

    from app.auth import bp as auth_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")

    from app.main import bp as main_bp

    app.register_blueprint(main_bp)

    from app.cli import bp as cli_bp

    app.register_blueprint(cli_bp)

    return app
