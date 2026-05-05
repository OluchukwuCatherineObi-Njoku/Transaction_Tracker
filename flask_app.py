from flask import Flask, request, redirect, url_for, send_from_directory, render_template, flash
from werkzeug.utils import secure_filename
import os
import socket
import cat_trans

app = Flask(__name__)
app.secret_key = os.urandom(24)

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(REPO_DIR, "cibc_data")
OUT_DIR  = os.path.join(REPO_DIR, "data_summary")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUT_DIR,  exist_ok=True)

ALLOWED_EXTENSIONS = {'.csv'}


def list_csv_files():
    return sorted(f for f in os.listdir(DATA_DIR) if f.lower().endswith('.csv'))


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))  # UDP connect: no packet sent, just resolves local interface
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return 'localhost'


@app.template_filter('currency')
def currency_filter(value):
    try:
        return f'${float(value):,.2f}'
    except (ValueError, TypeError):
        return str(value)


@app.route('/')
def index():
    return render_template('index.html', files=list_csv_files(), ip=get_local_ip())


@app.route('/refresh')
def refresh():
    return redirect(url_for('index'))


@app.route('/upload', methods=['POST'])
def upload():
    uploaded = request.files.getlist('files')
    if not uploaded or all(f.filename == '' for f in uploaded):
        flash('No files selected.', 'warning')
        return redirect(url_for('index'))

    saved = 0
    for f in uploaded:
        if not f.filename:
            continue
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            flash(f'Skipped {f.filename} — only CSV files are accepted.', 'warning')
            continue
        f.save(os.path.join(DATA_DIR, secure_filename(f.filename)))
        saved += 1

    if saved:
        flash(f'Uploaded {saved} file{"s" if saved != 1 else ""}.', 'success')
    return redirect(url_for('index'))


@app.route('/delete', methods=['POST'])
def delete_files():
    removed = 0
    for f in list_csv_files():
        try:
            os.remove(os.path.join(DATA_DIR, f))
            removed += 1
        except Exception as e:
            flash(f'Could not remove {f}: {e}', 'warning')
    flash(f'Removed {removed} file{"s" if removed != 1 else ""}.', 'success')
    return redirect(url_for('index'))


@app.route('/process', methods=['POST'])
def process():
    csvs = [os.path.join(DATA_DIR, f) for f in list_csv_files()]
    if not csvs:
        flash('No CSV files found — upload some first.', 'warning')
        return redirect(url_for('index'))

    transactions = []
    for fp in csvs:
        try:
            cat_trans.read_transactions(fp, transactions)
        except Exception as e:
            flash(f'Error reading {os.path.basename(fp)}: {e}', 'danger')
            return redirect(url_for('index'))

    if not transactions:
        flash('No transactions found in the CSV files.', 'warning')
        return redirect(url_for('index'))

    transactions.sort(key=lambda t: t['date'])
    trans_sums, monthlies = cat_trans.process_transactions(transactions)

    try:
        cat_trans.write_transactions_to_csv(transactions, trans_sums, os.path.join(OUT_DIR, 'processed.csv'))
        cat_trans.write_monthly_totals(monthlies, os.path.join(OUT_DIR, 'monthly_totals.csv'))
    except Exception as e:
        flash(f'Error writing outputs: {e}', 'danger')
        return redirect(url_for('index'))

    return render_template('result.html', monthlies=monthlies, trans_sums=trans_sums)


@app.route('/outputs')
def outputs():
    files = sorted(f for f in os.listdir(OUT_DIR) if os.path.isfile(os.path.join(OUT_DIR, f)))
    return render_template('outputs.html', files=files)


@app.route('/download/<path:filename>')
def download(filename):
    return send_from_directory(OUT_DIR, filename, as_attachment=True)


if __name__ == '__main__':
    ip = get_local_ip()
    print(f'\nTransaction Tracker — http://{ip}:5000/')
    print('Open this URL on your phone (same Wi-Fi network)\n')
    app.run(host='0.0.0.0', port=5000, debug=False)
