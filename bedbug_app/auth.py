import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from bedbug_app.db import get_db

MIN_USERNAME_LENGTH = 5
MAX_USERNAME_LENGTH = 15
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 20

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register', methods=('GET', 'POST'))
def register():
"""Sets up the user to be registered for the application. 
Returns HTML for the registration page on a GET request or HTML 
for the login page if the user registers correctly.
"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password2 = request.form['password2']
        db = get_db()
        error = None

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'

        if len(username) < MIN_USERNAME_LENGTH or len(username) > MAX_USERNAME_LENGTH or not username.isalnum():
            error = "Username must have a total length beween 5-15 and can only consists of alphanumeric characters."

        # Check for lowercase and uppercase, 1 int, and special character
        if not (MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH) or not password.isalnum():
            error = "Password must have a total length beween 8-20 and can only consists of alphanumeric characters."

        if password != password2:
            error = "Passwords must match."

        if error is None:
            try:
                db.execute(
                    "INSERT INTO user (username, password) VALUES (?, ?)",
                    (username, generate_password_hash(password)),
                )
                db.commit()
            except db.IntegrityError:
                error = f"User {username} is already registered."
            else:
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template('auth/register.html')


@bp.route('/login', methods=('GET', 'POST'))
def login():
"""Allows user to login. Returns login page on a GET request or index 
when the user logs in correctly. 
"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)
        ).fetchone()

        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('index'))

        flash(error)

    return render_template('auth/login.html')


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()


@bp.route('/logout')
def logout():
"Logs out the user. Returns the index page."
    session.clear()
    return redirect(url_for('index'))


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
    """If user is not logged in, will request that user logs in. """
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view
