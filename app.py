import threading
import time
import uuid

from flask import Flask, abort, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_bootstrap import Bootstrap5
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user,login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, DateTime, Date, Time, Boolean, or_
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
from flask import Response
import json
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import TooManyRequests
from wallet import nombank_access_token,nombank_balance,revoke_access,create_virtual,match_nombank,nombank_transfer,nombank_confirm,resolve_nombank

load_dotenv()
app = Flask(__name__)
# load_dotenv()
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
client_seccret = os.environ["NOMBANK_CLIENT_SECRET"]
client_id = os.environ["NOMBANK_CLIENT_ID"]
account_id = os.environ["NOMBANK_ACCOUNT_ID"]

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
    is_admin = db.Column(db.Boolean, default=False)
    email = db.Column(db.String(225), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.DateTime, nullable=False)
    gender =db.Column(db.String(100), nullable=False)#male or female
    state = db.Column(db.String(100), nullable=False)
    lga = db.Column(db.String(100), nullable=False)
    password = db.Column(db.Text, nullable=False)
    wallet = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.now())
    event = db.relationship('Event', backref='user', lazy='dynamic', cascade="all, delete-orphan")
    withdraws = db.relationship(
        'Withdraw',
        backref='user',
        cascade='all, delete-orphan'
    )
    notify = db.relationship('Notify', backref='user', lazy='dynamic', cascade="all, delete-orphan")
    attendee = db.relationship('Attendee', backref='user', lazy='dynamic', cascade="all, delete-orphan")
    private_attendee = db.relationship('PrivateAttendee', backref='user', lazy='dynamic', cascade="all, delete-orphan")
    profile_image = db.relationship('ProfileImage', backref='user', uselist=False, cascade="all, delete-orphan")
    bank=db.relationship('Bank', backref='user', uselist=False, cascade="all, delete-orphan")

class Notify(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text)
    level = db.Column(db.String(20))
    seen = db.Column(db.Boolean, default=False)
    expire_at = db.Column(db.DateTime)

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
    platform_amount = db.Column(db.Integer, default=0)
    event_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    attendee =db.Column(db.Integer, default=100)
    category = db.Column(db.String(200))#Nightlife,gosple event,tech event, convention, conference
    cover_img = db.Column(db.Text, nullable=False)
    attender = db.relationship('Attendee', backref='event', lazy='dynamic', cascade="all, delete-orphan")
    private = db.relationship('PrivateAttendee', backref='event', lazy='dynamic', cascade="all, delete-orphan")
    created_at = db.Column(db.DateTime, default=datetime.now())

class Withdraw(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reference = db.Column(db.String(100), unique=True, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    acct_name =db.Column(db.String(100), nullable=False)
    acct_number = db.Column(db.String(100), nullable=False)
    bank_code = db.Column(db.String(100), nullable=False)
    verify_code = db.Column(db.Integer(), nullable=False)
    status = db.Column(db.String(20), default='waiting')
    created_at = db.Column(db.DateTime, default=datetime.now())

class ProfileImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    image_url = db.Column(db.Text, nullable=False)
    image_id = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.now())

class Attendee(db.Model):
    __tablename__ = "attendee"
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    email = db.Column(db.String(225), nullable=False)
    name = db.Column(db.String(100), nullable=False)
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
    event_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now())

class Bank(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    acct_name= db.Column(db.String(100), nullable=False)
    acct_number=db.Column(db.String(100), nullable=False)
    acct_ref = db.Column(db.String(100), nullable=False)
    bank_name=db.Column(db.String(100), nullable=False)


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
Welcome to Watzup

Hello {name},

Your account has been created successfully.

Email: {user_email}
Password: {user_password}

Login and start exploring events on Watzup.
"""

    # HTML body (Watzup Ticketmaster-style onboarding)
    html_body = f"""
<html>
  <body style="margin:0; padding:0; background-color:#0F0F1A; font-family:Arial, sans-serif;">

    <div style="max-width:600px; margin:40px auto; background:#1A1A2E; border-radius:16px; overflow:hidden; box-shadow:0 0 25px rgba(0,198,255,0.15);">

      <!-- Header -->
      <div style="padding:25px; text-align:center; background:linear-gradient(90deg,#7B2FF7,#00C6FF);">
        <h1 style="margin:0; color:white; letter-spacing:2px;">WATZUP</h1>
        <p style="margin:5px 0 0; color:#eaeaea; font-size:13px;">Your Event Universe Starts Here</p>
      </div>

      <!-- Body -->
      <div style="padding:25px; color:#ffffff;">

        <p style="font-size:16px;">Hello <strong>{name}</strong>,</p>

        <p style="color:#cfcfcf;">
          Your Watzup account has been successfully created. You are now part of a growing world of events, discovery, and experiences.
        </p>

        <!-- Account Card (Ticket-style) -->
        <div style="margin:20px 0; padding:20px; background:#0F0F1A; border:1px solid #2a2a40; border-radius:12px;">

          <p style="margin:0; font-size:13px; color:#aaa;">ACCOUNT DETAILS</p>

          <p style="margin:10px 0;"><strong>Email:</strong> {user_email}</p>
          <p style="margin:10px 0;"><strong>Password:</strong> {user_password}</p>

        </div>

        <!-- CTA Button -->
        <p style="text-align:center; margin-top:25px;">
          <a href="#" 
             style="display:inline-block; padding:14px 26px; 
                    background:linear-gradient(90deg,#7B2FF7,#00C6FF);
                    color:white; text-decoration:none; 
                    border-radius:10px; font-weight:bold;">
            Enter Watzup
          </a>
        </p>

        <!-- Warning / Security -->
        <p style="margin-top:25px; font-size:13px; color:#ff6b6b;">
          🔐 For your security, never share your login details with anyone.
        </p>

        <p style="font-size:12px; color:#888;">
          If you did not create this account, please ignore this email.
        </p>

      </div>

      <!-- Footer -->
      <div style="padding:15px; text-align:center; font-size:12px; color:#888; border-top:1px solid #2a2a40;">
        © Watzup • Discover Events, Anywhere, Anytime
      </div>

    </div>

  </body>
</html>
"""

    # Send email
    msg = Message(
        subject="Welcome to Watzup 🎟️",
        recipients=[user_email],
        body=plain_body,
        html=html_body
    )

    with app.app_context():
        mail.send(msg)
        flash(f"Email sent to {user_email} ✅")

def send_attendance_email(name, user_email, event_name, event_address, lga, state, start_time):
    # Plain text fallback
    plain_body = f"""
Hello {name},

You have been successfully added as an attendee.

Event: {event_name}
Address: {event_address}
LGA: {lga}
State: {state}
Start Time: {start_time}

We look forward to seeing you there!
"""

    # HTML body (Ticketmaster-style Watzup event pass)
    html_body = f"""
<html>
  <body style="margin:0; padding:0; background-color:#0F0F1A; font-family:Arial, sans-serif;">

    <div style="max-width:600px; margin:40px auto; background:#1A1A2E; border-radius:16px; overflow:hidden; box-shadow:0 0 25px rgba(123,47,247,0.2);">

      <!-- Header -->
      <div style="padding:25px; text-align:center; background:linear-gradient(90deg,#7B2FF7,#00C6FF);">
        <h1 style="margin:0; color:white; letter-spacing:2px;">WATZUP</h1>
        <p style="margin:5px 0 0; color:#eaeaea; font-size:13px;">Event Attendance Confirmation</p>
      </div>

      <!-- Body -->
      <div style="padding:25px; color:#ffffff;">

        <p style="font-size:16px;">Hello <strong>{name}</strong>,</p>

        <p style="color:#cfcfcf;">
          You have been successfully added as an attendee for the following event.
        </p>

        <!-- Event Card -->
        <div style="margin:20px 0; padding:20px; background:#0F0F1A; border:1px solid #2a2a40; border-radius:12px;">

          <p style="margin:0; font-size:13px; color:#aaa;">EVENT DETAILS</p>

          <h2 style="margin:10px 0; color:#00C6FF;">{event_name}</h2>

          <p style="margin:8px 0;"><strong>Address:</strong> {event_address}</p>
          <p style="margin:8px 0;"><strong>LGA:</strong> {lga}</p>
          <p style="margin:8px 0;"><strong>State:</strong> {state}</p>
          <p style="margin:8px 0; color:#7B2FF7;"><strong>Start Time:</strong> {start_time}</p>

        </div>

        <!-- Status Badge -->
        <div style="text-align:center; margin-top:20px;">
          <span style="display:inline-block; padding:10px 16px; 
                       background:rgba(0,198,255,0.15); 
                       border:1px solid #00C6FF;
                       border-radius:20px;
                       color:#00C6FF;
                       font-size:13px;">
            ✓ You are confirmed as an attendee
          </span>
        </div>

        <p style="margin-top:25px; font-size:13px; color:#cfcfcf;">
          Please arrive at least 15–30 minutes before the start time.
        </p>

        <p style="font-size:12px; color:#888;">
          If you did not expect this invitation, please contact support.
        </p>

      </div>

      <!-- Footer -->
      <div style="padding:15px; text-align:center; font-size:12px; color:#888; border-top:1px solid #2a2a40;">
        © Watzup • Discover Events, Anywhere, Anytime
      </div>

    </div>

  </body>
</html>
"""

    msg = Message(
        subject=f"You're Going to {event_name} 🎟️",
        recipients=[user_email],
        body=plain_body,
        html=html_body
    )

    with app.app_context():
        mail.send(msg)
        flash("Attendance confirmation sent ✅")

def send_removal_email(name, user_email, event_name):
    # Plain text fallback
    plain_body = f"""
Hello {name},

You have been removed from the attendance list for the event:

Event: {event_name}

If this was a mistake, please contact support.
"""

    # HTML body (Watzup Ticketmaster-style removal notice)
    html_body = f"""
<html>
  <body style="margin:0; padding:0; background-color:#0F0F1A; font-family:Arial, sans-serif;">

    <div style="max-width:600px; margin:40px auto; background:#1A1A2E; border-radius:16px; overflow:hidden; box-shadow:0 0 25px rgba(255,107,107,0.15);">

      <!-- Header -->
      <div style="padding:25px; text-align:center; background:linear-gradient(90deg,#7B2FF7,#00C6FF);">
        <h1 style="margin:0; color:white; letter-spacing:2px;">WATZUP</h1>
        <p style="margin:5px 0 0; color:#eaeaea; font-size:13px;">Attendance Update</p>
      </div>

      <!-- Body -->
      <div style="padding:25px; color:#ffffff;">

        <p style="font-size:16px;">Hello <strong>{name}</strong>,</p>

        <p style="color:#cfcfcf;">
          This is to inform you that your attendance status has been updated.
        </p>

        <!-- Event Card -->
        <div style="margin:20px 0; padding:20px; background:#0F0F1A; border:1px solid #2a2a40; border-radius:12px;">

          <p style="margin:0; font-size:13px; color:#aaa;">EVENT</p>

          <h2 style="margin:10px 0; color:#00C6FF;">{event_name}</h2>

        </div>

        <!-- Status Badge -->
        <div style="text-align:center; margin-top:20px;">
          <span style="display:inline-block; padding:10px 16px; 
                       background:rgba(255,107,107,0.15); 
                       border:1px solid #ff6b6b;
                       border-radius:20px;
                       color:#ff6b6b;
                       font-size:13px;">
            ⚠️ You have been removed from the attendance list
          </span>
        </div>

        <p style="margin-top:25px; font-size:13px; color:#cfcfcf;">
          If you believe this was a mistake, please contact support or re-register if available.
        </p>

        <p style="font-size:12px; color:#888;">
          Thank you for using Watzup.
        </p>

      </div>

      <!-- Footer -->
      <div style="padding:15px; text-align:center; font-size:12px; color:#888; border-top:1px solid #2a2a40;">
        © Watzup • Discover Events, Anywhere, Anytime
      </div>

    </div>

  </body>
</html>
"""

    # Send email
    msg = Message(
        subject=f"Update: Removed from {event_name}",
        recipients=[user_email],
        body=plain_body,
        html=html_body
    )

    with app.app_context():
        mail.send(msg)
        flash("Removal notice sent ✅")


def send_withdrawal_processing_email(
    name,
    user_email,
    account_name,
    account_number,
    amount,
    reference_id
):
    # Plain text fallback
    plain_body = f"""
Hello {name},

Your withdrawal request is being processed and is on the way.

Amount: {amount}
Account Name: {account_name}
Account Number: {account_number}
Reference ID: {reference_id}

Please allow some time for the funds to reflect in your account.

Thank you for using Watzup.
"""

    # HTML body
    html_body = f"""
<html>
  <body style="margin:0; padding:0; background-color:#0F0F1A; font-family:Arial, sans-serif;">

    <div style="max-width:600px; margin:40px auto; background:#1A1A2E; border-radius:16px; overflow:hidden; box-shadow:0 0 25px rgba(0,198,255,0.18);">

      <!-- Header -->
      <div style="padding:25px; text-align:center; background:linear-gradient(90deg,#7B2FF7,#00C6FF);">
        <h1 style="margin:0; color:white; letter-spacing:2px;">WATZUP</h1>
        <p style="margin:5px 0 0; color:#eaeaea; font-size:13px;">
          Withdrawal Processing Update
        </p>
      </div>

      <!-- Body -->
      <div style="padding:25px; color:#ffffff;">

        <p style="font-size:16px;">
          Hello <strong>{name}</strong>,
        </p>

        <p style="color:#cfcfcf;">
          Your withdrawal request has been successfully initiated and the transfer is currently on the way to your bank account.
        </p>

        <!-- Withdrawal Card -->
        <div style="margin:20px 0; padding:20px; background:#0F0F1A; border:1px solid #2a2a40; border-radius:12px;">

          <p style="margin:0; font-size:13px; color:#aaa;">
            WITHDRAWAL DETAILS
          </p>

          <h2 style="margin:12px 0; color:#00C6FF;">
            {amount}
          </h2>

          <p style="margin:8px 0;">
            <strong>Account Name:</strong> {account_name}
          </p>

          <p style="margin:8px 0;">
            <strong>Account Number:</strong> {account_number}
          </p>

          <p style="margin:8px 0;">
            <strong>Reference ID:</strong> {reference_id}
          </p>

        </div>

        <!-- Status Badge -->
        <div style="text-align:center; margin-top:20px;">
          <span style="display:inline-block;
                       padding:10px 16px;
                       background:rgba(0,198,255,0.15);
                       border:1px solid #00C6FF;
                       border-radius:20px;
                       color:#00C6FF;
                       font-size:13px;">
            💸 Your withdrawal is on the way
          </span>
        </div>

        <p style="margin-top:25px; font-size:13px; color:#cfcfcf;">
          Depending on your bank, the funds may take a few minutes to reflect.
        </p>

        <p style="font-size:12px; color:#888;">
          If you did not authorize this withdrawal, please contact support immediately.
        </p>

      </div>

      <!-- Footer -->
      <div style="padding:15px; text-align:center; font-size:12px; color:#888; border-top:1px solid #2a2a40;">
        © Watzup • Secure Event & Payment Platform
      </div>

    </div>

  </body>
</html>
"""

    # Send email
    msg = Message(
        subject="Your Withdrawal is on the Way 💸",
        recipients=[user_email],
        body=plain_body,
        html=html_body
    )

    with app.app_context():
        mail.send(msg)
        flash("Withdrawal update sent ✅")




def withdrawal_verification(name, user_email, code, amount, reference_id):
    # Plain text fallback
    plain_body = f"""
Watzup Security Alert

Hello {name},

You are about to make a withdrawal.

Amount: {amount}
Verification Code: {code}
Reference: {reference_id}

If this wasn't you, ignore this message.
"""

    # HTML body (Ticketmaster-style, Watzup branded)
    html_body = f"""
<html>
  <body style="margin:0; padding:0; background-color:#0F0F1A; font-family:Arial, sans-serif;">

    <div style="max-width:600px; margin:40px auto; background:#1A1A2E; border-radius:16px; overflow:hidden; box-shadow:0 0 25px rgba(123,47,247,0.25);">

      <!-- Header -->
      <div style="padding:20px; background:linear-gradient(90deg,#7B2FF7,#00C6FF); text-align:center;">
        <h1 style="margin:0; color:white; letter-spacing:1px;">WATZUP</h1>
        <p style="margin:5px 0 0; color:#eaeaea; font-size:13px;">Secure Withdrawal Verification</p>
      </div>

      <!-- Body -->
      <div style="padding:25px; color:#ffffff;">

        <p style="font-size:16px;">Hello <strong>{name}</strong>,</p>

        <p style="color:#cfcfcf;">
          You are about to initiate a withdrawal. Please confirm this action using the code below.
        </p>

        <!-- Highlight Box (Ticketmaster-style code block) -->
        <div style="margin:20px 0; padding:20px; background:#0F0F1A; border:1px solid #2a2a40; border-radius:12px; text-align:center;">

          <p style="margin:0; font-size:13px; color:#aaa;">VERIFICATION CODE</p>
          <h2 style="margin:10px 0; font-size:32px; letter-spacing:6px; color:#00C6FF;">
            {code}
          </h2>

        </div>

        <!-- Transaction Details -->
        <div style="background:#15152A; padding:15px; border-radius:12px; border:1px solid #2a2a40;">

          <h3 style="margin-top:0; color:#7B2FF7;">Transaction Details</h3>

          <p style="margin:6px 0;"><strong>Amount:</strong> {amount}</p>
          <p style="margin:6px 0;"><strong>Reference:</strong> {reference_id}</p>

        </div>

        <!-- Warning -->
        <p style="margin-top:25px; font-size:13px; color:#ff6b6b;">
          ⚠️ If this wasn't you, ignore this email immediately or secure your account.
        </p>

      </div>

      <!-- Footer -->
      <div style="padding:15px; text-align:center; font-size:12px; color:#888; border-top:1px solid #2a2a40;">
        © Watzup • Secure Event & Payment Platform
      </div>

    </div>

  </body>
</html>
"""

    # Send message
    msg = Message(
        subject="Watzup Withdrawal Verification",
        recipients=[user_email],
        body=plain_body,
        html=html_body
    )

    with app.app_context():
        mail.send(msg)
        flash("Code sent to email ✅")

with open('nigeria.json', 'r') as f:
    states=json.load(f)

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    now = datetime.now()

    events_query = Event.query

    # 🔍 SEARCH (title, state, lga)
    if query:
        events_query = events_query.filter(
            or_(
                Event.title.ilike(f"%{query}%"),
                Event.state.ilike(f"%{query}%"),
                Event.lga.ilike(f"%{query}%")
            )
        )

    # 🎯 CATEGORY
    if category:
        events_query = events_query.filter(Event.category == category)

    # 📍 LOCATION PRIORITY (only if no manual filters)
    if current_user.is_authenticated and not (query or category):

        # 1. LGA + State
        lga_query = events_query.filter(
            Event.state == current_user.state,
            Event.lga == current_user.lga
        )

        lga_events = lga_query.order_by(Event.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)

        if lga_events.items:
            return render_template(
                'home.html',
                events=lga_events,
                query=query,
                category=category,
                now=now
            )

        # 2. State fallback
        state_query = events_query.filter(
            Event.state == current_user.state
        )

        state_events = state_query.order_by(Event.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)

        if state_events.items:
            return render_template(
                'home.html',
                events=state_events,
                query=query,
                category=category,
                now=now
            )


    # 🌍 DEFAULT / SEARCH RESULT
    events = events_query.order_by(Event.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        'home.html',
        events=events,
        query=query,
        category=category,
        now=now
    )

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email').lower()
        date = request.form.get('date')
        gender = request.form.get('gender')
        state = request.form.get('state')
        lga = request.form.get('lga')
        password = request.form.get('password1')
        confirm_pass = request.form.get('password2')

        user = User.query.filter_by(email=email).first()
        print(date)
        dateformat = datetime.strptime(date, '%Y-%m-%d')
        if not user:
            if password == confirm_pass:
                reg = User(name=name, dob=dateformat, email=email, password=generate_password_hash(password, salt_length=5),state=state,lga=lga,gender=gender)
                db.session.add(reg)
                db.session.commit()
                login_user(reg)
                try:
                    send_welcome_email(name, email, password)
                except Exception as e:
                    flash(f"Error: {str(e)}", "error")

                return redirect(url_for('index'))
            else:
                flash('passwords do not match')
        else:
            flash('User already exist', 'error')
    return render_template('register.html', states=states)


@app.route('/withdrawal', methods=['GET', 'POST'])
@login_required
def withdraw():
    if request.method == 'POST':
        name = request.form.get('name')
        acct_number = request.form.get('acct_number')
        amount = float(request.form.get('amount'))
        bank = request.form.get('bank')
        bank_code = match_nombank(bank)
        access = nombank_access_token(client_id, client_seccret, account_id)
        if access['description'] == 'Successful':
            access_token = access['data']['access_token']
        resolved = resolve_nombank(acct_number, bank_code, name,access_token,
                               account_id)
        reference_id = f'WTH-{current_user.id}-{uuid.uuid4().hex[:12]}'

        if (amount + 50) > current_user.wallet:
            flash('Insufficient balance.', 'error')
            return redirect(url_for('withdraw'))
        if resolved:
            code=random.randint(100000, 999999)
            tx = Withdraw(user_id=current_user.id,reference=reference_id,amount=amount,acct_name=name,
                          acct_number=str(acct_number),bank_code=str(bank_code), verify_code=code)
            db.session.add(tx)
            db.session.commit()

            withdrawal_verification(current_user.name,current_user.email, code,amount,reference_id)
            return redirect(url_for('withdraw_verify', withdraw_id=tx.id))
        else:
            flash('The account name doesnt match')
            return redirect(url_for('withdraw'))
    return render_template('withdraw.html')


@app.route('/withdraw_verify/<int:withdraw_id>', methods=['GET', 'POST'])
@login_required
def withdraw_verify(withdraw_id):
    sessions =Withdraw.query.filter_by(id=withdraw_id,user_id= current_user.id).first()
    if not sessions:
        flash('Session expired', 'error')
        return redirect(url_for('withdraw'))

    if request.method == 'POST':
        verify_code = sessions.verify_code
        bank_code = sessions.bank_code
        reference = sessions.reference
        amount = sessions.amount
        acct_number = sessions.acct_number
        acct_name = sessions.acct_name
        code = int(request.form.get('code'))
        if code == verify_code:
            try:
                if (amount+50) > current_user.wallet:
                    flash('Insufficient balance.', 'error')
                    return redirect(url_for('withdraw'))
                sessions.status = "processing"
                current_user.wallet -= (amount+50)
                db.session.commit()
                try:
                    send_withdrawal_processing_email(current_user.name,current_user.email,acct_name,acct_number,amount,reference)
                except Exception as e:
                    flash(f"{str(e)}", "error")

                flash("Withdrawal on the way, Thank you for choosing Watzup", "success")
                return redirect(url_for('index'))
            except Exception as e:
                flash(f'Transfer error {e}', 'error')
                return redirect(url_for('withdraw'))
        else:
            flash('Invalid verification code', 'error')
            return redirect(url_for('withdraw_verify', withdraw_id=withdraw_id))
    return render_template('verify_withdraw.html')


@app.route("/edit_profile/<int:user_id>",methods=["GET", "POST"])
@login_required
def edit_profile(user_id):
    user=User.query.get(user_id)

    ddate = user.dob.strftime('%Y-%m-%d')
    if not (current_user.id == 1 or current_user.is_admin or current_user.id == user.id):
        return redirect(url_for('index'))
    if request.method == "POST":
        wallet_balance = request.form.get("wallet")
        name = request.form.get("name")
        email = request.form.get("email")
        dob = request.form.get("date")
        gender = request.form.get("gender")
        state = request.form.get("state")
        lga = request.form.get("lga")
        profile_img = request.files.get("profile")

        dateformat = datetime.strptime(dob, '%Y-%m-%d')
        if current_user.id ==1:
            is_admin = request.form.get("admin")
            if is_admin == 'false':
                user.is_admin = False
            elif is_admin == "true":
                user.is_admin = True

        if current_user.is_admin or current_user.id == 1:
            user.wallet = wallet_balance
        user.name = name
        user.email = email
        user.dob =dateformat
        user.gender = gender
        user.state = state if state else user.state
        user.lga = lga if lga else user.lga
        if profile_img and profile_img.filename:
            profile_upload_path = os.path.join(current_app.root_path, 'static/profile')
            os.makedirs(profile_upload_path, exist_ok=True)
            # Use unique filename to avoid collisions
            profile_filename = f"{uuid4().hex}_{secure_filename(profile_img.filename)}"
            profile_img.save(os.path.join(profile_upload_path, profile_filename))

            if user.profile_image and user.profile_image.image_url:
                image_path = user.profile_image.image_url  # e.g. profile/image.jpg

                # ❌ Never delete default image
                if image_path != "images/default-avatar.jpg":

                    # Build full path from project root
                    full_path = os.path.join(app.root_path, "static", image_path)

                    # Extra safety (only allow profile folder)
                    if image_path.startswith("profile/") and os.path.exists(full_path):
                        try:
                            os.remove(full_path)
                        except Exception as e:
                            print(f"Error deleting file: {e}")

                user.profile_image.image_url = f"profile/{profile_filename}"
            else:
                new = ProfileImage(
                    user_id = user.id,
                    image_url = f"profile/{profile_filename}",
                    image_id = profile_filename
                )
                db.session.add(new)

        db.session.commit()
        flash("Successful", "succes")
        return redirect(url_for('index'))

    return render_template("edit_profile.html", user=user, states=states, date=ddate)

@app.route("/edit_event/<int:event_id>",methods=["GET", "POST"])
@login_required
def edit_event(event_id):
    event = Event.query.get(event_id)

    start_time = event.event_date.time()
    end_time = event.end_date.time()
    ddate = event.event_date.strftime('%Y-%m-%d')

    if not (current_user.id == 1 or current_user.is_admin or current_user.id == event.user_id):
        return redirect(url_for('index'))
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
        category = request.form.get("category")
        event_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")

        end_datetime = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M")

        if cover and cover.filename:
            image_path = event.cover  # e.g. profile/image.jpg

            # ❌ Never delete default image
            if image_path != "images/default-avatar.jpg":

                # Build full path from project root
                full_path = os.path.join(app.root_path, "static", image_path)

                # Extra safety (only allow profile folder)
                if image_path.startswith("cover/") and os.path.exists(full_path):
                    try:
                        os.remove(full_path)
                    except Exception as e:
                        print(f"Error deleting file: {e}")

            cover_upload_path = os.path.join(current_app.root_path, 'static/cover')
            os.makedirs(cover_upload_path, exist_ok=True)
            # Use unique filename to avoid collisions
            cover_filename = f"{uuid4().hex}_{secure_filename(cover.filename)}"
            cover.save(os.path.join(cover_upload_path, cover_filename))

            event.cover = f"cover/{cover_filename}"
        event.title = title
        event.description = description
        event.address = address
        event.state = state
        event.lga = lga
        event.category = category
        event.event_type =event_type
        event.event_date = event_datetime
        event.end_date = end_datetime
        event.attendee = attendee
        event.amount = amount if amount else 0

        db.session.commit()
    return render_template("edit_event.html",
                           event=event,
                           start_time=start_time,
                           end_time=end_time,
                           date=ddate)

@app.route("/my_events")
@login_required
def my_event():
    events=Event.query.filter_by(user_id=current_user.id).all()

    return render_template("my_events.html", events=events)

@app.route("/notifications")
@login_required
def notification():
    page = request.args.get('page', 1, type=int)
    per_page = 20  # number of data per page

    Notifys = Notify.query.filter(Notify.user_id == current_user.id, Notify.seen == False).paginate(page=page, per_page=per_page)

    return render_template('notify.html', notifys=Notifys)

@app.route("/users")
@login_required
def users():
    if not (current_user.id == 1 or current_user.is_admin):
        flash("Privileged route", "error")
        return redirect(url_for("index"))

    query = request.args.get("q", "").strip()

    users_query = User.query

    # 🔍 Search logic
    if query:
        users_query = users_query.filter(
            or_(
                User.name.ilike(f"%{query}%"),
                User.email.ilike(f"%{query}%")
            )
        )

    # 📄 Optional pagination (recommended)
    page = request.args.get("page", 1, type=int)
    users_paginated = users_query.order_by(User.created_at.desc())\
        .paginate(page=page, per_page=20, error_out=False)

    return render_template(
        "users.html",
        users=users_paginated,
        query=query
    )

@app.route("/events")
@login_required
def events():

    # 🔐 Fix permission logic
    if not (current_user.id == 1 or current_user.is_admin):
        flash("Privileged route", "error")
        return redirect(url_for("index"))

    # 🔍 Get filters
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    page = request.args.get("page", 1, type=int)
    per_page = 20

    events_query = Event.query

    # 🔍 Search (title)
    if query:
        events_query = events_query.filter(
            Event.title.ilike(f"%{query}%"),
            Event.state.ilike(f"%{query}%"),
            Event.lga.ilike(f"%{query}%")
        )

    # 🎯 Category filter
    if category:
        events_query = events_query.filter(Event.category == category)


    # 📄 Pagination
    events_paginated = events_query.order_by(Event.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "events.html",
        events=events_paginated,
        query=query,
        category=category
    )


@app.route("/delete/<table>/<int:action_id>", methods=["GET", "POST"])
@login_required
def delete(table, action_id):

    if request.method == "POST":
        code = request.form.get("code")

        if not check_password_hash(current_user.password, code):
            return render_template("delete.html", error="Invalid password")

        to_delete = None

        # ================= EVENT DELETE =================
        if table == 'event':
            event = Event.query.get_or_404(action_id)

            # ✅ FIXED permission logic
            if not (current_user.id == 1 or current_user.is_admin or current_user.id == event.user_id):
                return redirect(url_for('index'))

            # Delete cover image
            if event.cover and event.cover != "images/default-avatar.jpg":
                full_path = os.path.join(app.root_path, "static", event.cover)

                if event.cover.startswith("cover/") and os.path.exists(full_path):
                    try:
                        os.remove(full_path)
                    except Exception as e:
                        print(f"Error deleting file: {e}")

            to_delete = event

        # ================= USER DELETE =================
        elif table == 'user':
            user = User.query.get_or_404(action_id)

            # ✅ FIXED permission logic
            if not (current_user.id == 1 or current_user.is_admin or current_user.id == user.id):
                return redirect(url_for('index'))

            # Delete profile image
            if user.profile_image and user.profile_image.image_url:
                image_path = user.profile_image.image_url

                if image_path != "images/default-avatar.jpg":
                    full_path = os.path.join(app.root_path, "static", image_path)

                    if image_path.startswith("profile/") and os.path.exists(full_path):
                        try:
                            os.remove(full_path)
                        except Exception as e:
                            print(f"Error deleting file: {e}")

            # Delete user's events + their covers
            user_events = Event.query.filter_by(user_id=user.id).all()

            for event in user_events:
                if event.cover and event.cover != "images/default-avatar.jpg":
                    full_path = os.path.join(app.root_path, "static", event.cover)

                    if event.cover.startswith("cover/") and os.path.exists(full_path):
                        try:
                            os.remove(full_path)
                        except Exception as e:
                            print(f"Error deleting file: {e}")

                db.session.delete(event)

            to_delete = user

        # ================= FINAL DELETE =================
        if to_delete:
            db.session.delete(to_delete)
            db.session.commit()

            return redirect(url_for('index'))

    return render_template("delete.html")

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
        category = request.form.get("category")
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
        ratio = 0.1 * float(amount if amount else 0)
        platform_amount=float(amount if amount else 0) + float(ratio)

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
                          platform_amount=platform_amount,
                          category=category,
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

    attendee_count = Attendee.query.filter_by(event_id=event_id).count()

    if event.attendee is not None and attendee_count >= event.attendee:
        return jsonify({
            "message": "Max attendees reached",
            "status": "error"
        }), 409


    if not event:
        return jsonify({"message": "Event not found", "status": "error"}), 404

    if event.event_type == "paid":
        if event.platform_amount > current_user.wallet:
            return jsonify({"message": "Your balance is too low", "status": "error"}), 409
        current_user.wallet -= event.platform_amount
        event.user.wallet += event.amount

    elif event.event_type == "private":
        joined_private = PrivateAttendee.query.filter_by(event_id=event_id, user_id=current_user.id).first()
        if joined_private:
            return jsonify({"message": "You have already requested to join this event, hold for organisers!", "status": "error"}), 409
        private_attend = PrivateAttendee(
            event_id=event_id,
            user_id=current_user.id
        )
        db.session.add(private_attend)
        db.session.commit()
        return jsonify({
            "message": "You have requested to join this event",
            "status": "joined"
        })

    # Increment attendees

    attend = Attendee(
        event_id=event_id,
        user_id = current_user.id,
        name = current_user.name,
        email = current_user.email
    )
    db.session.add(attend)
    db.session.commit()
    try:
        send_attendance_email(current_user.name,current_user.email,event.title,event.address,event.lga,event.state,event.event_date.strftime('%I:%M %p'))
    except Exception as e:
        return jsonify({"message": f"{str(e)}", "status": "error"}), 409

    return jsonify({
        "message": "You have joined this event 🎉",
        "status": "joined"
    })

@app.route('/about')
def about():
    return render_template("about.html")

@app.route('/set-reminder/<int:event_id>', methods=['POST'])
def set_reminder(event_id):

    already_set = SetReminder.query.filter_by(
        event_id=event_id,
        user_id=current_user.id
    ).first()

    if already_set:
        return jsonify({
            "message": "You already set a reminder for this event",
            "status": "error"
        }), 409

    # Get event details (assuming you have Event model)
    event = Event.query.get_or_404(event_id)

    # Save to DB
    reminder = SetReminder(
        event_id=event_id,
        user_id=current_user.id,
        event_date=event.event_date
    )
    db.session.add(reminder)
    db.session.commit()

    # --- Generate ICS file ---
    start = event.event_date
    end = event.end_date or (start + timedelta(hours=1))

    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
SUMMARY:{event.title}
DESCRIPTION:{event.description or 'Event reminder'}
DTSTART:{start.strftime('%Y%m%dT%H%M%S')}
DTEND:{end.strftime('%Y%m%dT%H%M%S')}
BEGIN:VALARM
TRIGGER:-PT10M
ACTION:DISPLAY
DESCRIPTION:Reminder
END:VALARM
END:VEVENT
END:VCALENDAR
"""

    return Response(
        ics_content,
        mimetype="text/calendar",
        headers={
            "Content-Disposition": f"attachment; filename=event_{event_id}.ics"
        }
    )

@app.route('/event_detail/<int:event_id>')
@login_required
def event_detail(event_id):
    event = Event.query.get(event_id)
    joined = Attendee.query.filter_by(event_id=event_id, user_id=current_user.id).first()
    already_set = SetReminder.query.filter_by(event_id=event_id, user_id=current_user.id).first()
    attendee=Attendee.query.filter_by(event_id=event_id)

    query = request.args.get("q", "").strip()


    # 🔍 Search logic
    if query:
        attendee = attendee.filter(
            or_(
                Attendee.name.ilike(f"%{query}%"),
                Attendee.email.ilike(f"%{query}%")
            )
        )
    attendee = attendee.all()

    private = PrivateAttendee.query.filter_by(event_id=event_id).all()
    attendee_count = Attendee.query.filter_by(event_id=event_id).count()


    return render_template("event_detail.html", event=event,
                           joined=joined,
                           already_set=already_set,
                           attendee=attendee,
                           private= private,
                           attendee_count = attendee_count)

@app.route("/nombank/webhook", methods=["POST"])
def nombank_webhook():
    payload = request.get_json()

    signature = request.headers.get("nomba-signature")
    timestamp = request.headers.get("nomba-timestamp")

    WEBHOOK_SIGNATURE_KEY = account_id  # (use real secret later)

    # Extract fields
    merchant = payload.get("data", {}).get("merchant", {})
    transaction = payload.get("data", {}).get("transaction", {})

    event_type = payload.get("event_type", "")
    request_id = payload.get("requestId", "")

    user_id = merchant.get("userId", "")
    wallet_id = merchant.get("walletId", "")

    transaction_id = transaction.get("transactionId", "")
    transaction_type = transaction.get("type", "")
    transaction_time = transaction.get("time", "")
    response_code = transaction.get("responseCode") or ""

    # Build hashing payload (VERY IMPORTANT)
    hashing_payload = f"{event_type}:{request_id}:{user_id}:{wallet_id}:{transaction_id}:{transaction_type}:{transaction_time}:{response_code}:{timestamp}"

    # Generate signature
    computed = base64.b64encode(
        hmac.new(
            WEBHOOK_SIGNATURE_KEY.encode(),
            hashing_payload.encode(),
            hashlib.sha256
        ).digest()
    ).decode()

    # Verify
    if not hmac.compare_digest(computed, signature):
        return "Invalid signature", 400

    # Process events
    if event_type == "payout_success":
        pass

    elif event_type == "payment_success":
        pass

    else:
        pass

    db.session.commit()
    return "", 200

@app.route("/manage_attendee/<table>/<int:action>/<int:event_id>/<int:user_id>", methods=["GET","POST"])
@login_required
def manage_attendee(table,action,event_id,user_id):
    event = Event.query.get(event_id)
    if current_user.id != event.user_id:
        return redirect(url_for("event_detail", event_id=event_id))
    if event.event_type == "paid":
        return redirect(url_for("event_detail", event_id=event_id))
    attendee_count = Attendee.query.filter_by(event_id=event_id).count()
    user = User.query.get(user_id)

    if request.method == "POST":
        code = request.form.get("code")
        if check_password_hash(current_user.password, code):
            if table == "private":
                private = PrivateAttendee.query.filter_by(event_id=event_id, user_id=user_id).first()
                if not private:
                    flash("This request is no longer available", "error")
                    return redirect(url_for("event_detail", event_id=event_id))
                if action == 0:
                    flash("Request deleted", "error")
                    db.session.delete(private)
                elif action == 1:
                    if event.attendee is not None and attendee_count >= event.attendee:
                        flash("Max attendees reached", "error")
                        return redirect(url_for("event_detail", event_id=event_id))
                    attend = Attendee(
                        event_id=event_id,
                        user_id=user_id,
                        name= user.name,
                        email = user.email
                    )
                    db.session.add(attend)
                    db.session.delete(private)
                    try:
                        send_attendance_email(user.name, user.email, event.title, event.address,
                                              event.lga, event.state, event.event_date.strftime('%I:%M %p'))
                    except Exception as e:
                        flash(f"{str(e)}", "error")

                else:
                    return redirect(url_for("event_detail", event_id=event_id))
            elif table == "attendee":
                attendee = Attendee.query.filter_by(event_id=event_id, user_id=user_id).first()
                if not attendee:
                    flash("This user is no longer an attendee", "error")
                    return redirect(url_for("event_detail", event_id=event_id))
                if action == 0:
                    flash("Request deleted", "error")
                    db.session.delete(attendee)
                    try:
                        send_removal_email(user.name,user.email,event.title)
                    except Exception as e:
                        flash(f"{str(e)}", "error")
                else:
                    return redirect(url_for("event_detail", event_id=event_id))

            else:
                return redirect(url_for("event_detail", event_id=event_id))
            db.session.commit()
        else:
            flash("invalid credentials", "error")
            return redirect(url_for('manage_attendee',table=table,action=action,event_id=event_id,user_id=user_id))
        return redirect(url_for("event_detail", event_id=event_id))

    return render_template("manage_attendee.html")

@app.route("/generate_bank")
@login_required
def generate_bank():
    access = nombank_access_token(client_id, client_seccret, account_id)
    if access['description'] == 'Successful':
        access_token = access['data']['access_token']
    virtual = create_virtual(access_token, account_id, f"ACCOUNT-{uuid.uuid4().hex[:12]}", current_user.name)
    if virtual['description'] == 'SUCCESS':
        bank = Bank(
            user_id=current_user.id,
            acct_name=virtual['data']['bankAccountName'],
            acct_number=virtual['data']['bankAccountNumber'],
            acct_ref=virtual['data']['accountRef'],
            bank_name=virtual['data']['bankName']
        )
        db.session.add(bank)
        db.session.commit()
    revoke_access(access_token, client_id)
    return redirect(url_for('index'))

@app.route("/profile/<int:user_id>")
@login_required
def profile(user_id):
    user = User.query.get(user_id)
    today = datetime.now().date()
    dob = user.dob.date()
    age= today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return render_template("profile.html", user=user, age=age)

@app.route("/wallet")
@login_required
def wallet():
    return render_template("wallet.html")

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


def work(withdrawal):
    print(f"working on user:{withdrawal.user.id}")
    with app.app_context():
        try:
            if (withdrawal.amount +50) > withdrawal.user.wallet:
                db.session.add(Notify(
                    user_id=withdrawal.user.id,
                    message=f'Your withdrawal was not successful insufficient fund',
                    level='error',
                    seen=False,
                    expire_at=datetime.now() + timedelta(hours=1)
                ))
                db.session.commit()
                return 'failed'
            access = nombank_access_token(client_id, client_seccret, account_id)
            if access['description'] == 'Successful':
                access_token = access['data']['access_token']

            confirm = nombank_confirm(withdrawal.reference, account_id,access_token)

            # CASE 1: No Paystack record yet
            if confirm['description'] != 'SUCCESS':

                # Check bank info
                if not withdrawal.bank_code:
                    withdrawal.status = 'failed'
                    withdrawal.user.wallet = (withdrawal.amount+50)
                    db.session.add(Notify(
                        user_id=withdrawal.user.id,
                        message=f"This order: {withdrawal.acct_name}, doesnt have a valid bank, so the system could not get bankcode",
                        level="error",
                        seen=False,
                        expire_at=datetime.now() + timedelta(hours=1)
                    ))
                    db.session.commit()
                    return 'failed'


                # Resolve account name
                if not resolve_nombank(withdrawal.acct_number, withdrawal.bank_code, withdrawal.acct_name,access_token,
                               account_id):
                    withdrawal.status = 'failed'
                    withdrawal.user.wallet = (withdrawal.amount + 50)
                    db.session.add(Notify(
                        user_id=withdrawal.user.id,
                        message=f"This order: {withdrawal.acct_name}, Account name and resolved name doesnt match.",
                        level="error",
                        seen=False,
                        expire_at=datetime.now() + timedelta(hours=1)
                    ))
                    db.session.commit()
                    return 'failed'

                db.session.commit()
                # Initiate transfer
                transfered = nombank_transfer(float(withdrawal.amount),withdrawal.acct_number,withdrawal.acct_name,withdrawal.bank_code, withdrawal.reference,"Watzup",
                                      account_id,access_token)

                if transfered['description'] == 'FAILED':
                    db.session.add(Notify(
                        user_id=withdrawal.user.id,
                        message=transfered.get("message", "transfer failed"),
                        level="error",
                        seen=False,
                        expire_at=datetime.now() + timedelta(hours=1)
                    ))
                    db.session.commit()
                    return 'failed'

                withdrawal.status = 'pending'

            elif confirm['description'] == 'SUCCESS' and confirm['data']['status'] in ['SUCCESS', 'PAYMENT_SUCCESSFUL']:
                withdrawal.status = 'paid'
            elif confirm['description'] == 'SUCCESS' and confirm['data']['status'] in ['PENDING_PAYMENT','PENDING_BILLING','PENDING']:
                withdrawal.status = 'processing'
            elif confirm['description'] == 'SUCCESS' and confirm['data']['status'] in ['PAYMENT_FAILED','FAILED']:
                withdrawal.user.wallet = (withdrawal.amount + 50)
                withdrawal.status = "failed"
            # else:
            #     withdrawal.status = confirm['data']['status'].lower()
            db.session.commit()


        except Exception as e:
            db.session.rollback()
            db.session.add(Notify(
                user_id=withdrawal.user.id,
                message=f'{str(e)}',
                level='error',
                seen=False,
                expire_at=datetime.now() + timedelta(hours=1)
            ))
            db.session.commit()
        return "done"


def automating():
    print("Thread started")
    while True:
        with app.app_context():
            withdrawals = Withdraw.query.filter(Withdraw.status == "processing").all()
        threads = []
        for withdrawal in withdrawals:
            t = threading.Thread(target=work,args=(withdrawal,))
            t.start()
            threads.append(t)

            if len(threads)==5:
                for t in threads:
                    t.join()
                threads.clear()
        time.sleep(5)


if __name__ == "__main__":
    t = threading.Thread(target=automating, daemon=True)
    t.start()
    app.run(debug=False, port=5000)
