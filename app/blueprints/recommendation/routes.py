from flask import render_template
from . import recommendation_bp

@recommendation_bp.route('/recommendation')
def recommend():
    return render_template('recommendation.html')
