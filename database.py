import os
import datetime
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
    user = User[name]
    if user is None:
        return None
    password_db = user.password_hash
    salt = password_db[:32]
    password_hash_db = password_db[32:]
    key = generate_hash(password.encode("utf-8"), salt)
    if key == password_hash_db:
        token_salt = os.urandom(32)
        user.auth_token = (token_salt + generate_hash(os.urandom(64), token_salt)).decode("utf-8")
        user.token_expiration_date = datetime.now() + datetime.timedelta(days=1)
        return user.auth_token
    else:
        return None


@db_session
def logout_user(username):
    user = User[username]
    if user is not None:
        user.auth_token = None
        user.token_expiration_date = None


@db_session
def verify_auth_token(username, token):
    if token[:7] != "Bearer ":
        return False
    user = User[username]
    if user is None or user.auth_token is None or user.token_expiration_date is None:
        return False
    if user.token_expiration_date < datetime.now():
        user.auth_token = None
        user.token_expiration_date = None
        return False
    token_db = user.auth_token.encode("utf-8")
    salt = token_db[:32]
    key_db = token_db[32:]
    key = generate_hash(token[7:], salt)
    if key == key_db:
        return True
    return False


@db_session
def get_user_by_auth_token(token):
    if token[:7] != "Bearer ":
        return None
    user = User.get(auth_token=token[7:])
    if user is None or user.auth_token is None or user.token_expiration_date is None:
        return None
    if user.token_expiration_date < datetime.now():
        user.auth_token = None
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
    u = User[name]
    if u is None:
        return None
    return UserDto(u.name, u.profile_picture, u.balance, u.is_parent)


@db_session
def change_profile_picture_path(username, new_profile_picture_path):
    user = User[username]

    if user is None:
        return False

    if user.profile_picture is not None:
        os.remove(user.profile_picture)

    user.profile_picture = new_profile_picture_path


@db_session
def delete_user(name):
    user = User[name]
    if user is not None:

        log = select(entry for entry in Log if entry.sender_name == name or entry.receiver_name == name)
        for entry in log:
            if entry.sender_name == name:
                if entry.receiver_name == name or User[entry.receiver_name] is None:
                    entry.delete()
            else:
                if User[entry.sender_name] is None:
                    entry.delete()

        scheduled_payments = select(sp for sp in ScheduledPayment if sp.sender_name == name or sp.receiver_name == name)
        delete(scheduled_payments)

        if user.profile_picture is not None:
            os.remove(user.profile_picture)

        user.delete()


@db_session
def transfer_money(sender_name, receiver_name, amount, description):
    sender = User[sender_name]
    receiver = User[receiver_name]
    if sender is None or receiver is None:
        return False
    if sender.balance > amount:
        sender.balance -= amount
        receiver.balance += amount
        create_log_entry(sender.name, receiver.name, amount, sender.balance, receiver.balance, datetime.now(), description)
        return True
    return False


@db_session
def change_profile_picture(username, profile_picture):
    user = User[username]
    if user is None:
        return False
    user.profile_picture = profile_picture


# Scheduled Payment


@db_session
def get_all_scheduled_payments():
    schedules = select(sp for sp in ScheduledPayment)
    dtos = []
    for s in schedules:
        dtos.append(ScheduledPaymentDto(s.id, s.sender_name, s.receiver_name, s.days, s.schedule, s.amount, s.desc))
    return dtos


@db_session
def get_scheduled_payments(username):
    schedules = select(sp for sp in ScheduledPayment if sp.sender_name == username)
    dtos = []
    for s in schedules:
        dtos.append(ScheduledPaymentDto(s.id, s.sender_name, s.receiver_name, s.days, s.schedule, s.amount, s.desc))
    return dtos


@db_session
def create_scheduled_payment(sender_name, receiver_name, amount, schedule, description):
    if User[sender_name] is None or User[receiver_name] is None:
        return False
    ScheduledPayment(sender_name=sender_name, receiver_name=receiver_name, days=0, schedule=schedule, amount=amount, desc=description)
    return True


@db_session
def get_scheduled_payment(schedule_id):
    payment = ScheduledPayment[schedule_id]
    if payment is None:
        return None
    return ScheduledPaymentDto(schedule_id, payment.sender_name, payment.receiver_name, payment.days, payment.schedule, payment.amount, payment.desc)


@db_session
def delete_scheduled_payment(schedule_id):
    schedule = ScheduledPayment[schedule_id]
    if schedule is not None:
        schedule.delete()


@db_session
def execute_scheduled_payment(schedule_id):
    sp = ScheduledPayment[schedule_id]
    if sp is None:
        return False
    if sp.days >= sp.schedule:
        sender = User[sp.sender_name]
        receiver = User[sp.receiver_name]
        if sender is None or receiver is None:
            sp.delete()
            return False
        if sender.balance > sp.amount:
            sender.balance -= sp.amount
            receiver.balance += sp.amount
            create_log_entry(sender.name, receiver.name, sp.amount, sender.balance, receiver.balance, datetime.now(), sp.desc)
        sp.days -= sp.schedule
        return True
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
