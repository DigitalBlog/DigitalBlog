from flask import (
    render_template,
    redirect,
    url_for,
    flash,
    request,
    current_app,
    abort,
    g,
)
from werkzeug.urls import url_parse
from flask_login import login_user, logout_user, current_user, login_required
from flask_babel import _
from app import db, get_locale, current_app, cache
from app.auth import bp
from app.auth.forms import (
    LoginForm,
    RegistrationForm,
    forgetPasswordRequestForm,
    resetPasswordForm,
)
from app.models import User, Message, Stuff
from app.email import send_email
import os


@bp.before_app_request
def before_request():
    g.locale = str(get_locale())
    if (
        request.endpoint
        and request.endpoint != "static"
        and request.endpoint != "auth.register"
        and request.endpoint != "auth.login"
        and request.endpoint != "main.index_a"
    ):
        # f_1=Stuff.query.filter_by(name="Access_id").first()
        # if not f_1:
        #     s=Stuff(name="Access_id", content="1")
        #     db.session.add(s)
        #     db.session.commit()
        # f_2 = Stuff.query.filter_by(name="Access_comment").first()
        # if not f_2:
        #     s=Stuff(name="Access_comment", content="")
        #     db.session.add(s)
        #     db.session.commit()
        # f_3 = Stuff.query.filter_by(name="Login_id").first()
        # if not f_3:
        #     s=Stuff(name="Login_id", content="1")
        #     db.session.add(s)
        #     db.session.commit()
        # f_4 = Stuff.query.filter_by(name="Demand_id").first()
        # if not f_4:
        #     s=Stuff(name="Demand_id", content="1")
        #     db.session.add(s)
        #     db.session.commit()
        f_1 = Stuff.query.filter_by(name="Access_id").first().content
        f_2 = Stuff.query.filter_by(name="Access_comment").first().content
        if current_user.is_anonymous and f_1 != "1":
            return render_template("errors/503.html", text=f_2)
        if f_1 == "2":
            if current_user.is_anonymous or (
                not current_user.moderator() and not current_user.admin()
            ):
                return render_template("errors/503.html", text=f_2)
        elif f_1 == "3":
            if current_user.is_anonymous or not current_user.admin():
                return render_template("errors/503.html", text=f_2)
        elif f_1 == "4":
            if current_user.is_anonymous or not current_user.main_admin():
                return render_template("errors/503.html", text=f_2)
    if current_user.is_authenticated:
        if (
            not current_user.confirmed
            and request.endpoint
            and request.endpoint[:5] != "auth."
            and request.endpoint != "static"
        ):
            return redirect(url_for("auth.unconfirmed"))
        if (
            current_user.banned
            and request.endpoint
            and request.endpoint[:5] != "auth."
            and request.endpoint != "static"
        ):
            return redirect(url_for("auth.banned"))
        if current_user.confirmed and not current_user.confirmed:
            current_user.last_seen = datetime.utcnow()
            db.session.commit()


@bp.route("/banned")
def banned():
    if current_user.is_anonymous or not current_user.banned:
        return redirect(url_for("main.index"))
    return render_template("auth/banned.html", reason=current_user.banned_reason)


@bp.route("/unconfirmed")
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for("main.index"))
    return render_template("auth/unconfirmed.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = LoginForm()
    site_key = current_app.config["RECAPTCHA_SITE_KEY"]
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash(_("Неправильный email или пароль!"), "danger")
            return redirect(url_for("auth.login"))
        # r = requests.post('https://www.google.com/recaptcha/api/siteverify',
        #                   data = {'secret' :
        #                           'secret_key',
        #                           'response' :
        #                           request.form['g-recaptcha-response']})
        # google_response = json.loads(r.text)
        # print('JSON: ', google_response)
        # if google_response['success']:
        #     print('SUCCESS')
        #     return render_template('profile.html')
        # else:
        #     print('FAILED')
        #     return render_template('index.html')
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = url_for("main.index")
        flash(_("Вы успешно вошли в аккаунт"), "success")
        return redirect(next_page)
    return render_template(
        "auth/login.html", title="Вход", form=form, site_key=site_key
    )


@bp.route("/logout")
def logout():
    logout_user()
    flash(_("Вы вышли из аккаунта"), "success")
    return redirect(url_for("auth.login"))


@bp.route("/register", methods=["GET", "POST"])
def register():
    text = Stuff.query.filter_by(name="Login_id").first().content
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = RegistrationForm()
    site_key = current_app.config["RECAPTCHA_SITE_KEY"]
    if form.validate_on_submit():
        if form.email.data == current_app.config["EMAIL"]:
            role = 4
            confirmed = True
        else:
            role = 1
            confirmed = False
        user = User(
            username=form.username.data,
            email=form.email.data,
            confirmed=confirmed,
            role=role,
            blogger=confirmed,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            stroage_granted=5242880,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        token = user.generate_confirmation_token()
        f = open("app/templates/auth/confirm.html")
        confirm_html = (
            f.read()
            .replace(
                "{url}", f"{ url_for('auth.confirm', token=token, _external=True) }"
            )
            .replace("{name}", f"{user.username}")
        )
        f.close()
        send_email(user.email, "Подтвердите свой аккаунт - DigitalBlog", confirm_html)
        flash(_("Вы успешно зарегистрированы!"), "success")
        user.add_notify(
            "Добро пожаловать!", "Вы успешно зарегестрировались на сайте DigitalBlog!"
        )
        db.session.commit()
        login_user(user, remember=True)
        return redirect(url_for("main.index"))
    return render_template(
        "auth/register.html",
        title="Регистрация",
        form=form,
        text=text,
        site_key=site_key,
    )


@bp.route("/confirm/<token>", methods=["GET", "POST"])
@login_required
def confirm(token):
    try:
        email = current_user.confirm_token(token)
    except:
        flash(
            _("Ссылка для подтверждения повреждена или срок её действия истёк."),
            "danger",
        )
    user = User.query.filter_by(email=email).first_or_404()
    if user.confirmed:
        flash(_("Ваш аккаунт уже подтверждён"), "success")
    else:
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        flash(_("Вы подтвердили свой аккаунт."), "success")
    return redirect(url_for("main.index"))


@bp.route("/confirm", methods=["GET", "POST"])
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    f = open("app/templates/auth/confirm.html")
    confirm_html = (
        f.read()
        .replace("{url}", f"{ url_for('auth.confirm', token=token, _external=True) }")
        .replace("{name}", f"{current_user.username}")
    )
    f.close()
    send_email(
        current_user.email, "Подтвердите свой аккаунт - DigitalBlog", confirm_html
    )
    flash(_("Новое письмо для подтверждения отправлено."), "success")
    return redirect(url_for("main.index"))


@bp.route("/forget-password-request", methods=["GET", "POST"])
def forget_password_request():
    if not current_user.is_anonymous:
        return redirect(url_for("main.index"))
    form = forgetPasswordRequestForm()
    site_key = current_app.config["RECAPTCHA_SITE_KEY"]
    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).first()
        if user is not None:
            token = user.generate_resetPassword_token()
            f = open("app/templates/auth/forgetPassword.html")
            reset_password_html = (
                f.read()
                .replace(
                    "{url}",
                    f"{ url_for('auth.reset_password', token=token, _external=True) }",
                )
                .replace("{name}", f"{user.username}")
            )
            f.close()
            send_email(
                user.email, "Сброс вашего пароля - DigitalBlog", reset_password_html
            )
        return render_template(
            "auth/forgetPassswordNotificationMessage.html", email=email
        )
    return render_template(
        "auth/forgetPasswordRequest.html",
        form=form,
        title="Сброс пароля",
        site_key=site_key,
    )


@bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    form = resetPasswordForm()
    if form.validate_on_submit():
        user = User.confirm_token_user(token)
        if user:
            user.set_password(form.password.data)
            db.session.add(user)
            flash(_("Пароль успешно сброшен!"), "success")
        else:
            flash(
                _("Ссылка для сброса пароля повреждена или срок её действия истёк."),
                "danger",
            )
            return redirect(url_for("auth.login"))
        return redirect(url_for("auth.login"))
    return render_template("auth/resetPassword.html", form=form, title="Вход")


#@cache.cached(timeout=1200)
@bp.route("/user_agreement", methods=["GET", "POST"])
def user_agreement():
    return render_template(
        "auth/user_agreement.html", title="Пользовательское соглашение"
    )
