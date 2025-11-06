"""
Correct NDVI values (replace ndvi_mean=1.0 with ndvi_mean_original) 
and recalculate yield predictions.
"""

import json
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy.interpolate import interp1d
import sys

# Import yield prediction functions
from wheat_rue_values import WheatRUE

# Constants
HARVEST_INDEX = 0.48  # ton grain / ton total biomass


def calculate_fapar(ndvi):
    """Convert NDVI to fAPAR."""
    if np.isnan(ndvi) or ndvi is None:
        return np.nan
    fapar = 0.013 * np.exp(4.48 * ndvi)
    return fapar


def load_par_data(field_name, par_dir='solar_radiation_data'):
    """Load PAR data for a field."""
    par_filenames = [
        f"solar_radiation_{field_name.replace(' ', '_')}.json",
        f"solar_radiation_{field_name}.json"
    ]
    
    # Also check more_fields directory
    par_dirs = [par_dir, f'more_fields/{par_dir}']
    
    for par_dir_path in par_dirs:
        for par_filename in par_filenames:
            par_path = os.path.join(par_dir_path, par_filename)
            if os.path.exists(par_path):
                with open(par_path, 'r') as f:
                    par_data = json.load(f)
                
                par_dict = {}
                radiation_key = 'radiation_data' if 'radiation_data' in par_data else 'daily_radiation'
                
                for entry in par_data[radiation_key]:
                    par_value = entry.get('PAR_MJ', entry.get('par_mj_m2', entry.get('par_mj', 0)))
                    par_dict[entry['date']] = par_value
                
                return par_dict
    
    return None


def correct_ndvi_in_data(arps_data):
    """Correct NDVI values where ndvi_mean == 1.0."""
    corrections_made = 0
    
    for obs in arps_data.get('observations', []):
        if obs.get('ndvi_mean') == 1.0:
            # Use ndvi_mean_original if available
            if 'ndvi_mean_original' in obs and obs['ndvi_mean_original'] is not None:
                original_value = obs['ndvi_mean_original']
                obs['ndvi_mean'] = original_value
                obs['ndvi_corrected'] = True
                obs['ndvi_corrected_from'] = 1.0
                obs['ndvi_corrected_to'] = original_value
                corrections_made += 1
            # Fallback to p50 if original not available
            elif 'ndvi_p50' in obs and obs['ndvi_p50'] is not None:
                p50_value = obs['ndvi_p50']
                obs['ndvi_mean'] = p50_value
                obs['ndvi_corrected'] = True
                obs['ndvi_corrected_from'] = 1.0
                obs['ndvi_corrected_to'] = p50_value
                corrections_made += 1
    
    return corrections_made


def interpolate_fapar_to_daily(dates, fapar_values, start_date, end_date):
    """Interpolate fAPAR to daily values."""
    date_objects = [datetime.strptime(d, '%Y-%m-%d') for d in dates]
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    days_since_start = [(d - start_dt).days for d in date_objects]
    valid_indices = [i for i, d in enumerate(days_since_start) if 0 <= d <= (end_dt - start_dt).days]
    
    if len(valid_indices) < 2:
        return pd.DataFrame({'date': [], 'fapar': []})
    
    valid_days = [days_since_start[i] for i in valid_indices]
    valid_fapar = [fapar_values[i] for i in valid_indices]
    
    daily_dates = []
    current_date = start_dt
    while current_date <= end_dt:
        daily_dates.append(current_date)
        current_date += timedelta(days=1)
    
    daily_days = [(d - start_dt).days for d in daily_dates]
    
    interpolator = interp1d(
        valid_days, 
        valid_fapar, 
        kind='linear',
        bounds_error=False,
        fill_value=(valid_fapar[0], valid_fapar[-1])
    )
    
    daily_fapar = interpolator(daily_days)
    
    df = pd.DataFrame({
        'date': [d.strftime('%Y-%m-%d') for d in daily_dates],
        'fapar': daily_fapar
    })
    
    return df


def predict_yield_arps_corrected(field_name, arps_data, par_dict, sowing_date):
    """Predict yield using corrected ARPS NDVI data."""
    observations = arps_data['observations']
    
    valid_observations = []
    for obs in observations:
        ndvi = obs['ndvi_mean']
        if ndvi is not None and not np.isnan(ndvi):
            valid_observations.append(obs)
    
    if len(valid_observations) < 2:
        return None
    
    dates = [obs['date'] for obs in valid_observations]
    ndvi_values = [obs['ndvi_mean'] for obs in valid_observations]
    
    # Calculate fAPAR from corrected NDVI
    fapar_values = [calculate_fapar(ndvi) for ndvi in ndvi_values]
    
    start_date = sowing_date
    end_date = dates[-1]
    
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
        
        par = par_dict.get(date, 0.0)
        date_dt = datetime.strptime(date, '%Y-%m-%d')
        das = (date_dt - sow_dt).days
        
        rue = WheatRUE.get_rue_by_days(das)
        
        apar = fapar * par
        daily_biomass = rue * apar
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
    final_biomass_kg_ha = final_biomass_g_m2 * 10
    final_biomass_ton_ha = final_biomass_kg_ha / 1000
    grain_yield_ton_ha = final_biomass_ton_ha * HARVEST_INDEX
    
    return {
        'field_name': field_name,
        'sowing_date': sowing_date,
        'end_date': end_date,
        'data_source': 'ARPS (PlanetScope 3m) - CORRECTED',
        'observations_count': len(valid_observations),
        'days_monitored': len(biomass_data),
        'final_biomass_ton_ha': float(final_biomass_ton_ha),
        'grain_yield_ton_ha': float(grain_yield_ton_ha),
        'harvest_index': HARVEST_INDEX,
        'daily_biomass': biomass_data
    }


def main():
    """Correct NDVI and recalculate yields."""
    
    print("=" * 80)
    print("CORRECTING NDVI VALUES AND RECALCULATING YIELD PREDICTIONS")
    print("=" * 80)
    
    # Step 1: Correct NDVI in all data files
    print("\n" + "=" * 80)
    print("STEP 1: CORRECTING NDVI VALUES")
    print("=" * 80)
    
    arps_dirs = [
        'arps_ndvi_data_cleaned',
        'more_fields/arps_ndvi_data_cleaned'
    ]
    
    total_corrections = 0
    corrected_files = []
    
    for arps_dir in arps_dirs:
        if not os.path.exists(arps_dir):
            continue
        
        print(f"\nProcessing {arps_dir}...")
        
        for filename in os.listdir(arps_dir):
            if not filename.endswith('.json'):
                continue
            
            arps_path = os.path.join(arps_dir, filename)
            
            try:
                with open(arps_path, 'r') as f:
                    arps_data = json.load(f)
                
                corrections = correct_ndvi_in_data(arps_data)
                
                if corrections > 0:
                    # Save corrected version
                    corrected_path = arps_path.replace('.json', '_CORRECTED.json')
                    with open(corrected_path, 'w') as f:
                        json.dump(arps_data, f, indent=2)
                    
                    field_name = arps_data.get('field_name', filename)
                    print(f"  ✓ {field_name}: Corrected {corrections} NDVI value(s)")
                    total_corrections += corrections
                    corrected_files.append(field_name)
            
            except Exception as e:
                print(f"  ✗ Error processing {filename}: {e}")
    
    print(f"\n✓ Total corrections: {total_corrections} NDVI values")
    print(f"✓ Fields affected: {len(corrected_files)}")
    
    if total_corrections == 0:
        print("\nNo corrections needed - no NDVI=1.0 values found!")
        return
    
    # Step 2: Recalculate yield predictions for affected fields
    print("\n" + "=" * 80)
    print("STEP 2: RECALCULATING YIELD PREDICTIONS")
    print("=" * 80)
    
    # Load original predictions for comparison
    original_df = pd.read_csv('yield_predictions_arps_all_fields.csv')
    
    corrected_predictions = []
    comparison_data = []
    
    for field_name in corrected_files:
        print(f"\n{field_name}:")
        
        # Find the ARPS data file
        arps_data = None
        for arps_dir in arps_dirs:
            arps_path = os.path.join(arps_dir, f"arps_ndvi_{field_name.replace(' ', '_')}_CORRECTED.json")
            if os.path.exists(arps_path):
                with open(arps_path, 'r') as f:
                    arps_data = json.load(f)
                break
        
        if not arps_data:
            print(f"  ✗ Could not find corrected data")
            continue
        
        sowing_date = arps_data.get('sowing_date')
        if not sowing_date:
            print(f"  ✗ No sowing date")
            continue
        
        # Load PAR data
        par_dict = load_par_data(field_name)
        if not par_dict:
            print(f"  ✗ No PAR data")
            continue
        
        # Recalculate yield
        try:
            result = predict_yield_arps_corrected(field_name, arps_data, par_dict, sowing_date)
            
            if result:
                # Get original yield
                original_row = original_df[original_df['Field Name'] == field_name]
                original_yield = original_row['Grain Yield (ton/ha)'].iloc[0] if len(original_row) > 0 else None
                corrected_yield = result['grain_yield_ton_ha']
                
                print(f"  Original yield: {original_yield:.2f} ton/ha" if original_yield else "  Original yield: N/A")
                print(f"  Corrected yield: {corrected_yield:.2f} ton/ha")
                
                if original_yield:
                    diff = corrected_yield - original_yield
                    pct_diff = (diff / original_yield) * 100
                    print(f"  Difference: {diff:+.2f} ton/ha ({pct_diff:+.1f}%)")
                
                corrected_predictions.append({
                    'Field Name': field_name,
                    'Sowing Date': sowing_date,
                    'Data Source': 'ARPS (CORRECTED)',
                    'Observations': result['observations_count'],
                    'Days Monitored': result['days_monitored'],
                    'Final Biomass (ton/ha)': result['final_biomass_ton_ha'],
                    'Grain Yield (ton/ha)': corrected_yield,
                    'Original Yield (ton/ha)': original_yield if original_yield else None,
                    'Yield Difference (ton/ha)': diff if original_yield else None,
                    'Yield Difference (%)': pct_diff if original_yield else None
                })
                
                comparison_data.append({
                    'field_name': field_name,
                    'original_yield': original_yield,
                    'corrected_yield': corrected_yield,
                    'difference': diff if original_yield else None,
                    'pct_difference': pct_diff if original_yield else None
                })
        
        except Exception as e:
            print(f"  ✗ Error: {e}")
            import traceback
            traceback.print_exc()
    
    # Step 3: Create comparison and update combined dataset
    print("\n" + "=" * 80)
    print("STEP 3: UPDATING YIELD PREDICTIONS")
    print("=" * 80)
    
    if corrected_predictions:
        # Update original dataframe with corrected values
        corrected_df = original_df.copy()
        
        for pred in corrected_predictions:
            field_name = pred['Field Name']
            mask = corrected_df['Field Name'] == field_name
            if mask.any():
                corrected_df.loc[mask, 'Grain Yield (ton/ha)'] = pred['Grain Yield (ton/ha)']
                corrected_df.loc[mask, 'Final Biomass (ton/ha)'] = pred['Final Biomass (ton/ha)']
                corrected_df.loc[mask, 'Data Source'] = 'ARPS (CORRECTED)'
        
        # Save corrected predictions
        corrected_df.to_csv('yield_predictions_arps_all_fields_CORRECTED.csv', index=False)
        print(f"\n✓ Saved corrected predictions to: yield_predictions_arps_all_fields_CORRECTED.csv")
        
        # Save comparison
        comparison_df = pd.DataFrame(comparison_data)
        comparison_df.to_csv('yield_correction_comparison.csv', index=False)
        print(f"✓ Saved comparison to: yield_correction_comparison.csv")
        
        # Print summary
        print("\n" + "=" * 80)
        print("CORRECTION SUMMARY")
        print("=" * 80)
        print(f"\nFields with corrected yields: {len(corrected_predictions)}")
        
        if comparison_df['difference'].notna().any():
            print(f"\nYield impact:")
            print(f"  Mean difference: {comparison_df['difference'].mean():.3f} ton/ha")
            print(f"  Mean % difference: {comparison_df['pct_difference'].mean():.2f}%")
            print(f"  Range: {comparison_df['difference'].min():.3f} to {comparison_df['difference'].max():.3f} ton/ha")
            
            print(f"\nOverall statistics (corrected):")
            print(f"  Mean yield: {corrected_df['Grain Yield (ton/ha)'].mean():.2f} ton/ha")
            print(f"  Median yield: {corrected_df['Grain Yield (ton/ha)'].median():.2f} ton/ha")
            print(f"  Range: {corrected_df['Grain Yield (ton/ha)'].min():.2f} - {corrected_df['Grain Yield (ton/ha)'].max():.2f} ton/ha")
            
            print(f"\nOriginal statistics:")
            original_mean = original_df['Grain Yield (ton/ha)'].mean()
            original_median = original_df['Grain Yield (ton/ha)'].median()
            print(f"  Mean yield: {original_mean:.2f} ton/ha")
            print(f"  Median yield: {original_median:.2f} ton/ha")
            print(f"  Range: {original_df['Grain Yield (ton/ha)'].min():.2f} - {original_df['Grain Yield (ton/ha)'].max():.2f} ton/ha")
        
        print("\n" + "=" * 80)
        print("✓ CORRECTION COMPLETE")
        print("=" * 80)
        print("\nNext steps:")
        print("  1. Review yield_correction_comparison.csv for detailed changes")
        print("  2. Use yield_predictions_arps_all_fields_CORRECTED.csv for updated predictions")
        print("  3. Regenerate visualizations with corrected data if desired")


if __name__ == "__main__":
    main()

