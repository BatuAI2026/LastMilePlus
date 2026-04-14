"""
LastMile+ - Simple Streamlit UI
A lightweight browser interface for forecasting, stockout risk review,
delayed-LMIS distribution planning, priority-based allocation,
and FEFO warehouse collection guidance with batch traceability.
"""

from pathlib import Path
import sys
from io import BytesIO

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
    "supporting delayed-LMIS distribution planning, constrained allocation, "
    "and FEFO warehouse collection guidance."
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

MOS_SCENARIOS = {
    "Target MOS (3.0)": 3.0,
    "2.5 MOS": 2.5,
    "2.0 MOS": 2.0,
    "1.5 MOS": 1.5,
    "1.0 MOS": 1.0,
}

LMIS_PRODUCT_MAP = {
    "BB006000": "Artesunate injection 60mg/ml,1ML",
    "TBA4": "Artesunate injection 120mg/ml,PFR",
    "GF0561": "Artesunate 50mg+Amodiaquine 135mg 3 Tablets/blister",
    "GF0562": "Artesunate 100mg+Amodiaquine 270mg 3 Tablets/blister",
    "GF5637": "Dihydroartemisinin 20mg/Piperaquine160mg(DP)",
    "GF0563": "Artesunate 100mg+Amodiaquine 270mg 6 Tablets/blister",
    "PMI0004": "Long Lasting Insecticidal Net(LLIN)",
    "GF5639": "Dihydroartemisinin 60mg/Piperaquine 480mg(DP)",
    "GF5640": "Dihydroartemisinin 80mg/Piperaquine 640mg(DP)",
    "DN002900": "Malaria Rapid Diagnostic Test (MRDT) Kits",
    "AA058200": "Sulphadoxine 500mg / pyrimethamine 25mg (SP), tablets",
    "AA039600": "Lumefantrine 120mg/Artemether 20mg,6x1",
    "GF5638": "Dihydroartemisinin 40mg/Piperaquine 320mg (DP)",
    "AA039900": "Lumefantrine 120mg/Artemether 20mg, 6x2",
    "AA040200": "Lumefantrine 120mg/Artemether 20mg,  6x3",
    "AA040500": "Lumefantrine 120mg/Artemether 20mg, 6x4",
}

# -------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------
def standardize_product_fields(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "commodity_id" in df.columns:
        df["commodity_id"] = df["commodity_id"].astype(str).str.strip()
        df["standard_product_name"] = df["commodity_id"].map(LMIS_PRODUCT_MAP)
        df["standard_product_name"] = df["standard_product_name"].fillna(df["commodity_name"])
    return df


def standardize_warehouse_product_fields(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "product_code" in df.columns:
        df["product_code"] = df["product_code"].astype(str).str.strip()
        df["standard_product_name"] = df["product_code"].map(LMIS_PRODUCT_MAP)
        df["standard_product_name"] = df["standard_product_name"].fillna(df["product_name"])
    else:
        df["standard_product_name"] = df["product_name"]
    return df


def create_excel_workbook(
    planning_df: pd.DataFrame,
    constrained_df: pd.DataFrame,
    district_summary: pd.DataFrame,
    fefo_df: pd.DataFrame
) -> bytes:
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        if not planning_df.empty:
            planning_df.to_excel(writer, sheet_name="Planning_Table", index=False)

        if not constrained_df.empty:
            constrained_df.to_excel(writer, sheet_name="Constrained_Allocation", index=False)

        if not district_summary.empty:
            district_summary.to_excel(writer, sheet_name="District_Summary", index=False)

        if not fefo_df.empty:
            fefo_df.to_excel(writer, sheet_name="FEFO_Guidance", index=False)

    output.seek(0)
    return output.getvalue()


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

    text_cols = [
        "district",
        "facility_id",
        "facility_name",
        "commodity_id",
        "commodity_name",
        "unit",
    ]
    for col in text_cols:
        df[col] = df[col].astype(str).str.strip()

    df = standardize_product_fields(df)
    return df


def load_history_file(history_file: Path) -> pd.DataFrame:
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

    history_df["consumption"] = pd.to_numeric(
        history_df["consumption"], errors="coerce"
    ).fillna(0)
    history_df["stock_on_hand"] = pd.to_numeric(
        history_df["stock_on_hand"], errors="coerce"
    ).fillna(0)

    for col in [
        "district",
        "facility_id",
        "facility_name",
        "commodity_id",
        "commodity_name",
        "unit",
        "period",
    ]:
        history_df[col] = history_df[col].astype(str).str.strip()

    history_df = standardize_product_fields(history_df)
    return history_df


def clean_warehouse_data(raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    Expected cleaned warehouse columns:
    Required:
      - product_name
      - expiry_date
      - available_qty
    Optional:
      - warehouse_name
      - batch_no
      - product_code
    """
    df = raw_df.copy()
    df.columns = [str(col).strip().lower() for col in df.columns]

    required = ["product_name", "expiry_date", "available_qty"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(
            "Warehouse file is missing required columns: " + ", ".join(missing)
        )

    if "warehouse_name" not in df.columns:
        df["warehouse_name"] = "Unknown Warehouse"

    if "batch_no" not in df.columns:
        df["batch_no"] = "N/A"

    if "product_code" not in df.columns:
        df["product_code"] = ""

    df["product_name"] = df["product_name"].astype(str).str.strip()
    df["warehouse_name"] = df["warehouse_name"].astype(str).str.strip()
    df["batch_no"] = df["batch_no"].astype(str).str.strip()
    df["product_code"] = df["product_code"].astype(str).str.strip()

    df["expiry_date"] = pd.to_datetime(df["expiry_date"], errors="coerce")
    df["available_qty"] = pd.to_numeric(df["available_qty"], errors="coerce").fillna(0)

    df = df[df["expiry_date"].notna()].copy()
    df = df[df["available_qty"] > 0].copy()

    df = standardize_warehouse_product_fields(df)
    df = df.sort_values(["expiry_date", "warehouse_name", "batch_no"]).reset_index(drop=True)
    return df


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
    if history_df.empty:
        combined = latest_df.copy()
    else:
        combined = pd.concat([history_df, latest_df], ignore_index=True)

    combined["period"] = combined["period"].astype(str).str.strip()
    combined["period_date"] = pd.to_datetime(
        combined["period"], format="%Y-%m", errors="coerce"
    )

    combined = combined.drop_duplicates(
        subset=["period", "facility_id", "commodity_id"],
        keep="last"
    ).copy()

    combined = combined.sort_values(
        ["facility_name", "commodity_name", "period_date"],
        na_position="last"
    ).reset_index(drop=True)

    return combined


def build_planning_table(
    df_product: pd.DataFrame,
    amc_window: int,
    last_distribution_qty: float,
    target_mos: float,
) -> pd.DataFrame:
    planning_rows = []

    grouped = df_product.groupby(
        [
            "district",
            "facility_id",
            "facility_name",
            "commodity_id",
            "commodity_name",
            "unit",
            "standard_product_name",
        ],
        dropna=False
    )

    for keys, group in grouped:
        (
            district,
            facility_id,
            facility_name,
            commodity_id,
            commodity_name,
            unit,
            standard_product_name,
        ) = keys

        group = group.sort_values("period_date").copy()
        recent_data = group.tail(amc_window).copy()
        months_used = len(recent_data)

        amc = float(recent_data["consumption"].mean()) if not recent_data.empty else 0.0

        latest_row = group.iloc[-1]
        latest_period = latest_row["period"]
        latest_soh = float(latest_row["stock_on_hand"])

        projected_consumption = amc
        projected_end_month_soh = max(
            latest_soh + last_distribution_qty - projected_consumption,
            0
        )

        recommended_qty = max(
            (target_mos * amc) - projected_end_month_soh,
            0
        )

        current_mos = calculate_mos(latest_soh, amc)
        mos_status = classify_mos(current_mos)
        projected_mos = calculate_mos(projected_end_month_soh, amc)

        planning_rows.append(
            {
                "district": district,
                "facility_id": facility_id,
                "facility_name": facility_name,
                "commodity_id": commodity_id,
                "commodity_name": commodity_name,
                "standard_product_name": standard_product_name,
                "unit": unit,
                "latest_period": latest_period,
                "months_used_for_amc": months_used,
                "amc": round(amc, 2),
                "latest_soh": round(latest_soh, 2),
                "last_distribution_qty": round(last_distribution_qty, 2),
                "projected_consumption": round(projected_consumption, 2),
                "projected_end_month_soh": round(projected_end_month_soh, 2),
                "projected_mos": round(projected_mos, 2),
                "target_mos": round(target_mos, 2),
                "current_mos": round(current_mos, 2),
                "mos_status": mos_status,
                "recommended_qty": round(recommended_qty, 2),
            }
        )

    planning_df = pd.DataFrame(planning_rows)

    if not planning_df.empty:
        planning_df = planning_df.sort_values(
            ["district", "facility_name"]
        ).reset_index(drop=True)

    return planning_df


def assign_priority(projected_end_month_soh: float, amc: float) -> int:
    projected_mos = calculate_mos(projected_end_month_soh, amc)
    if projected_mos < 1:
        return 1
    elif projected_mos < 2:
        return 2
    elif projected_mos < 3:
        return 3
    else:
        return 4


def apply_priority_stock_constraint(planning_df: pd.DataFrame, available_stock: float) -> pd.DataFrame:
    if planning_df.empty:
        return planning_df.copy()

    constrained_df = planning_df.copy()

    constrained_df["priority"] = constrained_df.apply(
        lambda row: assign_priority(
            projected_end_month_soh=row["projected_end_month_soh"],
            amc=row["amc"]
        ),
        axis=1
    )

    constrained_df["allocated_qty"] = 0.0
    constrained_df["gap_qty"] = constrained_df["recommended_qty"]

    constrained_df = constrained_df.sort_values(
        by=["priority", "recommended_qty"],
        ascending=[True, False]
    ).reset_index(drop=True)

    remaining_stock = float(available_stock)

    for idx in constrained_df.index:
        recommended = float(constrained_df.at[idx, "recommended_qty"])

        if remaining_stock <= 0:
            allocated = 0.0
        else:
            allocated = min(recommended, remaining_stock)

        constrained_df.at[idx, "allocated_qty"] = round(allocated, 0)
        constrained_df.at[idx, "gap_qty"] = round(recommended - allocated, 2)

        remaining_stock -= allocated

    constrained_df["remaining_stock_after_allocation"] = round(max(remaining_stock, 0), 2)

    return constrained_df


def filter_matching_warehouse_stock(
    warehouse_df: pd.DataFrame,
    selected_commodity: str,
    selected_standard_name: str
) -> pd.DataFrame:
    if warehouse_df.empty:
        return warehouse_df.copy()

    stock_df = warehouse_df[
        warehouse_df["standard_product_name"].astype(str).str.strip() == str(selected_standard_name).strip()
    ].copy()

    if stock_df.empty:
        stock_df = warehouse_df[
            warehouse_df["product_name"].str.contains(selected_commodity, case=False, na=False)
        ].copy()

    stock_df = stock_df.sort_values(["expiry_date", "warehouse_name", "batch_no"]).reset_index(drop=True)
    return stock_df


def build_source_guidance(cycle_distributor: str, source_warehouse: str) -> str:
    cycle_distributor = str(cycle_distributor).strip()
    source_warehouse = str(source_warehouse).strip()

    if cycle_distributor.lower() == source_warehouse.lower():
        return f"{cycle_distributor} to distribute from own warehouse"
    return f"{cycle_distributor} to collect from {source_warehouse}"


def apply_fefo_collection_guidance(
    constrained_df: pd.DataFrame,
    warehouse_df: pd.DataFrame,
    selected_commodity: str,
    selected_standard_name: str,
    cycle_distributor: str,
) -> pd.DataFrame:
    """
    Assign allocated facility quantities to warehouse batches using FEFO.
    Returns batch-level traceability guidance.
    """
    if constrained_df.empty or warehouse_df.empty:
        return pd.DataFrame()

    stock_df = filter_matching_warehouse_stock(
        warehouse_df=warehouse_df,
        selected_commodity=selected_commodity,
        selected_standard_name=selected_standard_name,
    )

    if stock_df.empty:
        return pd.DataFrame()

    facility_df = constrained_df.copy()
    facility_df = facility_df[facility_df["allocated_qty"] > 0].copy()

    if facility_df.empty:
        return pd.DataFrame()

    facility_df = facility_df.sort_values(
        by=["priority", "allocated_qty"],
        ascending=[True, False]
    ).reset_index(drop=True)

    allocations = []
    stock_idx = 0
    remaining_batch_qty = float(stock_df.loc[stock_idx, "available_qty"])

    for _, facility_row in facility_df.iterrows():
        needed_qty = float(facility_row["allocated_qty"])

        while needed_qty > 0 and stock_idx < len(stock_df):
            batch_row = stock_df.loc[stock_idx]
            allocate_qty = min(needed_qty, remaining_batch_qty)
            source_warehouse = batch_row["warehouse_name"]

            allocations.append(
                {
                    "district": facility_row["district"],
                    "facility_id": facility_row["facility_id"],
                    "facility_name": facility_row["facility_name"],
                    "commodity_id": facility_row["commodity_id"],
                    "commodity_name": facility_row["commodity_name"],
                    "standard_product_name": facility_row["standard_product_name"],
                    "allocated_qty_to_facility": round(float(facility_row["allocated_qty"]), 2),
                    "priority": int(facility_row["priority"]),
                    "cycle_distributor": cycle_distributor,
                    "source_warehouse": source_warehouse,
                    "batch_no": batch_row["batch_no"],
                    "expiry_date": batch_row["expiry_date"].strftime("%Y-%m-%d"),
                    "batch_allocated_qty": round(float(allocate_qty), 2),
                    "collection_note": f"To be collected from {source_warehouse}",
                    "source_guidance": build_source_guidance(cycle_distributor, source_warehouse),
                }
            )

            needed_qty -= allocate_qty
            remaining_batch_qty -= allocate_qty

            if remaining_batch_qty <= 0:
                stock_idx += 1
                if stock_idx < len(stock_df):
                    remaining_batch_qty = float(stock_df.loc[stock_idx, "available_qty"])

    return pd.DataFrame(allocations)


# -------------------------------------------------------------------
# Load repository history
# -------------------------------------------------------------------
st.subheader("Repository history")

try:
    history_df = load_history_file(HISTORY_FILE)
    if history_df.empty:
        st.info(
            "No repository history file found yet. The app can still work with the latest uploaded month only."
        )
    else:
        st.success(f"Loaded history: {len(history_df):,} rows")
except Exception as e:
    st.error(f"Could not load repository history file: {e}")
    st.stop()

# -------------------------------------------------------------------
# Upload latest LMIS month
# -------------------------------------------------------------------
st.subheader("Upload latest LMIS month")

latest_period = st.text_input(
    "Reporting month (YYYY-MM)",
    value="2026-03"
)

uploaded_file = st.file_uploader(
    "Upload LMIS file",
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

    if pd.isna(pd.to_datetime(latest_period, format="%Y-%m", errors="coerce")):
        st.error("Reporting month must be in YYYY-MM format, for example 2026-03.")
        st.stop()

    st.success("Latest LMIS file loaded successfully.")
except Exception as e:
    st.error(f"Could not process uploaded LMIS file: {e}")
    st.stop()

# -------------------------------------------------------------------
# Upload warehouse stock for FEFO guidance
# -------------------------------------------------------------------
st.subheader("Upload warehouse stock (FEFO)")

warehouse_file = st.file_uploader(
    "Upload cleaned warehouse stock file",
    type=["csv", "xlsx"],
    key="warehouse_upload"
)

warehouse_df = pd.DataFrame()

if warehouse_file is not None:
    try:
        if warehouse_file.name.endswith(".csv"):
            raw_warehouse_df = pd.read_csv(warehouse_file)
        else:
            raw_warehouse_df = pd.read_excel(warehouse_file)

        warehouse_df = clean_warehouse_data(raw_warehouse_df)
        st.success(f"Warehouse stock loaded: {len(warehouse_df):,} batch row(s)")
        st.dataframe(warehouse_df, use_container_width=True)
    except Exception as e:
        st.error(f"Could not process warehouse stock file: {e}")
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

selected_standard_name = (
    filtered["standard_product_name"].iloc[0]
    if not filtered.empty and "standard_product_name" in filtered.columns
    else selected_commodity
)

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
            "standard_product_name",
            "unit",
            "consumption",
            "stock_on_hand",
        ]
    ],
    use_container_width=True
)

facility_id = filtered["facility_id"].iloc[0] if not filtered.empty else None
commodity_id = filtered["commodity_id"].iloc[0] if not filtered.empty else None

amc = 0.0
mos = 0.0
mos_status = "N/A"
last_distribution = 0.0
target_mos = 3.0
amc_window = 3
fefo_df = pd.DataFrame()
planning_df = pd.DataFrame()
constrained_df = pd.DataFrame()
district_summary = pd.DataFrame()

# -------------------------------------------------------------------
# Distribution Planning (Single Facility)
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

    last_distribution = st.number_input(
        "Enter last distribution quantity (previous month)",
        min_value=0.0,
        value=0.0,
        help="Enter quantity distributed in the last cycle."
    )

    projected_consumption = amc
    projected_end_month_soh = max(
        latest_soh + last_distribution - projected_consumption,
        0
    )

    scenario_name = st.selectbox(
        "Allocation scenario",
        options=list(MOS_SCENARIOS.keys()),
        index=0,
        help="Select the target stock scenario used for planning."
    )
    target_mos = MOS_SCENARIOS[scenario_name]

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
    c6.metric("Scenario", scenario_name)
    c7.metric("Recommended Qty", f"{recommended_qty:,.0f}")
    c8.metric("Current MOS", f"{mos:.2f}")

    st.write(f"**MOS Status:** {mos_status}")

# -------------------------------------------------------------------
# Planning Table + Priority Allocation + FEFO Guidance
# -------------------------------------------------------------------
st.subheader("Planning Table for Selected Product")

product_df = df[df["commodity_name"] == selected_commodity].copy()

if product_df.empty:
    st.warning("No product-level records found.")
else:
    planning_df = build_planning_table(
        df_product=product_df,
        amc_window=amc_window,
        last_distribution_qty=last_distribution,
        target_mos=target_mos,
    )

    if planning_df.empty:
        st.warning("Could not generate planning table.")
    else:
        st.dataframe(planning_df, use_container_width=True)

        planning_csv = planning_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download planning table as CSV",
            data=planning_csv,
            file_name="planning_table.csv",
            mime="text/csv",
        )

        st.subheader("National Stock Constraint Allocation")

        total_recommended = float(planning_df["recommended_qty"].sum())

        available_national_stock = st.number_input(
            "Enter available national stock for this product",
            min_value=0.0,
            value=total_recommended,
            help="Available stock at national level for allocation to facilities."
        )

        constrained_df = apply_priority_stock_constraint(
            planning_df=planning_df,
            available_stock=available_national_stock,
        )

        total_allocated = float(constrained_df["allocated_qty"].sum())
        total_gap = float(constrained_df["gap_qty"].sum())
        remaining_stock = (
            float(constrained_df["remaining_stock_after_allocation"].iloc[0])
            if not constrained_df.empty
            else 0.0
        )

        n1, n2, n3, n4, n5 = st.columns(5)
        n1.metric("Total Recommended Qty", f"{total_recommended:,.0f}")
        n2.metric("Available National Stock", f"{available_national_stock:,.0f}")
        n3.metric("Total Allocated Qty", f"{total_allocated:,.0f}")
        n4.metric("Total Gap Qty", f"{total_gap:,.0f}")
        n5.metric("Unallocated Stock Balance", f"{remaining_stock:,.0f}")

        st.write("**Allocation method:** Priority-based allocation (lowest projected MOS first)")

        st.subheader("Constrained Facility Allocation Table")
        st.dataframe(constrained_df, use_container_width=True)

        constrained_csv = constrained_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download constrained allocation table as CSV",
            data=constrained_csv,
            file_name="constrained_allocation_table.csv",
            mime="text/csv",
        )

        st.subheader("District Aggregation")

        district_summary = (
            constrained_df.groupby(["district", "commodity_name"], as_index=False)
            .agg(
                facilities=("facility_id", "nunique"),
                total_latest_soh=("latest_soh", "sum"),
                total_projected_end_month_soh=("projected_end_month_soh", "sum"),
                total_recommended_qty=("recommended_qty", "sum"),
                total_allocated_qty=("allocated_qty", "sum"),
                total_gap_qty=("gap_qty", "sum"),
            )
        )

        for col in [
            "total_latest_soh",
            "total_projected_end_month_soh",
            "total_recommended_qty",
            "total_allocated_qty",
            "total_gap_qty",
        ]:
            district_summary[col] = district_summary[col].round(2)

        st.dataframe(district_summary, use_container_width=True)

        # ---------------------------------------------------------------
        # Cycle Distributor and Source-Warehouse Guidance
        # ---------------------------------------------------------------
        st.subheader("Cycle Distributor and Source Guidance")

        cycle_distributor = st.selectbox(
            "Select distributing agent for this cycle",
            options=["CML", "AGL", "Other"],
            index=0,
            help="Choose the distributing agent responsible for this cycle."
        )

        # ---------------------------------------------------------------
        # FEFO Warehouse Collection Guidance with Batch Traceability
        # ---------------------------------------------------------------
        st.subheader("FEFO Warehouse Collection Guidance")

        if warehouse_df.empty:
            st.info("Upload cleaned warehouse stock data to enable FEFO warehouse collection guidance.")
        else:
            fefo_df = apply_fefo_collection_guidance(
                constrained_df=constrained_df,
                warehouse_df=warehouse_df,
                selected_commodity=selected_commodity,
                selected_standard_name=selected_standard_name,
                cycle_distributor=cycle_distributor,
            )

            if fefo_df.empty:
                st.warning(
                    "No matching warehouse stock rows found for the selected product. "
                    "Check product naming consistency between LMIS and warehouse data."
                )
            else:
                st.dataframe(fefo_df, use_container_width=True)

                fefo_csv = fefo_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Download FEFO warehouse guidance as CSV",
                    data=fefo_csv,
                    file_name="fefo_warehouse_guidance.csv",
                    mime="text/csv",
                )

        # ---------------------------------------------------------------
        # Excel Export
        # ---------------------------------------------------------------
        st.subheader("Excel Export")

        excel_bytes = create_excel_workbook(
            planning_df=planning_df,
            constrained_df=constrained_df,
            district_summary=district_summary,
            fefo_df=fefo_df,
        )

        st.download_button(
            label="Download full planning workbook (Excel)",
            data=excel_bytes,
            file_name="lastmileplus_planning_workbook.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
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

        forecast_input = filtered.copy()
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

    risk_input = filtered.copy()
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
st.caption(
    "Seasonality note: seasonality adjustment is not yet applied in this version. "
    "When introduced later, LLINs and SP should remain unadjusted."
)
