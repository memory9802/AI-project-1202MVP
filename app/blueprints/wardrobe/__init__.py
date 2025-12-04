from flask import Blueprint

wardrobe_bp = Blueprint('wardrobe', __name__, template_folder='templates')

from . import routes
