class UserDto:
    def __init__(self, name, profile_picture, balance, is_parent):
        self.name = name
        self.profile_picture = profile_picture
        self.balance = balance
        self.is_parent = is_parent


class ScheduledPaymentDto:
    def __init__(self, schedule_id, sender_name, receiver_name, days, schedule, amount, desc):
        self.id = schedule_id
        self.sender_name = sender_name
        self.receiver_name = receiver_name
        self.days = days
        self.schedule = schedule
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
