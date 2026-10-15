import csv, re, sys
from datetime import date
from pathlib import Path

PREFIX = {1: "FRI", 2: "COM", 3: "PHONE", 4: "NEWS", 5: "BANK",
          6: "TE", 7: "WEB", 8: "SYN", 9: "MIX"}

if len(sys.argv) < 2:
    sys.exit("Cach dung: python build_dataset.py A   (A = ma thanh vien)")
member = sys.argv[1].upper()

START = re.compile(r"^\s*(\d{1,2})\s*\|\s*(.*)$")
rows, errors = [], []

for fname, label in (("scam.txt", 1), ("ham.txt", 0)):
    cur = None
    lines = Path(fname).read_text(encoding="utf-8-sig").splitlines()
    for n, line in enumerate(lines, 1):
        m = START.match(line)
        if m:
            if cur:
                rows.append(cur)
            code = int(m.group(1))
            if code not in PREFIX:
                errors.append(f"{fname} dong {n}: ma {code} khong hop le")
                cur = None
            else:
                cur = {"prefix": PREFIX[code], "message": m.group(2), "label": label}
        elif line.strip():
            if cur:
                cur["message"] += " " + line.strip()
            else:
                errors.append(f"{fname} dong {n}: thieu 'so|' o dau tin")
    if cur:
        rows.append(cur)

if errors:
    sys.exit("\n".join(errors[:30]))

today = date.today().strftime("%d/%m/%Y")
seen, count, out_rows = set(), {}, []
for r in rows:
    msg = re.sub(r"\b0\d{9,10}\b", "[NUMBER]", r["message"])  # che SDT
    msg = " ".join(msg.split())
    key = msg.lower()
    if len(msg) <= 5 or key in seen:
        continue
    seen.add(key)
    p = r["prefix"]
    count[p] = count.get(p, 0) + 1
    out_rows.append([f"{p}_{member}{count[p]:04d}", today, msg, r["label"]])

out = f"out_{member}.csv"
with open(out, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["message_id", "date", "message", "label"])
    w.writerows(out_rows)

n1 = sum(r[3] for r in out_rows)
print(f"Xong: {len(out_rows)} mau -> {out} | scam: {n1}, ham: {len(out_rows) - n1}")