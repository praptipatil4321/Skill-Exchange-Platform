from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField, HiddenField, IntegerField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, URL, NumberRange


class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=30)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password", message="Passwords must match")]
    )


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])


class ProfileForm(FlaskForm):
    bio = TextAreaField("Bio", validators=[Optional(), Length(max=500)])
    github_url = StringField(
        "GitHub URL", validators=[Optional(), URL(), Length(max=255)]
    )
    linkedin_url = StringField(
        "LinkedIn URL", validators=[Optional(), URL(), Length(max=255)]
    )
    portfolio_url = StringField(
        "Portfolio / Other Link",
        validators=[Optional(), URL(), Length(max=255)],
        description="Personal site, Instagram, YouTube, SoundCloud — whatever best shows off your work.",
    )


class SkillForm(FlaskForm):
    title = StringField("Skill Title", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=500)])
    category = StringField("Category", validators=[Optional(), Length(max=80)])
    skill_type = SelectField(
        "Type",
        choices=[("offered", "I can teach this"), ("wanted", "I want to learn this")],
        validators=[DataRequired()],
    )
    years_experience = IntegerField(
        "Years of Experience", validators=[Optional(), NumberRange(min=0, max=80)]
    )
    certificate_name = StringField(
        "Certificate / Credential (optional)", validators=[Optional(), Length(max=150)]
    )
    certificate_url = StringField(
        "Certificate Link (optional)", validators=[Optional(), URL(), Length(max=255)]
    )


class ExchangeRequestForm(FlaskForm):
    requested_skill_id = HiddenField(validators=[DataRequired()])
    offered_skill_id = SelectField("Offer one of your skills in return (optional)", coerce=int, validators=[Optional()])
    message = TextAreaField("Message", validators=[Optional(), Length(max=500)])
