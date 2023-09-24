from datetime import datetime
from hashlib import md5
import json
from time import time
from flask import current_app, url_for
from flask_login import UserMixin, current_user
from itsdangerous import URLSafeTimedSerializer as Serializer
import os
from app import db, login, bcrypt
from sqlalchemy import*
import shutil
from .email import send_email
import os.path as op

class Followers(db.Model):
    __tablename__ = 'followers'
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)

class PostView(db.Model):
    __tablename__ = 'post_views'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), primary_key=True)

class PostFavourites(db.Model):
    __tablename__ = 'post_favourites'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), primary_key=True)

class Stuff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True)
    content = db.Column(db.String)

class CommentLikes(db.Model):
    __tablename__ = 'comment_likes'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), primary_key=True)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, index=True, unique=True)
    first_name = db.Column(db.String)
    last_name = db.Column(db.String)
    email = db.Column(db.String, index=True, unique=True)
    password = db.Column(db.String)
    avatar_url=db.Column(db.String, default="static/default.png")
    stroage_used=db.Column(db.Integer, default=0)
    stroage_granted=db.Column(db.Integer)
    sub_id=db.Column(db.SmallInteger, default=0)
    comments = db.relationship('Comment', backref='author', lazy='dynamic', cascade = "all,delete")
    posts = db.relationship('Post', backref='author', lazy='dynamic', cascade = "all,delete")
    about_me = db.Column(db.String)
    message_setting = db.Column(db.SmallInteger, default=0)
    role = db.Column(db.SmallInteger)
    confirmed = db.Column(db.Boolean, default=False)
    banned = db.Column(db.Boolean, default=False)
    banned_reason = db.Column(db.String, default="")
    blogger = db.Column(db.Boolean, default=False)
    member_since = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    email_notify = db.Column(db.Boolean, default=True)
    show_profile_id = db.Column(db.SmallInteger, default=0)
    anonymous_show = db.Column(db.Boolean, default=True)
    viewed_posts = db.relationship(
        'PostView',
        foreign_keys='PostView.user_id',
        backref='user', lazy='dynamic',cascade = "all,delete")
    liked_comments = db.relationship(
        'CommentLikes',
        foreign_keys='CommentLikes.user_id',
        backref='user', lazy='dynamic', cascade = "all,delete")
    favourited_posts = db.relationship(
        'PostFavourites',
        foreign_keys='PostFavourites.user_id',
        backref='user', lazy='dynamic', cascade = "all,delete")
    notifies = db.relationship(
        'Notify',
        foreign_keys='Notify.recipient_id',
        backref='user', lazy='dynamic', cascade = "all,delete")
    followed = db.relationship('Followers',
                                    foreign_keys='Followers.follower_id',
                                    backref='follower', lazy='dynamic', cascade = "all,delete")
    followers = db.relationship('Followers',
                                    foreign_keys='Followers.followed_id',
                                    backref='followed', lazy='dynamic', cascade = "all,delete")
    messages_sent = db.relationship('Message',
                                    foreign_keys='Message.sender_id',
                                    backref='author', lazy='dynamic', cascade = "all,delete")
    messages_received = db.relationship('Message',
                                        foreign_keys='Message.recipient_id',
                                        backref='recipient', lazy='dynamic', cascade = "all,delete")
    last_message_read_time = db.Column(db.DateTime, default=datetime.utcnow)
    last_notify_read_time = db.Column(db.DateTime, default=datetime.utcnow)
    notifications = db.relationship('Notification', backref='user', lazy='dynamic', cascade = "all,delete")
    
    def __repr__(self):
        return '<User {}>'.format(self.username)
    
    def main_admin(self):
    	if self.role==4:
    		return True
    	else:
    		return False

    def admin(self):
        if self.role==3 or self.role==4:
            return True
        else:
            return False
    
    def moderator(self):
        if self.role==2 or self.role==3 or self.role==4:
            return True
        else:
            return False

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')
        db.session.commit()

    def check_password(self, password):
        valid = bcrypt.check_password_hash(self.password, password)
        return valid
    
    def set_avatar(self, path):
        f=os.path.basename(path)
        self.avatar_url=f'uploads/avatar-{self.id}/{f}'
        db.session.commit()
        try:
            os.remove(f'app/{self.avatar_url}')
            os.rename(path, f'app/uploads/avatar-{self.id}/{f}')
        except:
            os.makedirs(f"app/uploads/avatar-{self.id}", exist_ok=True)
            os.rename(path, f'app/uploads/avatar-{self.id}/{f}')
    
    def delete_avatar(self):
        if self.avatar_url!="static/default.png":
            try:
                os.remove(f'app/{self.avatar_url}')
                os.rmdir(f"app/uploads/avatar-{self.id}")
            except:
                pass
            self.avatar_url="static/default.png"
            db.session.commit()
   
    def avatar(self):
        return url_for("main.avatar", user_id=self.id)
    
    def view(self, post):
        if not PostView.query.filter(PostView.user_id == self.id, PostView.post_id == post.id).count() > 0:
            view=PostView(user_id=self.id, post_id=post.id)
            post.views_count += 1
            db.session.add(view)
            db.session.commit()

    def follow(self, user):
        if not self.is_following(user):
            f = Followers(follower=self, followed=user)
            db.session.add(f)

    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)

    def is_following(self, user):
        return self.followed.filter_by(
            followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        return self.followers.filter_by(
            follower_id=user.id).first() is not None
    
    def followed_posts(self):
        return Post.query.join(Followers, Followers.followed_id == Post.user_id).filter(Followers.follower_id == self.id)

    def rate_post(self, post, t):
        if not self.is_rated_post(post):
            rate = PostReactions(user_id=self.id, post_id=post.id, t=t)
            if t==1:
            	post.likes_count += 1
            else:
            	post.dislikes_count += 1
            db.session.add(rate)
        else:
        	return

    def unrate_post(self, post):
        rate=PostReactions.query.filter(PostReactions.user_id == self.id,PostReactions.post_id == post.id)
        if self.is_rated_post(post):
            if rate.t==1:
                post.likes_count -= 1
            else:
                post.dislikes_count -= 1
            PostReactions.query.filter_by(
                user_id=self.id,
                post_id=post.id).delete()

    def favourite_post(self, post):
        if not self.is_favourited_post(post):
            like = PostFavourites(user_id=self.id, post_id=post.id)
            post.favourites_count += 1
            db.session.add(like)
   
    def unfavourite_post(self, post):
        if self.is_favourited_post(post):
            post.favourites_count -= 1
            PostFavourites.query.filter_by(
                user_id=self.id,
                post_id=post.id).delete()
    
    def is_favourited_post(self, post):
        return PostFavourites.query.filter(
            PostFavourites.user_id == self.id,
            PostFavourites.post_id == post.id).count() > 0 
    
    def like_comment(self, comment):
        if not self.is_liking_comment(comment):
            like = CommentLikes(user_id=self.id, comment_id=comment.id)
            db.session.add(like)

    def unlike_comment(self, comment):
        if self.is_liking_comment(comment):
            CommentLikes.query.filter_by(
                user_id=self.id,
                comment_id=comment.id).delete()

    def is_liking_comment(self, comment):
        return CommentLikes.query.filter(
            CommentLikes.user_id == self.id,
            CommentLikes.comment_id == comment.id).count() > 0
        
    def friends(self):
        friends=User.query.join(Followers, User.id == Followers.follower_id).filter(Followers.followed_id == self.id).filter(User.id.in_(User.query.join(Followers, User.id == Followers.followed_id).filter(Followers.follower_id == self.id).with_entities(User.id)))
        return friends

    def new_messages(self):
        last_read_time = self.last_message_read_time or datetime(1900, 1, 1)
        return Message.query.filter_by(recipient=self).filter(Message.timestamp > last_read_time).count()

    def new_notifies(self):
        last_read_time = self.last_notify_read_time or datetime(1900, 1, 1)
        return Notify.query.filter_by(user=self).filter(Notify.timestamp > last_read_time).count()

    def add_notification(self, name, data):
        self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, payload_json=json.dumps(data), user=self)
        db.session.add(n)
        return n

    def add_notify(self, title, body):
        n=Notify(title=title, body=body, user=self)
        self.add_notification('unread_notify_count', self.new_notifies())
        if self.email_notify==True:
            send_email(self.email, f'{n.title} - DigitalBlog', n.body)
        db.session.add(n)
        db.session.commit()
        return
    
    def generate_confirmation_token(self):
        s=Serializer(current_app.config['SECRET_KEY'])
        return s.dumps(self.email, salt=current_app.config['SECURITY_PASSWORD_SALT'])
    
    def confirm_token(self, token, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            email = s.loads(token,salt=current_app.config['SECURITY_PASSWORD_SALT'],max_age=expiration)
        except:
            return False
        return email

    def generate_resetPassword_token(self):
        s=Serializer(current_app.config['SECRET_KEY'])
        return s.dumps(self.email, salt=current_app.config['SECURITY_PASSWORD_SALT'])

    @staticmethod
    def confirm_token_user(token):
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            email = s.loads(token,salt=current_app.config['SECURITY_PASSWORD_SALT'],max_age=3600)
        except:
            return None
        if email:
            return User.query.filter_by(email=email).first()
        return None
    def get_id(self):
        return str(self.email)

@login.user_loader
def load_user(email):
    return User.query.filter_by(email=email).first()

class Notify(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    title = db.Column(db.String)
    body = db.Column(db.String)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return '<Notify {}>'.format(self.title)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    body = db.Column(db.String)
    timestamp = db.Column(db.DateTime, index=True)
    last_update_time = db.Column(db.DateTime, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    filename=db.Column(db.String)
    anonymous_show=db.Column(db.Boolean, default=False)
    file_size=db.Column(db.Integer, default=0)
    comments = db.relationship('Comment', backref='post', lazy='dynamic', cascade = "all,delete")
    views_count = db.Column(db.Integer, default=0)
    views = db.relationship('PostView', backref='post', lazy='dynamic', cascade = "all,delete")
    rate_count = db.Column(db.Integer, default=0)
    show=db.Column(db.Boolean, default=False)
    allow_comments=db.Column(db.Boolean, default=True)
    favourites_count= db.Column(db.Integer, default=0)
    favourites = db.relationship('PostFavourites', backref='post', lazy='dynamic', cascade = "all,delete")

    def __repr__(self):
        return '<Post {}>'.format(self.title)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    title = db.Column(db.String)
    read = db.Column(db.Boolean, default=False)
    read_time = db.Column(db.DateTime)
    body = db.Column(db.String)
    filename = db.Column(db.String)
    file_size=db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime, index=True)
    last_update_time = db.Column(db.DateTime, index=True)

    def __repr__(self):
        return '<Message {}>'.format(self.title)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.Float, index=True, default=time)
    payload_json = db.Column(db.String)

    def get_data(self):
        return json.loads(str(self.payload_json))

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    comment = db.Column(db.String)
    commented_on = db.Column(db.Integer, db.ForeignKey('post.id'))
    commented_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime, index=True)
    last_update_time = db.Column(db.DateTime, index=True)
    likes_count = db.Column(db.Integer, default=0)
    likes = db.relationship('CommentLikes', backref='comment', lazy='dynamic', cascade = "all,delete")