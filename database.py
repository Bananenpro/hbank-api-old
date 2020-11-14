import os
import uuid
from datetime import datetime, timedelta
import hashlib

from pony.orm import *
from models import *
from dtos import *

db.bind(provider="sqlite", filename="database.sqlite", create_db=True)
db.generate_mapping(create_tables=True)


# User
@db_session
def create_user(name, password, is_parent):

    salt = os.urandom(32)

    key = generate_hash(password.encode("utf-8"), salt)

    password_hash = salt + key
    User(name=name, password_hash=password_hash, is_parent=is_parent, balance=1000 if is_parent else 0)


@db_session
def login_user(name, password):
    try:
        user = User[name]
        if user is None:
            return None
        password_db = user.password_hash
        salt = password_db[:32]
        password_hash_db = password_db[32:]
        key = generate_hash(password.encode("utf-8"), salt)
        if key == password_hash_db:
            user.auth_token = str(uuid.uuid4())
            user.token_expiration_date = datetime.now() + timedelta(days=1)
            return user.auth_token
        else:
            return None
    except ObjectNotFound:
        return None


@db_session
def logout_user(username):
    try:
        user = User[username]
        user.auth_token = ""
        user.token_expiration_date = None
    except ObjectNotFound:
        return


@db_session
def verify_auth_token(username, token):
    if token[:7] != "Bearer ":
        return False
    try:
        user = User[username]
        if user.auth_token is None or user.token_expiration_date is None:
            return False
        if user.token_expiration_date < datetime.now():
            user.auth_token = ""
            user.token_expiration_date = None
            return False
        token_db = user.auth_token
        key_db = token_db
        key = token[7:]
        if key == key_db:
            return True
    except ObjectNotFound:
        return False
    return False


@db_session
def get_user_by_auth_token(token):
    if token[:7] != "Bearer ":
        return None
    user = User.get(auth_token=token[7:])
    if user is None or user.auth_token is None or user.token_expiration_date is None:
        return None
    if user.token_expiration_date < datetime.now():
        user.auth_token = ""
        user.token_expiration_date = None
        return None
    return user


def generate_hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password, salt, 1000000)


@db_session
def get_users():
    users = select(u for u in User)
    dtos = []
    for u in users:
        dtos.append(UserDto(u.name, u.profile_picture, u.balance, u.is_parent))
    return dtos


@db_session
def get_user(name):
    try:
        u = User[name]
        return UserDto(u.name, u.profile_picture, u.balance, u.is_parent)
    except ObjectNotFound:
        return None


@db_session
def change_profile_picture_path(username, new_profile_picture_path):
    try:
        user = User[username]

        if user.profile_picture is not None and os.path.isfile(user.profile_picture):
            os.remove(user.profile_picture)

        user.profile_picture = new_profile_picture_path
    except ObjectNotFound:
        return


@db_session
def delete_user(name):
    try:
        user = User[name]
        log = select(entry for entry in Log if entry.sender_name == name or entry.receiver_name == name)

        for entry in log:
            if entry.sender_name == name:
                if entry.receiver_name == name or User.get(name=entry.receiver_name) is None:
                    entry.delete()
            else:
                if User.get(name=entry.sender_name) is None:
                    entry.delete()

        delete(sp for sp in PaymentPlan if sp.sender_name == name or sp.receiver_name == name)

        if user.profile_picture is not None and os.path.isfile(user.profile_picture):
            os.remove(user.profile_picture)

        user.delete()
    except ObjectNotFound:
        return


@db_session
def transfer_money(sender_name, receiver_name, amount_str, description):

    amount = Decimal(amount_str.replace(",", "."))

    try:
        sender = User[sender_name]
        receiver = User[receiver_name]

        if sender.balance > amount:
            sender.balance -= amount
            receiver.balance += amount
            create_log_entry(sender.name, receiver.name, amount, sender.balance, receiver.balance, datetime.now(), description)
            return True
    except ObjectNotFound:
        return False
    return False


@db_session
def change_profile_picture(username, profile_picture):
    try:
        user = User[username]
        user.profile_picture = profile_picture
    except ObjectNotFound:
        return


# Payment Plan


@db_session
def get_all_payment_plans():
    schedules = select(sp for sp in PaymentPlan)
    dtos = []
    for s in schedules:
        dtos.append(PaymentPlan(s.id, s.sender_name, s.receiver_name, s.days, s.schedule, s.amount, s.desc))
    return dtos


@db_session
def get_payment_plans(username):
    schedules = select(sp for sp in PaymentPlan if sp.sender_name == username)
    dtos = []
    for s in schedules:
        dtos.append(PaymentPlan(s.id, s.sender_name, s.receiver_name, s.days, s.schedule, s.amount, s.desc))
    return dtos


@db_session
def create_payment_plan(sender_name, receiver_name, amount_str, schedule, description):
    try:
        sender = User[sender_name]
        receiver = User[receiver_name]
    except ObjectNotFound:
        return False
    amount = Decimal(amount_str.replace(",", "."))
    PaymentPlan(sender_name=sender_name, receiver_name=receiver_name, days=0, schedule=schedule, amount=amount, desc=description)
    return True


@db_session
def get_payment_plan(schedule_id):
    try:
        payment = PaymentPlan[schedule_id]
        return PaymentPlan(schedule_id, payment.sender_name, payment.receiver_name, payment.days, payment.schedule, payment.amount, payment.desc)
    except ObjectNotFound:
        return


@db_session
def delete_payment_plan(schedule_id):
    try:
        schedule = PaymentPlan[schedule_id]
        schedule.delete()
    except ObjectNotFound:
        return


@db_session
def execute_payment_plan(schedule_id):
    try:
        sp = PaymentPlan[schedule_id]

        sp.days += 1

        if sp.days >= sp.schedule:
            try:
                sender = User[sp.sender_name]
                receiver = User[sp.receiver_name]
                if sender.balance > sp.amount:
                    sender.balance -= sp.amount
                    receiver.balance += sp.amount
                    create_log_entry(sender.name, receiver.name, sp.amount, sender.balance, receiver.balance, datetime.now(), sp.desc)
                sp.days -= sp.schedule
                return True
            except ObjectNotFound:
                sp.delete()
                return False
        else:
            return True
    except ObjectNotFound:
        return False


# Log
@db_session
def create_log_entry(sender_name, receiver_name, amount, new_balance_sender, new_balance_receiver, time, description):
    Log(sender_name=sender_name, receiver_name=receiver_name, amount=amount, new_balance_sender=new_balance_sender, new_balance_receiver=new_balance_receiver, time=time, desc=description)


@db_session
def get_log(username):
    log = select(entry for entry in Log if entry.sender_name == username or entry.receiver_name == username).order_by(desc(Log.time))
    dtos = []
    for entry in log:
        dtos.append(LogDto(entry.id, entry.sender_name, entry.receiver_name, entry.amount, entry.new_balance_sender, entry.new_balance_receiver, entry.time, entry.desc))
    return dtos
