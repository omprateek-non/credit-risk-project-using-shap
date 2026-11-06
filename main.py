
from contextlib import asynccontextmanager
from pathlib import Path
import logging
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, ConfigDict

from portable_model import CreditRiskModel

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "credit_risk_portable"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LoanApplication(BaseModel):

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid"
    )

    person_age: int = Field(ge=18, le=99)
    person_income: float = Field(gt=0)
    person_home_ownership: str = Field(min_length=1)
    person_emp_length: float = Field(ge=0)
    loan_intent: str = Field(min_length=1)
    loan_grade: str = Field(min_length=1)
    loan_amnt: float = Field(gt=0)
    loan_int_rate: float = Field(gt=0, le=100)
    loan_percent_income: float = Field(gt=0, le=1)
    cb_person_default_on_file: str = Field(min_length=1)
    cb_person_cred_hist_length: float = Field(ge=0)


@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("Loading credit risk model...")

    try:
        if not MODEL_DIR.is_dir():
            raise FileNotFoundError(
                f"Model directory not found: {MODEL_DIR}"
            )

        model = CreditRiskModel(model_dir=MODEL_DIR)

        app.state.model = model
        app.state.threshold = float(model.threshold)

        logger.info("Model loaded successfully.")
        logger.info("Threshold: %.6f", model.threshold)

    except Exception:
        logger.exception("Model loading failed.")
        raise

    yield

    logger.info("API shutting down.")


app = FastAPI(
    title="Credit Risk Assessment API",
    description="Loan default prediction using a calibrated XGBoost ensemble.",
    version="1.0.0",
    lifespan=lifespan
)

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static"
)


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/health")
def health_check(request: Request):

    loaded = hasattr(request.app.state, "model")

    return {
        "status": "healthy" if loaded else "unavailable",
        "model_loaded": loaded,
        "threshold": (
            request.app.state.threshold if loaded else None
        )
    }

@app.post("/predict")
def predict_loan(
    application: LoanApplication,
    request: Request
):

    try:
        input_data = pd.DataFrame(
            [application.model_dump()]
        )

        model = request.app.state.model
        threshold = request.app.state.threshold

        probabilities = model.predict_proba(input_data)

        no_default_probability = float(probabilities[0][0])
        default_probability = float(probabilities[0][1])

        prediction = int(default_probability >= threshold)

        return {
            "prediction": prediction,
            "risk_status": (
                "High Risk" if prediction == 1 else "Low Risk"
            ),
            "default_probability": round(default_probability, 6),
            "default_probability_percentage": round(
                default_probability * 100, 2
            ),
            "no_default_probability": round(
                no_default_probability, 6
            ),
            "no_default_probability_percentage": round(
                no_default_probability * 100, 2
            ),
            "threshold": round(threshold, 6),
            "threshold_percentage": round(threshold * 100, 2),
            "model": "Sigmoid Calibrated XGBoost Ensemble"
        }

    except Exception:
        logger.exception("Prediction failed.")
        raise HTTPException(
            status_code=500,
            detail="Prediction failed. Check server logs."
        )
