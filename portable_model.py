
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.special import expit


class CreditRiskModel:

    def __init__(self, model_dir="credit_risk_portable"):
        self.model_dir = Path(model_dir)

        with open(self.model_dir / "metadata.json", "r") as f:
            self.metadata = json.load(f)

        self.threshold = self.metadata["threshold"]

        self.feature_columns = [
            "person_age",
            "person_income",
            "person_emp_length",
            "loan_amnt",
            "loan_int_rate",
            "loan_percent_income",
            "cb_person_cred_hist_length",
            "person_home_ownership",
            "loan_intent",
            "loan_grade",
            "cb_person_default_on_file",
        ]

        self.preprocessors = []
        self.boosters = []

        for i in range(self.metadata["n_models"]):
            preprocessor = joblib.load(
                self.model_dir / f"preprocessor_{i}.pkl"
            )

            booster = xgb.Booster()
            booster.load_model(
                str(self.model_dir / f"booster_{i}.json")
            )

            self.preprocessors.append(preprocessor)
            self.boosters.append(booster)

        print("Portable credit risk model loaded successfully.")

    def predict_proba(self, data):
        if isinstance(data, dict):
            data = pd.DataFrame([data])
        elif not isinstance(data, pd.DataFrame):
            data = pd.DataFrame(data)

        missing = [
            col for col in self.feature_columns
            if col not in data.columns
        ]

        if missing:
            raise ValueError(f"Missing features: {missing}")

        data = data[self.feature_columns].copy()
        predictions = []

        for i in range(self.metadata["n_models"]):
            transformed = self.preprocessors[i].transform(data)

            raw_probability = self.boosters[i].predict(
                xgb.DMatrix(transformed)
            )

            calibration = self.metadata["calibrators"][i]

            calibrated_probability = expit(
                -(calibration["a"] * raw_probability
                  + calibration["b"])
            )

            predictions.append(calibrated_probability)

        positive_probability = np.mean(predictions, axis=0)

        return np.column_stack([
            1 - positive_probability,
            positive_probability
        ])

    def predict(self, data):
        probabilities = self.predict_proba(data)[:, 1]

        return (probabilities >= self.threshold).astype(int)
