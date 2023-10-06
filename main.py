from app import create_app
from app.models import (
    User,
    Post,
    Message,
    Followers,
    Notification,
    Comment,
    CommentLikes,
    PostView,
    PostFavourites,
)

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {
        "db": db,
        "User": User,
        "Post": Post,
        "Message": Message,
        "Followers": Followers,
        "Notification": Notification,
        "Comment": Comment,
        "PostFavourites": PostFavourites,
        "CommentLikes": CommentLikes,
        "PostView": PostView,
    }


app.run(host="0.0.0.0")
