from flask import render_template
from . import wardrobe_bp

@wardrobe_bp.route('/wardrobe')
def wardrobe():
    return render_template('wardrobe.html')
