import os
import psutil

import pytz
from decimal import Decimal, InvalidOperation

import math
from gpiozero import CPUTemperature, DiskUsage

from datetime import datetime
from dateutil.relativedelta import relativedelta

from flask import Flask, jsonify, request, send_file
from waitress import serve
import database
import uuid
from PIL import Image
from salt import SALT


app = Flask(__name__)

profile_picture_directory = 'uploads/profile_pictures/'
TIMEZONE = "Europe/Berlin"
PASSWORD = ""
PARENT_PASSWORD = ""


@app.route("/user")
def get_users():
    if not server_password():
        return "", 403
    users = database.get_users()
    response = []
    for u in users:
        response.append({
            "name": u.name,
            "is_parent": u.is_parent
        })
    return jsonify(response)


@app.route("/user/<string:name>")
def get_user(name):
    if not server_password():
        return "", 403
    user = database.get_user(name)
    if user is None:
        return "", 404
    can_view_balance = False
    try:
        if database.verify_auth_token(name, request.headers["Authorization"]):
            can_view_balance = True
        elif database.get_user_by_auth_token(request.headers["Authorization"]).is_parent:
            can_view_balance = True
    except Exception:
        can_view_balance = False

    if can_view_balance:
        return jsonify({
            "name": user.name,
            "balance": str(user.balance),
            "cash": str(user.cash),
            "last_cash_edit": user.last_cash_edit.astimezone(pytz.timezone(TIMEZONE)).strftime("%d.%m.%Y - %H:%M"),
            "is_parent": user.is_parent
        })
    else:
        return jsonify({
            "name": user.name,
            "is_parent": user.is_parent
        })


@app.route("/register", methods=["POST"])
def register():
    if not server_password():
        return "", 403
    body = request.json
    try:
        name_length = False
        password_length = False
        already_exists = False
        wrong_parent_password = False
        if 1 < len(body["name"]) <= 15:
            name_length = True
        if 6 <= len(body["password"]) <= 15:
            password_length = True
        if database.get_user(body["name"]) is not None:
            already_exists = True
        if body["is_parent"] and body["parent_password"] != PARENT_PASSWORD:
            wrong_parent_password = True

        if password_length and name_length and not already_exists and not wrong_parent_password:
            database.create_user(body["name"], body["password"], body["is_parent"])
            return jsonify({
                "name_length": name_length,
                "password_length": password_length,
                "required_password_length": 6,
                "already_exists": already_exists,
                "wrong_parent_password": wrong_parent_password
            }), 201
        else:
            return jsonify({
                "name_length": name_length,
                "password_length": password_length,
                "required_password_length": 6,
                "already_exists": already_exists,
                "wrong_parent_password": wrong_parent_password
            }), 500
    except KeyError:
        return "", 400


@app.route("/login", methods=["POST"])
def login():
    if not server_password():
        return "", 403
    body = request.json
    try:
        token = database.login_user(body["name"], body["password"])
    except KeyError:
        return "", 400

    if token is None:
        return "", 403

    return jsonify({
        "token": token
    })


@app.route("/logout", methods=["POST"])
def logout():
    if not server_password():
        return "", 403
    try:
        user = database.get_user_by_auth_token(request.headers["Authorization"])
        if user is None:
            return "", 403

        database.logout_user(user.name)
        return "", 200
    except KeyError:
        return "", 403


@app.route("/profile_picture", methods=["POST"])
def change_profile_picture():
    try:
        user = database.get_user_by_auth_token(request.headers["Authorization"])

        if user is None:
            return "", 403

        if "profile_picture" in request.files and request.files is not None and request.files != "":
            image = request.files["profile_picture"]
            root, extension = os.path.splitext(image.filename)

            if extension != ".jpg" and extension != ".jpeg" and extension != ".png":
                return "", 400

            path = os.path.join(profile_picture_directory, str(uuid.uuid4()) + ".jpg")
            image.save(path)
            resize(path, 500.0)
            database.change_profile_picture_path(user.name, path)
            return "", 200
        else:
            return "", 400
    except KeyError:
        return "", 403


@app.route("/cash", methods=["PUT"])
def update_cash():
    if not server_password():
        return "", 403
    try:
        user = database.get_user_by_auth_token(request.headers["Authorization"])
        if user is None:
            return "", 403
        try:
            database.update_cash(user.name, round(Decimal(request.json["cash"].replace(",", ".")), 2))
        except (KeyError, InvalidOperation):
            return "", 400
    except KeyError:
        return "", 403


def resize(filepath, target_size):
    if os.path.isfile(filepath):
        image = Image.open(filepath)
        width, height = image.size

        if width > height:
            factor = height / target_size
        else:
            factor = width / target_size

        new_dim = (int(width/factor), int(height/factor))
        new_image = image.resize(new_dim)
        new_image.save(filepath, "JPEG", dpi=[300, 300], quality=80)


@app.route("/profile_picture/<string:name>")
def get_profile_picture(name):
    try:
        user = database.get_user(name)

        if user is None:
            return "", 404

        picture = user.profile_picture
        if not os.path.isfile(picture):
            picture = os.path.join(profile_picture_directory, "empty.png")
            database.change_profile_picture_path(user.name, "")

        return send_file(picture)
    except Exception:
        return "", 500


@app.route("/profile_picture_id/<string:name>")
def get_profile_picture_id(name):
    user = database.get_user(name)

    if user is None:
        return "", 404

    profile_picture_id = user.profile_picture_id

    return jsonify({"id": profile_picture_id})


@app.route("/user/<string:name>", methods=["DELETE"])
def delete_user(name):
    if not server_password():
        return "", 403
    try:
        if not database.verify_auth_token(name, request.headers["Authorization"]):
            return "", 403
        database.delete_user(name)
        return "", 200
    except KeyError:
        return "", 403


@app.route("/transaction", methods=["POST"])
def transfer_money():
    if not server_password():
        return "", 403
    body = request.json
    try:

        try:
            Decimal(body["amount"].replace(",", "."))
        except InvalidOperation:
            return "", 400

        if body["amount"].startswith("-"):
            return "", 400

        user = database.get_user_by_auth_token(request.headers["Authorization"])
        if user is None:
            return "", 403

        try:
            if len(body["description"]) > 25:
                return "", 400
            if database.transfer_money(user.name, body["receiver"], body["amount"], body["description"]):
                return "", 200
            else:
                return "", 400
        except KeyError:
            return "", 400
    except KeyError:
        return "", 403


@app.route("/payment_plans/")
@app.route("/payment_plans/<string:name>")
def get_payment_plans(name=""):
    if not server_password():
        return "", 403
    response = []
    try:
        user = database.get_user_by_auth_token(request.headers["Authorization"])
        if user is None:
            return "", 403
        payments = database.get_payment_plans(user.name, name)
        for p in payments:
            left_unit_var = left_unit(datetime.now(), p.last_exec, p.schedule, p.schedule_unit)
            next_str = next_exec(p.last_exec, p.schedule, p.schedule_unit).astimezone(pytz.timezone(TIMEZONE)).strftime("%d.%m.%Y")
            next_str = next_str[:-4]+next_str[-2:]
            response.append({
                "id": p.id,
                "schedule": p.schedule,
                "amount": "+" + str(p.amount) if p.receiver_name == user.name else "-" + str(p.amount),
                "description": p.desc,
                "next": next_str,
                "left": left(datetime.now(), p.last_exec, p.schedule, left_unit_var, p.schedule_unit),
                "left_unit": left_unit_var,
                "schedule_unit": p.schedule_unit,
                "user": p.sender_name if p.receiver_name == user.name else p.receiver_name
            })
        return jsonify(response)
    except KeyError:
        return "", 403


def next_exec(last_exec, schedule, schedule_unit):
    last_exec_date = datetime(last_exec.year, last_exec.month, last_exec.day)
    if schedule_unit == "years":
        return last_exec_date + relativedelta(years=schedule)
    elif schedule_unit == "months":
        return last_exec_date + relativedelta(months=schedule)
    elif schedule_unit == "weeks":
        return last_exec_date + relativedelta(weeks=schedule)
    elif schedule_unit == "days":
        return last_exec_date + relativedelta(days=schedule)


def left_unit(now, last_exec, schedule, schedule_unit):
    now_date = datetime(now.year, now.month, now.day)

    next_date = next_exec(last_exec, schedule, schedule_unit)

    delta = relativedelta(next_date, now_date)
    left_years = delta.years

    left_months = delta.months + delta.years * 12

    left_weeks = int(math.floor((next_date - now_date).days / 7.0))

    if left_years > 0 and schedule_unit == "years":
        return "years"

    if (left_months > 0 and (schedule_unit == "years" or schedule_unit == "months")) or (schedule_unit == "months" and left_months == 0 and left_weeks == 5):
        return "months"

    if left_weeks > 0 and schedule_unit != "days":
        return "weeks"

    return "days"


def left(now, last_exec, schedule, unit, schedule_unit):
    now_date = datetime(now.year, now.month, now.day)
    last_exec_date = datetime(last_exec.year, last_exec.month, last_exec.day)

    next_date = None

    if schedule_unit == "years":
        next_date = last_exec_date + relativedelta(years=schedule)
    elif schedule_unit == "months":
        next_date = last_exec_date + relativedelta(months=schedule)
    elif schedule_unit == "weeks":
        next_date = last_exec_date + relativedelta(weeks=schedule)
    elif schedule_unit == "days":
        next_date = last_exec_date + relativedelta(days=schedule)

    if next_date is not None:
        if unit == "years":
            delta = relativedelta(next_date, now_date)
            years = delta.years
            if delta.months > 0 or delta.weeks > 0 or delta.days > 0:
                years += 1
            return years
        elif unit == "months":
            delta = relativedelta(next_date, now_date)
            months = delta.months + delta.years * 12
            if delta.weeks > 0 or delta.days > 0:
                months += 1
            return months
        elif unit == "weeks":
            return int(math.ceil((next_date - now_date).days / 7.0))
        elif unit == "days":
            return (next_date - now_date).days
    return schedule


@app.route("/payment_plan/<int:payment_id>")
def get_payment_plan(payment_id):
    if not server_password():
        return "", 403
    try:
        user = database.get_user_by_auth_token(request.headers["Authorization"])
        plan = database.get_payment_plan(payment_id)
        if user is None or plan is None or (plan.sender_name != user.name and plan.receiver_name != user.name):
            return "", 403

        left_unit_var = left_unit(datetime.now(), plan.last_exec, plan.schedule, plan.schedule_unit)
        next_str = next_exec(plan.last_exec, plan.schedule, plan.schedule_unit).astimezone(pytz.timezone(TIMEZONE)).strftime("%d.%m.%Y")
        next_str = next_str[:-4]+next_str[-2:]
        return jsonify({
            "id": payment_id,
            "schedule": plan.schedule,
            "amount": "+" + str(plan.amount) if plan.receiver_name == user.name else "-" + str(plan.amount),
            "description": plan.desc,
            "next": next_str,
            "left": left(datetime.now(), plan.last_exec, plan.schedule, left_unit_var, plan.schedule_unit),
            "left_unit": left_unit_var,
            "schedule_unit": plan.schedule_unit,
            "user": plan.sender_name if plan.receiver_name == user.name else plan.receiver_name
        })

    except KeyError:
        return "", 403


@app.route("/payment_plan", methods=["POST"])
def create_payment_plan():
    if not server_password():
        return "", 403
    body = request.json
    try:

        try:
            Decimal(body["amount"].replace(",", "."))
        except InvalidOperation:
            return "", 400

        if body["amount"].startswith("-") or body["schedule_unit"].startswith("-"):
            return "", 400

        user = database.get_user_by_auth_token(request.headers["Authorization"])
        if user is None:
            return "", 403
        try:
            if len(body["description"]) > 25:
                return "", 400
            if database.create_payment_plan(user.name, body["receiver"], body["amount"], body["schedule"], body["schedule_unit"], body["description"]):
                return "", 201
            else:
                return "", 400
        except KeyError:
            return "", 400
    except KeyError:
        return "", 403


@app.route("/payment_plan/<int:payment_id>", methods=["DELETE"])
def delete_payment_plan(payment_id):
    if not server_password():
        return "", 403
    try:
        user = database.get_user_by_auth_token(request.headers["Authorization"])
        payment = database.get_payment_plan(payment_id)

        if user is None or payment is None or payment.sender_name != user.name:
            return "", 403

        if payment is None:
            return "", 404

        if database.delete_payment_plan(payment_id):
            return "", 200
        else:
            return "", 500
    except KeyError:
        return "", 403


@app.route("/log/<int:page>")
def get_log(page):
    if not server_password():
        return "", 403
    try:
        user = database.get_user_by_auth_token(request.headers["Authorization"])
        if user is None:
            return "", 403
        log = database.get_log(user.name, page)
        response = []
        for entry in log:
            date_str = entry.time.astimezone(pytz.timezone(TIMEZONE)).strftime("%d.%m.%Y")
            date_str = date_str[:-4]+date_str[-2:]

            today_str = datetime.now().astimezone(pytz.timezone(TIMEZONE)).strftime("%d.%m.%Y")
            today_str = today_str[:-4]+today_str[-2:]

            if date_str == today_str:
                date_str = entry.time.astimezone(pytz.timezone(TIMEZONE)).strftime("%H:%M")

            response.append({
                "id": entry.id,
                "username": entry.sender_name if entry.receiver_name == user.name else entry.receiver_name,
                "amount": "+" + str(entry.amount) if entry.receiver_name == user.name else "-" + str(entry.amount),
                "new_balance": str(entry.new_balance_receiver) if entry.receiver_name == user.name else str(
                    entry.new_balance_sender),
                "date": date_str,
                "description": entry.desc,
                "is_payment_plan": entry.is_payment_plan,
                "payment_plan_id": entry.payment_plan_id
            })
        return jsonify(response)
    except KeyError:
        return "", 403


@app.route("/log/item/<int:item_id>")
def get_log_item(item_id):
    if not server_password():
        return "", 403
    try:
        user = database.get_user_by_auth_token(request.headers["Authorization"])
        if user is None:
            return "", 403

        log_item = database.get_log_item(item_id)

        if log_item is None:
            return "", 404

        if log_item.sender_name != user.name and log_item.receiver_name != user.name:
            return "", 403

        return jsonify({
            "id": log_item.id,
            "username": log_item.sender_name if log_item.receiver_name == user.name else log_item.receiver_name,
            "amount": "+" + str(log_item.amount) if log_item.receiver_name == user.name else "-" + str(log_item.amount),
            "new_balance": str(log_item.new_balance_receiver) if log_item.receiver_name == user.name else str(
                log_item.new_balance_sender),
            "date": log_item.time.astimezone(pytz.timezone(TIMEZONE)).strftime("%d.%m.%Y - %H:%M"),
            "description": log_item.desc,
            "is_payment_plan": log_item.is_payment_plan,
            "payment_plan_id": log_item.payment_plan_id
        })
    except KeyError:
        return "", 403


@app.route("/log-size")
def get_log_size():
    if not server_password():
        return "", 403
    try:
        user = database.get_user_by_auth_token(request.headers["Authorization"])
        if user is None:
            return "", 403
        log_size = database.get_log_size(user.name)

        return jsonify({
            "size": log_size
        })
    except KeyError:
        return "", 403


def calculate_from_date(user, date, deltaunit):
    payments = database.get_all_payment_plans()
    balance = Decimal(str(user.balance))

    for payment in payments:
        if payment.sender_name == user.name or payment.receiver_name == user.name:
            last_exec = datetime(payment.last_exec.year, payment.last_exec.month, payment.last_exec.day)
            while database.should_execute(date, last_exec, payment.schedule, payment.schedule_unit):
                balance += payment.amount if payment.receiver_name == user.name else -payment.amount

                if payment.schedule_unit == "days":
                    last_exec += relativedelta(days=payment.schedule)
                elif payment.schedule_unit == "weeks":
                    last_exec += relativedelta(weeks=payment.schedule)
                elif payment.schedule_unit == "months":
                    last_exec += relativedelta(months=payment.schedule)
                elif payment.schedule_unit == "years":
                    last_exec += relativedelta(years=payment.schedule)

    balance_str = str(balance)
    if balance_str.startswith("-"):
        balance_str = "0"

    return {
        "date": date.astimezone(pytz.timezone(TIMEZONE)).strftime("%d.%m.%Y"),
        "deltatime": str(get_deltatime(date, deltaunit)),
        "deltaunit": deltaunit,
        "balance": balance_str
    }


def calculate_from_deltatime(user, deltatime, deltaunit):
    if deltaunit == "weeks":
        return calculate_from_date(user, datetime.now() + relativedelta(weeks=deltatime), deltaunit)
    elif deltaunit == "months":
        return calculate_from_date(user, datetime.now() + relativedelta(months=deltatime), deltaunit)
    elif deltaunit == "years":
        return calculate_from_date(user, datetime.now() + relativedelta(years=deltatime), deltaunit)
    else:
        return calculate_from_date(user, datetime.now() + relativedelta(days=deltatime), "days")


def get_deltatime(date, deltaunit):
    now = datetime.now()
    now_date = datetime(now.year, now.month, now.day)
    if deltaunit == "years":
        delta = relativedelta(date, now_date)
        years = delta.years
        if delta.months > 0 or delta.weeks > 0 or delta.days > 0:
            years += 1
        return years
    elif deltaunit == "months":
        delta = relativedelta(date, now_date)
        months = delta.months + delta.years * 12
        if delta.weeks > 0 or delta.days > 0:
            months += 1
        return months
    elif deltaunit == "weeks":
        return int(math.ceil((date - now_date).days / 7.0))
    elif deltaunit == "days":
        return (date - now_date).days

    return -1


def calculate_from_money(user, money, deltaunit):
    now = datetime.now()
    now_date = datetime(now.year, now.month, now.day)
    date = datetime(now_date.year, now_date.month, now_date.day)

    result = calculate_from_date(user, date, deltaunit)

    while Decimal(result["balance"]) < money and relativedelta(date, now_date).years < 5:
        if deltaunit == "years":
            date += relativedelta(years=1)
        elif deltaunit == "months":
            date += relativedelta(months=1)
        elif deltaunit == "weeks":
            date += relativedelta(weeks=1)
        else:
            date += relativedelta(days=1)
        result = calculate_from_date(user, date, deltaunit)

    return result


@app.route("/calculate")
def calculate():
    if not server_password():
        return "", 403

    try:
        user = database.get_user_by_auth_token(request.headers["Authorization"])
        if user is None:
            return "", 403

        date_str = request.args.get("date").strip()
        deltatime_str = request.args.get("deltatime").strip()
        deltaunit = request.args.get("deltaunit").strip()
        money_str = request.args.get("money").strip()

        if date_str == "":
            date_str = None
        if deltatime_str == "":
            deltatime_str = None
        if deltaunit == "" or (deltaunit != "days" and deltaunit != "weeks" and deltaunit != "months" and deltaunit != "years"):
            deltaunit = None
        if money_str == "":
            money_str = None

        if ((date_str is not None and deltatime_str is not None) or (money_str is not None and deltatime_str is not None) or (date_str is not None and money_str is not None)) or deltaunit is None:
            return "Too many parameters or no deltaunit!", 400

        try:
            if date_str is not None:
                date = datetime.strptime(date_str, "%d.%m.%Y")
                if relativedelta(date, datetime.now()).years >= 5 + 1:
                    return "Too long", 400
                if date < datetime.now():
                    return "Invalid date", 400
                return jsonify(calculate_from_date(user, date, deltaunit))
            elif deltatime_str is not None:
                deltatime = int(deltatime_str)

                if deltatime < 1:
                    return "Invalid deltatime", 400

                if deltaunit == "weeks":
                    if deltatime >= 52 * 5 + 1:
                        return "Too long", 400
                elif deltaunit == "months":
                    if deltatime >= 12 * 5 + 1:
                        return "Too long", 400
                elif deltaunit == "years":
                    if deltatime >= 5 + 1:
                        return "Too long", 400
                else:
                    if deltatime >= 356 * 5 + 1:
                        return "Too long", 400

                return jsonify(calculate_from_deltatime(user, deltatime, deltaunit))
            elif money_str is not None and not money_str.startswith("-"):
                return jsonify(calculate_from_money(user, Decimal(money_str), deltaunit))
            else:
                return "Too few parameters", 400
        except (ValueError, InvalidOperation):
            return "Invalid parameter(s)!", 400

    except KeyError:
        return "", 403


@app.route("/version/android")
def version():
    if not server_password():
        return "", 403
    file = open("app/android/version", "r")
    app_version = file.read()
    file.close()
    return jsonify({
        "version": int(app_version)
    })


@app.route("/apk")
def apk():
    try:
        return send_file("app/android/h-bank.apk", as_attachment=True)
    except Exception:
        return "", 500


@app.route("/info")
def info():
    if not server_password():
        return "", 403
    payment_plans = os.system("systemctl status hbank-payment-plans.timer") == 0 and os.system("systemctl show hbank-payment-plans.service | grep Result=success") == 0
    backups = os.system("systemctl status hbank-backup.timer") == 0 and os.system("systemctl show hbank-backup.service | grep Result=success") == 0
    temperature = str(round(CPUTemperature().temperature)) + "°C"
    cpu = str(round(psutil.cpu_percent(interval=0.5))) + "%"
    ram_info = get_ram_info()
    ram = str(round((float(ram_info[1])/float(ram_info[0]))*100)) + "%"
    disk = str(round(DiskUsage().usage)) + "%"
    return jsonify({
        "payment_plans": payment_plans,
        "backups": backups,
        "cpu": cpu,
        "ram": ram,
        "disk": disk,
        "temperature": temperature
    })


@app.route("/connect")
def connect():
    if not server_password():
        return "", 403
    else:
        return "", 200


def get_ram_info():
    p = os.popen('free')
    i = 0
    while 1:
        i += 1
        line = p.readline()
        if i == 2:
            return line.split()[1:4]


def server_password():
    try:
        password = request.headers["Password"].strip()
        key = database.generate_hash(password.encode("utf-8"), SALT)
        return key == PASSWORD
    except KeyError:
        return False


if __name__ == "__main__":
    file = open("password", "rb")
    PASSWORD = file.read()
    file.close()
    if PASSWORD is None or len(PASSWORD.strip().strip(b"\r").strip(b"\n")) == 0:
        PASSWORD = b'\xf2\x15\xcd\xb3\xfd\x19(\xa9\x81\xd6\xad\x9dl,<\xce\x02jUX\xe0\x0e\xefc\xf1\x97\x11t\xc6\x14O\xa7'

    file2 = open("parent_password", "rb")
    PARENT_PASSWORD = file2.read()
    file2.close()
    if PARENT_PASSWORD is None or len(PARENT_PASSWORD.strip().strip(b"\r").strip(b"\n")) == 0:
        PARENT_PASSWORD = b"\xf0\x9c\xd9\xabF\xc8\x1aj\xfa\xff\x9e\x1d\x7fq\x19Y\xf1\x14\xb5\x9c\xaa\x9c\xd5\x8co\x8c\xa4\xbbS:'\\"

    serve(app, host='0.0.0.0', port=5000, url_scheme='https')
