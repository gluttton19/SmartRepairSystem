from pathlib import Path
from flask import Flask
from config import config
from app.extensions import db, login_manager, migrate, csrf

_ROOT = Path(__file__).resolve().parent.parent  # autoservice/


def create_app(config_name: str = 'default') -> Flask:
    app = Flask(
        __name__,
        template_folder=str(_ROOT / 'templates'),
        static_folder=str(_ROOT / 'static'),
    )
    app.config.from_object(config[config_name])

    _register_extensions(app)
    _register_blueprints(app)
    _register_shell_context(app)
    _register_root_route(app)

    return app


def _register_extensions(app: Flask) -> None:
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))


def _register_blueprints(app: Flask) -> None:
    from app.auth import bp as auth_bp
    from app.client import bp as client_bp
    from app.master import bp as master_bp
    from app.admin import bp as admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(client_bp)
    app.register_blueprint(master_bp)
    app.register_blueprint(admin_bp)


def _register_root_route(app: Flask) -> None:
    from flask import render_template, redirect, url_for
    from flask_login import current_user

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            destinations = {
                'client': 'client.dashboard',
                'master': 'master.dashboard',
                'admin':  'admin.dashboard',
            }
            return redirect(url_for(destinations.get(current_user.role, 'auth.login')))
        return render_template('index.html')


def _register_shell_context(app: Flask) -> None:
    from app.models import User, Car, Master, MasterSkill, Service, Request, RequestStatusHistory, Notification

    @app.shell_context_processor
    def make_shell_context():
        return {
            'db': db,
            'User': User,
            'Car': Car,
            'Master': Master,
            'MasterSkill': MasterSkill,
            'Service': Service,
            'Request': Request,
            'RequestStatusHistory': RequestStatusHistory,
            'Notification': Notification,
        }
