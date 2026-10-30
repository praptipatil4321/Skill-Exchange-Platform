from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from extensions import db
from models import Skill, ExchangeRequest, User
from forms import SkillForm, ExchangeRequestForm

skills_bp = Blueprint("skills", __name__)


@skills_bp.route("/skills/browse")
def browse():
    query = Skill.query.filter_by(skill_type="offered")

    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    min_experience = request.args.get("min_experience", "").strip()

    if search:
        query = query.filter(Skill.title.ilike(f"%{search}%"))
    if category:
        query = query.filter(Skill.category.ilike(f"%{category}%"))
    if min_experience.isdigit():
        query = query.filter(Skill.years_experience >= int(min_experience))

    sort = request.args.get("sort", "newest")
    order = {
        "experience": Skill.years_experience.desc().nullslast(),
        "title": Skill.title.asc(),
    }.get(sort, Skill.created_at.desc())
    skills = query.order_by(order).all()
    categories = [
        c[0] for c in db.session.query(Skill.category)
        .filter_by(skill_type="offered").distinct().order_by(Skill.category).all() if c[0]
    ]
    if current_user.is_authenticated:
        skills = [s for s in skills if s.user_id != current_user.id]

    return render_template(
        "browse_skills.html",
        skills=skills,
        search=search,
        category=category,
        min_experience=min_experience,
        sort=sort,
        categories=categories,
    )


@skills_bp.route("/skills/add", methods=["GET", "POST"])
@login_required
def add_skill():
    form = SkillForm()
    if form.validate_on_submit():
        skill = Skill(
            user_id=current_user.id,
            title=form.title.data,
            description=form.description.data,
            category=form.category.data or "General",
            skill_type=form.skill_type.data,
            years_experience=form.years_experience.data,
            certificate_name=form.certificate_name.data,
            certificate_url=form.certificate_url.data,
        )
        db.session.add(skill)
        db.session.commit()
        flash("Skill added.", "success")
        return redirect(url_for("main.dashboard"))
    return render_template("add_skill.html", form=form)


@skills_bp.route("/skills/<int:skill_id>/delete", methods=["POST"])
@login_required
def delete_skill(skill_id):
    skill = Skill.query.get_or_404(skill_id)
    if skill.user_id != current_user.id:
        flash("You can't delete a skill that isn't yours.", "danger")
        return redirect(url_for("main.dashboard"))
    db.session.delete(skill)
    db.session.commit()
    flash("Skill removed.", "info")
    return redirect(url_for("main.dashboard"))


@skills_bp.route("/exchange/request/<int:skill_id>", methods=["GET", "POST"])
@login_required
def request_exchange(skill_id):
    requested_skill = Skill.query.get_or_404(skill_id)
    if requested_skill.user_id == current_user.id:
        flash("You can't request an exchange for your own skill.", "danger")
        return redirect(url_for("skills.browse"))

    form = ExchangeRequestForm()
    form.offered_skill_id.choices = [(0, "-- None --")] + [
        (s.id, s.title) for s in current_user.offered_skills()
    ]
    form.requested_skill_id.data = str(skill_id)

    if form.validate_on_submit():
        offered_id = form.offered_skill_id.data or 0
        exchange = ExchangeRequest(
            sender_id=current_user.id,
            receiver_id=requested_skill.user_id,
            requested_skill_id=requested_skill.id,
            offered_skill_id=offered_id if offered_id != 0 else None,
            message=form.message.data,
        )
        db.session.add(exchange)
        db.session.commit()
        flash("Exchange request sent!", "success")
        return redirect(url_for("skills.browse"))

    return render_template("request_exchange.html", form=form, skill=requested_skill)


@skills_bp.route("/exchange/requests")
@login_required
def exchange_requests():
    received = ExchangeRequest.query.filter_by(receiver_id=current_user.id).order_by(
        ExchangeRequest.created_at.desc()
    ).all()
    sent = ExchangeRequest.query.filter_by(sender_id=current_user.id).order_by(
        ExchangeRequest.created_at.desc()
    ).all()
    return render_template("exchange_requests.html", received=received, sent=sent)


@skills_bp.route("/exchange/<int:request_id>/respond/<string:action>", methods=["POST"])
@login_required
def respond_exchange(request_id, action):
    exchange = ExchangeRequest.query.get_or_404(request_id)
    if exchange.receiver_id != current_user.id:
        flash("You can't respond to a request that isn't yours.", "danger")
        return redirect(url_for("skills.exchange_requests"))

    if action not in ("accept", "reject"):
        flash("Invalid action.", "danger")
        return redirect(url_for("skills.exchange_requests"))

    exchange.status = "accepted" if action == "accept" else "rejected"
    db.session.commit()
    flash(f"Request {exchange.status}.", "success")
    return redirect(url_for("skills.exchange_requests"))
