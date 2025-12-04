from flask import render_template
from . import share_bp

@share_bp.route('/share')
def share():
    return render_template('share.html')
