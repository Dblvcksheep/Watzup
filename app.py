from flask import Flask, abort, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_bootstrap import Bootstrap5
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user,login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text,DateTime,Date,Time
from functools import wraps
from http import HTTPStatus
import os
from datetime import datetime, timedelta
from flask_mail import Mail, Message
import requests
from uuid import uuid4
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
import base64
import random
import hmac
import hashlib
import json
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import TooManyRequests

load_dotenv()
app = Flask(__name__)
# load_dotenv()
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
Bootstrap5(app)


login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# CREATE DATABASE
class Base(DeclarativeBase):
    pass


app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy(model_class=Base)
db.init_app(app)
migrate = Migrate(app, db)

class User(db.Model, UserMixin):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(225), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.DateTime, nullable=False)
    state = db.Column(db.String(100), nullable=False)
    lga = db.Column(db.String(100), nullable=False)
    password = db.Column(db.Text, nullable=False)
    wallet = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.now())
    event = db.relationship('Event', backref='user', lazy='dynamic', cascade="all, delete-orphan")
    attendee = db.relationship('Attendee', backref='user', lazy='dynamic', cascade="all, delete-orphan")
    private_attendee = db.relationship('PrivateAttendee', backref='user', lazy='dynamic', cascade="all, delete-orphan")

class Event(db.Model):
    __tablename__ = "event"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    description = db.Column(db.Text, nullable=False)
    address = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    lga = db.Column(db.String(100), nullable=False)
    likes = db.Column(db.Integer, default = 0)
    event_type= db.Column(db.String(200), default='free')#can be free, paid, private
    amount = db.Column(db.Integer, default=0)
    event_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    attendee =db.Column(db.Integer, default=100)
    cover_img = db.Column(db.Text, nullable=False)
    attender = db.relationship('Attendee', backref='event', lazy='dynamic', cascade="all, delete-orphan")
    private = db.relationship('PrivateAttendee', backref='event', lazy='dynamic', cascade="all, delete-orphan")
    images = db.relationship('EventImage', backref='event', lazy='dynamic', cascade="all, delete-orphan")
    created_at = db.Column(db.DateTime, default=datetime.now())


class EventImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    image_url = db.Column(db.Text, nullable=False)
    image_id = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.now())

class Attendee(db.Model):
    __tablename__ = "attendee"
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now())

class PrivateAttendee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now())

class SetReminder(db.Model):
    __tablename__ = "setreminder"
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now())


with app.app_context():
    db.create_all()

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
)
#storage_uri=os.environ['CELERY_BROKER_URL']

app.config['MAIL_SERVER']   = os.environ['MAIL_SERVER']
app.config['MAIL_PORT']     = 587
app.config['MAIL_USE_TLS']  = True
app.config['MAIL_USERNAME'] = os.environ['MAIL_USERNAME']
app.config['MAIL_PASSWORD'] = os.environ['MAIL_PASSWORD']
app.config['MAIL_DEFAULT_SENDER'] = ('Watzup', os.environ['MAIL_USERNAME'])

mail = Mail(app)

def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If id is not 1 then return abort with 403 error
        if not current_user.is_authenticated and current_user.id != 1:
            return abort(403)
        # Otherwise continue with the route function
        return f(*args, **kwargs)
    return decorated_function

def login_key():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    if email:
        return f"email:{email}"
    return f"ip:{get_remote_address()}"

def send_welcome_email(name, user_email, user_password):
    # Plain text fallback
    plain_body = f"""
Hello {name},

Your account has been created. Please find your login details below:

Email: {user_email}
Password: {user_password}

Thank you for registering!
"""

    # HTML body
    html_body = f"""
<html>
  <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
    <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 12px; background-color: #f9f9f9;">
      <h2 style="color: #0d6efd; text-align: center;">Welcome to Watzup</h2>
      <p>Hello <strong>{name}</strong>,</p>
      <p>Your Account have been created successfully, You can start enjoying Watzup:</p>


      <p style="margin-top: 20px;">Your login details:</p>
      <table style="width: 100%; border-collapse: collapse; margin: 10px 0;">
        <tr>
          <td style="padding: 8px; font-weight: bold;">Email:</td>
          <td style="padding: 8px;">{user_email}</td>
        </tr>
        <tr style="background-color: #f1f1f1;">
          <td style="padding: 8px; font-weight: bold;">Password:</td>
          <td style="padding: 8px;">{user_password}</td>
        </tr>
      </table>

      <p style="text-align: center; margin-top: 30px;">
        <a href='#' style="display: inline-block; padding: 12px 24px; background-color: #0d6efd; color: #fff; text-decoration: none; border-radius: 8px; font-weight: 600;">Login Now</a>
      </p>

      <hr style="margin-top: 30px;">
      <p style="font-size: 12px; color: #888; text-align: center;">
        Thank you for Registering.
      </p>
    </div>
  </body>
</html>
"""

    # Create the message
    msg = Message(
        subject="Your Watzup Account Details",
        recipients=[user_email],
        body=plain_body,
        html=html_body
    )

    # Send it
    with app.app_context():
        mail.send(msg)
        flash(f"Email sent to {user_email} ✅")

with open('nigeria.json', 'r') as f:
    states=json.load(f)

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    events = Event.query.order_by(Event.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    if current_user.is_authenticated:
        events = Event.query.filter(Event.state == current_user.state, Event.lga == current_user.lga).order_by(Event.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('home.html', events=events)

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email').lower()
        date = request.form.get('date')
        state = request.form.get('state')
        lga = request.form.get('lga')
        password = request.form.get('password1')
        confirm_pass = request.form.get('password2')

        user = User.query.filter_by(email=email).first()
        print(date)
        dateformat = datetime.strptime(date, '%Y-%m-%d')
        if not user:
            if password == confirm_pass:
                reg = User(name=name, dob=dateformat, email=email, password=generate_password_hash(password, salt_length=5),state=state,lga=lga)
                db.session.add(reg)
                db.session.commit()
                login_user(reg)
                send_welcome_email(name, email, password)
                return redirect(url_for('index'))
            else:
                flash('passwords do not match')
        else:
            flash('User already exist', 'error')
    return render_template('register.html', states=states)


@app.route('/create_event', methods=["GET", "POST"])
@login_required
def create_event():
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        address = request.form.get("address")
        state = request.form.get("state")
        lga = request.form.get("lga")
        event_type = request.form.get("event_type")
        date = request.form.get('date')  # "2026-04-20"
        time = request.form.get('time')  # "14:30"
        end_time = request.form.get('endtime')
        attendee = request.form.get("attendee")
        amount = request.form.get("amount")
        cover = request.files.get("cover")
        event_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")

        end_datetime = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M")

        cover_filename = None
        if cover and cover.filename:
            cover_upload_path = os.path.join(current_app.root_path, 'static/cover')
            os.makedirs(cover_upload_path, exist_ok=True)
            # Use unique filename to avoid collisions
            cover_filename = f"{uuid4().hex}_{secure_filename(cover.filename)}"
            cover.save(os.path.join(cover_upload_path, cover_filename))

        new_event = Event(title=title,
                          description=description,
                          address=address,
                          state=state,
                          lga=lga,
                          user_id=current_user.id,
                          attendee = attendee,
                          cover_img =f"cover/{cover_filename}",
                          event_type=event_type,
                          amount = amount if amount else 0,
                          event_date=event_datetime,
                          end_date = end_datetime)

        db.session.add(new_event)
        db.session.commit()

        return redirect(url_for('index'))
    return render_template("create_event.html",states=states)


@app.route('/join-event/<int:event_id>', methods=['POST'])
@login_required
def join_event(event_id):

    joined = Attendee.query.filter_by(event_id=event_id, user_id = current_user.id).first()
    if joined:
        return jsonify({"message": "You are already registered for this event", "status": "error"}), 409
    # Example logic (you’ll expand this)

    event = Event.query.get(event_id)

    if not event:
        return jsonify({"message": "Event not found", "status": "error"}), 404

    if event.event_type == "paid":
        if event.amount > current_user.wallet:
            return jsonify({"message": "Your balance is too low", "status": "error"}), 409
        current_user.wallet -= event.amount

    elif event.event_type == "private":
        private_attend = PrivateAttendee(
            event_id=event_id,
            user_id=current_user.id
        )
        db.session.add(private_attend)
        db.session.commit()
        return jsonify({
            "message": "If you are selected you will be added to the list",
            "status": "joined"
        })

    # Increment attendees

    attend = Attendee(
        event_id=event_id,
        user_id = current_user.id
    )
    db.session.add(attend)
    db.session.commit()

    return jsonify({
        "message": "You have joined this event 🎉",
        "status": "joined"
    })

@app.route('/set-reminder/<int:event_id>', methods=['POST'])
def set_reminder(event_id):

    already_set = SetReminder.query.filter_by(event_id=event_id, user_id = current_user.id).first()
    if already_set:
        return jsonify({"message": "You are already set reminder for this event", "status": "error"}), 409


    reminder = SetReminder(
        event_id=event_id,
        user_id = current_user.id
    )
    db.session.add(reminder)
    db.session.commit()
    # For now: simple logic (you’ll expand later)

    # Example: store in DB or session later
    return jsonify({
        "message": "Reminder set successfully 🔔"
    })

@app.route('/event_detail/<int:event_id>')
@login_required
def event_detail(event_id):
    event = Event.query.get(event_id)

    return render_template("event_detail.html", event=event)


@app.route("/get-lgas")
def get_lgas():
    selected_state = request.args.get("state")

    for s in states:
        if s["state"] == selected_state:
            return jsonify(s["lga"])  # make sure key is 'lgas'

    return jsonify([])

@app.route('/login', methods=["GET", "POST"])
@limiter.limit("10 per hour", key_func=login_key, methods=["POST"])
def login():
    if request.method == 'POST':
        email = request.form.get('email').lower()
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('index'))
            else:
                flash('invalid credentials')
                return redirect(url_for('login'))

        else:
            flash('invalid credentials')
            return redirect(url_for('login'))
    return render_template('login.html')
@app.errorhandler(TooManyRequests)
def rate_limit_handler(e):
    flash("Too many login attempt.", "warning")
    # stay on the same page
    return redirect(request.referrer or url_for("index"))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@login_manager.unauthorized_handler
def unauthorized():
    if request.blueprint == 'api':
        abort(HTTPStatus.UNAUTHORIZED)
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(debug=False, port=5000)