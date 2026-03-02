from flask import Flask
from config import Config
from routes.main import main_bp

def create_app():
    """Application Factory"""
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB for graph image uploads
    
    # Register Blueprints
    app.register_blueprint(main_bp)
    
    return app

if __name__ == "__main__":
    app = create_app()
    print(f"[INFO] Starting DILI Analysis Platform on port {Config.PORT}...")
    app.run(debug=Config.DEBUG, host="0.0.0.0", port=Config.PORT)
