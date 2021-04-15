from datetime import datetime
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flaskblog import db, login_manager, app
from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    your_name = db.Column(db.String(20), nullable=False)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.png')
    password = db.Column(db.String(60), nullable=False)
    cmmt = db.relationship('Comment', backref='author_user', lazy=True)
    movies = db.relationship('Movie', backref='movie_author', lazy=True)

    def get_reset_token(self, expires_sec=180):
        s = Serializer(app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.your_name}','{self.username}', '{self.email}', '{self.image_file}')"


class Post(db.Model):
    post_id = db.Column(db.Integer, primary_key=True)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"('{self.date_posted}')"
class Comment(db.Model,UserMixin):
    comment_id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.movie_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    def __repr__(self):
        return f"Comment('{self.content}','{self.movie_id}','{self.user_id}')"

class Movie(db.Model,UserMixin):
    movie_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    language = db.Column(db.String(100), nullable=False)
    genres = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer)
    link = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    movie_image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Movie('{self.title}', '{self.language}', '{self.genres}', '{self.year}', '{self.link}', '{self.content}','{self.movie_image_file}')"

class User_Movie(db.Model):
    user_movie_id = db.Column(db.Integer, primary_key=True)
    movie_id      = db.Column(db.Integer)

    def __repr__(self):
        return f"User_Movie('{self.movie_id}')"

class Credits(db.Model):
    user_movie_id = db.Column(db.Integer, primary_key=True)
    movie_id      = db.Column(db.Integer)

    def __repr__(self):
        return f"Credits('{self.movie_id}')"
        