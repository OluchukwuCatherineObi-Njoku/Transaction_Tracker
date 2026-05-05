from flask import Flask, request, redirect, url_for, send_from_directory, render_template
import os
import socket
import cat_trans

app = Flask(__name__)

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(REPO_DIR, "cibc_data")
OUT_DIR = os.path.join(REPO_DIR, "data_summary")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)


def list_csv_files():
    return sorted([f for f in os.listdir(DATA_DIR) if f.lower().endswith('.csv')])


def format_table(monthlies, trans_sums):
    if not monthlies:
        return "<p>No monthly records.</p>"
    html = ["<table border='1' cellpadding='6' style='border-collapse:collapse;'>"]
    html.append("<tr><th>Month</th><th>Income</th><th>Expense</th><th>Savings</th><th>Balance</th></tr>")
    for m in sorted(monthlies.keys()):
        r = monthlies[m]
        html.append(f"<tr><td>{m}</td><td style='text-align:right'>{r.get('income',0):,.2f}</td><td style='text-align:right'>{r.get('expense',0):,.2f}</td><td style='text-align:right'>{r.get('savings',0):,.2f}</td><td style='text-align:right'>{r.get('balance',0):,.2f}</td></tr>")
    html.append("</table>")
    html.append("<p>")
    html.append(f"<strong>Totals:</strong> Income {trans_sums.get('total_income',0):,.2f} &nbsp; Expense {trans_sums.get('total_expense',0):,.2f} &nbsp; Savings {trans_sums.get('total_savings',0):,.2f} &nbsp; Balance {trans_sums.get('balance',0):,.2f}")
    html.append("</p>")
    return '\n'.join(html)


@app.route('/')
def index():
    files = list_csv_files()
    ip = get_local_ip()
    return render_template('index.html', files=files, ip=ip)


@app.route('/refresh')
def refresh():
    return redirect(url_for('index'))


@app.route('/delete', methods=['POST'])
def delete_files():
    files = list_csv_files()
    removed = 0
    for f in files:
        p = os.path.join(DATA_DIR, f)
        try:
            os.remove(p)
            removed += 1
        except Exception as e:
            print('Could not remove', p, e)
    return f"<p>Removed {removed} file(s). <a href='/'>Back</a></p>"


@app.route('/process', methods=['POST'])
def process():
    csvs = [os.path.join(DATA_DIR, f) for f in list_csv_files()]
    if not csvs:
        return render_template('index.html', files=[], ip=get_local_ip(), message='No CSV files found in cibc_data.')

    transactions = []
    for fp in csvs:
        try:
            cat_trans.read_transactions(fp, transactions)
        except Exception as e:
            return f"<p>Error reading {fp}: {e} <a href='/'>Back</a></p>"

    if not transactions:
        return "<p>No transactions loaded from CSVs. <a href='/'>Back</a></p>"

    transactions.sort(key=lambda t: t['date'])
    trans_sums, monthlies = cat_trans.process_transactions(transactions)

    # write outputs
    processed_path = os.path.join(OUT_DIR, 'processed.csv')
    monthly_path = os.path.join(OUT_DIR, 'monthly_totals.csv')
    try:
        cat_trans.write_transactions_to_csv(transactions, trans_sums, processed_path)
        cat_trans.write_monthly_totals(monthlies, monthly_path)
    except Exception as e:
        return f"<p>Error writing outputs: {e} <a href='/'>Back</a></p>"

    return render_template('result.html', monthlies=monthlies, trans_sums=trans_sums)


@app.route('/outputs')
def outputs():
    files = [f for f in os.listdir(OUT_DIR) if os.path.isfile(os.path.join(OUT_DIR, f))]
    return render_template('outputs.html', files=files)


@app.route('/download/<path:filename>')
def download(filename):
    return send_from_directory(OUT_DIR, filename, as_attachment=True)


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return 'localhost'


if __name__ == '__main__':
    print('Starting web UI on 0.0.0.0:5000 (accessible from phone on same network)')
    app.run(host='0.0.0.0', port=5000)
