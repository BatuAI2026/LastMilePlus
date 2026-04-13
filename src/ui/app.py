"""
LastMile+ - Simple Streamlit UI
A lightweight browser interface for forecasting, stockout risk review,
and delayed-LMIS distribution planning.
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
    "and supporting delayed-LMIS distribution planning for health commodities."
)

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------
HISTORY_FILE = ROOT_DIR / "data" / "history" / "lmis_history.csv" 

REQUIRED_COLUMNS = {
    "District": "district",
    "Facility Code": "facility_id",
    "Facility Name": "facility_name",
    "Product Code": "commodity_id",
    "Product": "commodity_name",
    "Unit of Issue": "unit",
    "Quantity Issued": "consumption",
    "Closing balance (SOH)": "stock_on_hand",
}

# -------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------
def standardize_lmis_columns(raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    Keep only trusted LMIS columns and rename to app-standard names.
    """
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in raw_df.columns]
    if missing_columns:
        raise ValueError(
            "The uploaded file is missing these required columns: "
            + ", ".join(missing_columns)
        )

    df = raw_df[list(REQUIRED_COLUMNS.keys())].copy()
    df.rename(columns=REQUIRED_COLUMNS, inplace=True)

    df["consumption"] = pd.to_numeric(df["consumption"], errors="coerce").fillna(0)
    df["stock_on_hand"] = pd.to_numeric(df["stock_on_hand"], errors="coerce").fillna(0)

    # Keep text columns clean
    text_cols = ["district", "facility_id", "facility_name", "commodity_id", "commodity_name", "unit"]
    for col in text_cols:
        df[col] = df[col].astype(str).str.strip()

    return df


def load_history_file(history_file: Path) -> pd.DataFrame:
    """
    Load repository historical file if available.
    Expected format:
    period,district,facility_id,facility_name,commodity_id,commodity_name,unit,consumption,stock_on_hand
    """
    if not history_file.exists():
        return pd.DataFrame()

    history_df = pd.read_csv(history_file)

    required_history_cols = [
        "period",
        "district",
        "facility_id",
        "facility_name",
        "commodity_id",
        "commodity_name",
        "unit",
        "consumption",
        "stock_on_hand",
    ]

    missing = [col for col in required_history_cols if col not in history_df.columns]
    if missing:
        raise ValueError(
            "History file exists but is missing required columns: "
            + ", ".join(missing)
        )

    history_df["consumption"] = pd.to_numeric(history_df["consumption"], errors="coerce").fillna(0)
    history_df["stock_on_hand"] = pd.to_numeric(history_df["stock_on_hand"], errors="coerce").fillna(0)

    for col in ["district", "facility_id", "facility_name", "commodity_id", "commodity_name", "unit", "period"]:
        history_df[col] = history_df[col].astype(str).str.strip()

    return history_df


def calculate_amc(history_df: pd.DataFrame) -> float:
    if history_df.empty:
        return 0.0
    return float(history_df["consumption"].fillna(0).mean())


def calculate_mos(stock_on_hand: float, amc: float) -> float:
    if amc <= 0:
        return 0.0
    return float(stock_on_hand) / float(amc)


def classify_mos(mos: float) -> str:
    if mos < 1:
        return "Stockout risk"
    elif mos < 2:
        return "Understock"
    elif mos <= 3:
        return "Optimal"
    else:
        return "Overstock"


def prepare_combined_dataset(history_df: pd.DataFrame, latest_df: pd.DataFrame) -> pd.DataFrame:
    """
    Combine repository history + latest uploaded month.
    Deduplicate by period + facility + product.
    Latest uploaded rows take precedence over history if duplicates exist.
    """
    if history_df.empty:
        combined = latest_df.copy()
    else:
        combined = pd.concat([history_df, latest_df], ignore_index=True)

    combined["period"] = combined["period"].astype(str).str.strip()
    combined["period_date"] = pd.to_datetime(combined["period"], format="%Y-%m", errors="coerce")

    # Keep latest occurrence for duplicate period/facility/product combinations
    combined = combined.drop_duplicates(
        subset=["period", "facility_id", "commodity_id"],
        keep="last"
    ).copy()

    combined = combined.sort_values(
        ["facility_name", "commodity_name", "period_date"],
        na_position="last"
    ).reset_index(drop=True)

    return combined


# -------------------------------------------------------------------
# Load repository history
# -------------------------------------------------------------------
st.subheader("Repository history")

try:
    history_df = load_history_file(HISTORY_FILE)
    if history_df.empty:
        st.info(
            "No repository history file found yet. "
            "The app can still work with the latest uploaded month only."
        )
    else:
        st.success(
            f"Loaded repository history: {len(history_df):,} rows from "
            f"`data/history/lmis_history.csv`"
        )
except Exception as e:
    st.error(f"Could not load repository history file: {e}")
    st.stop()

# -------------------------------------------------------------------
# Upload latest month
# -------------------------------------------------------------------
st.subheader("Upload latest LMIS month")

latest_period = st.text_input(
    "Enter reporting month for the uploaded file (YYYY-MM)",
    value="2026-03"
)

uploaded_file = st.file_uploader(
    "Upload the latest LMIS file (CSV or Excel)",
    type=["csv", "xlsx"]
)

if uploaded_file is None:
    st.info("Please upload the latest LMIS file to continue.")
    st.stop()

try:
    if uploaded_file.name.endswith(".csv"):
        raw_latest_df = pd.read_csv(uploaded_file)
    else:
        raw_latest_df = pd.read_excel(uploaded_file)

    latest_df = standardize_lmis_columns(raw_latest_df)
    latest_df["period"] = latest_period.strip()

    if pd.to_datetime(latest_period, format="%Y-%m", errors="coerce") is pd.NaT:
        st.error("Reporting month must be in YYYY-MM format, for example 2026-03.")
        st.stop()

    st.success("Latest LMIS file loaded successfully.")
except Exception as e:
    st.error(f"Could not process uploaded LMIS file: {e}")
    st.stop()

# -------------------------------------------------------------------
# Combine repo history + latest upload
# -------------------------------------------------------------------
try:
    df = prepare_combined_dataset(history_df, latest_df)
except Exception as e:
    st.error(f"Could not combine historical data with latest upload: {e}")
    st.stop()

st.subheader("Combined dataset preview")
st.dataframe(df.head(20), use_container_width=True)

# -------------------------------------------------------------------
# Filters
# -------------------------------------------------------------------
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

filtered = filtered.sort_values("period_date").reset_index(drop=True)

st.subheader("Historical records")
st.dataframe(
    filtered[
        [
            "period",
            "district",
            "facility_id",
            "facility_name",
            "commodity_id",
            "commodity_name",
            "unit",
            "consumption",
            "stock_on_hand",
        ]
    ],
    use_container_width=True
)

facility_id = filtered["facility_id"].iloc[0] if not filtered.empty else None
commodity_id = filtered["commodity_id"].iloc[0] if not filtered.empty else None

# Default values used later in tabs
amc = 0.0
mos = 0.0
mos_status = "N/A"

# -------------------------------------------------------------------
# Distribution Planning (Delayed LMIS logic)
# -------------------------------------------------------------------
st.subheader("Distribution Planning (Delayed LMIS)")

if filtered.empty:
    st.warning("No matching records found.")
else:
    filtered_sorted = filtered.sort_values("period_date").copy()

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
    latest_reported_period = latest_row["period"]
    latest_soh = float(latest_row["stock_on_hand"])

    # Temporary proxy:
    # using latest month's Quantity Issued as the previous distribution proxy.
    # Later this should be replaced with actual distribution data if available.
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

    st.write(f"**Latest reported month:** {latest_reported_period}")

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
    st.caption(
        "Planning note: repository history is used as baseline, and the uploaded latest month "
        "is appended in-memory for current analysis."
    )

# -------------------------------------------------------------------
# Tabs
# -------------------------------------------------------------------
tab1, tab2 = st.tabs(["Forecast", "Risk scoring"])

with tab1:
    st.subheader("Demand forecast")
    if filtered.empty:
        st.warning("No matching records found.")
    else:
        forecaster = DemandForecaster()

        forecast_input = filtered_sorted.copy()
        forecast_input["period"] = forecast_input["period"].astype(str)

        forecast_df, method = forecaster.fit_and_forecast(
            df=forecast_input,
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

    # Build a simplified risk input from current combined data
    risk_input = filtered_sorted.copy()
    risk_input["days_stock_out"] = 0  # placeholder until reliable field is added

    scorer = StockoutRiskScorer()
    risk_df = scorer.score_all(risk_input)

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
