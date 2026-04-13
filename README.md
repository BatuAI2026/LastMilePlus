# LastMile+ | AI-Powered Distribution Planning

**Objective:** Support Ministries of Health, NGOs, and implementing partners in making better-informed last-mile distribution decisions for health commodities.

**Core Focus:** Planning support only — forecasting, stockout risk identification, and scenario-based planning. The system supports human decision-making and does not automate execution.

## Key Features

- Facility-level demand forecasting
- Stockout risk scoring
- Planning support for distribution decisions
- Scenario testing under uncertainty
- Explainable outputs

## Repository Structure
LastMilePlus/
├── README.md
├── requirements.txt
├── .gitignore
├── docs/
│ ├── project-charter.md
│ └── data-model.md
├── data/
│ └── sample/
│ └── sample_consumption.csv
└── src/
├── core/
│ ├── forecasting.py
│ └── risk_scoring.py
└── ui/
└── app.py

## Technology Stack

- Python
- Streamlit
- pandas, numpy

## Run the App

## Constraints

- No autonomous decisions
- Human validation required
- Designed for low-resource environments

## Status

MVP prototype with:
- Forecasting module
- Risk scoring module
- Sample dataset
- Basic UI

## Disclaimer

This is a decision-support tool only.
