# LastMile+ Data Model

**Version**: 0.1  
**Date**: April 2026  

This document defines the data structures used by LastMile+ for demand forecasting, stockout risk prediction, and distribution planning. The system is designed to work primarily with CSV exports from DHIS2, eLMIS/OpenLMIS, and facility stock reports.

## 1. Core Entities

### Facilities
- `facility_id`: Unique identifier (string, preferably DHIS2 orgUnit ID)
- `facility_name`: Human-readable name
- `district`: District name
- `region`: Region name
- `facility_type`: Hospital, Health Centre, Clinic, Dispensary, or CHW
- `cold_chain`: Boolean (True if the facility has cold chain capacity)

### Commodities
- `commodity_id`: Unique code
- `commodity_name`: Full name (e.g., Artemether-Lumefantrine (AL) 6x1)
- `unit`: Tablet, Vial, Dose, Test, Kit, etc.
- `is_vaccine`: Boolean
- `requires_cold_chain`: Boolean

### Historical Consumption (Main Time-Series Table)
This is the primary dataset used for forecasting.

Columns:
- `facility_id`
- `facility_name`
- `district`
- `region`
- `commodity_id`
- `commodity_name`
- `period`: YYYY-MM format (e.g., 2024-01)
- `consumption`: Actual quantity consumed/issued to patients (numeric)
- `issues`: Quantity issued from higher level (numeric)
- `stock_on_hand`: Ending stock balance (numeric)
- `days_stock_out`: Number of days the facility reported stockout (integer)
- `outpatient_visits`: Optional service utilization data (integer)

## 2. File Structure Recommendation

