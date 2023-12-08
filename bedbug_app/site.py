import secrets

from bedbug_app.auth import login_required
from bedbug_app.db import get_db

from bedbug_app.helper import allowed_file, upload_blob, predict_image_classification_sample, create_thumbnail
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename


UPLOAD_FOLDER = 'tmp/images/'

bp = Blueprint('site', __name__)


@bp.route('/')
@login_required
def index():
    db = get_db()
    posts = db.execute(
        'SELECT p.id, title, body,  date(created, "localtime") as created, author_id, username'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' ORDER BY p.id DESC'
    ).fetchall()

    img_list = db.execute(
        'SELECT image_name, post_id, prediction, probability'
        ' FROM images ORDER by post_id DESC').fetchall()

    return render_template('site/index.html', posts=posts, img_list=img_list, homepage=True)


@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            temp_file_name = "/tmp/photo.jpg"
            file.save(temp_file_name)

            thumbnail_temp_name = create_thumbnail(temp_file_name)

            random_id = secrets.token_hex(10)

            for prefix, local_photo_name in [("raw_images/", temp_file_name), ("thumbnails/", thumbnail_temp_name)]:
                img_name = random_id + "." + filename.split(".")[-1]
                upload_blob("cs50bedbugs", local_photo_name, prefix + img_name)

            prediction_results = None
            try:
                prediction_results = predict_image_classification_sample(
                    filename=temp_file_name)
            except:
                pass
        else:
            error = "Photo has to be a jpg, jpeg, or webm"

        if error is not None:
            flash(error)
        else:
            db = get_db()

            max_id = db.execute(
                'SELECT MAX(id) as id FROM post'
            ).fetchone()

            if max_id['id'] is None:
                new_id = 1
            else:
                new_id = int(max_id['id']) + 1

            db.execute(
                'INSERT INTO post (id, title, body, author_id)'
                ' VALUES (?, ?, ?,?)',
                (new_id, title, body, g.user['id'])
            )
            if prediction_results:
                prob = round(float(prediction_results["confidence"]), 2)
                db.execute('INSERT INTO images (id, post_id, image_name, author_id, prediction, probability) VALUES (?, ?, ?, ?, ?, ? )',
                           (random_id, new_id, img_name, g.user['id'], prediction_results['classification'], prob))
            else:
                db.execute('INSERT INTO images (id, post_id, image_name, author_id) VALUES (?, ?, ?, ?)',
                           (random_id, new_id, img_name, g.user['id']))
            db.execute
            db.commit()
            return redirect(url_for('site.results', id=new_id))

    return render_template('site/create.html')


def get_post(id, check_author=False):
    post = get_db().execute(
        'SELECT p.id, title, body, created, author_id, username'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' WHERE p.id = ?',
        (id,)
    ).fetchone()

    if post is None:
        abort(404, f"Post id {id} doesn't exist.")

    if check_author and post['author_id'] != g.user['id']:
        abort(403)

    return post


def get_img(post_id):
    img = get_db().execute(
        'SELECT image_name, post_id, prediction, probability'
        ' FROM images i'
        ' WHERE i.post_id = ?',
        (post_id,)
    ).fetchone()

    if img is None:
        abort(404, f"Image for Post id {post_id} doesn't exist.")

    result = {}

    if img["prediction"] == True:
        result["classification"] = "Bed Bug"
    else:
        result["classification"] = "Not a Bed Bug"
    result["probability"] = img["probability"]
    result["url"] = "https://storage.googleapis.com/cs50bedbugs/raw_images/" + \
        img["image_name"]
    result["thumbnail_url"] = "https://storage.googleapis.com/cs50bedbugs/thumbnails/" + img["image_name"]
    result["post_id"] = img["post_id"]
    return result


@bp.route('/<int:id>/results', methods=('GET', 'POST'))
@login_required
def results(id):
    post = get_post(id)
    img_info = get_img(id)

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE post SET title = ?, body = ?'
                ' WHERE id = ?',
                (title, body, id)
            )
            db.commit()
            return redirect(url_for('site.index'))
    return render_template('site/results.html', post=post, img_info=img_info)


@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_post(id)
    db = get_db()
    db.execute('DELETE FROM post WHERE id = ?', (id))
    db.commit()
    return redirect(url_for('site.index'))
