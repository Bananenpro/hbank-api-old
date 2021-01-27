import hashlib
from dateutil.relativedelta import relativedelta
import os
import uuid
from datetime import timedelta

from pony.orm import *

from dtos import *
from models import *

db.bind(provider="sqlite", filename="database.sqlite", create_db=True)
db.generate_mapping(create_tables=True) 

LOG_PAGE_SIZE = 10


# User
@db_session
def create_user(name, password, is_parent):

    salt = os.urandom(32)

    key = generate_hash(password.encode("utf-8"), salt)

    password_hash = salt + key
    User(name=name, password_hash=password_hash, profile_picture_id=0, is_parent=is_parent, balance=5000 if is_parent else 0)


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
            if user.auth_token is not None and user.token_expiration_date is not None and user.auth_token != "" and user.token_expiration_date > datetime.now():
                return user.auth_token
            else:
                user.auth_token = str(uuid.uuid4())
                user.token_expiration_date = datetime.now() + timedelta(days=30)
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
    return UserDto(user.name, user.profile_picture, user.profile_picture_id, user.balance, user.is_parent)


def generate_hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password, salt, 10000)


@db_session
def get_users():
    users = select(u for u in User)
    dtos = []
    for u in users:
        dtos.append(UserDto(u.name, u.profile_picture, u.profile_picture_id, u.balance, u.is_parent))
    return dtos


@db_session
def get_user(name):
    try:
        u = User[name]
        return UserDto(u.name, u.profile_picture, u.profile_picture_id, u.balance, u.is_parent)
    except ObjectNotFound:
        return None


@db_session
def change_profile_picture_path(username, new_profile_picture_path):
    try:
        user = User[username]

        if user.profile_picture is not None and os.path.isfile(user.profile_picture):
            os.remove(user.profile_picture)

        if new_profile_picture_path != "":
            user.profile_picture_id += 1
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

        delete(pp for pp in PaymentPlan if pp.sender_name == name or pp.receiver_name == name)

        if user.profile_picture is not None and os.path.isfile(user.profile_picture):
            os.remove(user.profile_picture)

        user.delete()
    except ObjectNotFound:
        return


@db_session
def transfer_money(sender_name, receiver_name, amount_str, description):

    amount = round(abs(Decimal(amount_str.replace(",", "."))), 2)

    try:
        sender = User[sender_name]
        receiver = User[receiver_name]

        if sender.balance >= amount:
            sender.balance -= amount
            receiver.balance += amount
            create_log_entry(sender.name, receiver.name, amount, sender.balance, receiver.balance, datetime.now(), description, False, -1)
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
    payments = select(pp for pp in PaymentPlan)
    dtos = []
    for p in payments:
        dtos.append(PaymentPlanDto(p.id, p.sender_name, p.receiver_name, p.last_exec, p.schedule, p.schedule_unit, p.amount, p.desc))
    return dtos


@db_session
def get_payment_plans(username, username2):
    if username2 != "":
        payments = select(pp for pp in PaymentPlan if (pp.sender_name == username and pp.receiver_name == username2) or (pp.sender_name == username2 and pp.receiver_name == username))
    else:
        payments = select(pp for pp in PaymentPlan if pp.sender_name == username or pp.receiver_name == username)
    dtos = []
    for p in payments:
        dtos.append(PaymentPlanDto(p.id, p.sender_name, p.receiver_name, p.last_exec, p.schedule, p.schedule_unit, p.amount, p.desc))
    return dtos


@db_session
def create_payment_plan(sender_name, receiver_name, amount_str, schedule, schedule_unit, description):
    if sender_name == receiver_name:
        return False
    try:
        sender = User[sender_name]
        receiver = User[receiver_name]
    except ObjectNotFound:
        return False
    amount = round(abs(Decimal(amount_str.replace(",", "."))), 2)

    last_exec = datetime.now()
    if schedule_unit == "years":
        last_exec = datetime(last_exec.year, 1, 1, last_exec.hour, last_exec.minute, last_exec.second, last_exec.microsecond)
    elif schedule_unit == "months":
        last_exec = datetime(last_exec.year, last_exec.month, 1, last_exec.hour, last_exec.minute, last_exec.second, last_exec.microsecond)

    PaymentPlan(sender_name=sender_name, receiver_name=receiver_name, last_exec=last_exec, schedule=schedule, schedule_unit=schedule_unit, amount=amount, desc=description)
    return True


@db_session
def get_payment_plan(payment_id):
    try:
        payment = PaymentPlan[payment_id]
        return PaymentPlanDto(payment_id, payment.sender_name, payment.receiver_name, payment.last_exec, payment.schedule, payment.schedule_unit, payment.amount, payment.desc)
    except ObjectNotFound:
        return None


@db_session
def delete_payment_plan(payment_id):
    try:
        payment = PaymentPlan[payment_id]
        if execute_payment_plan(payment_id):
            payment.delete()
            return True
    except ObjectNotFound:
        return False
    return False


@db_session
def execute_payment_plan(payment_id):
    try:
        pp = PaymentPlan[payment_id]

        while should_execute(datetime.now(), pp.last_exec, pp.schedule, pp.schedule_unit):
            try:
                sender = User[pp.sender_name]
                receiver = User[pp.receiver_name]
                if sender.balance >= pp.amount:
                    sender.balance -= pp.amount
                    receiver.balance += pp.amount
                    create_log_entry(sender.name, receiver.name, pp.amount, sender.balance, receiver.balance, datetime.now(), pp.desc, True, payment_id)
                    if pp.schedule_unit == "days":
                        pp.last_exec += relativedelta(days=pp.schedule)
                    elif pp.schedule_unit == "weeks":
                        pp.last_exec += relativedelta(weeks=pp.schedule)
                    elif pp.schedule_unit == "months":
                        pp.last_exec += relativedelta(months=pp.schedule)
                    elif pp.schedule_unit == "years":
                        pp.last_exec += relativedelta(years=pp.schedule)
                else:
                    return False
            except ObjectNotFound:
                pp.delete()
                return True

    except ObjectNotFound:
        return True
    return True


def should_execute(now, last_exec, schedule, unit):
    now_date = datetime(now.year, now.month, now.day)
    last_exec_date = datetime(last_exec.year, last_exec.month, last_exec.day)
    if now_date > last_exec_date:
        if unit == "years":
            return now_date >= last_exec_date + relativedelta(years=schedule)
        elif unit == "months":
            return now_date >= last_exec_date + relativedelta(months=schedule)
        elif unit == "weeks":
            return now_date >= last_exec_date + relativedelta(weeks=schedule)
        elif unit == "days":
            return now_date >= last_exec_date + relativedelta(days=schedule)
    return False


# Log
@db_session
def create_log_entry(sender_name, receiver_name, amount, new_balance_sender, new_balance_receiver, time, description, is_payment_plan, payment_plan_id):
    Log(sender_name=sender_name, receiver_name=receiver_name, amount=amount, new_balance_sender=new_balance_sender, new_balance_receiver=new_balance_receiver, time=time, desc=description, is_payment_plan=is_payment_plan, payment_plan_id=payment_plan_id)


@db_session
def get_log(username, page):
    try:
        log = select(entry for entry in Log if entry.sender_name == username or entry.receiver_name == username).order_by(desc(Log.time))[page*LOG_PAGE_SIZE:page*LOG_PAGE_SIZE+LOG_PAGE_SIZE]
    except IndexError:
        try:
            log = select(entry for entry in Log if entry.sender_name == username or entry.receiver_name == username).order_by(desc(Log.time))[page*LOG_PAGE_SIZE:]
        except IndexError:
            return []
    dtos = []
    for entry in log:
        dtos.append(LogDto(entry.id, entry.sender_name, entry.receiver_name, entry.amount, entry.new_balance_sender, entry.new_balance_receiver, entry.time, entry.desc, entry.is_payment_plan, entry.payment_plan_id))
    return dtos


@db_session
def get_log_item(log_id):
    try:
        item = Log[log_id]
        return LogDto(item.id, item.sender_name, item.receiver_name, item.amount, item.new_balance_sender, item.new_balance_receiver, item.time, item.desc, item.is_payment_plan, item.payment_plan_id)
    except ObjectNotFound:
        return None
