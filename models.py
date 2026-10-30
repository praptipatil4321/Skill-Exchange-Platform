from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    bio = db.Column(db.Text, default="")
    github_url = db.Column(db.String(255), default="")
    linkedin_url = db.Column(db.String(255), default="")
    portfolio_url = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    skills = db.relationship("Skill", backref="owner", lazy=True, cascade="all, delete-orphan")

    sent_requests = db.relationship(
        "ExchangeRequest",
        foreign_keys="ExchangeRequest.sender_id",
        backref="sender",
        lazy=True,
        cascade="all, delete-orphan",
    )
    received_requests = db.relationship(
        "ExchangeRequest",
        foreign_keys="ExchangeRequest.receiver_id",
        backref="receiver",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def offered_skills(self):
        return [s for s in self.skills if s.skill_type == "offered"]

    def wanted_skills(self):
        return [s for s in self.skills if s.skill_type == "wanted"]

    def __repr__(self):
        return f"<User {self.username}>"


class Skill(db.Model):
    __tablename__ = "skills"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default="")
    category = db.Column(db.String(80), default="General")
    # "offered"  = a skill this user can teach
    # "wanted"   = a skill this user wants to learn
    skill_type = db.Column(db.String(10), nullable=False)
    years_experience = db.Column(db.Integer, nullable=True)
    certificate_name = db.Column(db.String(150), default="")
    certificate_url = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Skill {self.title} ({self.skill_type})>"


class ExchangeRequest(db.Model):
    __tablename__ = "exchange_requests"

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # The skill (owned by receiver) that the sender wants to learn
    requested_skill_id = db.Column(db.Integer, db.ForeignKey("skills.id"), nullable=False)
    # The skill (owned by sender) offered in return, optional
    offered_skill_id = db.Column(db.Integer, db.ForeignKey("skills.id"), nullable=True)

    message = db.Column(db.Text, default="")
    status = db.Column(db.String(20), default="pending")  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    requested_skill = db.relationship("Skill", foreign_keys=[requested_skill_id])
    offered_skill = db.relationship("Skill", foreign_keys=[offered_skill_id])

    def is_participant(self, user_id):
        return user_id in (self.sender_id, self.receiver_id)

    def other_user(self, user_id):
        return self.receiver if user_id == self.sender_id else self.sender

    def __repr__(self):
        return f"<ExchangeRequest {self.sender_id} -> {self.receiver_id} ({self.status})>"


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    exchange_request_id = db.Column(
        db.Integer, db.ForeignKey("exchange_requests.id"), nullable=False, index=True
    )
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.Text, nullable=True)
    image_path = db.Column(db.String(255), nullable=True)  # legacy image-only uploads
    # Generic attachment (any file type)
    file_path = db.Column(db.String(255), nullable=True)   # stored name, relative to CHAT_FILES_FOLDER
    file_name = db.Column(db.String(255), nullable=True)   # original name shown to users
    file_mime = db.Column(db.String(120), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)

    exchange_request = db.relationship(
        "ExchangeRequest",
        backref=db.backref(
            "messages", lazy=True, cascade="all, delete-orphan", order_by="Message.created_at"
        ),
    )
    sender = db.relationship("User")

    def __repr__(self):
        return f"<Message {self.sender_id} on exchange {self.exchange_request_id}>"
