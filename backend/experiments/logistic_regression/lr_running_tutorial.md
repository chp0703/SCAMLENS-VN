# Running Logistic Regression Experiments

Run these commands from the repository root (`SCAMLENS-VN`) in PowerShell.

## 1. Install dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

## 2. Run baseline (B4)

```powershell
.\.venv\Scripts\python.exe backend\src\ML\train_lr.py
```

## 3. Run hyperparameter tuning (B5)

```powershell
.\.venv\Scripts\python.exe backend\src\ML\tune_lr.py
```

A successful tuning run saves the best pipeline and metadata to:

- `backend/artifacts/logistic_regression/runs/<run_id>/model.joblib`
- `backend/artifacts/logistic_regression/runs/<run_id>/metadata.json`

`backend/artifacts/logistic_regression/current.json` atomically selects the complete version to use. Existing root-level artifacts are retained as legacy files and are not overwritten. Load the active version using `src.ML.artifacts.load_artifact()` from a Python session started in `backend/`.

Both baseline and tuning read `backend/src/ML/configs/lr.yaml`. Override it with `--config PATH`; override the report destination with `--report-dir PATH`. The YAML controls TF-IDF/model parameters, the tuning grid, and `evaluation.primary_metric`.

Each run writes Markdown and JSON reports under:

- `backend/experiments/logistic_regression/runs/`

## 4. Run unit tests

```powershell
.\.venv\Scripts\python.exe -m unittest backend.tests.test_ml_data_utils -v
.\.venv\Scripts\python.exe -m unittest backend.tests.test_train_lr -v
.\.venv\Scripts\python.exe -m unittest backend.tests.test_tune_lr -v
```

## Notes

- Run the scripts from the repository root using the paths above.
- Baseline and tuning use the shared `PredefinedSplit` from `cv_folds.csv`.
- The test set is not used for baseline evaluation or hyperparameter tuning. Final test evaluation is reserved for B6 after the team lead confirms the protocol.
