from flask import Blueprint

login_bp = Blueprint('login', __name__, template_folder='templates')

from . import routes
