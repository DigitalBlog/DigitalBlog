from flask import request
from flask_wtf.file import FileAllowed
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SubmitField,
    TextAreaField,
    PasswordField,
    FileField,
    BooleanField,
    SelectField,
    IntegerField,
)
from wtforms.validators import (
    ValidationError,
    DataRequired,
    Length,
    Email,
    EqualTo,
    Regexp,
)
from app.models import User
from flask_babel import _, lazy_gettext as _l
from flask_pagedown.fields import PageDownField
from PIL import Image
import os
from random import randint


class SendNotifyForm(FlaskForm):
    title = StringField(_l("Тема:"), validators=[DataRequired(), Length(1, 40)])
    body = TextAreaField(_l("Содержание:"), validators=[DataRequired()])
    submit = SubmitField(_l("Отправить"))


class ChangePasswordForm(FlaskForm):
    oldpassword = PasswordField(_l("Старый пароль:"), validators=[DataRequired()])
    password = PasswordField(
        _l("Новый пароль:"), validators=[DataRequired(), Length(min=6, max=128)]
    )
    password2 = PasswordField(
        _l("Повторите новый пароль:"),
        validators=[
            DataRequired(),
            EqualTo(
                "password", message="Текст этого поля должен совпадать с верхним полем."
            ),
        ],
    )
    submit = SubmitField(_l("Сохранить"))

    def __init__(self, original_password, *args, **kwargs):
        super(ChangePasswordForm, self).__init__(*args, **kwargs)
        self.original_password = original_password

    def validate_oldpassword(self, oldpassword):
        valid = current_user.check_password(self.original_password, oldpassword.data)
        if oldpassword.data != self.original_password:
            raise ValidationError("Неправильный cтарый пароль!")


class EditProfileForm(FlaskForm):
    photo = FileField(
        validators=[
            FileAllowed(
                ["jpg", "jpeg", "png", "bmp", "gif", "tif", "webp", "heic", "avif"],
                _l("Файл не является изображением"),
            )
        ]
    )
    username = StringField(
        _l("Имя пользователя:"),
        validators=[
            DataRequired(),
            Length(min=3, max=20),
            Regexp("^[A-Za-z0-9_]*$", message="a-z,0-9,_"),
        ],
    )
    first_name = StringField(_l("Имя:"), validators=[Length(max=24)])
    last_name = StringField(_l("Фамилия:"), validators=[Length(max=24)])
    about_me = TextAreaField(_l("Обо мне:"), validators=[Length(min=0, max=100)])
    email = StringField(
        _l("Email(при изменении вы выйдете из аккаунта и он станет неподтверждённым):"),
        validators=[DataRequired(), Email(), Length(min=1, max=64)],
    )
    profile_access = SelectField(
        _l("Кто может просматривать мой профиль:"),
        coerce=int,
        choices=[
            ("0", "Все пользователи"),
            ("1", "Подписчики"),
            ("2", "Подписки"),
            ("3", "Друзья"),
            ("4", "Никто"),
        ],
    )
    message_setting = SelectField(
        _l("Кто может отправлять мне сообщения:"),
        coerce=int,
        choices=[
            ("0", _l("Все пользователи")),
            ("1", _l("Подписчики")),
            ("2", _l("Подписки")),
            ("3", _l("Друзья")),
            ("4", _l("Никто")),
        ],
    )
    anonymous_show = BooleanField(
        _l("Показывать профиль неавторизованным пользователям")
    )
    submit = SubmitField(_("Сохранить"))

    def __init__(self, original_username, original_email, original_id, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email
        self.original_id = original_id

    def validate_photo(self, photo):
        if photo.data:
            filename = f"{self.original_id}{os.path.splitext(photo.data.filename)[1]}"
            photo.data.save(f"app/static/{filename}")
            try:
                Image.open(f"app/static/{filename}")
                if os.path.getsize(f"app/static/{filename}") > 1 * 1024 * 1024:
                    os.remove(f"app/static/{filename}")
                    raise ValidationError(_("Файл слишком большой, макс.1MB"))
            except IOError:
                os.remove(f"app/static/{filename}")
                raise ValidationError(_("Файл не является изображением"))

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError(_("Пожалуйста, введите другое имя"))

    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=self.email.data).first()
            if user is not None:
                raise ValidationError(_("Пожалуйста, введите другой email"))


class EditProfileMainAdminForm(FlaskForm):
    photo = FileField()
    role = SelectField(
        "Роль:",
        coerce=int,
        choices=[
            ("1", "Пользователь"),
            ("2", "Модератор"),
            ("3", "Администартор"),
            ("4", "Главный администратор"),
        ],
    )
    username = StringField(
        _l("Имя пользователя:"),
        validators=[
            DataRequired(),
            Length(min=3, max=20),
            Regexp("^[A-Za-z0-9_]*$", message="a-z,0-9,_"),
        ],
    )
    first_name = StringField(_l("Имя:"), validators=[Length(max=24)])
    last_name = StringField(_l("Фамилия:"), validators=[Length(max=24)])
    about_me = TextAreaField(_l("Обо мне:"), validators=[Length(min=0, max=100)])
    email = StringField(
        "Email:", validators=[DataRequired(), Email(), Length(min=1, max=64)]
    )
    profile_access = SelectField(
        _l("Кто может просматривать мой профиль:"),
        coerce=int,
        choices=[
            ("0", "Все пользователи"),
            ("1", "Подписчики"),
            ("2", "Подписки"),
            ("3", "Друзья"),
            ("4", "Никто"),
        ],
    )
    message_setting = SelectField(
        "Кто может отправлять мне сообщения:",
        coerce=int,
        choices=[
            ("0", "Все пользователи"),
            ("1", "Подписчики"),
            ("2", "Подписки"),
            ("3", "Друзья"),
            ("4", "Никто"),
        ],
    )
    anonymous_show = BooleanField(
        _l("Показывать профиль неавторизованным пользователям")
    )
    granted_stroage = IntegerField(
        "Выделеное хранилище(в байтах):", validators=[DataRequired()]
    )
    confirmed = BooleanField("Подтверждён")
    banned = BooleanField("Заблокирован")
    banned_reason = StringField("Причина блокировки:")
    blogger = BooleanField("Блогер")
    submit = SubmitField("Сохранить")

    def __init__(self, original_username, original_email, original_id, *args, **kwargs):
        super(EditProfileMainAdminForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email
        self.original_id = original_id

    def validate_photo(self, photo):
        if photo.data:
            filename = f"{self.original_id}{os.path.splitext(photo.data.filename)[1]}"
            photo.data.save(f"app/static/{filename}")
            try:
                Image.open(f"app/static/{filename}")
                if os.path.getsize(f"app/static/{filename}") > 1 * 1024 * 1024:
                    os.remove(f"app/static/{filename}")
                    raise ValidationError(_("Файл слишком большой, макс.1MB"))
            except IOError:
                os.remove(f"app/static/{filename}")
                raise ValidationError(_("Файл не является изображением"))

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError(_("Пожалуйста, введите другое имя"))

    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=self.email.data).first()
            if user is not None:
                raise ValidationError(_("Пожалуйста, введите другой email"))


class EditProfileAdminForm(FlaskForm):
    photo = FileField()
    username = StringField(
        _l("Имя пользователя:"),
        validators=[
            DataRequired(),
            Length(min=3, max=20),
            Regexp("^[A-Za-z0-9_]*$", message="a-z,0-9,_"),
        ],
    )
    first_name = StringField(_l("Имя:"), validators=[Length(max=24)])
    last_name = StringField(_l("Фамилия:"), validators=[Length(max=24)])
    about_me = TextAreaField(_l("Обо мне:"), validators=[Length(min=0, max=100)])
    profile_access = SelectField(
        _l("Кто может просматривать мой профиль:"),
        coerce=int,
        choices=[
            ("0", "Все пользователи"),
            ("1", "Подписчики"),
            ("2", "Подписки"),
            ("3", "Друзья"),
            ("4", "Никто"),
        ],
    )
    message_setting = SelectField(
        _l("Кто может отправлять мне сообщения:"),
        coerce=int,
        choices=[
            ("0", "Все пользователи"),
            ("1", "Подписчики"),
            ("2", "Подписки"),
            ("3", "Друзья"),
            ("4", "Никто"),
        ],
    )
    anonymous_show = BooleanField(
        _l("Показывать профиль неавторизованным пользователям")
    )
    granted_stroage = IntegerField(
        _l("Выделеное хранилище(в байтах):"), validators=[DataRequired()]
    )
    blogger = BooleanField(_l("Блогер"))
    banned = BooleanField(_l("Заблокирован"))
    banned_reason = StringField(_l("Причина блокировки:"))
    submit = SubmitField(_l("Сохранить"))

    def __init__(self, original_username, original_id, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_id = original_id

    def validate_photo(self, photo):
        if photo.data:
            filename = f"{self.original_id}{os.path.splitext(photo.data.filename)[1]}"
            photo.data.save(f"app/static/{filename}")
            try:
                Image.open(f"app/static/{filename}")
                if os.path.getsize(f"app/static/{filename}") > 1 * 1024 * 1024:
                    os.remove(f"app/static/{filename}")
                    raise ValidationError(_("Файл слишком большой, макс.1MB"))
            except IOError:
                os.remove(f"app/static/{filename}")
                raise ValidationError(_("Файл не является изображением"))

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError(_("Пожалуйста, введите другое имя"))


class EmptyForm(FlaskForm):
    submit = SubmitField(_l("Отправить"))


class PostForm(FlaskForm):
    file = FileField()
    title = StringField(validators=[DataRequired(), Length(1, 100)])
    body = TextAreaField(render_kw={"placeholder": _l("Содержание публикации")})
    tag = StringField()
    allow_comments = BooleanField(_l("Показывать комментарии"))
    anonymous_show = BooleanField(_l("Показывать неавторизованным пользователям"))
    show = BooleanField(_l("Показывать"))
    submit = SubmitField(_l("Отправить"))

    def __init__(
        self,
        original_id,
        original_stroage_used,
        original_stroage_granted,
        *args,
        **kwargs,
    ):
        super(PostForm, self).__init__(*args, **kwargs)
        self.original_id = original_id
        self.original_stroage_used = original_stroage_used
        self.original_stroage_granted = original_stroage_granted

    def validate_file(self, file):
        if file.data:
            filename = f"post-{self.original_id}{randint(1000000, 9999999)}{os.path.splitext(file.data.filename)[1]}"
            file.data.save(f"app/static/{filename}")
            size = os.path.getsize(f"app/static/{filename}")
            if size > 10 * 1024 * 1024:
                os.remove(f"app/static/{filename}")
                raise ValidationError(_("Файл слишком большой, макс.10MB"))
            else:
                if self.original_stroage_used + size > self.original_stroage_granted:
                    os.remove(f"app/static/{filename}")
                    raise ValidationError(
                        _('Не хватает места, посетите "Использование"')
                    )
                else:
                    file.data = [f"app/static/{filename}", size]


class MessageForm(FlaskForm):
    file = FileField()
    title = StringField(
        _l("Тема сообщения:"), validators=[DataRequired(), Length(min=1, max=70)]
    )
    body = TextAreaField(
        _l("Содержание сообщения:"),
        render_kw={"placeholder": _l("Содержание сообщения")},
    )
    submit = SubmitField(_l("Отправить"))

    def __init__(
        self,
        original_id,
        original_stroage_used,
        original_stroage_granted,
        *args,
        **kwargs,
    ):
        super(MessageForm, self).__init__(*args, **kwargs)
        self.original_id = original_id
        self.original_stroage_used = original_stroage_used
        self.original_stroage_granted = original_stroage_granted

    def validate_file(self, file):
        if file.data:
            filename = f"message-{self.original_id}{randint(1000000, 9999999)}{os.path.splitext(file.data.filename)[1]}"
            file.data.save(f"app/static/{filename}")
            size = os.path.getsize(f"app/static/{filename}")
            if size > 10 * 1024 * 1024:
                os.remove(f"app/static/{filename}")
                raise ValidationError(_("Файл слишком большой, макс.10MB"))
            else:
                if self.original_stroage_used + size > self.original_stroage_granted:
                    os.remove(f"app/static/{filename}")
                    raise ValidationError(
                        _('Не хватает места, посетите "Использование"')
                    )
                else:
                    file.data = [f"app/static/{filename}", size]


class CommentForm(FlaskForm):
    comment = PageDownField(
        _l("Комментарий:"), validators=[DataRequired(), Length(min=1, max=500)]
    )
    submit = SubmitField(_l("Отправить"))
