import os
import pytz
from decimal import Decimal, InvalidOperation

from datetime import datetime

from flask import Flask, jsonify, request, send_file
from waitress import serve
import database
import uuid
from PIL import Image

app = Flask(__name__)

profile_picture_directory = 'uploads/profile_pictures/'
TIMEZONE = "Europe/Berlin"


@app.route("/user")
def get_users():
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
            "is_parent": user.is_parent
        })
    else:
        return jsonify({
            "name": user.name,
            "is_parent": user.is_parent
        })


@app.route("/register", methods=["POST"])
def register():
    body = request.json
    try:
        name_length = False
        password_length = False
        already_exists = False
        if len(body["name"]) > 1:
            name_length = True
        if len(body["password"]) >= 6:
            password_length = True
        if database.get_user(body["name"]) is not None:
            already_exists = True

        if password_length and name_length and not already_exists:
            database.create_user(body["name"], body["password"], body["is_parent"])
            return jsonify({
                "name_length": name_length,
                "password_length": password_length,
                "required_password_length": 6,
                "already_exists": already_exists
            }), 201
        else:
            return jsonify({
                "name_length": name_length,
                "password_length": password_length,
                "required_password_length": 6,
                "already_exists": already_exists
            }), 500
    except KeyError:
        return "", 400


@app.route("/login", methods=["POST"])
def login():
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
    try:
        if not database.verify_auth_token(name, request.headers["Authorization"]):
            return "", 403
    except KeyError:
        return "", 403

    database.delete_user(name)
    return "", 200


@app.route("/transaction", methods=["POST"])
def transfer_money():
    body = request.json
    try:

        try:
            Decimal(body["amount"].replace(",", "."))
        except InvalidOperation:
            return 400

        if body["amount"].startswith("-"):
            return 400

        user = database.get_user_by_auth_token(request.headers["Authorization"])
        if user is None:
            return "", 403

        try:
            if database.transfer_money(user.name, body["receiver"], body["amount"], body["description"]):
                return "", 200
            else:
                return "", 400
        except KeyError:
            return "", 400
    except KeyError:
        return "", 403


@app.route("/payment_plans")
@app.route("/payment_plans/<string:name>")
def get_payment_plans(name=""):
    response = []
    try:
        user = database.get_user_by_auth_token(request.headers["Authorization"])
        if user is None:
            return "", 403
        payments = database.get_payment_plans(user.name, name)
        for p in payments:
            response.append({
                "id": p.id,
                "schedule": p.schedule,
                "amount": "+" + str(p.amount) if p.sender_name == name else "-" + str(p.amount),
                "description": p.desc,
                "days_left": p.schedule - p.days
            })
        return jsonify(response)
    except KeyError:
        return "", 403


@app.route("/payment_plan/<int:payment_id>")
def get_payment_plan(payment_id):
    try:
        user = database.get_user_by_auth_token(request.headers["Authorization"])
        plan = database.get_payment_plan(payment_id)
        if user is None or plan is None or (plan.sender_name != user.name and plan.receiver_name != user.name):
            return "", 403

        return jsonify({
            "id": payment_id,
            "schedule": plan.schedule,
            "amount": "+" + str(plan.amount) if plan.receiver_name == user.name else "-" + str(plan.amount),
            "description": plan.desc,
            "days_left": plan.schedule - plan.days
        })

    except KeyError:
        return "", 403


@app.route("/payment_plan", methods=["POST"])
def create_payment_plan():
    body = request.json
    try:

        try:
            Decimal(body["amount"].replace(",", "."))
        except InvalidOperation:
            return 400

        if body["amount"].startswith("-"):
            return 400

        user = database.get_user_by_auth_token(request.headers["Authorization"])
        if user is None:
            return "", 403
        try:
            if database.create_payment_plan(user.name, body["receiver"], body["amount"], body["schedule"], body["description"]):
                return "", 201
            else:
                return "", 400
        except KeyError:
            return "", 400
    except KeyError:
        return "", 403


@app.route("/payment_plan/<int:payment_id>", methods=["DELETE"])
def delete_payment_plan(payment_id):
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
                "description": entry.desc
            })
        return jsonify(response)
    except KeyError:
        return "", 403


@app.route("/log/item/<int:item_id>")
def get_log_item(item_id):
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
            "description": log_item.desc
        })
    except KeyError:
        return "", 403


@app.route("/version/android")
def version():
    file = open("app/android/version", "r")
    app_version = file.read()
    file.close()
    return jsonify({
        "version": int(app_version)
    })


@app.route("/apk")
def apk():
    try:
        return send_file("app/android/h-bank.apk")
    except Exception:
        return "", 500


if __name__ == "__main__":
    serve(app, host='0.0.0.0', port=5000)
