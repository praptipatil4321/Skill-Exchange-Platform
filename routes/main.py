from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from extensions import db
from models import User, Skill, ExchangeRequest, Message
from forms import ProfileForm

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    stats = {
        "members": User.query.count(),
        "skills": Skill.query.filter_by(skill_type="offered").count(),
        "exchanges": ExchangeRequest.query.filter_by(status="accepted").count(),
    }
    return render_template("index.html", stats=stats)


@main_bp.route("/dashboard")
@login_required
def dashboard():
    stats = {
        "pending": ExchangeRequest.query.filter_by(receiver_id=current_user.id, status="pending").count(),
        "active": ExchangeRequest.query.filter(
            ExchangeRequest.status == "accepted",
            (ExchangeRequest.sender_id == current_user.id) | (ExchangeRequest.receiver_id == current_user.id),
        ).count(),
        "unread": Message.query.join(ExchangeRequest, Message.exchange_request_id == ExchangeRequest.id)
        .filter(
            (ExchangeRequest.sender_id == current_user.id) | (ExchangeRequest.receiver_id == current_user.id),
            Message.sender_id != current_user.id,
            Message.is_read.is_(False),
        ).count(),
    }
    return render_template("dashboard.html", user=current_user, stats=stats)


@main_bp.route("/profile/<username>")
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template("profile.html", profile_user=user)


@main_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.bio = form.bio.data
        current_user.github_url = form.github_url.data
        current_user.linkedin_url = form.linkedin_url.data
        current_user.portfolio_url = form.portfolio_url.data
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("main.profile", username=current_user.username))
    return render_template("edit_profile.html", form=form)
