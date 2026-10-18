
# Hướng dẫn Nhanh: Tải Bộ Dữ Liệu & Huấn Luyện Mô Hình (Quickstart Guide)
ENGLISH BELLOW

Tài liệu này hướng dẫn cách tải bộ dữ liệu **Vietnamese SMS Phishing Dataset** thông qua CLI / Python và cách cấu hình huấn luyện hai mô hình đại diện: **PhoBERT-base** (Transformer) và **Char (3–5 gram) SVM** (Mô hình siêu nhẹ cho Mobile Gateway).

---

## 1. Tải Bộ Dữ Liệu Thông Qua Hugging Face CLI & Python

### Cách 1: Sử dụng Hugging Face CLI (Tải trực tiếp các file CSV về máy)

```bash
# Cài đặt CLI (nếu chưa có)
pip install huggingface_hub

# Tải toàn bộ kho dữ liệu về thư mục local
huggingface-cli download trannguyenthaituan/vietnamese_sms_phishing_dataset --repo-type dataset --local-dir ./vietnamese_sms_dataset
```

### Cách 2: Tải trực tiếp trong Python thông qua thư viện `datasets`

```python
from datasets import load_dataset

# Tải bộ dữ liệu chính thức từ Hugging Face
dataset = load_dataset("trannguyenthaituan/vietnamese_sms_phishing_dataset")

# Xem thông tin phân bố tập dữ liệu
print(dataset)

# Chuyển đổi sang Pandas DataFrame để xử lý
train_df = dataset['train'].to_pandas()
test_df = dataset['test'].to_pandas()

print(f"Số lượng mẫu tập Train: {len(train_df)}")
print(f"Số lượng mẫu tập Test: {len(test_df)}")
```

---

## 2. Cấu hình & Huấn luyện Mô hình Baseline

### Kịch bản 1: Huấn luyện Mô hình Siêu nhẹ Char (3–5 gram) SVM (Khuyến nghị cho Gateway)

```python
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.metrics import classification_report, f1_score

# 1. Load tập dữ liệu Train và Test
train_df = pd.read_csv("./vietnamese_sms_dataset/train.csv")
test_df = pd.read_csv("./vietnamese_sms_dataset/test.csv")

# 2. Khởi tạo TfidfVectorizer cấp độ n-gram ký tự (3-5 gram)
vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(3, 5), max_features=10000)

X_train = vectorizer.fit_transform(train_df['message'].astype(str).str.lower())
X_test = vectorizer.transform(test_df['message'].astype(str).str.lower())
y_train = train_df['label']
y_test = test_df['label']

# 3. Huấn luyện Linear SVM với cấu hình mặc định (C=1.0)
clf = SVC(kernel='linear', C=1.0, random_state=42)
clf.fit(X_train, y_train)

# 4. Dự đoán và hiển thị báo cáo đánh giá
y_pred = clf.predict(X_test)
print(classification_report(y_test, y_pred, target_names=['HAM', 'SPAM']))
print(f"F1-Score (SPAM Class): {f1_score(y_test, y_pred):.4f}")
```

### Kịch bản 2: Fine-tune Mô hình Transformer PhoBERT-base

```python
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
from datasets import Dataset

# 1. Load Tokenizer & Pre-trained Model PhoBERT-base
model_name = "vinai/phobert-base"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=2)

# 2. Hàm Tiền xử lý Tokenize
def tokenize_function(examples):
    return tokenizer(examples["message"], padding="max_length", truncation=True, max_length=128)

# 3. Chuyển đổi dữ liệu và mã hóa
train_ds = Dataset.from_pandas(train_df).map(tokenize_function, batched=True)
test_ds = Dataset.from_pandas(test_df).map(tokenize_function, batched=True)

# 4. Cấu hình Siêu tham số Huấn luyện
training_args = TrainingArguments(
    output_dir="./phobert_sms_output",
    learning_rate=2e-5,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    num_train_epochs=4,
    weight_decay=0.01,
    evaluation_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="f1"
)

# 5. Khởi tạo Trainer và tiến hành Huấn luyện
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=test_ds,
    tokenizer=tokenizer
)

trainer.train()
```
# EMGLISH VERSION
# Quickstart Guide: Download the Dataset & Train Baseline Models

This guide demonstrates how to download the **Vietnamese SMS Phishing Dataset** using either the Hugging Face CLI or Python, and how to train two representative baseline models: **PhoBERT-base** (Transformer) and **Char (3–5 gram) SVM** (an ultra-lightweight model suitable for deployment on mobile SMS gateways).

---

## 1. Download the Dataset via Hugging Face CLI or Python

### Option 1: Download Using the Hugging Face CLI

```bash
# Install the Hugging Face CLI (if not already installed)
pip install huggingface_hub

# Download the complete dataset repository
huggingface-cli download trannguyenthaituan/vietnamese_sms_phishing_dataset \
    --repo-type dataset \
    --local-dir ./vietnamese_sms_dataset
```

### Option 2: Load the Dataset Directly in Python

```python
from datasets import load_dataset

# Load the official dataset from Hugging Face
dataset = load_dataset("trannguyenthaituan/vietnamese_sms_phishing_dataset")

# Display dataset information
print(dataset)

# Convert splits into Pandas DataFrames
train_df = dataset["train"].to_pandas()
test_df = dataset["test"].to_pandas()

print(f"Training samples: {len(train_df)}")
print(f"Testing samples: {len(test_df)}")
```

---

## 2. Configure & Train Baseline Models

### Scenario 1: Train the Ultra-Lightweight Char (3–5 gram) SVM (Recommended for SMS Gateways)

```python
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.metrics import classification_report, f1_score

# 1. Load the training and testing datasets
train_df = pd.read_csv("./vietnamese_sms_dataset/train.csv")
test_df = pd.read_csv("./vietnamese_sms_dataset/test.csv")

# 2. Initialize a character-level TF-IDF vectorizer (3–5 grams)
vectorizer = TfidfVectorizer(
    analyzer="char",
    ngram_range=(3, 5),
    max_features=10000
)

X_train = vectorizer.fit_transform(train_df["message"].astype(str).str.lower())
X_test = vectorizer.transform(test_df["message"].astype(str).str.lower())

y_train = train_df["label"]
y_test = test_df["label"]

# 3. Train a Linear SVM using the default configuration (C=1.0)
clf = SVC(kernel="linear", C=1.0, random_state=42)
clf.fit(X_train, y_train)

# 4. Evaluate the trained model
y_pred = clf.predict(X_test)

print(classification_report(y_test, y_pred, target_names=["HAM", "SPAM"]))
print(f"Spam F1-Score: {f1_score(y_test, y_pred):.4f}")
```

---

### Scenario 2: Fine-Tune the PhoBERT-base Transformer

```python
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    Trainer,
    TrainingArguments,
)
from datasets import Dataset

# 1. Load the PhoBERT tokenizer and pre-trained model
model_name = "vinai/phobert-base"

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(
    model_name,
    num_labels=2
)

# 2. Define the tokenization function
def tokenize_function(examples):
    return tokenizer(
        examples["message"],
        padding="max_length",
        truncation=True,
        max_length=128,
    )

# 3. Convert DataFrames into Hugging Face Datasets
train_ds = Dataset.from_pandas(train_df).map(tokenize_function, batched=True)
test_ds = Dataset.from_pandas(test_df).map(tokenize_function, batched=True)

# 4. Configure training hyperparameters
training_args = TrainingArguments(
    output_dir="./phobert_sms_output",
    learning_rate=2e-5,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    num_train_epochs=4,
    weight_decay=0.01,
    evaluation_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="f1",
)

# 5. Initialize the Trainer and start fine-tuning
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=test_ds,
    tokenizer=tokenizer,
)

trainer.train()
```