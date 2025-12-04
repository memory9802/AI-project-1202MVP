from flask import Blueprint

aichat_bp = Blueprint('aichat', __name__, template_folder='templates')

from . import routes
