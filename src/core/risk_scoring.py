"""
LastMile+ - Stockout Risk Scoring Module
Simple and explainable stockout risk scoring for health commodities.
"""

from pathlib import Path
import pandas as pd
import numpy as np


class StockoutRiskScorer:
    def __init__(self):
        self.high_risk_days = 7
        self.medium_risk_days = 3

    def calculate_monthly_consumption(self, row):
        consumption = row.get("consumption", 0)
        try:
            return max(float(consumption), 0)
        except Exception:
            return 0.0

    def calculate_daily_consumption(self, row):
        monthly = self.calculate_monthly_consumption(row)
        return monthly / 30 if monthly > 0 else 0.0

    def calculate_days_of_stock(self, row):
        soh = row.get("stock_on_hand", 0)
        try:
            soh = max(float(soh), 0)
        except Exception:
            soh = 0.0

        daily = self.calculate_daily_consumption(row)
        if daily <= 0:
            return np.inf if soh > 0 else 0.0
        return soh / daily

    def score_row(self, row):
        days_of_stock = self.calculate_days_of_stock(row)
        days_stock_out = row.get("days_stock_out", 0)

        try:
            days_stock_out = int(days_stock_out)
        except Exception:
            days_stock_out = 0

        score = 0
        reasons = []

        if days_of_stock <= self.medium_risk_days:
            score += 60
            reasons.append("Very low stock relative to consumption")
        elif days_of_stock <= self.high_risk_days:
            score += 40
            reasons.append("Low stock relative to consumption")
        elif days_of_stock <= 14:
            score += 20
            reasons.append("Moderate stock cover")

        if days_stock_out >= 5:
            score += 30
            reasons.append("Recent stockout history is high")
        elif days_stock_out >= 1:
            score += 15
            reasons.append("Recent stockout history detected")

        if self.calculate_monthly_consumption(row) == 0 and row.get("stock_on_hand", 0) == 0:
            score += 20
            reasons.append("No stock and no recent consumption reported")

        score = min(score, 100)

        if score >= 70:
            risk_level = "High"
        elif score >= 40:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        return pd.Series({
            "days_of_stock": round(days_of_stock, 1) if np.isfinite(days_of_stock) else None,
            "risk_score": score,
            "risk_level": risk_level,
            "risk_reason": "; ".join(reasons) if reasons else "Stable stock situation"
        })

    def score_all(self, df):
        latest = (
            df.sort_values("period")
            .groupby(["facility_id", "commodity_id"], as_index=False)
            .tail(1)
            .copy()
        )

        risk_results = latest.apply(self.score_row, axis=1)
        return pd.concat([latest.reset_index(drop=True), risk_results], axis=1)


if __name__ == "__main__":
    sample_path = Path("data/sample/sample_consumption.csv")
    if sample_path.exists():
        df = pd.read_csv(sample_path)
        scorer = StockoutRiskScorer()
        result = scorer.score_all(df)
        print("Risk scoring completed successfully!")
        print(result[[
            "facility_id",
            "commodity_id",
            "stock_on_hand",
            "consumption",
            "risk_score",
            "risk_level"
        ]].head())
    else:
        print("Sample data not found")
