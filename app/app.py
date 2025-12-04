from flask import Flask
import os

def create_app():
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')

    # 設定環境變數
    app.config['JSON_AS_ASCII'] = False
    app.config['JSON_SORT_KEYS'] = False
    app.json.ensure_ascii = False

    # 從環境變數加載設定 (如果需要)
    # app.config.from_envvar('YOUR_APP_SETTINGS', silent=True)

    # 註冊 Blueprints
    from blueprints.home import home_bp
    app.register_blueprint(home_bp)

    from blueprints.aichat import aichat_bp
    app.register_blueprint(aichat_bp, url_prefix='/aichat')

    from blueprints.login import login_bp
    app.register_blueprint(login_bp, url_prefix='/login')

    from blueprints.recommendation import recommendation_bp
    app.register_blueprint(recommendation_bp, url_prefix='/recommendation')

    from blueprints.share import share_bp
    app.register_blueprint(share_bp, url_prefix='/share')

    from blueprints.wardrobe import wardrobe_bp
    app.register_blueprint(wardrobe_bp, url_prefix='/wardrobe')


    @app.route('/')
    def index():
        from flask import redirect, url_for
        return redirect(url_for('home.index'))

    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
