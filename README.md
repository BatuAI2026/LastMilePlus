# LastMile+ | AI-Powered Distribution Planning

**Objective**: Support Ministries of Health, NGOs, and implementing partners in making better-informed last-mile distribution decisions for health commodities (medicines, vaccines, diagnostics, and supplies).

**Core Focus**: Planning support only — demand forecasting, stockout risk identification, allocation recommendations, and scenario simulation. The system assists human planners and never makes autonomous decisions.

## Features (MVP)
- Facility-level demand forecasting with uncertainty intervals
- Stockout risk scoring with clear explanations
- Distribution quantity recommendations respecting transport and stock constraints
- What-if scenario testing (delays, budget limits, emergencies)
- Explainable outputs using SHAP values and simple rules

## Technology Stack
- **Language**: Python 3.11+
- **UI**: Streamlit (lightweight, works in low-bandwidth settings)
- **Data**: pandas, Polars
- **Forecasting**: Prophet, statsmodels, LightGBM with SHAP
- **Optimization**: PuLP

## Quick Start (for technical users)
```bash
pip install -e .
streamlit run src/ui/app.py

