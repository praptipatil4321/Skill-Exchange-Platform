import os

from flask import Flask, jsonify, request
from sqlalchemy import inspect, text

from config import Config, BASE_DIR
from extensions import db, login_manager


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Make sure the instance folder exists so SQLite has somewhere to write.
    os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)
    # Make sure the chat image upload folder exists.
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["CHAT_FILES_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    # Import models so SQLAlchemy knows about them before create_all()
    import models  # noqa: F401

    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.skills import skills_bp
    from routes.chat import chat_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(skills_bp)
    app.register_blueprint(chat_bp)

    @app.template_filter("initials")
    def initials(name):
        return (name or "?")[:2].upper()

    @app.errorhandler(413)
    def too_large(_e):
        limit = app.config["MAX_UPLOAD_MB"]
        if request.path.startswith("/messages"):
            return jsonify({"error": f"File is too large (max {limit} MB)."}), 413
        return f"File is too large (max {limit} MB).", 413

    with app.app_context():
        db.create_all()
        _add_missing_message_columns()

    return app


def _add_missing_message_columns():
    """Lightweight migration so existing databases gain the new attachment
    columns without needing to be deleted."""
    insp = inspect(db.engine)
    if "messages" not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns("messages")}
    wanted = {
        "file_path": "VARCHAR(255)",
        "file_name": "VARCHAR(255)",
        "file_mime": "VARCHAR(120)",
        "file_size": "INTEGER",
    }
    for name, ddl in wanted.items():
        if name not in existing:
            db.session.execute(text(f"ALTER TABLE messages ADD COLUMN {name} {ddl}"))
    db.session.commit()


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
