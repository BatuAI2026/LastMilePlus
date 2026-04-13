"""
LastMile+ - Simple Streamlit UI
A lightweight browser interface for forecasting and stockout risk review.
"""

from pathlib import Path
import pandas as pd
import streamlit as st

from src.core.forecasting import DemandForecaster
from src.core.risk_scoring import StockoutRiskScorer

st.set_page_config(page_title="LastMile+", layout="wide")

st.title("LastMile+ | AI-Powered Distribution Planning")
st.write(
    "Decision-support tool for forecasting demand and identifying stockout risk "
    "for health commodities."
)

sample_path = Path("data/sample/sample_consumption.csv")

if not sample_path.exists():
    st.error("Sample data file not found at data/sample/sample_consumption.csv")
    st.stop()

df = pd.read_csv(sample_path)

st.subheader("Sample data preview")
st.dataframe(df.head(20), use_container_width=True)

facility_options = sorted(df["facility_name"].dropna().unique().tolist())
commodity_options = sorted(df["commodity_name"].dropna().unique().tolist())

col1, col2 = st.columns(2)

with col1:
    selected_facility = st.selectbox("Select facility", facility_options)

with col2:
    selected_commodity = st.selectbox("Select commodity", commodity_options)

filtered = df[
    (df["facility_name"] == selected_facility) &
    (df["commodity_name"] == selected_commodity)
].copy()

st.subheader("Historical records")
st.dataframe(filtered, use_container_width=True)

facility_id = filtered["facility_id"].iloc[0] if not filtered.empty else None
commodity_id = filtered["commodity_id"].iloc[0] if not filtered.empty else None

tab1, tab2 = st.tabs(["Forecast", "Risk scoring"])

with tab1:
    st.subheader("Demand forecast")
    if filtered.empty:
        st.warning("No matching records found.")
    else:
        forecaster = DemandForecaster()
        forecast_df, method = forecaster.fit_and_forecast(
            df=df,
            facility_id=facility_id,
            commodity_id=commodity_id,
            periods=3
        )

        st.write(f"**Forecast method:** {method}")
        display_df = forecast_df.copy()
        display_df["ds"] = display_df["ds"].dt.strftime("%Y-%m")
        st.dataframe(display_df, use_container_width=True)

with tab2:
    st.subheader("Latest stockout risk")
    scorer = StockoutRiskScorer()
    risk_df = scorer.score_all(df)

    if filtered.empty:
        st.warning("No matching records found.")
    else:
        risk_filtered = risk_df[
            (risk_df["facility_id"] == facility_id) &
            (risk_df["commodity_id"] == commodity_id)
        ].copy()

        cols_to_show = [
            "facility_name",
            "commodity_name",
            "period",
            "consumption",
            "stock_on_hand",
            "days_stock_out",
            "days_of_stock",
            "risk_score",
            "risk_level",
            "risk_reason",
        ]
        st.dataframe(risk_filtered[cols_to_show], use_container_width=True)

st.markdown("---")
st.caption(
    "Important: This tool supports planning only. All recommendations require human review."
)
