import csv
import re
import sys
from datetime import date
from pathlib import Path

# Ma nhom noi dung -> tien to message_id
PREFIX = {
    1: "FRI",
    2: "COM",
    3: "PHONE",
    4: "NEWS",
    5: "BANK",
    6: "TE",
    7: "WEB",
    8: "SYN",
    9: "MIX",
}

# Dinh dang cu: 3 | noi dung tin nhan
PIPE_START = re.compile(r"^\s*(\d{1,2})\s*\|\s*(.*)$")

# Che so dien thoai Viet Nam dang lien nhau hoac co dau cach/gach.
# Vi du: 0912345678, 0912 345 678, +84 912345678.
PHONE_RE = re.compile(
    r"(?<!\d)(?:0(?:[\s().-]*\d){9,10}|\+?84(?:[\s().-]*\d){9})(?!\d)"
)


def clean_message(text: str) -> str:
    """Chuan hoa khoang trang va che so dien thoai."""
    text = str(text or "")
    text = PHONE_RE.sub("[NUMBER]", text)
    return " ".join(text.split())


def is_header(row) -> bool:
    """Nhan dien dong tieu de cua file TSV xuat tu Excel."""
    if len(row) < 2:
        return False
    first = row[0].strip().casefold()
    second = row[1].strip().casefold()
    return first in {"nhãn", "label", "mã", "ma", "code"} and second in {
        "text", "message", "tin nhắn", "tin nhan"
    }


def read_tsv(path: Path, label: int):
    """Doc file dang bang: cot 1 = ma nhom, cot 2 = noi dung.

    csv.reader xu ly duoc noi dung co nhieu dong neu o Excel duoc bao bang ngoac kep.
    Cac cot trong them (neu co) se duoc bo qua.
    """
    records, errors = [], []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f, delimiter="\t", quotechar='"')
            for row_no, row in enumerate(reader, start=1):
                if not row or not any(cell.strip() for cell in row):
                    continue
                if row_no == 1 and is_header(row):
                    continue
                if len(row) < 2:
                    errors.append(f"{path.name}, ban ghi {row_no}: khong co cot noi dung")
                    continue

                code_text = row[0].strip()
                if not re.fullmatch(r"\d{1,2}", code_text):
                    errors.append(
                        f"{path.name}, ban ghi {row_no}: ma nhom '{code_text}' khong hop le"
                    )
                    continue

                code = int(code_text)
                if code not in PREFIX:
                    errors.append(
                        f"{path.name}, ban ghi {row_no}: ma {code} khong nam trong 1-9"
                    )
                    continue

                message = row[1].strip()
                if not message:
                    errors.append(f"{path.name}, ban ghi {row_no}: tin nhan rong")
                    continue

                records.append({
                    "prefix": PREFIX[code],
                    "message": message,
                    "label": label,
                    "source": path.name,
                    "row_no": row_no,
                })
    except (OSError, csv.Error) as exc:
        errors.append(f"Khong doc duoc {path.name}: {exc}")

    return records, errors