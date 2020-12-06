class UserDto:
    def __init__(self, name, profile_picture, profile_picture_id, balance, is_parent):
        self.name = name
        self.profile_picture = profile_picture
        self.profile_picture_id = profile_picture_id
        self.balance = balance
        self.is_parent = is_parent


class PaymentPlanDto:
    def __init__(self, payment_id, sender_name, receiver_name, last_exec, schedule, schedule_unit, amount, desc):
        self.id = payment_id
        self.sender_name = sender_name
        self.receiver_name = receiver_name
        self.last_exec = last_exec
        self.schedule = schedule
        self.schedule_unit = schedule_unit
        self.amount = amount
        self.desc = desc


class LogDto:
    def __init__(self, log_id, sender_name, receiver_name, amount, new_balance_sender, new_balance_receiver, time, desc):
        self.id = log_id
        self.sender_name = sender_name
        self.receiver_name = receiver_name
        self.amount = amount
        self.new_balance_sender = new_balance_sender
        self.new_balance_receiver = new_balance_receiver
        self.time = time
        self.desc = desc
