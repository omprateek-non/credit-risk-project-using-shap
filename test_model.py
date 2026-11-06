
from portable_model import CreditRiskModel

print("Loading credit risk model...")

model = CreditRiskModel()

sample = {
    "person_age": 25,
    "person_income": 50000,
    "person_emp_length": 3,
    "loan_amnt": 10000,
    "loan_int_rate": 12.5,
    "loan_percent_income": 0.20,
    "cb_person_cred_hist_length": 4,
    "person_home_ownership": "RENT",
    "loan_intent": "PERSONAL",
    "loan_grade": "B",
    "cb_person_default_on_file": "N",
}

probabilities = model.predict_proba(sample)
prediction = model.predict(sample)

print("\nModel output:")
print("No default probability:", probabilities[0][0])
print("Default probability:", probabilities[0][1])
print("Threshold:", model.threshold)
print("Prediction:", prediction[0])

if prediction[0] == 1:
    print("Result: Higher predicted default risk")
else:
    print("Result: Lower predicted default risk")

print("\nSUCCESS: Portable model is working.")
