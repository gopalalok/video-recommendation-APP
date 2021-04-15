import os
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort
from flaskblog import app, db, bcrypt, mail
from flaskblog.forms import (RegistrationForm, LoginForm, UpdateAccountForm,
                             CommentForm, RequestResetForm, ResetPasswordForm,MovieForm,
                             DeleteCommentForm,UpdateCommentForm)
from flaskblog.models import User, Post, Movie, Comment, Credits
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import sigmoid_kernel
from sqlalchemy import create_engine
''' '''
basedir = os.path.abspath(os.path.dirname(__file__))

def get_home_recommendation():
    sql_engine = create_engine(os.path.join('sqlite:///' + os.path.join(basedir, 'site.db')), echo=False)
    movies_results = pd.read_sql_query('select movie_id,genres from Movie',sql_engine)
    movies_results.to_csv(os.path.join(basedir, 'Movie.csv'),index=False,sep=";")

    user_movies_results = pd.read_sql_query('select movie_id from Credits',sql_engine)
    user_movies_results.to_csv(os.path.join(basedir, 'Credits.csv'),index=False,sep=";")

    movies_df = pd.read_csv(os.path.join(basedir,'Movie.csv'),sep=';')
    credits = pd.read_csv(os.path.join(basedir,'Credits.csv'),sep=';')

    cred_count = credits['movie_id'].value_counts()
    cred_index = cred_count.index
    rem_movie_id = set(movies_df['movie_id']) - set(cred_index)
    all_movie = list(cred_index) + list(rem_movie_id)
    l,L = [],[]
    for i in all_movie:
        l.append(i)
        if len(l) == 12:
            L.append(l)
            l = []
    L.append(l)
    return L


def get_recommendations(movie_id):
    sql_engine = create_engine(os.path.join('sqlite:///' + os.path.join(basedir, 'site.db')), echo=False)
    movies_results = pd.read_sql_query('select movie_id,genres from Movie',sql_engine)
    movies_results.to_csv(os.path.join(basedir, 'Movie.csv'),index=False,sep=";")

    user_movies_results = pd.read_sql_query('select movie_id from Credits',sql_engine)
    user_movies_results.to_csv(os.path.join(basedir, 'Credits.csv'),index=False,sep=";")

    movies_df = pd.read_csv(os.path.join(basedir,'Movie.csv'),sep=';')
    user_df = pd.read_csv(os.path.join(basedir,'Credits.csv'),sep=';')
    user_df.drop_duplicates(subset = 'movie_id',inplace = True)
    user_df.reset_index(drop=True, inplace=True)
    movies_df_merge = movies_df.merge(user_df, on='movie_id')
    tfv = TfidfVectorizer(min_df=3,  max_features=None, 
                strip_accents='unicode', analyzer='word',token_pattern=r'\w{1,}',
                ngram_range=(1, 3),
                stop_words = 'english')
    tfv_matrix = tfv.fit_transform(movies_df_merge['genres'])
    indices = pd.Series(movies_df_merge.index, index=movies_df_merge['movie_id']).drop_duplicates()

    sig = sigmoid_kernel(tfv_matrix, tfv_matrix)
    # Get the index corresponding to original_title
    idx = indices[movie_id]

    # Get the pairwsie similarity scores 
    sig_scores = list(enumerate(sig[idx]))

    # Sort the movies 
    sig_scores = sorted(sig_scores, key=lambda x: x[1], reverse=True)

    # Scores of the 10 most similar movies
    sig_scores = sig_scores[1:]

    # Movie indices
    movie_indices = [i[0] for i in sig_scores]

    # Top 10 most similar movies
    rem_movie = list(movies_df_merge['movie_id'].iloc[movie_indices])
    return rem_movie






@app.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', title=post.title, post=post)

@app.route("/movie/<int:movie_id>",methods=['GET', 'POST'])
@login_required
def play_movie(movie_id):
    form = CommentForm()
    post = Movie.query.get_or_404(movie_id)
    credit = Credits(movie_id = movie_id)
    db.session.add(credit)
    db.session.commit()
    rem_movie = get_recommendations(movie_id)
    if form.validate_on_submit():
        comm = Comment(content=form.content.data, movie_id=movie_id,author_user=current_user)
        db.session.add(comm)
        db.session.commit()
        flash('Your comment has been posted!', 'success')
        return redirect(url_for('play_movie',movie_id=movie_id))
    comm = Comment.query.filter_by(movie_id = movie_id).order_by(Comment.date_posted.desc())
    usrr = User.query.all()
    com_total = comm.count()
    movie = Movie.query.all()
    return render_template('play_movie.html',com_total = com_total,title=post.title,usrr = usrr,post=post,comm=comm,rem_movie = rem_movie,movie=movie,form=form)


@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('create_post.html', title='Update Post',
                           form=form, legend='Update Post')


@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('home'))

@app.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user)\
        .order_by(Post.date_posted.desc())\
        .paginate(page=page, per_page=5)
    return render_template('user_posts.html', posts=posts, user=user)

def save_movie_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(basedir, 'static/pics/movie_pics', picture_fn)

    form_picture.save(picture_path)
    return picture_fn

@app.route("/movie/new", methods=['GET', 'POST'])
@login_required
def new_movie_post():
    form = MovieForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_movie_picture(form.picture.data)
            current_user.movie_image_file = picture_file
        movie = Movie(title=form.title.data,language=form.language.data,genres=form.genres.data,
            year=form.year.data,link=form.link.data,content=form.content.data,
            movie_image_file = picture_file,movie_author=current_user)
        db.session.add(movie)
        db.session.commit()
        flash('Your movie has been posted!', 'success')
        return redirect(url_for('upload_history'))
    return render_template('new_movie_post.html', title='New Post',
                           form=form, legend='New Post')
def delete_movie_picture(movie_image_file):
    picture_path = os.path.join(basedir, 'static/pics/movie_pics', movie_image_file)
    if os.path.exists(picture_path):
        os.remove(picture_path)
        return True

@app.route("/movie/<int:movie_id>/update", methods=['GET', 'POST'])
@login_required
def updateMovie(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    if movie.movie_author != current_user:
        abort(403)
    form = MovieForm()
    if movie.movie_image_file:
        delete_movie_picture(movie.movie_image_file)
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_movie_picture(form.picture.data)
            current_user.movie_image_file = picture_file
            movie.movie_image_file = picture_file
        movie.title = form.title.data
        movie.language = form.language.data
        movie.genres = form.genres.data
        movie.year = form.year.data
        movie.link = form.link.data
        movie.content = form.content.data
        db.session.commit()
        flash('Movie has been updated!', 'success')
        return redirect(url_for('upload_history'))
    elif request.method == 'GET':
        form.title.data = movie.title
        form.language.data = movie.language
        form.genres.data = movie.genres
        form.year.data = movie.year
        form.link.data  = movie.link
        form.content.data = movie.content
    movie_image_file = url_for('static', filename='pics/movie_pics/' + movie.movie_image_file)
    return render_template('new_movie_post.html', title=movie.movie_id,
                           movie_image_file=movie_image_file, form=form)

@app.route("/movie/<int:movie_id>/delete", methods=['POST'])
@login_required
def delete_movie(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    if movie.movie_author != current_user:
        abort(403)
    if movie.movie_image_file:
        delete_movie_picture(movie.movie_image_file)
    db.session.delete(movie)
    db.session.commit()
    flash('Movie has been deleted!', 'success')
    return redirect(url_for('upload_history'))




''' start User Section '''
@app.route("/")
@app.route("/home")
def home():
    page = request.args.get('page', 1, type=int)
    recomm_movie_id = get_home_recommendation()
    all_movie = recomm_movie_id[page-1]
    total_page = [(i+1) for i in range(len(recomm_movie_id))]
    movie_post = Movie.query.all()
    return render_template('home.html', movie_post=movie_post, total_page = total_page,all_movie = all_movie,page = page)


@app.route("/upload_history")
def upload_history():
    page = request.args.get('page', 1, type=int)
    movie_post = Movie.query.filter_by(user_id = current_user.id).order_by(Movie.date_posted.desc()).paginate(page=page, per_page=12)
    return render_template('upload_history.html', movie_post=movie_post,title = "my uploaded history")


@app.route("/about")
def about():
    return render_template('about.html', title='About')

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(your_name = form.your_name.data, username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

def save_user_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(basedir, 'static/pics/user_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    return picture_fn

@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_user_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.your_name.data = current_user.your_name
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='pics/user_pics/' + current_user.image_file)
    return render_template('account.html', title='Account',
                           image_file=image_file, form=form)


''' end User section '''

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                  sender='noreply@demo.com',
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}
If you did not make this request then simply ignore this email and no changes will be made.
'''
    mail.send(msg)


@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)


@app.errorhandler(404)
def error_404(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(403)
def error_403(error):
    return render_template('errors/403.html'), 403

@app.errorhandler(410)
def error_403(error):
    return render_template('errors/403.html'), 410


@app.errorhandler(500)
def error_500(error):
    return render_template('errors/500.html'), 500


@app.route("/movie/<int:movie_id>/comment/<int:comment_id>/update", methods=['GET', 'POST'])
@login_required
def updateComment(movie_id,comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if comment.author_user != current_user:
        abort(403)
    form = UpdateCommentForm()
    if form.validate_on_submit():
        comment.content = form.content.data
        db.session.commit()
        flash('Your Comment has been updated!', 'success')
        return redirect(url_for('play_movie',movie_id = movie_id))
    elif request.method == 'GET':
        form.content.data = comment.content
    movie = Movie.query.get_or_404(movie_id)
    image_file = url_for('static', filename='pics/user_pics/' + current_user.image_file)
    return render_template('updateComment.html', title=movie.title, form=form,image_file = image_file)

@app.route("/movie/<int:movie_id>/comment/<int:comment_id>/delete", methods=['GET', 'POST'])
@login_required
def delete_comment(movie_id,comment_id):
    comment = Comment.query.get_or_404(comment_id)
    movie = Movie.query.get_or_404(movie_id)
    form = DeleteCommentForm()
    if form.validate_on_submit():
        db.session.delete(comment)
        db.session.commit()
        flash('Your comment has been deleted!', 'success')
        return redirect(url_for('play_movie',movie_id = movie_id))
    elif request.method == 'GET':
        form.content.data = comment.content
    else:
        abort(403)
    image_file = url_for('static', filename='pics/user_pics/' + current_user.image_file)
    return render_template('updateComment.html', title=movie.title, form=form,image_file = image_file)

