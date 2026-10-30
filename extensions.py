from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Instantiated here (without an app) to avoid circular imports.
# They get bound to the Flask app in app.py via init_app().
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"
