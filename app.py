from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime
from flask_mail import Mail, Message
from dotenv import load_dotenv
import os
from flask import url_for, flash, render_template, request, redirect
from datetime import datetime, timedelta
import random
from sqlalchemy import func
from urllib.parse import urlparse, parse_qs
from sqlalchemy.sql import case


def generate_key():
    return str(random.randint(100000, 999999)) 


load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')
MAIL_USERNAME = os.getenv('MAIL_USERNAME')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SECRET_KEY'] = SECRET_KEY
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Flask-Mail Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587 
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = MAIL_USERNAME
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = MAIL_USERNAME

mail = Mail(app)

class Upvote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    is_upvote = db.Column(db.Boolean, nullable=False)  # True for upvote, False for downvote

    user = db.relationship('User', backref='user_upvotes')
    post = db.relationship('Post', back_populates='upvotes')  # Use back_populates

    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='unique_user_post_vote'),)


# User Model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False) 
    password_hash = db.Column(db.String(128), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)
    reset_key = db.Column(db.String(64), unique=True, nullable=True)
    reset_key_expires = db.Column(db.DateTime, nullable=True)

    def generate_reset_key(self):
        self.reset_key = generate_key()  
        self.reset_key_expires = datetime.utcnow() + timedelta(minutes=10) 



# Post Model
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    upvotes = db.relationship('Upvote', back_populates='post', lazy='dynamic')  # Fix backref issue

    @property
    def upvote_count(self):
        return self.upvotes.count()  # Get total upvotes dynamically


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/test')
def test():
    return render_template('test.html')

# Main Blog Feed (Index Page)
@app.route('/')
def index():
    sort_by = request.args.get('sort', 'recent')

    # Calculate net votes
    net_votes = (func.sum(case((Upvote.is_upvote == True, 1), else_=0)) -
                 func.sum(case((Upvote.is_upvote == False, 1), else_=0)))

    if sort_by == 'top':  # Sort by net upvotes
        posts = db.session.query(Post, net_votes.label("net_votes")) \
            .outerjoin(Upvote) \
            .group_by(Post.id) \
            .order_by(func.coalesce(net_votes, 0).desc()) \
            .all()
    else:  # Default: Sort by most recent
        posts = db.session.query(Post, func.coalesce(net_votes, 0).label("net_votes")) \
            .outerjoin(Upvote) \
            .group_by(Post.id) \
            .order_by(Post.date_posted.desc()) \
            .all()
    
    # Attach user votes (Only if user is logged in)
    posts_with_votes = []
    for post, net_votes in posts:
        user_vote = None
        if current_user.is_authenticated:
            user_vote = Upvote.query.filter_by(user_id=current_user.id, post_id=post.id).first()
        
        posts_with_votes.append((post, net_votes, user_vote))

    return render_template('index.html', posts=posts_with_votes)



# User Profile Page
@app.route('/profile/<username>')
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    user_posts = Post.query.filter_by(author=user).order_by(Post.date_posted.desc()).all()
    return render_template('profile.html', user=user, posts=user_posts)


# Add New Post
@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        new_post = Post(title=title, content=content, author=current_user)
        db.session.add(new_post)
        db.session.commit()
        flash('Post created successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('add_post.html')


# Edit Post
@app.route('/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        flash('You are not authorized to edit this post.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        post.title = request.form['title']
        post.content = request.form['content']
        db.session.commit()
        flash('Post updated successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('edit_post.html', post=post)


# Delete Post
@app.route('/delete/<int:post_id>')
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        flash('You are not authorized to delete this post.', 'danger')
        return redirect(url_for('index'))

    db.session.delete(post)
    db.session.commit()
    flash('Post deleted successfully!', 'success')
    return redirect(url_for('index'))


# Register Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Check if user exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))

        # Hash password and create new user
        hashed_password = bcrypt.generate_password_hash(password)
        new_user = User(username=username, email=email, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        # Send welcome email
        send_welcome_email(email, username)

        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/upvote/<int:post_id>', methods=['POST'])
@login_required
def upvote(post_id):
    post = Post.query.get_or_404(post_id)
    existing_vote = Upvote.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    
    if existing_vote:
        if existing_vote.is_upvote:
            db.session.delete(existing_vote)
        else:
            existing_vote.is_upvote = True
    else:
        new_vote = Upvote(user_id=current_user.id, post_id=post_id, is_upvote=True)
        db.session.add(new_vote)
    
    db.session.commit()

    # Extract sorting method from referrer
    referrer = request.referrer
    sort = "recent"
    if referrer:
        parsed_url = urlparse(referrer)
        query_params = parse_qs(parsed_url.query)
        sort = query_params.get("sort", ["recent"])[0]  # Default to "recent" if not found
    
    return redirect(url_for('index', sort=sort))

@app.route('/downvote/<int:post_id>', methods=['POST'])
@login_required
def downvote(post_id):
    post = Post.query.get_or_404(post_id)
    existing_vote = Upvote.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    
    if existing_vote:
        if not existing_vote.is_upvote:
            db.session.delete(existing_vote)
        else:
            existing_vote.is_upvote = False
    else:
        new_vote = Upvote(user_id=current_user.id, post_id=post_id, is_upvote=False)
        db.session.add(new_vote)
    
    db.session.commit()

    # Extract sorting method from referrer
    referrer = request.referrer
    sort = "recent"
    if referrer:
        parsed_url = urlparse(referrer)
        query_params = parse_qs(parsed_url.query)
        sort = query_params.get("sort", ["recent"])[0]  # Default to "recent" if not found
    
    return redirect(url_for('index', sort=sort))



# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')


# Logout Route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# Dark Mode Toggle
@app.route('/toggle-dark-mode')
def toggle_dark_mode():
    if 'dark_mode' in session and session['dark_mode']:
        session['dark_mode'] = False
    else:
        session['dark_mode'] = True
    return redirect(request.referrer or url_for('index'))

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()
        
        if user:
            user.generate_reset_key()
            db.session.commit()
            
            send_reset_email(user.email, user.reset_key)

            flash("A reset code has been sent to your email.", "info")
            return redirect(url_for("verify_reset_key"))

    return render_template("forgot_password.html")


@app.route("/verify-reset-key", methods=["GET", "POST"])
def verify_reset_key():
    if request.method == "POST":
        key = request.form.get("reset_key")
        user = User.query.filter_by(reset_key=key).first()
        
        if user and user.reset_key_expires > datetime.utcnow():
            session["reset_user_id"] = user.id 
            return redirect(url_for("reset_password"))

        flash("Invalid or expired reset key.", "danger")

    return render_template("verify_reset_key.html")


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    user_id = session.get("reset_user_id")
    if not user_id:
        return redirect(url_for("forgot_password"))

    user = User.query.get(user_id)

    if request.method == "POST":
        new_password = request.form.get("password")
        user.password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
        user.reset_key = None  
        user.reset_key_expires = None
        db.session.commit()

        flash("Your password has been reset.", "success")
        return redirect(url_for("login"))

    return render_template("reset_password.html")


@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        old_password = request.form.get("old_password")
        new_password = request.form.get("new_password")

        if bcrypt.check_password_hash(current_user.password_hash, old_password):
            current_user.password_hash = bcrypt.generate_password_hash(new_password)
            db.session.commit()
            flash("Password changed successfully!", "success")
            return redirect(url_for("profile", username=current_user.username))
        else:
            flash("Old password is incorrect.", "danger")

    return render_template("change_password.html")



def send_reset_email(email, reset_key):
    subject = "Password Reset Code"
    body = f"Use this code to reset your password: {reset_key}\nThis code will expire in 10 minutes."
    send_email(email, subject, body) 


def send_welcome_email(email, username):
    msg = Message("Welcome to Microblog!", recipients=[email])
    msg.body = f"Hello {username},\n\nThanks for signing up for Microblog! We're happy to have you here.\n\nHappy blogging!\n\n- The Microblog Team"
    mail.send(msg)

def send_email(to, subject, body):
    try:
        msg = Message(subject, recipients=[to], body=body)
        mail.send(msg)
        print(f"Email sent to {to}")
    except Exception as e:
        print(f"Error sending email: {e}")



# Run App
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  
    app.run(debug=True)
