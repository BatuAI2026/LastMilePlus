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

    text_cols = ["district", "facility_id", "facility_name", "commodity_id", "commodity_name", "unit"]
    for col in text_cols:
        df[col] = df[col].astype(str).str.strip()

    return df


def load_history_file(history_file: Path) -> pd.DataFrame:
    if not history_file.exists():
        return pd.DataFrame()

    history_df = pd.read_csv(history_file)

    required_history_cols = [
        "period", "district", "facility_id", "facility_name",
        "commodity_id", "commodity_name", "unit",
        "consumption", "stock_on_hand",
    ]

    missing = [col for col in required_history_cols if col not in history_df.columns]
    if missing:
        raise ValueError(
            "History file exists but is missing required columns: "
            + ", ".join(missing)
        )

    history_df["consumption"] = pd.to_numeric(history_df["consumption"], errors="coerce").fillna(0)
    history_df["stock_on_hand"] = pd.to_numeric(history_df["stock_on_hand"], errors="coerce").fillna(0)

    for col in required_history_cols:
        history_df[col] = history_df[col].astype(str).str.strip()

    return history_df


def calculate_mos(stock_on_hand: float, amc: float) -> float:
    return 0 if amc <= 0 else stock_on_hand / amc


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
    combined = pd.concat([history_df, latest_df], ignore_index=True) if not history_df.empty else latest_df.copy()

    combined["period"] = combined["period"].astype(str).str.strip()
    combined["period_date"] = pd.to_datetime(combined["period"], format="%Y-%m", errors="coerce")

    combined = combined.drop_duplicates(
        subset=["period", "facility_id", "commodity_id"],
        keep="last"
    )

    return combined.sort_values("period_date").reset_index(drop=True)

# -------------------------------------------------------------------
# Load repository history (DEBUG VERSION)
# -------------------------------------------------------------------
st.subheader("Repository history")

st.write(f"ROOT_DIR resolved to: {ROOT_DIR}")
st.write(f"Looking for history file at: {HISTORY_FILE}")
st.write(f"History file exists: {HISTORY_FILE.exists()}")

# 🔍 DEBUG
history_dir = ROOT_DIR / "data" / "history"
st.write(f"History directory path: {history_dir}")
st.write(f"History directory exists: {history_dir.exists()}")

if history_dir.exists():
    try:
        st.write(f"Files in history directory: {[p.name for p in history_dir.iterdir()]}")
    except Exception as e:
        st.write(f"Error reading directory: {e}")

try:
    history_df = load_history_file(HISTORY_FILE)
    if history_df.empty:
        st.info("No repository history file found yet.")
    else:
        st.success(f"Loaded history: {len(history_df)} rows")
except Exception as e:
    st.error(f"Error loading history: {e}")
    st.stop()

# -------------------------------------------------------------------
# Upload latest month
# -------------------------------------------------------------------
st.subheader("Upload latest LMIS month")

latest_period = st.text_input("Reporting month (YYYY-MM)", "2026-03")

uploaded_file = st.file_uploader("Upload LMIS file", type=["csv", "xlsx"])

if uploaded_file is None:
    st.stop()

raw_latest_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)

latest_df = standardize_lmis_columns(raw_latest_df)
latest_df["period"] = latest_period

df = prepare_combined_dataset(history_df, latest_df)

st.subheader("Combined dataset preview")
st.dataframe(df.head(20))

# -------------------------------------------------------------------
# Filters
# -------------------------------------------------------------------
facility = st.selectbox("Facility", sorted(df["facility_name"].unique()))
commodity = st.selectbox("Commodity", sorted(df["commodity_name"].unique()))

filtered = df[
    (df["facility_name"] == facility) &
    (df["commodity_name"] == commodity)
].copy()

filtered = filtered.sort_values("period_date")

st.subheader("Historical records")
st.dataframe(filtered)

# -------------------------------------------------------------------
# Planning
# -------------------------------------------------------------------
if not filtered.empty:
    amc_window = st.selectbox("AMC window", [3, 6, 12])
    recent = filtered.tail(amc_window)
    amc = recent["consumption"].mean()

    latest = filtered.iloc[-1]
    soh = float(latest["stock_on_hand"])
    
    # Check this line below specifically - make sure it aligns with 'soh' above
    last_dist = float(latest["consumption"]) 
    
    projected_soh = max(soh + last_dist - amc, 0)
    target_mos = st.number_input("Target MOS", 1.0, 12.0, 3.0)

    recommended = max((target_mos * amc) - projected_soh, 0)

    mos = calculate_mos(soh, amc)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("SOH", round(soh))
    col2.metric("AMC", round(amc, 1))
    col3.metric("Projected SOH", round(projected_soh))
    col4.metric("Recommended Qty", round(recommended))

    st.write(f"MOS: {round(mos,2)} → {classify_mos(mos)}")

st.caption("Planning support tool only.")
