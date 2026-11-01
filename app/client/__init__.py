from flask import Blueprint

bp = Blueprint('client', __name__, url_prefix='/client')

from app.client import routes  # noqa: E402, F401
