from flask_wtf import FlaskForm, Recaptcha
from flask_wtf.recaptcha import RecaptchaField
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import (
    ValidationError,
    DataRequired,
    Email,
    EqualTo,
    Length,
    Regexp,
)
from flask_babel import _, lazy_gettext as _l
from app.models import User
from flask import flash


class LoginForm(FlaskForm):
    email = StringField(
        _l("Email:"),
        validators=[DataRequired(), Email(message=_l("Неправильный формат почты."))],
    )
    password = PasswordField(_l("Пароль:"), validators=[DataRequired()])
    recaptcha = RecaptchaField(
        validators=[Recaptcha(message=_l("Докажите, что вы не робот."))]
    )
    remember_me = BooleanField(_l("Запомнить меня"))
    submit = SubmitField(_l("Войти"))


class RegistrationForm(FlaskForm):
    username = StringField(
        _l("Имя пользователя:"),
        validators=[
            DataRequired(),
            Length(min=3, max=20),
            Regexp("^[A-Za-z0-9_]*$", message="a-z,0-9,_"),
        ],
    )
    first_name = StringField(_l("Имя:"), validators=[Length(max=255)])
    last_name = StringField(_l("Фамилия:"), validators=[Length(max=255)])
    email = StringField(
        _l("Email:"),
        validators=[
            DataRequired(),
            Email(message=_l("Неправильный формат почты.")),
            Length(min=1, max=320),
        ],
    )
    password = PasswordField(
        _l("Пароль:"), validators=[DataRequired(), Length(min=6, max=128)]
    )
    password2 = PasswordField(
        _l("Повторите пароль:"),
        validators=[
            DataRequired(),
            EqualTo(
                "password",
                message=_l("Текст этого поля должен совпадать с верхним полем."),
            ),
        ],
    )
    recaptcha = RecaptchaField(
        validators=[Recaptcha(message=_l("Докажите, что вы не робот."))]
    )
    agree = BooleanField(_l("Я согласен на обработку персональных данных*"), validators=[DataRequired()])
    submit = SubmitField(_l("Зарегистрироваться"))

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError(_("Пожалуйста, введите другое имя пользователя."))

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError(_("Пожалуйста, введите другой email."))


class forgetPasswordRequestForm(FlaskForm):
    email = StringField(
        _l("Email"),
        validators=[
            DataRequired(),
            Email(message=_l("Неправильный формат почты.")),
            Length(1, 64),
        ],
    )
    recaptcha = RecaptchaField(
        validators=[Recaptcha(message=_l("Докажите, что вы не робот."))]
    )
    submit = SubmitField(_l("Восстановить пароль"))


class resetPasswordForm(FlaskForm):
    password = PasswordField(
        _l("Новый пароль"), validators=[DataRequired(), Length(min=6, max=128)]
    )
    password2 = PasswordField(
        _l("Подтвердите новый пароль"),
        validators=[
            DataRequired(),
            EqualTo(
                "password", _l("Текст этого поля должен совпадать с верхним полем.")
            ),
        ],
    )
    submit = SubmitField(_l("Сбросить пароль"))
