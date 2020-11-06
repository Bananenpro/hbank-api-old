import database

if __name__ == "__main__":
    payments = database.get_all_scheduled_payments()

    for payment in payments:
        if not database.execute_scheduled_payment(payment.id):
            print("Cannot execute scheduled payment '" + payment.id + "'!")
