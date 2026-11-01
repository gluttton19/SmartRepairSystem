from flask import Blueprint

bp = Blueprint('master', __name__, url_prefix='/master')

from app.master import routes  # noqa: E402, F401
