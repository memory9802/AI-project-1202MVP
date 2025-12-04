from flask import Blueprint

recommendation_bp = Blueprint('recommendation', __name__, template_folder='templates')

from . import routes
