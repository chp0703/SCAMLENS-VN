import csv, glob

def norm(s):
    return " ".join(s.lower().split())

# Đọc bộ cũ
with open("full_dataset.csv", newline="", encoding="utf-8-sig") as f:
    old = list(csv.DictReader(f))

# Gộp file của các thành viên, bỏ tin trùng (trùng với bộ cũ hoặc trùng giữa các người)
seen = {norm(r["message"]) for r in old}
new = []
for fname in sorted(glob.glob("out_*.csv")):
    with open(fname, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            key = norm(r["message"])
            if key in seen:
                continue
            seen.add(key)
            new.append(r)

full = old + new

# Kiểm tra ID không trùng
ids = [r["message_id"] for r in full]
assert len(ids) == len(set(ids)), "ID bi trung!"

# Ghi file kết quả
cols = ["message_id", "date", "message", "label"]
with open("full_dataset_v2.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(full)

n1 = sum(int(r["label"]) for r in full)
print(f"Them {len(new)} mau, tong {len(full)} | scam: {n1}, ham: {len(full) - n1}")