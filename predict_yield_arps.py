"""
Predict wheat yield using ARPS (PlanetScope) NDVI data.
Follows the same methodology as predict_yield.py but with daily ARPS data.
"""

import json
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from scipy.interpolate import interp1d

# Import existing modules
import sys
sys.path.append('.')
from wheat_rue_values import WheatRUE


# Constants
HARVEST_INDEX = 0.48  # Calibrated value (ton grain / ton total biomass)


def calculate_fapar(ndvi):
    """
    Convert NDVI to fAPARg (fraction of Absorbed PAR for green vegetation).
    
    Args:
        ndvi: NDVI value
    
    Returns:
        fAPARg value
    """
    if np.isnan(ndvi):
        return np.nan
    fapar = 0.013 * np.exp(4.48 * ndvi)
    return fapar


def load_par_data(field_name, par_dir='solar_radiation_data'):
    """
    Load PAR data for a field.
    
    Args:
        field_name: Name of the field
        par_dir: Directory containing PAR data
    
    Returns:
        Dictionary with date -> PAR mapping
    """
    # Try different filename formats
    par_filenames = [
        f"solar_radiation_{field_name.replace(' ', '_')}.json",
        f"solar_radiation_{field_name}.json"
    ]
    
    for par_filename in par_filenames:
        par_path = os.path.join(par_dir, par_filename)
        if os.path.exists(par_path):
            with open(par_path, 'r') as f:
                par_data = json.load(f)
            
            # Convert to date -> PAR mapping
            par_dict = {}
            # Handle different possible key names
            radiation_key = 'radiation_data' if 'radiation_data' in par_data else 'daily_radiation'
            
            for entry in par_data[radiation_key]:
                # Handle different PAR key names
                par_value = entry.get('PAR_MJ', entry.get('par_mj_m2', entry.get('par_mj', 0)))
                par_dict[entry['date']] = par_value
            
            return par_dict
    
    return None


def load_phenology_data(field_name, phenology_dir='phenology_predictions'):
    """
    Load phenology data for a field.
    
    Args:
        field_name: Name of the field
        phenology_dir: Directory containing phenology predictions
    
    Returns:
        Dictionary with phenology stages
    """
    phenology_filename = f"phenology_{field_name.replace(' ', '_')}.json"
    phenology_path = os.path.join(phenology_dir, phenology_filename)
    
    if os.path.exists(phenology_path):
        with open(phenology_path, 'r') as f:
            return json.load(f)
    
    return None


def interpolate_fapar_to_daily(dates, fapar_values, start_date, end_date):
    """
    Interpolate fAPAR to daily values for biomass calculation.
    
    Args:
        dates: List of observation dates
        fapar_values: List of fAPAR values
        start_date: Start date for interpolation
        end_date: End date for interpolation
    
    Returns:
        DataFrame with daily fAPAR values
    """
    # Convert dates to datetime
    date_objects = [datetime.strptime(d, '%Y-%m-%d') for d in dates]
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Convert to days since start
    days_since_start = [(d - start_dt).days for d in date_objects]
    
    # Filter to only dates within range
    valid_indices = [i for i, d in enumerate(days_since_start) if 0 <= d <= (end_dt - start_dt).days]
    
    if len(valid_indices) < 2:
        return pd.DataFrame({'date': [], 'fapar': []})
    
    valid_days = [days_since_start[i] for i in valid_indices]
    valid_fapar = [fapar_values[i] for i in valid_indices]
    
    # Create daily date range
    daily_dates = []
    current_date = start_dt
    while current_date <= end_dt:
        daily_dates.append(current_date)
        current_date += timedelta(days=1)
    
    daily_days = [(d - start_dt).days for d in daily_dates]
    
    # Interpolate fAPAR (linear for daily data)
    interpolator = interp1d(
        valid_days, 
        valid_fapar, 
        kind='linear',
        bounds_error=False,
        fill_value=(valid_fapar[0], valid_fapar[-1])
    )
    
    daily_fapar = interpolator(daily_days)
    
    # Create DataFrame
    df = pd.DataFrame({
        'date': [d.strftime('%Y-%m-%d') for d in daily_dates],
        'fapar': daily_fapar
    })
    
    return df


def predict_yield_arps(field_name, arps_data, par_dict, phenology_data, sowing_date):
    """
    Predict wheat yield using ARPS NDVI data.
    
    Args:
        field_name: Name of the field
        arps_data: ARPS NDVI data dictionary
        par_dict: Dictionary with date -> PAR mapping
        phenology_data: Phenology predictions dictionary
        sowing_date: Sowing date string (YYYY-MM-DD)
    
    Returns:
        Dictionary with yield predictions and biomass accumulation
    """
    # Extract NDVI observations, filtering out NaN values
    observations = arps_data['observations']
    
    # Filter out observations with NaN NDVI
    valid_observations = []
    for obs in observations:
        ndvi = obs['ndvi_mean']
        if ndvi is not None and not np.isnan(ndvi):
            valid_observations.append(obs)
    
    if len(valid_observations) < 2:
        return None
    
    dates = [obs['date'] for obs in valid_observations]
    ndvi_values = [obs['ndvi_mean'] for obs in valid_observations]
    
    # Calculate fAPAR
    fapar_values = [calculate_fapar(ndvi) for ndvi in ndvi_values]
    
    # Get date range
    start_date = sowing_date
    end_date = dates[-1]
    
    # Interpolate fAPAR to daily (ARPS is already daily, but this ensures no gaps)
    daily_fapar_df = interpolate_fapar_to_daily(dates, fapar_values, start_date, end_date)
    
    if daily_fapar_df.empty:
        return None
    
    # Calculate daily biomass accumulation
    biomass_data = []
    cumulative_biomass = 0.0
    
    sow_dt = datetime.strptime(sowing_date, '%Y-%m-%d')
    
    for _, row in daily_fapar_df.iterrows():
        date = row['date']
        fapar = row['fapar']
        
        # Get PAR for this date
        par = par_dict.get(date, 0.0)
        
        # Calculate days after sowing
        date_dt = datetime.strptime(date, '%Y-%m-%d')
        das = (date_dt - sow_dt).days
        
        # Get RUE for this growth stage
        rue = WheatRUE.get_rue_by_days(das)
        
        # Calculate daily biomass (g/m²)
        apar = fapar * par  # MJ/m²
        daily_biomass = rue * apar  # g/m²
        cumulative_biomass += daily_biomass
        
        biomass_data.append({
            'date': date,
            'days_after_sowing': das,
            'fapar': float(fapar),
            'par_mj_m2': float(par),
            'apar_mj_m2': float(apar),
            'rue_g_mj': float(rue),
            'daily_biomass_g_m2': float(daily_biomass),
            'cumulative_biomass_g_m2': float(cumulative_biomass)
        })
    
    # Calculate grain yield
    final_biomass_g_m2 = cumulative_biomass
    final_biomass_kg_ha = final_biomass_g_m2 * 10  # Convert g/m² to kg/ha
    final_biomass_ton_ha = final_biomass_kg_ha / 1000  # Convert to ton/ha
    
    grain_yield_ton_ha = final_biomass_ton_ha * HARVEST_INDEX
    
    return {
        'field_name': field_name,
        'sowing_date': sowing_date,
        'end_date': end_date,
        'data_source': 'ARPS (PlanetScope 3m)',
        'observations_count': len(valid_observations),
        'days_monitored': len(biomass_data),
        'final_biomass_ton_ha': float(final_biomass_ton_ha),
        'grain_yield_ton_ha': float(grain_yield_ton_ha),
        'harvest_index': HARVEST_INDEX,
        'daily_biomass': biomass_data,
        'phenology': phenology_data.get('stages', {}) if phenology_data else {}
    }


def main():
    """Main execution function."""
    print("=" * 80)
    print("WHEAT YIELD PREDICTION USING ARPS DATA")
    print("=" * 80)
    
    # Process both original and new fields
    field_groups = [
        {
            'arps_dir': 'arps_ndvi_data_cleaned',
            'par_dir': 'solar_radiation_data',
            'phenology_dir': 'phenology_predictions',
            'output_file': 'yield_predictions_arps.csv',
            'label': 'Original'
        },
        {
            'arps_dir': 'more_fields/arps_ndvi_data_cleaned',
            'par_dir': 'more_fields/solar_radiation_data',
            'phenology_dir': 'more_fields/phenology_predictions',
            'output_file': 'more_fields/yield_predictions_arps.csv',
            'label': 'New'
        }
    ]
    
    all_predictions = []
    
    for group in field_groups:
        if not os.path.exists(group['arps_dir']):
            print(f"\n⚠️  {group['label']} ARPS directory not found: {group['arps_dir']}")
            continue
        
        print(f"\n{'=' * 80}")
        print(f"PROCESSING {group['label'].upper()} FIELDS")
        print('=' * 80)
        
        arps_files = sorted([f for f in os.listdir(group['arps_dir']) if f.endswith('.json')])
        
        for i, filename in enumerate(arps_files, 1):
            arps_path = os.path.join(group['arps_dir'], filename)
            
            # Load ARPS data
            with open(arps_path, 'r') as f:
                arps_data = json.load(f)
            
            field_name = arps_data['field_name']
            sowing_date = arps_data.get('sowing_date')
            
            print(f"\n{i}/{len(arps_files)}: {field_name}")
            
            if not sowing_date:
                print(f"  ⊘ Skipping (no sowing date)")
                continue
            
            # Load PAR data
            par_dict = load_par_data(field_name, group['par_dir'])
            if not par_dict:
                print(f"  ⚠️  PAR data not found")
                continue
            
            # Load phenology data (optional)
            phenology_data = load_phenology_data(field_name, group['phenology_dir'])
            
            try:
                # Predict yield
                result = predict_yield_arps(
                    field_name, 
                    arps_data, 
                    par_dict, 
                    phenology_data,
                    sowing_date
                )
                
                if result:
                    print(f"  ✓ Final biomass: {result['final_biomass_ton_ha']:.2f} ton/ha")
                    print(f"  ✓ Grain yield: {result['grain_yield_ton_ha']:.2f} ton/ha")
                    print(f"  📊 Based on {result['observations_count']} daily observations")
                    
                    all_predictions.append({
                        'Field Name': field_name,
                        'Sowing Date': sowing_date,
                        'Data Source': 'ARPS',
                        'Observations': result['observations_count'],
                        'Days Monitored': result['days_monitored'],
                        'Final Biomass (ton/ha)': result['final_biomass_ton_ha'],
                        'Grain Yield (ton/ha)': result['grain_yield_ton_ha']
                    })
                    
                    # Save detailed results
                    output_detail_path = os.path.join(
                        os.path.dirname(group['output_file']),
                        f"yield_detail_arps_{field_name.replace(' ', '_')}.json"
                    )
                    with open(output_detail_path, 'w') as f:
                        json.dump(result, f, indent=2)
                else:
                    print(f"  ✗ Prediction failed")
                    
            except Exception as e:
                print(f"  ✗ Error: {e}")
                import traceback
                traceback.print_exc()
        
        # Save CSV for this group
        if all_predictions:
            df = pd.DataFrame(all_predictions)
            df.to_csv(group['output_file'], index=False)
            print(f"\n✓ Saved predictions to {group['output_file']}")
    
    # Save combined results
    if all_predictions:
        combined_df = pd.DataFrame(all_predictions)
        combined_df.to_csv('yield_predictions_arps_all_fields.csv', index=False)
        
        print("\n" + "=" * 80)
        print("SUMMARY STATISTICS - ARPS PREDICTIONS")
        print("=" * 80)
        print(f"Total fields: {len(combined_df)}")
        print(f"Mean yield: {combined_df['Grain Yield (ton/ha)'].mean():.2f} ton/ha")
        print(f"Median yield: {combined_df['Grain Yield (ton/ha)'].median():.2f} ton/ha")
        print(f"Std dev: {combined_df['Grain Yield (ton/ha)'].std():.2f} ton/ha")
        print(f"Range: {combined_df['Grain Yield (ton/ha)'].min():.2f} - {combined_df['Grain Yield (ton/ha)'].max():.2f} ton/ha")
        print(f"Avg observations per field: {combined_df['Observations'].mean():.0f}")
        print("=" * 80)


if __name__ == "__main__":
    main()

