"""
Wheat Yield Prediction Model

This script combines:
1. Weekly fAPAR data (from Sentinel-2 NDVI)
2. Daily PAR data (from Open-Meteo)
3. Growth stage-specific RUE values (from literature)
4. Phenology predictions (growth stages)

To estimate total biomass and grain yield for each field.

Key approach:
- Interpolate weekly fAPAR to daily values
- Calculate daily biomass: Biomass = fAPAR × PAR × RUE
- Sum daily biomass over growing season
- Apply harvest index to get grain yield
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from wheat_rue_values import WheatRUE


class YieldPredictor:
    """Wheat yield prediction using radiation use efficiency approach."""
    
    # Harvest index for modern wheat varieties
    HARVEST_INDEX = 0.45  # Grain weight / Total above-ground biomass
    HARVEST_INDEX_RANGE = (0.40, 0.50)  # Typical range
    
    def __init__(self):
        """Initialize yield predictor."""
        self.rue_calculator = WheatRUE()
    
    def interpolate_fapar_to_daily(
        self, 
        fapar_weekly: List[Dict],
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Interpolate weekly fAPAR values to daily values.
        
        Args:
            fapar_weekly: List of weekly fAPAR observations with 'from', 'to', 'fapar_mean'
            start_date: Start date for interpolation
            end_date: End date for interpolation
            
        Returns:
            DataFrame with daily fAPAR values
        """
        # Create DataFrame from weekly data
        weekly_data = []
        for obs in fapar_weekly:
            # Use middle of the week as the observation date
            week_start = datetime.strptime(obs['from'], '%Y-%m-%d')
            week_end = datetime.strptime(obs['to'], '%Y-%m-%d')
            mid_date = week_start + (week_end - week_start) / 2
            
            weekly_data.append({
                'date': mid_date,
                'fapar': obs.get('fapar_mean', 0)
            })
        
        if not weekly_data:
            return pd.DataFrame()
        
        df_weekly = pd.DataFrame(weekly_data)
        df_weekly = df_weekly.sort_values('date')
        
        # Create daily date range
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        df_daily = pd.DataFrame({'date': date_range})
        
        # Merge and interpolate
        df_combined = pd.concat([df_weekly, df_daily]).sort_values('date').drop_duplicates('date')
        df_combined['fapar'] = df_combined['fapar'].interpolate(method='linear', limit_direction='both')
        
        # Keep only the daily values
        df_result = df_combined[df_combined['date'].isin(date_range)].reset_index(drop=True)
        
        return df_result
    
    def calculate_daily_biomass(
        self,
        field_name: str,
        variety: str,
        sowing_date: str,
        fapar_weekly: List[Dict],
        par_daily: List[Dict],
        phenology_stages: Dict
    ) -> pd.DataFrame:
        """
        Calculate daily biomass accumulation for a field.
        
        Args:
            field_name: Name of the field
            variety: Wheat variety
            sowing_date: Sowing date (YYYY-MM-DD)
            fapar_weekly: Weekly fAPAR observations
            par_daily: Daily PAR observations
            phenology_stages: Dictionary with phenology stage dates
            
        Returns:
            DataFrame with daily biomass calculations
        """
        sowing_dt = datetime.strptime(sowing_date, '%Y-%m-%d')
        
        # Create DataFrame from PAR data
        par_data = []
        for obs in par_daily:
            date = datetime.strptime(obs['date'], '%Y-%m-%d')
            par_data.append({
                'date': date,
                'PAR': obs['PAR_MJ']
            })
        
        df_par = pd.DataFrame(par_data)
        df_par = df_par.sort_values('date')
        
        # Interpolate fAPAR to daily
        end_date = df_par['date'].max()
        df_fapar = self.interpolate_fapar_to_daily(fapar_weekly, sowing_dt, end_date)
        
        if df_fapar.empty:
            return pd.DataFrame()
        
        # Merge PAR and fAPAR
        df = pd.merge(df_par, df_fapar, on='date', how='inner')
        
        # Calculate days since sowing
        df['days_since_sowing'] = (df['date'] - sowing_dt).dt.days
        
        # Determine growth stage for each day
        df['growth_stage'] = df['days_since_sowing'].apply(
            lambda days: self._get_growth_stage(days, phenology_stages)
        )
        
        # Get RUE for each day based on growth stage
        df['RUE'] = df['growth_stage'].apply(WheatRUE.get_rue_by_stage)
        
        # Calculate absorbed PAR
        df['APAR'] = df['fapar'] * df['PAR']
        
        # Calculate daily biomass (g DM/m²/day)
        df['daily_biomass'] = df['APAR'] * df['RUE']
        
        # Calculate cumulative biomass
        df['cumulative_biomass'] = df['daily_biomass'].cumsum()
        
        # Add field info
        df['field_name'] = field_name
        df['variety'] = variety
        df['sowing_date'] = sowing_date
        
        return df
    
    def _get_growth_stage(self, days_since_sowing: int, phenology_stages: Dict) -> str:
        """Determine growth stage based on days since sowing and phenology."""
        # Use phenology stage dates if available
        for stage, date_str in phenology_stages.items():
            if date_str and stage != 'sowing':
                # This is a simplified approach - you could make it more sophisticated
                pass
        
        # Fall back to days-based estimation
        if days_since_sowing < 20:
            return 'Emergence'
        elif days_since_sowing < 45:
            return 'Tillering'
        elif days_since_sowing < 75:
            return 'Stem Extension'
        elif days_since_sowing < 105:
            return 'Heading/Anthesis'
        elif days_since_sowing < 140:
            return 'Grain Fill'
        else:
            return 'Maturity'
    
    def predict_yield(
        self,
        total_biomass: float,
        harvest_index: float = None
    ) -> Dict:
        """
        Predict grain yield from total biomass.
        
        Args:
            total_biomass: Total above-ground dry biomass (g DM/m²)
            harvest_index: Harvest index (default: 0.45)
            
        Returns:
            Dictionary with yield predictions
        """
        if harvest_index is None:
            harvest_index = self.HARVEST_INDEX
        
        # Calculate grain yield
        grain_yield_g_m2 = total_biomass * harvest_index
        
        # Convert to common units
        grain_yield_kg_ha = grain_yield_g_m2 * 10  # g/m² to kg/ha
        grain_yield_ton_ha = grain_yield_kg_ha / 1000  # kg/ha to ton/ha
        
        # Calculate range based on HI uncertainty
        yield_low = total_biomass * self.HARVEST_INDEX_RANGE[0] * 10 / 1000
        yield_high = total_biomass * self.HARVEST_INDEX_RANGE[1] * 10 / 1000
        
        return {
            'total_biomass_g_m2': round(total_biomass, 2),
            'total_biomass_kg_ha': round(total_biomass * 10, 2),
            'grain_yield_kg_ha': round(grain_yield_kg_ha, 2),
            'grain_yield_ton_ha': round(grain_yield_ton_ha, 3),
            'yield_range_ton_ha': (round(yield_low, 3), round(yield_high, 3)),
            'harvest_index': harvest_index
        }


def load_all_data() -> Tuple[Dict, Dict, Dict]:
    """Load all required datasets."""
    print("Loading data...")
    
    # Load fAPAR data
    with open('sentinel_ndvi_fapar_data.json', 'r') as f:
        fapar_data = json.load(f)
    print(f"✓ Loaded fAPAR data for {len(fapar_data['fields'])} fields")
    
    # Load PAR data
    with open('solar_radiation_par_data.json', 'r') as f:
        par_data = json.load(f)
    print(f"✓ Loaded PAR data for {len(par_data['fields'])} fields")
    
    # Load phenology data
    with open('phenology_analysis_results.json', 'r') as f:
        phenology_data = json.load(f)
    print(f"✓ Loaded phenology data for {len(phenology_data['fields'])} fields")
    
    return fapar_data, par_data, phenology_data


def process_all_fields() -> Dict:
    """Process all fields and predict yield."""
    print("\n" + "=" * 80)
    print("WHEAT YIELD PREDICTION MODEL")
    print("=" * 80)
    print("\nApproach:")
    print("  1. Interpolate weekly fAPAR to daily values")
    print("  2. Calculate daily biomass: Biomass = fAPAR × PAR × RUE")
    print("  3. Sum daily biomass over growing season")
    print("  4. Apply harvest index (0.45) to get grain yield")
    print("=" * 80)
    
    # Load data
    fapar_data, par_data, phenology_data = load_all_data()
    
    # Initialize predictor
    predictor = YieldPredictor()
    
    # Process each field
    results = {}
    all_daily_data = []
    
    fapar_fields = fapar_data['fields']
    par_fields = par_data['fields']
    phenology_fields = {f['field_name']: f for f in phenology_data['fields']}
    
    total_fields = len(fapar_fields)
    print(f"\nProcessing {total_fields} fields...")
    print("=" * 80)
    
    for idx, (field_name, field_fapar) in enumerate(fapar_fields.items(), 1):
        print(f"\n[{idx}/{total_fields}] {field_name}")
        
        # Get corresponding data
        if field_name not in par_fields:
            print(f"  ✗ No PAR data found, skipping")
            continue
        
        field_par = par_fields[field_name]
        field_pheno = phenology_fields.get(field_name, {})
        
        variety = field_fapar.get('variety', 'Unknown')
        sowing_date = field_fapar.get('sowing_date')
        
        # Get data
        fapar_weekly = field_fapar.get('ndvi_time_series', [])
        par_daily = field_par.get('radiation_data', [])
        phenology_stages = field_pheno.get('stage_dates', {})
        
        if not fapar_weekly or not par_daily:
            print(f"  ✗ Missing data, skipping")
            continue
        
        # Calculate daily biomass
        df_daily = predictor.calculate_daily_biomass(
            field_name,
            variety,
            sowing_date,
            fapar_weekly,
            par_daily,
            phenology_stages
        )
        
        if df_daily.empty:
            print(f"  ✗ Could not calculate biomass, skipping")
            continue
        
        # Get total biomass
        total_biomass = df_daily['cumulative_biomass'].iloc[-1]
        
        # Predict yield
        yield_prediction = predictor.predict_yield(total_biomass)
        
        print(f"  Total Biomass: {yield_prediction['total_biomass_kg_ha']:,.0f} kg/ha")
        print(f"  Grain Yield:   {yield_prediction['grain_yield_ton_ha']:.2f} ton/ha "
              f"({yield_prediction['yield_range_ton_ha'][0]:.2f} - {yield_prediction['yield_range_ton_ha'][1]:.2f})")
        
        # Store results
        results[field_name] = {
            'variety': variety,
            'sowing_date': sowing_date,
            'days_growing': len(df_daily),
            **yield_prediction,
            'current_stage': field_pheno.get('current_stage', 'Unknown')
        }
        
        # Store daily data
        all_daily_data.append(df_daily)
    
    # Combine all daily data
    if all_daily_data:
        df_all_daily = pd.concat(all_daily_data, ignore_index=True)
    else:
        df_all_daily = pd.DataFrame()
    
    return results, df_all_daily


def save_results(results: Dict, df_daily: pd.DataFrame):
    """Save yield prediction results."""
    # Save summary JSON
    output_data = {
        'prediction_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'model': 'Radiation Use Efficiency',
        'harvest_index': YieldPredictor.HARVEST_INDEX,
        'fields': results
    }
    
    with open('yield_predictions.json', 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n✓ Saved yield predictions to: yield_predictions.json")
    
    # Save summary CSV
    rows = []
    for field_name, field_data in results.items():
        rows.append({
            'Field Name': field_name,
            'Variety': field_data['variety'],
            'Sowing Date': field_data['sowing_date'],
            'Days Growing': field_data['days_growing'],
            'Current Stage': field_data['current_stage'],
            'Total Biomass (kg/ha)': field_data['total_biomass_kg_ha'],
            'Grain Yield (ton/ha)': field_data['grain_yield_ton_ha'],
            'Yield Min (ton/ha)': field_data['yield_range_ton_ha'][0],
            'Yield Max (ton/ha)': field_data['yield_range_ton_ha'][1],
            'Harvest Index': field_data['harvest_index']
        })
    
    df_summary = pd.DataFrame(rows)
    df_summary = df_summary.sort_values('Grain Yield (ton/ha)', ascending=False)
    df_summary.to_csv('yield_predictions.csv', index=False)
    
    print(f"✓ Saved yield summary to: yield_predictions.csv")
    
    # Save daily biomass data
    if not df_daily.empty:
        df_daily.to_csv('daily_biomass_accumulation.csv', index=False)
        print(f"✓ Saved daily biomass data to: daily_biomass_accumulation.csv")


def print_summary_statistics(results: Dict):
    """Print summary statistics of yield predictions."""
    print("\n" + "=" * 80)
    print("YIELD PREDICTION SUMMARY")
    print("=" * 80)
    
    yields = [r['grain_yield_ton_ha'] for r in results.values()]
    biomass = [r['total_biomass_kg_ha'] for r in results.values()]
    
    print(f"\nTotal fields predicted: {len(results)}")
    
    print("\n" + "─" * 80)
    print("GRAIN YIELD STATISTICS (ton/ha)")
    print("─" * 80)
    print(f"Mean:   {np.mean(yields):.2f}")
    print(f"Median: {np.median(yields):.2f}")
    print(f"Std:    {np.std(yields):.2f}")
    print(f"Min:    {np.min(yields):.2f}")
    print(f"Max:    {np.max(yields):.2f}")
    
    print("\n" + "─" * 80)
    print("TOP 10 FIELDS BY PREDICTED YIELD")
    print("─" * 80)
    
    sorted_fields = sorted(results.items(), key=lambda x: x[1]['grain_yield_ton_ha'], reverse=True)
    
    print(f"\n{'Field Name':30} {'Variety':15} {'Yield (ton/ha)':15} {'Biomass (kg/ha)':15}")
    print("─" * 80)
    
    for field_name, data in sorted_fields[:10]:
        print(f"{field_name[:30]:30} "
              f"{data['variety'][:15]:15} "
              f"{data['grain_yield_ton_ha']:15.2f} "
              f"{data['total_biomass_kg_ha']:15.0f}")
    
    # Variety comparison
    print("\n" + "─" * 80)
    print("YIELD BY VARIETY")
    print("─" * 80)
    
    by_variety = {}
    for field_name, data in results.items():
        variety = data['variety']
        if variety not in by_variety:
            by_variety[variety] = []
        by_variety[variety].append(data['grain_yield_ton_ha'])
    
    variety_stats = []
    for variety, yields in by_variety.items():
        variety_stats.append({
            'variety': variety,
            'mean_yield': np.mean(yields),
            'count': len(yields)
        })
    
    variety_stats.sort(key=lambda x: x['mean_yield'], reverse=True)
    
    print(f"\n{'Variety':20} {'Avg Yield (ton/ha)':20} {'Fields':10}")
    print("─" * 80)
    
    for stat in variety_stats:
        print(f"{stat['variety'][:20]:20} "
              f"{stat['mean_yield']:20.2f} "
              f"{stat['count']:10}")


if __name__ == "__main__":
    try:
        # Process all fields
        results, df_daily = process_all_fields()
        
        if results:
            # Save results
            save_results(results, df_daily)
            
            # Print statistics
            print_summary_statistics(results)
            
            print("\n" + "=" * 80)
            print("✓ YIELD PREDICTION COMPLETE")
            print("=" * 80)
            print("\nFiles created:")
            print("  - yield_predictions.json (detailed results)")
            print("  - yield_predictions.csv (summary table)")
            print("  - daily_biomass_accumulation.csv (daily data)")
        else:
            print("\n✗ No yield predictions generated")
        
    except FileNotFoundError as e:
        print(f"\n✗ Error: Missing required data file")
        print(f"   {e}")
        print("\nPlease ensure you have run:")
        print("  1. sentinel_ndvi_fetcher.py")
        print("  2. calculate_fapar.py")
        print("  3. fetch_solar_radiation.py")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

