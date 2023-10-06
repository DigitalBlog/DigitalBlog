from flask import render_template, flash, redirect, url_for, request
from app import db
from app.errors import bp
from flask_babel import _


@bp.app_errorhandler(413)
def too_large(e):
    flash("Файл слишком большой", "warning")
    return redirect(request.path)


@bp.app_errorhandler(403)
def forgotten_error(error):
    return render_template("errors/403.html", title=_("403 - Доступ запрещён")), 403


@bp.app_errorhandler(404)
def not_found_error(error):
    return render_template("errors/404.html", title=_("404 - Страница не найдена")), 404


@bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template("errors/500.html", title=_("500 - Ошибка сервера")), 500
