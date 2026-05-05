import os
import glob
import time
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
                # don't recurse into subdirs for safety
                print(f"Skipping directory: {fpath}")
        except Exception as e:
            print(f"Could not remove {fpath}: {e}")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "cibc_data")
    os.makedirs(data_dir, exist_ok=True)

    current_files = [f for f in os.listdir(data_dir) if os.path.isfile(os.path.join(data_dir, f))]

    if current_files:
        print(f"The folder '{data_dir}' contains {len(current_files)} file(s).")
        if prompt_yes_no("Do you want to delete all files in this folder before downloading new ones?", default=False):
            clean_directory(data_dir)
            print("Existing files deleted.")
        else:
            print("Keeping existing files.")
    else:
        print(f"The folder '{data_dir}' is empty and ready for downloads.")

    print("When you're ready, download the CIBC CSV files into the folder:")
    print(f"  {data_dir}")
    print("When downloads are complete, return here and press Enter to continue.")
    input("Press Enter to continue after downloads are finished...\n")

    # After unpausing, collect CSV files in the folder and process them
    csv_files = sorted([os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.lower().endswith('.csv')])

    if not csv_files:
        print("No CSV files found in the data folder. Exiting.")
        return

    print(f"Found {len(csv_files)} CSV files to process:")
    for p in csv_files:
        print(" - ", p)

    transactions = []
    for fp in csv_files:
        try:
            cat_trans.read_transactions(fp, transactions)
        except Exception as e:
            print(f"Error reading {fp}: {e}")

    if not transactions:
        print("No transactions were loaded from the CSV files.")
        return

    transactions.sort(key=lambda t: t["date"]) if transactions else None

    trans_sums, monthlies = cat_trans.process_transactions(transactions)

    out_dir = os.path.join(script_dir, "data_summary")
    os.makedirs(out_dir, exist_ok=True)

    processed_path = os.path.join(out_dir, "processed.csv")
    monthly_path = os.path.join(out_dir, "monthly_totals.csv")


    def resolve_output_path(path, description):
        path = os.path.abspath(path)
        if os.path.exists(path):
            try:
                os.remove(path)
                return path
            except PermissionError:
                print(f"Cannot remove existing {description} at: {path}")
                print("Common causes: file is open in another program (Excel) or you lack permissions.")
                while True:
                    resp = input("Close the file and press Enter to retry, type a new full path to use instead, or type 'skip' to skip writing this file: ").strip()
                    if resp.lower() == 'skip':
                        return None
                    if resp:
                        # treat as new path
                        new_path = os.path.abspath(resp)
                        new_dir = os.path.dirname(new_path)
                        try:
                            os.makedirs(new_dir, exist_ok=True)
                            return new_path
                        except Exception as e:
                            print(f"Could not use path {new_path}: {e}")
                            continue
                    # empty response -> retry remove
                    try:
                        os.remove(path)
                        return path
                    except PermissionError:
                        print("Still cannot remove the file. Make sure it's closed and try again.")
                    except FileNotFoundError:
                        return path
        else:
            # ensure directory exists
            os.makedirs(os.path.dirname(path), exist_ok=True)
            return path

    proc_path = resolve_output_path(processed_path, 'processed CSV')
    month_path = resolve_output_path(monthly_path, 'monthly totals CSV')

    if proc_path:
        cat_trans.write_transactions_to_csv(transactions, trans_sums, proc_path)
    else:
        print("Skipped writing processed CSV.")

    if month_path:
        cat_trans.write_monthly_totals(monthlies, month_path)
    else:
        print("Skipped writing monthly totals CSV.")

    print("Processing complete. Output written to data_summary folder.")


if __name__ == '__main__':
    main()
