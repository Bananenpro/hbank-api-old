import database

if __name__ == "__main__":
    payments = database.get_all_payment_plans()

    for payment in payments:
        database.execute_payment_plan(payment.id, True)
