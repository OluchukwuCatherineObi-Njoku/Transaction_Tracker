import os
import cat_trans


def prompt_yes_no(prompt, default=False):
    yn = "[y/N]" if not default else "[Y/n]"
    resp = input(f"{prompt} {yn}: ").strip().lower()
    if not resp:
        return default
    return resp in ("y", "yes")


def clean_directory(dir_path):
    for fname in os.listdir(dir_path):
        fpath = os.path.join(dir_path, fname)
        try:
            if os.path.isfile(fpath) or os.path.islink(fpath):
                os.remove(fpath)
            elif os.path.isdir(fpath):
                print(f"Skipping directory: {fpath}")
        except Exception as e:
            print(f"Could not remove {fpath}: {e}")


def resolve_output_path(path, description):
    path = os.path.abspath(path)
    if os.path.exists(path):
        try:
            os.remove(path)
            return path
        except PermissionError:
            print(f"Cannot remove existing {description} at: {path}")
            print("The file may be open in another program (e.g. Excel).")
            while True:
                resp = input(
                    "Close the file and press Enter to retry, type a new path, or 'skip': "
                ).strip()
                if resp.lower() == 'skip':
                    return None
                if resp:
                    new_path = os.path.abspath(resp)
                    try:
                        os.makedirs(os.path.dirname(new_path), exist_ok=True)
                        return new_path
                    except Exception as e:
                        print(f"Could not use path {new_path}: {e}")
                        continue
                try:
                    os.remove(path)
                    return path
                except PermissionError:
                    print("Still locked — close the file and try again.")
                except FileNotFoundError:
                    return path
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "cibc_data")
    os.makedirs(data_dir, exist_ok=True)

    current_files = [f for f in os.listdir(data_dir) if os.path.isfile(os.path.join(data_dir, f))]
    if current_files:
        print(f"'{data_dir}' contains {len(current_files)} file(s).")
        if prompt_yes_no("Delete existing files before adding new ones?", default=False):
            clean_directory(data_dir)
            print("Existing files deleted.")
        else:
            print("Keeping existing files.")
    else:
        print(f"'{data_dir}' is empty and ready.")

    print(f"\nDownload your CIBC CSV files into:\n  {data_dir}")
    input("\nPress Enter when downloads are complete...\n")

    csv_files = sorted(
        os.path.join(data_dir, f)
        for f in os.listdir(data_dir)
        if f.lower().endswith('.csv')
    )

    if not csv_files:
        print("No CSV files found. Exiting.")
        return

    print(f"Found {len(csv_files)} CSV file(s):")
    for p in csv_files:
        print(f"  {p}")

    transactions = []
    for fp in csv_files:
        try:
            cat_trans.read_transactions(fp, transactions)
        except Exception as e:
            print(f"Error reading {fp}: {e}")

    if not transactions:
        print("No transactions loaded. Exiting.")
        return

    transactions.sort(key=lambda t: t["date"])

    trans_sums, monthlies = cat_trans.process_transactions(transactions)

    out_dir = os.path.join(script_dir, "data_summary")
    os.makedirs(out_dir, exist_ok=True)

    proc_path  = resolve_output_path(os.path.join(out_dir, "processed.csv"),      "processed CSV")
    month_path = resolve_output_path(os.path.join(out_dir, "monthly_totals.csv"), "monthly totals CSV")

    if proc_path:
        cat_trans.write_transactions_to_csv(transactions, trans_sums, proc_path)
    else:
        print("Skipped writing processed CSV.")

    if month_path:
        cat_trans.write_monthly_totals(monthlies, month_path)
    else:
        print("Skipped writing monthly totals CSV.")

    print("\n--- Summary ---")
    print(f"  Income:  ${trans_sums['total_income']:>10,.2f}")
    print(f"  Expense: ${trans_sums['total_expense']:>10,.2f}")
    print(f"  Savings: ${trans_sums['total_savings']:>10,.2f}")
    print(f"  Balance: ${trans_sums['balance']:>10,.2f}")
    print(f"\nOutput written to: {out_dir}")


if __name__ == '__main__':
    main()
