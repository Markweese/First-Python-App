# coding: utf-8

from datetime import datetime
import os

from flask import flash, Flask, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, LoginManager, logout_user, UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from werkzeug.debug import DebuggedApplication
from wtforms import PasswordField, StringField, SubmitField, validators
from wtforms.validators import DataRequired

from app import commands

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://{}:{}@{}:3306/{}'.format(
    os.getenv('MYSQL_USERNAME', 'web_user'),
    os.getenv('MYSQL_PASSWORD', 'password'),
    os.getenv('MYSQL_HOST', 'db'), os.getenv('MYSQL_DATABASE', 'sample_app'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'this is something special'

if app.debug:
    app.wsgi_app = DebuggedApplication(app.wsgi_app, True)

db = SQLAlchemy(app)
commands.init_app(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id) if user_id else None


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(120))

    def __repr__(self):
        return '<User %r>' % self.email

    def check_password(self, password):
        return self.password == password


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80))
    author = db.Column(db.String(100))
    body = db.Column(db.Text(15000))
    pub_date = db.Column(db.DateTime)

    def __init__(self, title, author, body, pub_date=None):
        self.title = title
        self.author = author
        self.body = body
        if pub_date is None:
            pub_date = datetime.utcnow()
        self.pub_date = pub_date

    def __repr__(self):
        return '<Post %r>' % self.title


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<Category %r>' % self.name


@app.route("/")
def index():
    posts = Post.query.all()
    return render_template('index.html', posts=posts)

@app.route("/<int:page>")
def paginate(page):
    maxNum = page*10
    minNum = maxNum-10
    #.filter() not supporting gt lt comparison between id max/min
    #error: '>' not supported between instances of 'builtin_function_or_method' and 'int'
    posts = Post.query.all()
    return render_template('paginated.html', posts=posts, max=maxNum, min=minNum)

#archive filter
@app.route('/archive/<int:date>')
def archive(date):
# --name 'pub_date' is not defined-- keeps holding queries up,
# doesn't like the .month on end of it.
# passing to jinja for check
    posts = Post.query.all()
    return render_template('archive.html', posts=posts, date=date)

#archive and paginate
@app.route('/archive/<int:date>/<int:page>')
def arcpag(date, page):
    maxNum = page*10
    minNum = maxNum-10
    posts = Post.query.all()
    return render_template('arc_pag.html', posts=posts, date=date, max=maxNum, min=minNum)

#about page
@app.route("/about")
def about():
    return render_template('about.html')

#blog post form
class BlogForm(FlaskForm):
    title = StringField('Title', [validators.Length(max=80)])
    author = StringField('Author', [validators.Length(max=80)])
    body = StringField('Story', [validators.Length(min=10)])
    submit = SubmitField('Post Blog')

#blog post page
@app.route('/create', methods=['GET', 'POST'])
def create():
    form = BlogForm()
    if form.validate_on_submit():
        post = Post(form.title.data, form.author.data, form.body.data)
        db.session.add(post)
        db.session.commit()
        return redirect('/')
    return render_template('create.html', title='create blog', form=form)


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = StringField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

    def __init__(self, *args, **kwargs):
        FlaskForm.__init__(self, *args, **kwargs)
        self.user = None

    def validate(self):
        rv = FlaskForm.validate(self)
        if not rv:
            return False

        user = User.query.filter_by(email=self.email.data).one_or_none()
        if user:
            password_match = user.check_password(self.password.data)
            if password_match:
                self.user = user
                return True

        self.password.errors.append('Invalid email and/or password specified.')
        return False


@app.route('/auth/login/', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        login_user(form.user)
        flash('Logged in successfully.')
        return redirect(request.args.get('next') or url_for('index'))

    return render_template('login.html', form=form)


@app.route('/logout/')
@login_required
def logout():
    logout_user()
    return redirect(request.args.get('next') or url_for('index'))


@app.route('/account/')
@login_required
def account():
    return render_template('account.html', user=current_user)


@app.before_first_request
def initialize_data():
    # just make sure we have some sample data, so we can get started.
    user = User.query.filter_by(email='blogger@sample.com').one_or_none()
    if user is None:
        user = User(email='blogger@sample.com', password='password')
        db.session.add(user)
        db.session.commit()


if __name__ == "__main__":
    app.run()
