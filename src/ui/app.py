"""
LastMile+ - Simple Streamlit UI
A lightweight browser interface for forecasting and stockout risk review.
"""

from pathlib import Path
import sys

import pandas as pd
import streamlit as st

# Make project root importable on Streamlit Cloud
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from src.core.forecasting import DemandForecaster
from src.core.risk_scoring import StockoutRiskScorer

st.set_page_config(page_title="LastMile+", layout="wide")

st.title("LastMile+ | AI-Powered Distribution Planning")
st.write(
    "Decision-support tool for forecasting demand, identifying stockout risk, "
    "and reviewing Months of Stock (MOS) for health commodities."
)

# -----------------------------
# Upload LMIS data
# -----------------------------
st.subheader("Upload LMIS data")

uploaded_file = st.file_uploader(
    "Upload LMIS file (CSV or Excel)",
    type=["csv", "xlsx"]
)

if uploaded_file is None:
    st.info("Please upload an LMIS file to continue.")
    st.stop()

# Read file
if uploaded_file.name.endswith(".csv"):
    raw_df = pd.read_csv(uploaded_file)
else:
    raw_df = pd.read_excel(uploaded_file)

# Select only trusted columns
required_columns = {
    "District": "district",
    "Facility Code": "facility_id",
    "Facility Name": "facility_name",
    "Product Code": "commodity_id",
    "Product": "commodity_name",
    "Unit of Issue": "unit",
    "Quantity Issued": "consumption",
    "Closing balance (SOH)": "stock_on_hand"
}

missing_columns = [col for col in required_columns if col not in raw_df.columns]
if missing_columns:
    st.error(
        "The uploaded file is missing these required columns: "
        + ", ".join(missing_columns)
    )
    st.stop()

# Keep only relevant columns
df = raw_df[list(required_columns.keys())].copy()

# Rename columns to app format
df.rename(columns=required_columns, inplace=True)

# Add dummy period for now
reporting_month = st.text_input(
    "Enter reporting month (YYYY-MM)",
    value="2026-02"
)

df["period"] = reporting_month

# Clean numeric fields
df["consumption"] = pd.to_numeric(df["consumption"], errors="coerce").fillna(0)
df["stock_on_hand"] = pd.to_numeric(df["stock_on_hand"], errors="coerce").fillna(0)

st.success("LMIS data loaded successfully")

# -----------------------------
# Helper functions
# -----------------------------
def calculate_amc(history_df: pd.DataFrame) -> float:
    """Average monthly consumption using available historical records."""
    if history_df.empty:
        return 0.0
    return float(history_df["consumption"].fillna(0).mean())

def calculate_mos(stock_on_hand: float, amc: float) -> float:
    """Months of stock."""
    if amc <= 0:
        return 0.0
    return float(stock_on_hand) / float(amc)

def classify_mos(mos: float) -> str:
    """MOS category using facility-level target bands."""
    if mos < 1:
        return "Stockout risk"
    elif mos < 2:
        return "Understock"
    elif mos <= 3:
        return "Optimal"
    else:
        return "Overstock"

# -----------------------------
# Data preview
# -----------------------------
st.subheader("LMIS data preview")
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

filtered = filtered.sort_values("period").reset_index(drop=True)

st.subheader("Historical records")
st.dataframe(filtered, use_container_width=True)

facility_id = filtered["facility_id"].iloc[0] if not filtered.empty else None
commodity_id = filtered["commodity_id"].iloc[0] if not filtered.empty else None

# Default values used later in tabs
amc = 0.0
mos = 0.0
mos_status = "N/A"

# -----------------------------
# Distribution Planning (Delayed LMIS logic)
# -----------------------------
st.subheader("Distribution Planning (Delayed LMIS)")

if filtered.empty:
    st.warning("No matching records found.")
else:
    filtered_sorted = filtered.sort_values("period").copy()

    amc_window = st.selectbox(
        "AMC calculation period",
        options=[3, 6, 12],
        index=0
    )

    recent_data = filtered_sorted.tail(amc_window).copy()
    months_used = len(recent_data)

    amc = float(recent_data["consumption"].mean()) if not recent_data.empty else 0.0
    st.caption(f"AMC calculated using the most recent {months_used} month(s) available.")

    latest_row = filtered_sorted.iloc[-1]
    latest_soh = float(latest_row["stock_on_hand"])

    # Temporary proxy: using Quantity Issued as last distribution
    last_distribution = float(latest_row["consumption"])

    projected_consumption = amc

    projected_end_month_soh = max(
        latest_soh + last_distribution - projected_consumption,
        0
    )

    target_mos = st.number_input(
        "Target MOS",
        min_value=1.0,
        max_value=12.0,
        value=3.0
    )

    recommended_qty = max(
        (target_mos * amc) - projected_end_month_soh,
        0
    )

    mos = calculate_mos(latest_soh, amc)
    mos_status = classify_mos(mos)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Latest SOH", f"{latest_soh:,.0f}")
    c2.metric("AMC", f"{amc:,.1f}")
    c3.metric("Last Distribution", f"{last_distribution:,.0f}")
    c4.metric("Projected Consumption", f"{projected_consumption:,.1f}")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Projected End-Month SOH", f"{projected_end_month_soh:,.1f}")
    c6.metric("Target MOS", f"{target_mos:.1f}")
    c7.metric("Recommended Qty", f"{recommended_qty:,.0f}")
    c8.metric("Current MOS", f"{mos:.2f}")

    st.write(f"**MOS Status:** {mos_status}")

# -----------------------------
# Tabs
# -----------------------------
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

        if not risk_filtered.empty:
            risk_filtered = risk_filtered.sort_values("period").copy()
            risk_filtered["amc"] = amc
            risk_filtered["mos"] = risk_filtered.apply(
                lambda row: calculate_mos(row["stock_on_hand"], amc), axis=1
            )
            risk_filtered["mos_status"] = risk_filtered["mos"].apply(classify_mos)
            risk_filtered["mos"] = risk_filtered["mos"].round(2)

        cols_to_show = [
            "facility_name",
            "commodity_name",
            "period",
            "consumption",
            "stock_on_hand",
            "amc",
            "mos",
            "mos_status",
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
