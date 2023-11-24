from datetime import datetime, timedelta
from flask import (
    render_template,
    flash,
    redirect,
    url_for,
    request,
    g,
    jsonify,
    current_app,
    abort,
    send_file,
    after_this_request,
    make_response,
)
from flask_login import current_user, login_required
from flask_babel import get_locale, _
from flask_caching import CachedResponse
from langdetect import detect, LangDetectException
from app import db, cache
from app.main.forms import (
    EditProfileForm,
    EmptyForm,
    PostForm,
    MessageForm,
    CommentForm,
    ChangePasswordForm,
    EditProfileAdminForm,
    EditProfileMainAdminForm,
    SendNotifyForm,
)
from app.models import (
    User,
    Post,
    Message,
    Notification,
    Comment,
    CommentLikes,
    PostView,
    PostFavourites,
    Notify,
    Followers,
)
from app.main import bp
import os
import markdown
from sqlalchemy import *
import re
from app.email import send_email
from flask_babel import format_datetime
from time import sleep
from bs4 import BeautifulSoup


@bp.route("/posts", methods=["GET", "POST"])
def posts():
    if current_user.is_anonymous:
        page = request.args.get("page", 1, type=int)
        order = request.cookies.get("order_posts", "1")
        if order == "6":
            order_query = Post.last_update_time
        elif order == "5":
            order_query = Post.last_update_time.desc()
        elif order == "4":
            order_query = Post.favourites_count
        elif order == "3":
            order_query = Post.favourites_count.desc()
        elif order == "2":
            order_query = Post.timestamp
        else:
            order_query = Post.timestamp.desc()
        posts = (
            Post.query.filter_by(show=True)
            .filter_by(anonymous_show=True)
            .order_by(order_query)
            .paginate(
                page=page,
                per_page=current_app.config["POSTS_PER_PAGE"],
                error_out=False,
            )
        )
        return render_template(
            "index.html",
            description="Сообщество для программистов и увлекающихся IT. Подписывайтесь, создавайте публикации, обсуждайте, ставьте лайки, пишите личные сообщения, а также возможность подкреплять файлы к публикациям и сообщениям.",
            title="Все публикации",
            posts=posts.items,
            pagination=posts,
            order=order,
        )
    else:
        return redirect(url_for("main.index"))


@bp.route("/~", methods=["GET", "POST"])
@login_required
def index():
    page = request.args.get("page", 1, type=int)
    show_posts = request.cookies.get("show_posts", "1")
    order = request.cookies.get("order_posts", "1")
    if show_posts == "4":
        query = current_user.followed_posts()
    elif show_posts == "3":
        query = Post.query.filter_by(author=current_user)
    elif show_posts == "2":
        query = Post.query.filter(
            PostFavourites.user_id == current_user.id,
            PostFavourites.post_id == Post.id,
        )
    else:
        query = Post.query
    if order == "6":
        order_query = Post.last_update_time
    elif order == "5":
        order_query = Post.last_update_time.desc()
    elif order == "4":
        order_query = Post.favourites_count
    elif order == "3":
        order_query = Post.favourites_count.desc()
    elif order == "2":
        order_query = Post.timestamp
    else:
        order_query = Post.timestamp.desc()
    if current_user.admin():
        posts = query.order_by(order_query).paginate(
            page=page,
            per_page=current_app.config["POSTS_PER_PAGE"],
            error_out=False,
        )
    else:
        posts = (
            query.order_by(order_query)
            .filter_by(show=True)
            .paginate(
                page=page,
                per_page=current_app.config["POSTS_PER_PAGE"],
                error_out=False,
            )
        )
    return render_template(
        "index.html",
        title="Главная страница",
        posts=posts.items,
        pagination=posts,
        show_posts=show_posts,
        order=order,
        Post=Post,
    )


@bp.route("/")
def index_a():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    return CachedResponse(
        response=make_response(render_template('index-a.html')),
        timeout=3600,
    )


@bp.route("/moderation")
@login_required
def moderation():
    if not current_user.moderator():
        abort(403)
    page = request.args.get("page", 1, type=int)
    comments = Comment.query
    comments = comments.order_by(Comment.timestamp.desc()).paginate(
        page=page, per_page=current_app.config["POSTS_PER_PAGE"], error_out=False
    )
    return render_template(
        "moderation.html",
        comments=comments,
        m=markdown.markdown,
        pagination=comments,
        title="Модерация",
    )


@bp.route("/request_bloger")
@login_required
def request_bloger():
    return render_template("request_bloger.html", title="Запрос роли блогера")


@bp.route("/post/<int:post_id>/body", methods=["GET", "POST"])
def post_body(post_id):
    post = Post.query.filter_by(id=post_id).first_or_404()
    if current_user.is_anonymous:
        if post.show == False:
            abort(403)
    else:
        if post.show == False and not current_user.admin():
            abort(403)
    return render_template(
        "post_body.html", body=post.body, title=post.title, description=post.description
    )


@bp.route("/user/<int:user_id>/avatar")
def avatar(user_id):
    user = User.query.get_or_404(user_id)
    return send_file(user.avatar_url)


@bp.route("/post/<int:post_id>", methods=["GET", "POST"])
def post_detail(post_id):
    post = Post.query.filter_by(id=post_id).first_or_404()
    if current_user.is_anonymous:
        if post.show == False:
            abort(403)
    else:
        if post.show == False and not current_user.admin():
            abort(403)
    if not current_user.is_anonymous:
        current_user.view(post)
    form = CommentForm()
    page = request.args.get("page", 1, type=int)
    if post.filename:
        file = True
    else:
        file = False
    if request.method == "POST":
        if form.validate_on_submit():
            time = datetime.utcnow() - timedelta(seconds=1)
            comment = Comment(comment=form.comment.data, post=post, author=current_user)
            db.session.add(comment)
            db.session.commit()
            comment.timestamp = time
            comment.last_update_time = time
            db.session.commit()
            flash(_("Вы прокомментировали эту публикацию"), "success")
            return redirect(url_for("main.post_detail", post_id=post.id))
    comments = post.comments.order_by(Comment.timestamp.desc()).paginate(
        page=page, per_page=3, error_out=False
    )
    return render_template(
        "detail_post.html",
        title=post.title,
        post=post,
        form=form,
        comments=comments.items,
        pagination=comments,
        file=file,
        m=markdown.markdown,
        description=post.description,
    )


# @bp.route('/redirect/', methods=['GET', 'POST'])
# @login_required
# def redirect_view():
#    url=requests.args.get('url')
#    return redirect(url)


@bp.route("/message/<int:message_id>", methods=["GET", "POST"])
@login_required
def message_detail(message_id):
    message = Message.query.get_or_404(message_id)
    if (
        current_user != message.author
        and current_user != message.recipient
        and not current_user.main_admin()
    ):
        abort(403)
    read_time_formatted = format_datetime(message.read_time, "short")
    if message.filename:
        name = message.filename
        file = True
    else:
        file = False
        name = ""
    if current_user == message.recipient and message.read == False:
        message.read = True
        message.read_time = datetime.utcnow()
        db.session.commit()
    return render_template(
        "detail_message.html",
        title=message.title,
        message=message,
        file=file,
        read_time_formatted=read_time_formatted,
    )


@bp.route("/user/<username>")
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    if current_user.is_anonymous:
        if not user.anonymous_show or user.show_profile_id != 0:
            abort(403)
    else:
        if current_user.admin() or current_user == user:
            pass
        elif user.show_profile_id == 1 and not current_user.is_following(user):
            abort(403)
        elif user.show_profile_id == 2 and not current_user.is_followed_by(user):
            abort(403)
        elif user.show_profile_id == 3 and not (
            current_user.is_following(user) and current_user.is_followed_by(user)
        ):
            abort(403)
        elif user.show_profile_id == 4:
            abort(403)
    page_posts = request.args.get("page_posts", 1, type=int)
    page_comments = request.args.get("page_comments", 1, type=int)
    if current_user.is_anonymous:
        posts = (
            user.posts.filter_by(show=True)
            .filter_by(anonymous_show=True)
            .order_by(Post.timestamp.desc())
            .paginate(page=page_posts, per_page=3, error_out=False)
        )
        comments = (
            Comment.query.join(Post)
            .filter(
                Comment.commented_by == user.id,
                Comment.commented_on == Post.id,
                Post.anonymous_show == True,
            )
            .order_by(Comment.timestamp.desc())
            .paginate(page=page_comments, per_page=3, error_out=False)
        )
    else:
        posts = (
            user.posts.filter_by(show=True)
            .order_by(Post.timestamp.desc())
            .paginate(page=page_posts, per_page=3, error_out=False)
        )
        comments = user.comments.order_by(Comment.timestamp.desc()).paginate(
            page=page_comments, per_page=3, error_out=False
        )
    form = EmptyForm()
    formNotify = SendNotifyForm()
    return render_template(
        "user.html",
        title="Профиль - {}".format(username),
        user=user,
        posts=posts.items,
        comments=comments.items,
        form=form,
        pagination_posts=posts,
        pagination_comments=comments,
        m=markdown.markdown,
        page_posts=page_posts,
        page_comments=page_comments,
        len=len,
        formNotify=formNotify,
    )


@bp.route("/comment/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    url = request.args.get("url")
    if (
        comment.author != current_user
        and not current_user.admin()
        and not current_user.moderator()
    ):
        abort(403)
    db.session.delete(comment)
    db.session.commit()
    flash(_("Комментарий удалён"), "success")
    if url:
        return redirect(url)
    else:
        return redirect(url_for("main.post_detail", post_id=comment.commented_on))


@bp.route("/user/<username>/popup")
@login_required
def user_popup(username):
    user = User.query.filter_by(username=username).first_or_404()
    form = EmptyForm()
    return render_template("user_popup.html", user=user, form=form)


@bp.route("/search", methods=["GET", "POST"])
def search():
    page = request.args.get("page", 1, type=int)
    sss = "%" + request.args.get("search", "", type=str) + "%"
    posts = (
        Post.query.filter_by(show=True)
        .filter(or_(Post.description.like(sss), Post.title.like(sss)))
        .paginate(
            page=page, per_page=current_app.config["POSTS_PER_PAGE"], error_out=False
        )
    )
    return render_template(
        "search.html",
        posts=posts.items,
        page=page,
        pagination=posts,
        title=f"Поиск: {request.args.get('search', '', type=str)}",
        str=str,
    )


@bp.route("/user/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    old_email = current_user.email
    form = EditProfileForm(current_user.username, current_user.email, current_user.id)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        current_user.email = form.email.data
        current_user.message_setting = form.message_setting.data
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.anonymous_show = form.anonymous_show.data
        current_user.show_profile_id = form.profile_access.data
        if form.photo.data:
            filename = f"app/static/{current_user.id}{os.path.splitext(form.photo.data.filename)[-1]}"
            current_user.set_avatar(filename)
        if old_email != form.email.data:
            current_user.confirmed = False
            send_email(
                user.email, "Подтвердите свой аккаунт - DigitalBlog", confirm_html
            )
        db.session.commit()
        flash(_("Изменения сохранены"), "success")
        return redirect(url_for("main.user", username=current_user.username))
    elif request.method == "GET":
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
        form.email.data = current_user.email
        form.message_setting.data = current_user.message_setting
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.anonymous_show.data = current_user.anonymous_show
        form.profile_access.data = current_user.show_profile_id
    return render_template(
        "edit_profile.html", title="Редактирование профиля", form=form
    )


@bp.route("/user/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
def edit_user_profile(user_id):
    user = User.query.get_or_404(user_id)
    if not current_user.admin():
        abort(403)
    if user.main_admin() and not current_user.main_admin():
        abort(403)
    if current_user.main_admin():
        form = EditProfileMainAdminForm(user.username, user.email, user.id)
    else:
        form = EditProfileAdminForm(user.username, user.id)
    if form.validate_on_submit():
        if current_user.main_admin():
            user.username = form.username.data
            user.about_me = form.about_me.data
            user.email = form.email.data
            user.confirmed = form.confirmed.data
            user.role = form.role.data
            user.message_setting = form.message_setting.data
            user.blogger = form.blogger.data
            user.banned = form.banned.data
            user.first_name = form.first_name.data
            user.last_name = form.last_name.data
            user.banned_reason = form.banned_reason.data
            user.stroage_granted = form.granted_stroage.data
            user.anonymous_show = form.anonymous_show.data
            user.show_profile_id = form.profile_access.data
        else:
            user.username = form.username.data
            user.about_me = form.about_me.data
            user.message_setting = form.message_setting.data
            user.blogger = form.blogger.data
            user.first_name = form.first_name.data
            user.last_name = form.last_name.data
            user.banned = form.banned.data
            user.banned_reason = form.banned_reason.data
            user.stroage_granted = form.granted_stroage.data
            user.anonymous_show = form.anonymous_show.data
            user.show_profile_id = form.profile_access.data
        if form.photo.data:
            filename = (
                f"app/static/{user.id}{os.path.splitext(form.photo.data.filename)[-1]}"
            )
            user.set_avatar(filename)
        db.session.commit()
        flash(_("Изменения сохранены"), "success")
        return redirect(url_for("main.user", username=user.username))
    elif request.method == "GET":
        if current_user.main_admin():
            form.username.data = user.username
            form.about_me.data = user.about_me
            form.email.data = user.email
            form.confirmed.data = user.confirmed
            form.role.data = user.role
            form.message_setting.data = user.message_setting
            form.blogger.data = user.blogger
            form.banned.data = user.banned
            form.first_name.data = user.first_name
            form.last_name.data = user.last_name
            form.banned_reason.data = user.banned_reason
            form.granted_stroage.data = user.stroage_granted
            form.anonymous_show.data = user.anonymous_show
            form.profile_access.data = user.show_profile_id
        else:
            form.username.data = user.username
            form.about_me.data = user.about_me
            form.message_setting.data = user.message_setting
            form.blogger.data = user.blogger
            form.first_name.data = user.first_name
            form.last_name.data = user.last_name
            form.banned.data = user.banned
            form.banned_reason.data = user.banned_reason
            form.granted_stroage.data = user.stroage_granted
            form.anonymous_show.data = user.anonymous_show
            form.profile_access.data = user.show_profile_id
    return render_template(
        "edit_profile.html", title="Редактирование профиля", form=form, user=user
    )


@bp.route("/user/<int:user_id>/delete", methods=["GET", "POST"])
@login_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    url = request.args.get("url")
    if current_user.main_admin() or current_user == user:
        if user.main_admin() and not current_user.main_admin():
            abort(403)
        user.delete_avatar()
        msgs = Message.query.filter(
            (Message.recipient_id == user.id) | (Message.sender_id == user.id)
        ).all()
        for m in msgs:
            try:
                os.remove(f"app/uploads/message-{m.id}/{m.filename}")
                os.rmdir(f"app/uploads/message-{m.id}")
            except:
                pass
        Message.query.filter(
            (Message.recipient_id == user.id) | (Message.sender_id == user.id)
        ).delete()
        posts = Post.query
        for post in posts:
            post.favourites_count = post.favourites.count()
            post.views_count = post.views.count()
            db.session.commit()
        posts = Post.query.filter_by(user_id=user.id).all()
        for post in posts:
            try:
                os.remove(f"app/uploads/post-{post.id}/{post.filename}")
                os.rmdir(f"app/uploads/post-{post.id}")
            except:
                pass
        db.session.delete(user)
        db.session.commit()
        flash(_("Пользователь %(username)s удалён", username=user.username), "success")
    else:
        abort(403)
    return redirect(url_for("main.users"))


@bp.route("/users", methods=["GET", "POST"])
def users():
    page = request.args.get("page", 1, type=int)
    if not current_user.is_anonymous:
        show_users = request.cookies.get("show_users", "1")
        if show_users == "3":
            query = (
                User.query.join(Followers, User.id == Followers.followed_id)
                .filter(Followers.follower_id == current_user.id)
                .order_by(User.last_seen.desc())
            )
        elif show_users == "4":
            query = (
                User.query.join(Followers, User.id == Followers.follower_id)
                .filter(Followers.followed_id == current_user.id)
                .order_by(User.last_seen.desc())
            )
        elif show_users == "5" and current_user.main_admin():
            query = User.query.filter_by(confirmed=False).order_by(
                User.last_seen.desc()
            )
        elif show_users == "6" and current_user.main_admin():
            query = User.query.filter_by(banned=True).order_by(User.last_seen.desc())
        elif show_users == "2":
            query = (
                User.query.join(Followers, User.id == Followers.follower_id)
                .filter(Followers.followed_id == current_user.id)
                .filter(
                    User.id.in_(
                        User.query.join(Followers, User.id == Followers.followed_id)
                        .filter(Followers.follower_id == current_user.id)
                        .with_entities(User.id)
                    )
                )
                .order_by(User.last_seen.desc())
            )
        else:
            query = User.query.order_by(User.last_seen.desc())
    else:
        query = User.query.order_by(User.last_seen.desc())
        show_users = 1
    users = query.paginate(
        page=page, per_page=current_app.config["POSTS_PER_PAGE"], error_out=False
    )
    return render_template(
        "users.html",
        description="Сообщество для программистов и увлекающихся IT. Подписывайтесь, создавайте публикации, обсуждайте, ставьте лайки, пишите личные сообщения, а также возможность подкреплять файлы к публикациям и сообщениям.",
        title="Пользователи",
        users=users.items,
        datetime=datetime,
        pagination=users,
        show_users=show_users,
        User=User,
    )


@bp.route("/about", methods=["GET", "POST"])
def about():
    return render_template("about.html")


@bp.route("/follow/<username>", methods=["POST"])
@login_required
def follow(username):
    form = EmptyForm()
    url = request.args.get("url")
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first_or_404()
        if user == current_user:
            flash("Вы не можете подписаться на себя!", "warning")
            return redirect(url_for("main.index"))
        current_user.follow(user)
        db.session.commit()
        flash(f"Вы подписались на {username}", "success")
        return redirect(url)
    else:
        return redirect(url_for("main.index"))


@bp.route("/unfollow/<username>", methods=["POST"])
@login_required
def unfollow(username):
    form = EmptyForm()
    url = request.args.get("url")
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first_or_404()
        if user == current_user:
            flash("Вы не можете отписаться от себя!", "warning")
            return redirect(url_for("main.index"))
        current_user.unfollow(user)
        db.session.commit()
        flash(f"Вы отписались от {username}", "success")
        return redirect(url)
    else:
        return redirect(url_for("main.index"))


@bp.route("/post/<int:post_id>/favourite")
@login_required
def favourite_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.show or current_user.admin() or current_user == post.author:
        pass
    else:
        abort(403)
    current_user.favourite_post(post)
    db.session.commit()
    return redirect(request.args.get("url"))


@bp.route("/billing")
@login_required
def billing():
    return render_template(
        "billing.html",
        title="Использование",
        used_space=current_user.stroage_used,
        total_space=current_user.stroage_granted,
        user=current_user,
    )


@bp.route("/notifies")
@login_required
def notifies():
    current_user.add_notification("unread_notify_count", 0)
    db.session.commit()
    page = request.args.get("page", 1, type=int)
    ns = current_user.notifies
    ns = ns.order_by(Notify.timestamp.desc()).paginate(
        page=page, per_page=current_app.config["POSTS_PER_PAGE"], error_out=False
    )

    @after_this_request
    def update(response):
        current_user.last_notify_read_time = datetime.utcnow()
        db.session.commit()
        return response

    return render_template(
        "notifies.html", title="Уведомления", ns=ns.items, len=len, pagination=ns
    )


@bp.route("/post/<int:post_id>/unfavourite")
@login_required
def unfavourite_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.show or current_user.admin() or current_user == post.author:
        pass
    else:
        abort(403)
    current_user.unfavourite_post(post)
    db.session.commit()
    return redirect(request.args.get("url"))


@bp.route("/comment/<int:comment_id>/like")
@login_required
def like_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    current_user.like_comment(comment)
    db.session.commit()
    return redirect(request.args.get("url"))


@bp.route("/comment/<int:comment_id>/unlike")
@login_required
def unlike_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    current_user.unlike_comment(comment)
    db.session.commit()
    return redirect(request.args.get("url"))


@bp.route("/send_message/<recipient>", methods=["GET", "POST"])
@login_required
def send_message(recipient):
    user = User.query.filter_by(username=recipient).first_or_404()
    if user.message_setting != 0:
        if current_user.admin() or current_user == user:
            pass
        elif user.message_setting == 1 and not current_user.is_following(user):
            abort(403)
        elif user.message_setting == 2 and not current_user.is_followed_by(user):
            abort(403)
        elif user.message_setting == 3 and not (
            current_user.is_following(user) and current_user.is_followed_by(user)
        ):
            abort(403)
        elif user.message_setting == 4:
            abort(403)
    form = MessageForm(
        current_user.id, current_user.stroage_used, current_user.stroage_granted
    )
    if form.validate_on_submit():
        time = datetime.utcnow()
        message = Message(
            author=current_user,
            recipient=user,
            body=form.body.data,
            title=form.title.data,
            timestamp=time,
            last_update_time=time,
        )
        f = form.file.data
        db.session.add(message)
        user.add_notification("unread_message_count", user.new_messages())
        db.session.commit()
        if f:
            fn = os.path.basename(f[0])
            message_url = f"app/uploads/message-{message.id}/{fn}"
            try:
                os.remove(f"app/{message_url}")
                os.rename(f[0], f"app/uploads/message-{message.id}/{fn}")
            except:
                os.makedirs(f"app/uploads/message-{message.id}", exist_ok=True)
                os.rename(f[0], f"app/uploads/message-{message.id}/{fn}")
                message.file_size = f[1]
                current_user.stroage_used += f[1]
            message.filename = fn
            db.session.commit()
        flash(f"Ваше сообщение отправлено {recipient}", "success")
        return redirect(url_for("main.message_detail", message_id=message.id))
    form.body.data = " "
    form.title.data = ""
    return render_template(
        "send_message.html",
        title=f"Отправить личное сообщение {user.username}".format(recipient),
        form=form,
        recipient=recipient,
    )


@bp.route("/messages")
@login_required
def messages():
    current_user.add_notification("unread_message_count", 0)
    db.session.commit()
    page = request.args.get("page", 1, type=int)
    if current_user.main_admin():
        messages = Message.query.order_by(Message.timestamp.desc()).paginate(
            page=page, per_page=current_app.config["POSTS_PER_PAGE"], error_out=False
        )
    else:
        messages = Message.query.filter(
            (Message.recipient_id == current_user.id)
            | (Message.sender_id == current_user.id)
        )
        messages = messages.order_by(Message.timestamp.desc()).paginate(
            page=page, per_page=current_app.config["POSTS_PER_PAGE"], error_out=False
        )

    @after_this_request
    def update(response):
        current_user.last_message_read_time = datetime.utcnow()
        db.session.commit()
        return response

    return render_template(
        "messages.html",
        title="Личные сообщения",
        messages=messages.items,
        len=len,
        pagination=messages,
    )


@bp.route("/notifications")
@login_required
def notifications():
    current_user.last_seen = datetime.utcnow()
    db.session.commit()
    since = request.args.get("since", 0.0, type=float)
    notifications = current_user.notifications.filter(
        Notification.timestamp > since
    ).order_by(Notification.timestamp.asc())
    return jsonify(
        [
            {"name": n.name, "data": n.get_data(), "timestamp": n.timestamp}
            for n in notifications
        ]
    )


@bp.route("/post/<int:post_id>/delete", methods=["GET", "POST"])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if current_user == post.author or current_user.admin():
        try:
            os.remove(f"app/uploads/post-{post_id}/{post.filename}")
            os.rmdir(f"app/uploads/post-{post_id}")
        except:
            pass
        post.author.stroage_used -= post.file_size
        db.session.delete(post)
        db.session.commit()
        flash(f"Публикация {post.title} удалена", "success")
    else:
        abort(403)
    return redirect(url_for("main.index"))


@bp.route("/post/<int:post_id>/update", methods=["GET", "POST"])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user and not current_user.admin():
        abort(403)
    old_title = post.title
    old_body = post.body
    if post.filename:
        name = post.filename
        file = True
    else:
        file = False
        name = ""
    real_stroage = post.author.stroage_used - post.file_size
    form = PostForm(current_user.id, real_stroage, current_user.stroage_granted)
    if form.validate_on_submit():
        post.title = form.title.data
        post.body = form.body.data
        post.allow_comments = form.allow_comments.data
        post.show = form.show.data
        post.anonymous_show = form.anonymous_show.data
        soup = BeautifulSoup(form.body.data, "html.parser")
        text = soup.get_text()
        cleaned_text = " ".join(text.split())
        post.description = cleaned_text
        if old_title != post.title or old_body != post.body:
            post.last_update_time = datetime.utcnow()
        f = form.file.data
        if f:
            fn = os.path.basename(f[0])
            try:
                os.remove(f"app/uploads/post-{post.id}/{post.filename}")
                os.rename(f[0], f"app/uploads/post-{post.id}/{fn}")
                new_stroage_used = (
                    int(post.author.stroage_used) - int(post.file_size) + int(f[1])
                )
                post.file_size = f[1]
                post.author.stroage_used = new_stroage_used
            except Exception as e:
                os.makedirs(f"app/uploads/post-{post.id}", exist_ok=True)
                os.rename(f[0], f"app/uploads/post-{post.id}/{fn}")
                post.file_size = f[1]
                post.author.stroage_used += f[1]
            post.filename = fn
            db.session.commit()
            flash("Изменения сохранены", "success")
            return redirect(url_for("main.post_detail", post_id=post.id))
        db.session.commit()
        flash("Изменения сохранены", "success")
        return redirect(url_for("main.post_detail", post_id=post.id))
    form.body.data = post.body
    form.title.data = post.title
    form.allow_comments.data = post.allow_comments
    form.show.data = post.show
    form.anonymous_show.data = post.anonymous_show
    return render_template(
        "create_post.html",
        title="Редактирование публикации",
        form=form,
        file=file,
        name=name,
        post=post,
    )


@bp.route("/message/<int:message_id>/update", methods=["GET", "POST"])
@login_required
def update_message(message_id):
    message = Message.query.get_or_404(message_id)
    if message.author != current_user and not current_user.main_admin():
        abort(403)
    old_title = message.title
    old_body = message.body
    if message.filename:
        name = message.filename
        file = True
    else:
        file = False
        name = ""
    real_stroage = message.author.stroage_used - message.file_size
    form = MessageForm(current_user.id, real_stroage, current_user.stroage_granted)
    if form.validate_on_submit():
        message.title = form.title.data
        message.body = form.body.data
        if old_title != message.title or old_body != message.body:
            message.last_update_time = datetime.utcnow()
        db.session.commit()
        f = form.file.data
        if f:
            fn = os.path.basename(f[0])
            try:
                os.remove(f"app/uploads/message-{message.id}/{message.filename}")
                os.rename(f[0], f"app/uploads/message-{message.id}/{fn}")
                new_stroage_used = (
                    int(message.author.stroage_used)
                    - int(message.file_size)
                    + int(f[1])
                )
                message.file_size = f[1]
                message.author.stroage_used = new_stroage_used
            except Exception as e:
                os.makedirs(f"app/uploads/message-{message.id}", exist_ok=True)
                os.rename(f[0], f"app/uploads/message-{message.id}/{fn}")
                message.file_size = f[1]
                message.author.stroage_used += f[1]
            message.filename = fn
            db.session.commit()
        flash("Изменения сохранены", "success")
        return redirect(url_for("main.message_detail", message_id=message_id))
    form.body.data = message.body
    form.title.data = message.title
    return render_template(
        "update_message.html",
        title="Редактирование сообщения",
        form=form,
        name=name,
        file=file,
        message=message,
    )


@bp.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm(current_user.password)
    if form.validate_on_submit():
        current_user.set_password(form.password.data)
        db.session.commit()
        flash("Изменения сохранены", "success")
        return redirect(url_for("main.user", username=current_user.username))
    return render_template("change_password.html", title="Изменение пароля", form=form)


@bp.route("/comment/<int:comment_id>/update", methods=["GET", "POST"])
@login_required
def update_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if (
        comment.author != current_user
        and not current_user.admin()
        and not current_user.moderator()
    ):
        abort(403)
    form = CommentForm()
    old_comment = comment.comment
    if form.validate_on_submit():
        comment.comment = form.comment.data
        if old_comment != comment.comment:
            comment.last_update_time = datetime.utcnow()
        db.session.commit()
        flash("Изменения сохранены", "success")
        return redirect(url_for("main.post_detail", post_id=comment.post.id))
    form.comment.data = comment.comment
    return render_template(
        "update_comment.html",
        title="Редактирование комментария",
        form=form,
        comment=comment,
    )


@bp.route("/message/<int:message_id>/delete", methods=["GET", "POST"])
@login_required
def delete_message(message_id):
    message = Message.query.get_or_404(message_id)
    if current_user == message.author or current_user.main_admin():
        try:
            os.remove(f"app/uploads/message-{message_id}/{message.filename}")
            os.rmdir(f"app/uploads/message-{message_id}")
        except:
            pass
        message.author.stroage_used -= message.file_size
        db.session.delete(message)
        db.session.commit()
        flash("Сообщение удалено", "success")
    else:
        abort(403)
    return redirect(url_for("main.messages"))


@bp.route("/post/create", methods=["GET", "POST"])
@login_required
def new_post():
    if not current_user.blogger:
        abort(403)
    form = PostForm(
        current_user.id, current_user.stroage_used, current_user.stroage_granted
    )
    if form.validate_on_submit():
        soup = BeautifulSoup(form.body.data, "html.parser")
        text = soup.get_text()
        cleaned_text = " ".join(text.split())
        time = datetime.utcnow()
        post = Post(
            title=form.title.data,
            body=form.body.data,
            author=current_user,
            timestamp=time,
            last_update_time=time,
            allow_comments=form.allow_comments.data,
            show=form.show.data,
            anonymous_show=form.anonymous_show.data,
            description=cleaned_text,
        )
        f = form.file.data
        db.session.add(post)
        db.session.commit()
        if f:
            fn = os.path.basename(f[0])
            post_url = f"app/uploads/post-{post.id}/{fn}"
            try:
                os.remove(f"app/{post_url}")
                os.rename(f[0], f"app/uploads/post-{post.id}/{fn}")
            except:
                os.makedirs(f"app/uploads/post-{post.id}", exist_ok=True)
                os.rename(f[0], f"app/uploads/post-{post.id}/{fn}")
                post.file_size = f[1]
                current_user.stroage_used += f[1]
            post.filename = fn
            db.session.commit()
        flash("Ваша публикация размещена", "success")
        return redirect(url_for("main.post_detail", post_id=post.id))
    form.show.data = True
    form.anonymous_show.data = True
    form.allow_comments.data = True
    form.body.data = " "
    form.title.data = ""
    form.tag.data = ""
    return render_template("create_post.html", title="Новая публикация", form=form)


@bp.route("/post/<int:post_id>/file/download")
def download_file_from_post(post_id):
    post = Post.query.get_or_404(post_id)
    try:
        return send_file(f"uploads/post-{post_id}/{post.filename}", as_attachment=True)
    except:
        abort(404)


@bp.route("/post/<int:post_id>/file")
def file_from_post(post_id):
    post = Post.query.get_or_404(post_id)
    try:
        return send_file(f"uploads/post-{post_id}/{post.filename}")
    except:
        abort(404)


@bp.route("/message/<int:message_id>/file/download")
@login_required
def download_file_from_message(message_id):
    message = Message.query.get_or_404(message_id)
    if (
        current_user != message.author
        and current_user != message.recipient
        and not current_user.main_admin()
    ):
        abort(403)
    try:
        return send_file(
            f"uploads/message-{message_id}/{message.filename}", as_attachment=True
        )
    except:
        abort(404)


@bp.route("/message/<int:message_id>/file")
@login_required
def file_from_message(message_id):
    message = Message.query.get_or_404(message_id)
    if (
        current_user != message.author
        and current_user != message.recipient
        and not current_user.main_admin()
    ):
        abort(403)
    try:
        return send_file(f"uploads/message-{message_id}/{message.filename}")
    except:
        abort(404)


@bp.route("/post/<int:post_id>/file/delete")
@login_required
def delete_file_from_post(post_id):
    post = Post.query.get_or_404(post_id)
    if current_user != post.author and not current_user.admin():
        abort(403)
    try:
        os.remove(f"app/uploads/post-{post_id}/{post.filename}")
        os.rmdir(f"app/uploads/post-{post_id}")
        post.filename = None
        post.author.stroage_used -= post.file_size
        post.file_size = 0
        db.session.commit()
        return redirect(url_for("main.update_post", post_id=post_id))
    except:
        post.filename = None
        post.file_size = 0
        db.session.commit()
        return redirect(url_for("main.update_post", post_id=post_id))


@bp.route("/message/<int:message_id>/file/delete")
@login_required
def delete_file_from_message(message_id):
    message = Message.query.get_or_404(message_id)
    if current_user != message.author and not current_user.main_admin():
        abort(403)
    try:
        os.remove(f"app/uploads/message-{message_id}/{message.filename}")
        os.rmdir(f"app/uploads/message-{message_id}")
        message.filename = None
        message.author.stroage_used -= message.file_size
        message.file_size = 0
        db.session.commit()
        return redirect(url_for("main.update_message", message_id=message_id))
    except:
        message.filename = None
        message.file_size = 0
        db.session.commit()
        return redirect(url_for("main.update_message", message_id=message_id))


@bp.route("/user/<int:user_id>/avatar/delete")
@login_required
def delete_avatar(user_id):
    user = User.query.get_or_404(user_id)
    if user != current_user and not current_user.admin():
        abort(403)
    user.delete_avatar()
    return redirect(request.args.get("url"))


@bp.route("/user/<int:user_id>/recount_stroage")
@login_required
def recount_stroage(user_id):
    user = User.query.get_or_404(user_id)
    if current_user.admin():
        pass
    else:
        abort(403)
    recounted_stroage = 0
    posts = user.posts
    for post in posts:
        recounted_stroage += post.file_size
    msgs = user.messages_sent
    for m in msgs:
        recounted_stroage += m.file_size
    user.stroage_used = recounted_stroage
    db.session.commit()
    flash("Пересчёт произведён", "success")
    return redirect(request.args.get("url"))


@bp.route("/query/run")
@login_required
def run_query():
    if not current_user.main_admin():
        abort(403)
    users = User.query
    for i in users:
        i.add_notify(
            "DigitalBlog восстановлен!",
            "<p>Спустя ровно сутки после начала инцидента DigitalBlog был наконец-то восстановлен! У хостинга были большие проблемы связанные с файловой системой, поэтому, к сожалению, файлы прикреплённые к публикациям безвозвратно утеряны, но к счастью все аватары были восстановлены. Я надеюсь, что больше такого не повторится и буду делать всё для этого.</p><p>С уважением,</p><p>DigitalBlog</p>",
        )
    return "Query runned"


@bp.route("/user/<int:user_id>/send_notify", methods=["POST"])
@login_required
def send_notify(user_id):
    if not current_user.moderator():
        abort(403)
    if request.method == "POST":
        user = User.query.get_or_404(user_id)
        user.add_notify(request.form.get("title"), request.form.get("body"))
        flash = ("Уведомление отправлено пользователю", "success")
        return redirect(request.args.get("url"))
