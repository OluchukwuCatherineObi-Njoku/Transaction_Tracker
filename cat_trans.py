import csv
import re
from datetime import datetime
from collections import defaultdict


SAVINGS = 1
NULL_TRANSFERS = 2
EXPENSE = 3



def name_processing(name):
    if 'Internet Banking INTERNET TRANSFER' in name:
        return ['Internet Banking INTERNET TRANSFER',NULL_TRANSFERS]
    elif re.search(r"E-TRANSFER\s+(.*?)\s+MeeeW", name):
        return ['Internet Banking E-TRANSFER MeeeW',SAVINGS]
    elif name == 'Electronic Funds Transfer PREAUTHORIZED DEBIT SPECIAL DEPOSIT':
        return ['Electronic Funds Transfer PREAUTHORIZED DEBIT SPECIAL DEPOSIT',SAVINGS]
    elif name == 'PAYMENT THANK YOU/PAIEMEN T MERCI':
        return ['PAYMENT THANK YOU/PAIEMEN T MERCI',NULL_TRANSFERS]
    else:
        return [name.strip(),EXPENSE]

def write_transactions_to_csv(transactions, totals, output_file):
    if not transactions:
        print("No transactions to write.")
        return

    # Define column order
    fieldnames = ["date", "name", "savings", "expense", "income"]

    with open(output_file, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        writer.writeheader()

        for t in transactions:
            writer.writerow({
                "date": t["date"].strftime("%Y-%m-%d"),
                "name": t["name"],
                "savings": t["savings"],
                "expense": t["expense"],
                "income": t["income"]
            })

        writer.writerow({k: "" for k in fieldnames})

        # Totals section
        writer.writerow({
            "date": "TOTAL",
            "name": "Income",
            "savings": totals["total_income"],
            "expense": "",
            "income": ""
        })

        writer.writerow({
            "date": "TOTAL",
            "name": "Expense",
            "savings": totals["total_expense"],
            "expense": "",
            "income": ""
        })

        writer.writerow({
            "date": "TOTAL",
            "name": "Savings",
            "savings": totals["total_savings"],
            "expense": "",
            "income": ""
        })

        writer.writerow({
            "date": "TOTAL",
            "name": "Unallocated",
            "savings": totals["unallocated"],
            "expense": "",
            "income": ""
        })

        writer.writerow({
            "date": "BALANCE",
            "name": "Total Income - Total Expense",
            "savings": totals["balance"],
            "expense": "",
            "income": ""
        })


def write_monthly_totals(monthly, output_file):
    
    # Write to CSV
    fieldnames = ["month", "income", "expense", "savings", "balance", "unallocated"]

    with open(output_file, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for month in sorted(monthly.keys()):
            row = {"month": month}
            row.update(monthly[month])
            writer.writerow(row)

    print(f"Monthly totals exported: {output_file}")


def read_transactions(file_path,transactions):

    with open(file_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)

        for row_num, row in enumerate(reader, start=1):
            if len(row) < 4:
                print(f"Skipping row {row_num}: incorrect number of columns")
                continue

            date_str, name, expense, income = row[:4]

            try:
                trans_cat = name_processing(name)
                transaction = {
                    "date": datetime.strptime(date_str, "%Y-%m-%d"),
                    "name": trans_cat[0],
                    "savings": float(expense) if trans_cat[1] == SAVINGS and expense.strip() else 0.0,
                    "expense": float(expense) if trans_cat[1] == EXPENSE and expense.strip() else 0.0,
                    "income": float(income) if trans_cat[1] != NULL_TRANSFERS and income.strip() else 0.0
                }
                transactions.append(transaction)

            except ValueError as e:
                print(f"Skipping row {row_num}: {e}")

    return transactions


def process_transactions(transactions):

    total_expense = 0
    total_income = 0
    total_savings = 0

    monthly_recs = defaultdict(lambda: {
    "income": 0.0,
    "expense": 0.0,
    "savings": 0.0,
    "balance": 0.0,
    "unallocated": 0.0
})

    for t in transactions: 
        month = t["date"].strftime("%Y-%m")

        monthly_recs[month]["income"] += t["income"]
        monthly_recs[month]["expense"] += t["expense"]
        monthly_recs[month]["savings"] += t["savings"]
        monthly_recs[month]["balance"] = monthly_recs[month]["income"] - monthly_recs[month]["expense"]
        monthly_recs[month]["unallocated"] = monthly_recs[month]["balance"] - monthly_recs[month]["savings"]

        total_expense += t["expense"]
        total_income += t["income"]
        total_savings += t["savings"]

    balance = total_income - total_expense
    unallocated = balance - total_savings

    print(f"Total Income : {total_income:.2f}")
    print(f"Total Expense: {total_expense:.2f}")
    print(f"Total Savings: {total_savings:.2f}")
    print(f"Unallocated  : {unallocated:.2f}")
    print(f"Balance      : {balance:.2f}")
    

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "total_savings": total_savings,
        "balance": balance,
        "unallocated": unallocated
    }, monthly_recs


if __name__ == "__main__":

    transactions = []
    read_transactions("cibc.csv", transactions)
    read_transactions("cibc_saving.csv", transactions)
    read_transactions("cibc_credit.csv", transactions)

    transactions.sort(key=lambda t: t["date"])

    print(f"Loaded {len(transactions)} transactions\n")

    trans_sums, monthlies = process_transactions(transactions)

    write_transactions_to_csv(transactions, trans_sums, "processed.csv")
    write_monthly_totals(monthlies, "monthly_totals.csv")
    # print("CSV exported: processed.csv")
    print(monthlies)

    # # Example: print all transactions
    # for t in transactions:
    #     print(t)