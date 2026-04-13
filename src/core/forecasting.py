"""
LastMile+ - Demand Forecasting Module
Conservative and explainable forecasting for health commodities.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

class DemandForecaster:
    def __init__(self):
        self.forecast_horizon = 3  # months ahead

    def prepare_data(self, df, facility_id, commodity_id):
        mask = (df['facility_id'] == facility_id) & (df['commodity_id'] == commodity_id)
        ts = df[mask].copy()
        if ts.empty:
            return pd.DataFrame()
        
        ts = ts.sort_values('period')
        ts['ds'] = pd.to_datetime(ts['period'] + '-01')
        ts['y'] = ts['consumption'].fillna(0)
        return ts[['ds', 'y']].reset_index(drop=True)

    def fit_and_forecast(self, df, facility_id, commodity_id, periods=3):
        ts = self.prepare_data(df, facility_id, commodity_id)
        
        if len(ts) < 6:
            mean_demand = ts['y'].tail(3).mean() if not ts.empty else 0
            forecast = pd.DataFrame({
                'ds': pd.date_range(start=ts['ds'].max() + pd.offsets.MonthBegin(1), periods=periods, freq='MS') if not ts.empty else pd.date_range(start=datetime.now(), periods=periods, freq='MS'),
                'yhat': [mean_demand] * periods,
                'yhat_lower': [mean_demand * 0.7] * periods,
                'yhat_upper': [mean_demand * 1.3] * periods
            })
            return forecast, "Simple average (limited data)"

        # Simple statistical forecast
        base = ts['y'].mean()
        trend = (ts['y'].iloc[-1] - ts['y'].iloc[0]) / len(ts) if len(ts) > 1 else 0
        forecast_values = [max(0, base + trend * (i+1)) for i in range(periods)]
        
        last_date = ts['ds'].max()
        forecast = pd.DataFrame({
            'ds': pd.date_range(start=last_date + pd.offsets.MonthBegin(1), periods=periods, freq='MS'),
            'yhat': forecast_values,
            'yhat_lower': [v * 0.75 for v in forecast_values],
            'yhat_upper': [v * 1.35 for v in forecast_values]
        })
        return forecast, "Statistical trend forecast"

    def forecast_all(self, df, horizon=3):
        results = []
        unique_pairs = df[['facility_id', 'commodity_id']].drop_duplicates()
        
        for _, row in unique_pairs.iterrows():
            forecast, method = self.fit_and_forecast(df, row['facility_id'], row['commodity_id'], horizon)
            if not forecast.empty:
                forecast['facility_id'] = row['facility_id']
                forecast['commodity_id'] = row['commodity_id']
                forecast['forecast_method'] = method
                forecast['forecast_period'] = forecast['ds'].dt.strftime('%Y-%m')
                results.append(forecast)
        
        return pd.concat(results, ignore_index=True) if results else pd.DataFrame()

# Test
if __name__ == "__main__":
    sample_path = Path("data/sample/sample_consumption.csv")
    if sample_path.exists():
        df = pd.read_csv(sample_path)
        forecaster = DemandForecaster()
        forecast_df = forecaster.forecast_all(df)
        print("Forecast generated successfully!")
        print(forecast_df.head())
    else:
        print("Sample data not found")
      Add demand forecasting module
