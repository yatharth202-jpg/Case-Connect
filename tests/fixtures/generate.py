"""
Seed-controlled Robustness Fixture Generator for CaseConnect AI.
Produces synthetic, non-personal data fixtures in diverse layouts, delimiters, encodings,
preambles, currency formats, and edge-case structures.
Complies with non-negotiable project privacy and data-agnostic standards.
"""

import argparse
import csv
import os
import random
from pathlib import Path

try:
    import openpyxl
except ImportError:
    openpyxl = None


def generate_fixtures(output_dir: str = "tests/fixtures/generated", scale_rows: int = 5000):
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    random.seed(42)

    # ---------------------------------------------------------
    # Fixture 1: Shuffled CDR, Pipe-delimited, ISO-8859-1, Hindi/Hinglish headers, Preamble=5
    # ---------------------------------------------------------
    f1_path = out_path / "fixture_1_shuffled_cdr_pipe.csv"
    with open(f1_path, "w", encoding="iso-8859-1", newline="") as f:
        # 5-row preamble
        f.write("# TELECOM FORENSIC DUMP CIRCLE NORTH\n")
        f.write("# CONFIDENTIAL DISCLOSURE UNDER BSA 2023\n")
        f.write("# EXTRACT TIME: 2024-08-01 10:00:00\n")
        f.write("# CELL TOWER RADIUS: 500M\n")
        f.write("# AUTHORIZED BY NODAL OFFICER\n")
        writer = csv.writer(f, delimiter="|")
        # Shuffled columns + unknown columns + Hindi/Hinglish headers
        writer.writerow(["samay_avadh_sec", "anumanit_tower_code", "kall_paane_wala", "extra_vendor_tag", "kall_karne_wala", "call_start_utc"])
        base_phones = ["9876543210", "9811122233", "9722233344", "9633344455", "9544455566"]
        for i in range(100):
            caller = random.choice(base_phones)
            receiver = f"98{random.randint(10000000, 99999999)}"
            duration = random.randint(10, 1800)
            tower = f"DEL-TWR-{random.randint(100, 999)}"
            vendor = f"VEND_REF_{random.randint(1000, 9999)}"
            ts = f"2024-08-{random.randint(1, 28):02d} {random.randint(0, 23):02d}:{random.randint(0, 59):02d}:{random.randint(0, 59):02d}"
            writer.writerow([duration, tower, receiver, vendor, caller, ts])

    # ---------------------------------------------------------
    # Fixture 2: Bank Statement, Semicolon-delimited, Windows-1252, Separate Debit/Credit,
    # Lakh-style amounts, Preamble=15, Day-first dates
    # ---------------------------------------------------------
    f2_path = out_path / "fixture_2_bank_lakh_semicolon.csv"
    with open(f2_path, "w", encoding="cp1252", newline="") as f:
        # 15-row preamble simulating bank statement letterhead
        f.write("STATE BANK FORENSIC DISCLOSURE STATEMENT\n")
        f.write("BRANCH: CONNAUGHT PLACE NEW DELHI\n")
        f.write("IFSC: SBIN0000691\n")
        f.write("ACCOUNT HOLDER: M/S ENTERPRISE HOLDINGS\n")
        f.write("ACCOUNT NUMBER: 00000030123456789\n")
        f.write("STATEMENT PERIOD: 01/01/2024 TO 31/07/2024\n")
        f.write("CURRENCY: INR (INDIAN RUPEES)\n")
        for p in range(8):
            f.write(f"NOTICE LINE {p+1}: SYSTEM GENERATED COMPUTER RECORD\n")
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["Txn Date", "Value Date", "Description / Narration", "Debit (Dr)", "Credit (Cr)", "Balance (INR)", "RRN / Reference No"])
        accounts = ["30123456789", "40987654321", "50111222333"]
        for i in range(120):
            day = random.randint(1, 28)
            month = random.randint(1, 7)
            txn_date = f"{day:02d}/{month:02d}/2024"
            val_date = f"{day:02d}/{month:02d}/2024"
            rrn = f"420{random.randint(100000000, 999999999)}"
            is_credit = random.random() > 0.5
            amt = random.randint(500, 2500000) / 100.0
            # format lakh style with Rs. for cp1252 compatibility
            amt_str = f"Rs. {amt:,.2f}"
            if is_credit:
                writer.writerow([txn_date, val_date, f"UPI/TRANSFER/{rrn}/PAYMENT", "", amt_str, "Rs. 5,00,000.00", rrn])
            else:
                writer.writerow([txn_date, val_date, f"IMPS/OUTWARD/{rrn}/MULE", amt_str, "", "Rs. 4,75,000.00", rrn])

    # ---------------------------------------------------------
    # Fixture 3: Bank Signed Amount, TSV (Tab), UTF-8, Single Signed Amount, Month-first dates, No Preamble
    # ---------------------------------------------------------
    f3_path = out_path / "fixture_3_bank_signed_tab.tsv"
    with open(f3_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["transaction_date", "from_account", "to_account", "net_amount", "upi_vpa", "remarks_tag"])
        for i in range(100):
            m = random.randint(1, 12)
            d = random.randint(1, 28)
            date_str = f"{m:02d}/{d:02d}/2024 14:20:00"
            from_acc = f"ACC{random.randint(100000, 999999)}"
            to_acc = f"ACC{random.randint(100000, 999999)}"
            sign = -1 if random.random() > 0.5 else 1
            net_amt = sign * (random.randint(1000, 500000) / 100.0)
            vpa = f"merchant{random.randint(10, 99)}@okaxis"
            tag = f"AUDIT_FLAG_{random.randint(1, 5)}"
            writer.writerow([date_str, from_acc, to_acc, f"{net_amt:+.2f}", vpa, tag])

    # ---------------------------------------------------------
    # Fixture 4: Multi-sheet Excel (.xlsx), Two sheets (CDR + Banking)
    # ---------------------------------------------------------
    if openpyxl:
        f4_path = out_path / "fixture_4_multisheet_evidence.xlsx"
        wb = openpyxl.Workbook()
        # Sheet 1: CDR_Summary
        ws1 = wb.active
        ws1.title = "CDR_Summary"
        ws1.append(["Call_ID", "Originating_MSISDN", "Terminating_MSISDN", "Start_Timestamp", "Duration_Sec", "IMEI_Number"])
        for i in range(50):
            imei = f"8675430{random.randint(10000000, 99999999)}"
            ws1.append([f"CALL-{i+1000}", f"98765{i:05d}", f"91234{i:05d}", "2024-07-10 12:00:00", random.randint(30, 600), imei])

        # Sheet 2: Banking_Ledger
        ws2 = wb.create_sheet(title="Banking_Ledger")
        ws2.append(["Txn_Ref", "Remitter_Account", "Beneficiary_Account", "Amount_INR", "IFSC", "Payment_Type"])
        for i in range(50):
            ws2.append([f"TXN-{i+5000}", f"100200300{i:03d}", f"900800700{i:03d}", random.randint(1000, 90000), "HDFC0000001", "RTGS"])

        wb.save(f4_path)

    # ---------------------------------------------------------
    # Fixture 5: Edge Cases
    #   - empty.csv (0 bytes)
    #   - header_only.csv (0 data rows)
    #   - one_row_leading_zeros.csv (1 row, preserved zeros)
    # ---------------------------------------------------------
    f5_empty = out_path / "fixture_5a_empty.csv"
    with open(f5_empty, "w", encoding="utf-8") as f:
        pass  # 0 bytes

    f5_header = out_path / "fixture_5b_header_only.csv"
    with open(f5_header, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["caller_phone", "receiver_phone", "timestamp", "duration"])

    f5_onerow = out_path / "fixture_5c_one_row_leading_zeros.csv"
    with open(f5_onerow, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["phone_number", "bank_account", "customer_name", "amount_inr"])
        writer.writerow(["09876543210", "000123456789", "Aditi Sharma", "1500.00"])

    # ---------------------------------------------------------
    # Fixture 6: Scalable Dataset (default 5,000 rows, can be scaled up to 200,000)
    # ---------------------------------------------------------
    f6_path = out_path / "fixture_6_scale_dataset.csv"
    with open(f6_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["record_seq", "source_msisdn", "destination_msisdn", "call_timestamp_utc", "duration_seconds", "cell_site_id"])
        for i in range(scale_rows):
            src = f"98{random.randint(10000000, 99999999)}"
            dst = f"97{random.randint(10000000, 99999999)}"
            ts = "2024-06-15 08:30:00"
            dur = random.randint(5, 1200)
            site = f"DEL-{random.randint(1000, 9999)}"
            writer.writerow([i + 1, src, dst, ts, dur, site])

    print(f"Successfully generated all robustness fixtures in: {out_path.resolve()}")
    print(f"Scale dataset row count: {scale_rows}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate CaseConnect AI Robustness Fixtures")
    parser.add_argument("--output", default="tests/fixtures/generated", help="Output directory")
    parser.add_argument("--scale", type=int, default=5000, help="Row count for scale fixture (default 5000)")
    args = parser.parse_args()
    generate_fixtures(output_dir=args.output, scale_rows=args.scale)
