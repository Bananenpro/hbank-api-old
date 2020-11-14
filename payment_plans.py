import database

if __name__ == "__main__":
    payments = database.get_all_payment_plans()

    for payment in payments:
        if not database.execute_payment_plan(payment.id):
            print("Cannot execute payment plan '" + str(payment.id) + "'!")
