"""
Create comprehensive time series plots for each field showing:
- NDVI
- fAPAR
- PAR (Solar Radiation)
- Daily Biomass Accumulation
- Cumulative Biomass & Final Yield

One PNG per field.
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import numpy as np
from pathlib import Path


def load_all_data():
    """Load all data sources for both original and new fields."""
    
    print("\n" + "=" * 80)
    print("LOADING DATA FOR ALL FIELDS")
    print("=" * 80)
    
    data = {
        'ndvi_fapar': {},
        'par': {},
        'biomass': {},
        'yield': {},
        'phenology': {}
    }
    
    # Load new fields data first (we have complete data for these)
    print("\nLoading new fields data...")
    try:
        # NDVI/fAPAR - Note: structure is dict with field names as keys
        with open('output_new_fields/sentinel_ndvi_fapar_data.json', 'r') as f:
            new_ndvi = json.load(f)
            # fields is a dict with field names as keys
            for field_name, field_data in new_ndvi['fields'].items():
                data['ndvi_fapar'][field_name] = {
                    'field_name': field_name,
                    'variety': field_data['variety'],
                    'sowing_date': field_data['sowing_date'],
                    'observations': field_data['ndvi_time_series']  # This contains the time series
                }
        print(f"  ✓ NDVI/fAPAR: {len(new_ndvi['fields'])} new fields")
        
        # PAR - Note: structure is also dict with field names as keys
        with open('output_new_fields/solar_radiation_par_data.json', 'r') as f:
            new_par = json.load(f)
            for field_name, field_data in new_par['fields'].items():
                data['par'][field_name] = {
                    'field_name': field_name,
                    'variety': field_data['variety'],
                    'sowing_date': field_data['sowing_date'],
                    'daily_data': field_data['radiation_data']  # This contains the daily PAR data
                }
        print(f"  ✓ PAR: {len(new_par['fields'])} new fields")
        
        # Biomass
        biomass_df = pd.read_csv('output_new_fields/daily_biomass_accumulation.csv')
        for field_name in biomass_df['field_name'].unique():
            field_data = biomass_df[biomass_df['field_name'] == field_name]
            data['biomass'][field_name] = field_data
        print(f"  ✓ Biomass: {len(biomass_df['field_name'].unique())} new fields")
        
        # Phenology
        with open('output_new_fields/phenology_analysis_results.json', 'r') as f:
            new_pheno = json.load(f)
            for field_data in new_pheno['fields']:
                data['phenology'][field_data['field_name']] = field_data
        print(f"  ✓ Phenology: {len(new_pheno['fields'])} new fields")
        
    except Exception as e:
        print(f"  ✗ Error loading new fields: {e}")
        import traceback
        traceback.print_exc()
    
    # Note: Original fields data is not in JSON format in main directory
    # We'll only process fields where we have complete data
    print("\n⚠️  Note: Creating timeseries only for fields with complete data")
    
    # Load yield predictions
    yield_df = pd.read_csv('yield_predictions_combined_all.csv')
    for _, row in yield_df.iterrows():
        data['yield'][row['Field Name']] = {
            'grain_yield': row['Grain Yield (ton/ha)'],
            'variety': row['Variety'],
            'sowing_date': row['Sowing Date']
        }
    print(f"\n✓ Yield predictions: {len(data['yield'])} total fields")
    
    # Count fields with complete data
    complete_fields = set(data['ndvi_fapar'].keys()) & \
                     set(data['par'].keys()) & \
                     set(data['biomass'].keys()) & \
                     set(data['yield'].keys())
    
    print(f"✓ Fields with complete data: {len(complete_fields)}")
    
    return data


def create_field_timeseries(field_name, data, output_dir):
    """Create comprehensive time series plot for a single field."""
    
    # Get field data
    ndvi_data = data['ndvi_fapar'].get(field_name)
    par_data = data['par'].get(field_name)
    biomass_data = data['biomass'].get(field_name)
    yield_data = data['yield'].get(field_name)
    phenology_data = data['phenology'].get(field_name)
    
    # Check if data exists (biomass_data is a DataFrame, need special check)
    if ndvi_data is None or par_data is None or biomass_data is None or yield_data is None:
        print(f"  ⚠️ Missing data for {field_name}, skipping...")
        return False
    
    if isinstance(biomass_data, pd.DataFrame) and biomass_data.empty:
        print(f"  ⚠️ Empty biomass data for {field_name}, skipping...")
        return False
    
    # Create figure with 5 subplots
    fig, axes = plt.subplots(5, 1, figsize=(14, 16), sharex=True)
    fig.suptitle(f"{field_name} - {yield_data['variety']}\n"
                 f"Sowing: {yield_data['sowing_date']} | "
                 f"Predicted Yield: {yield_data['grain_yield']:.2f} ton/ha",
                 fontsize=14, fontweight='bold', y=0.995)
    
    # Parse dates
    sowing_date = datetime.strptime(yield_data['sowing_date'], '%Y-%m-%d')
    
    # Parse phenology stages
    stages = {}
    if phenology_data and 'stages_achieved' in phenology_data:
        for stage_name, stage_date in phenology_data['stages_achieved'].items():
            try:
                stages[stage_name] = datetime.strptime(stage_date, '%Y-%m-%d')
            except:
                pass
    
    # --- PLOT 1: NDVI ---
    ax1 = axes[0]
    if 'observations' in ndvi_data and ndvi_data['observations']:
        # Use 'from' date as the date, and 'ndvi_mean' as the value
        ndvi_dates = [datetime.strptime(obs['from'], '%Y-%m-%d') 
                      for obs in ndvi_data['observations']]
        ndvi_values = [obs['ndvi_mean'] for obs in ndvi_data['observations']]
        
        ax1.plot(ndvi_dates, ndvi_values, 'o-', color='darkgreen', 
                linewidth=2, markersize=6, label='NDVI')
        ax1.fill_between(ndvi_dates, ndvi_values, alpha=0.3, color='green')
        ax1.set_ylabel('NDVI', fontsize=11, fontweight='bold')
        ax1.set_title('Normalized Difference Vegetation Index', fontsize=11, loc='left')
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(0, 1)
        ax1.axhline(0.5, color='gray', linestyle='--', alpha=0.5, linewidth=1)
    
    # Add phenology stages
    for stage_name, stage_date in stages.items():
        ax1.axvline(stage_date, color='red', linestyle='--', alpha=0.3, linewidth=1)
    
    # --- PLOT 2: fAPAR ---
    ax2 = axes[1]
    if 'observations' in ndvi_data and ndvi_data['observations']:
        fapar_dates = [datetime.strptime(obs['from'], '%Y-%m-%d') 
                       for obs in ndvi_data['observations']]
        fapar_values = [obs['fapar_mean'] for obs in ndvi_data['observations']]
        
        ax2.plot(fapar_dates, fapar_values, 'o-', color='darkblue', 
                linewidth=2, markersize=6, label='fAPAR')
        ax2.fill_between(fapar_dates, fapar_values, alpha=0.3, color='blue')
        ax2.set_ylabel('fAPAR', fontsize=11, fontweight='bold')
        ax2.set_title('Fraction of Absorbed PAR (green vegetation)', fontsize=11, loc='left')
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim(0, 1)
    
    # Add phenology stages
    for stage_name, stage_date in stages.items():
        ax2.axvline(stage_date, color='red', linestyle='--', alpha=0.3, linewidth=1)
    
    # --- PLOT 3: PAR ---
    ax3 = axes[2]
    if 'daily_data' in par_data and par_data['daily_data']:
        par_dates = [datetime.strptime(day['date'], '%Y-%m-%d') 
                     for day in par_data['daily_data']]
        par_values = [day['PAR_MJ'] for day in par_data['daily_data']]
        
        ax3.plot(par_dates, par_values, '-', color='orange', 
                linewidth=1.5, alpha=0.8, label='PAR')
        ax3.fill_between(par_dates, par_values, alpha=0.2, color='orange')
        ax3.set_ylabel('PAR\n(MJ/m²/day)', fontsize=11, fontweight='bold')
        ax3.set_title('Photosynthetically Active Radiation', fontsize=11, loc='left')
        ax3.grid(True, alpha=0.3)
    
    # Add phenology stages
    for stage_name, stage_date in stages.items():
        ax3.axvline(stage_date, color='red', linestyle='--', alpha=0.3, linewidth=1)
    
    # --- PLOT 4: Daily Biomass Accumulation ---
    ax4 = axes[3]
    biomass_dates = pd.to_datetime(biomass_data['date'])
    daily_biomass = biomass_data['daily_biomass']
    
    ax4.bar(biomass_dates, daily_biomass, width=1.0, 
           color='purple', alpha=0.6, edgecolor='darkviolet', linewidth=0.5)
    ax4.set_ylabel('Daily Biomass\n(kg/ha/day)', fontsize=11, fontweight='bold')
    ax4.set_title('Daily Biomass Accumulation', fontsize=11, loc='left')
    ax4.grid(True, alpha=0.3, axis='y')
    
    # Add phenology stages
    for stage_name, stage_date in stages.items():
        ax4.axvline(stage_date, color='red', linestyle='--', alpha=0.3, linewidth=1)
    
    # --- PLOT 5: Cumulative Biomass ---
    ax5 = axes[4]
    cumulative_biomass = biomass_data['cumulative_biomass']
    
    ax5.plot(biomass_dates, cumulative_biomass, '-', color='darkred', 
            linewidth=2.5, label='Total Biomass')
    ax5.fill_between(biomass_dates, cumulative_biomass, alpha=0.2, color='red')
    
    # Add grain yield line
    grain_yield_kg = yield_data['grain_yield'] * 1000  # Convert to kg/ha
    ax5.axhline(grain_yield_kg, color='green', linestyle='--', 
               linewidth=2, label=f'Grain Yield: {yield_data["grain_yield"]:.2f} ton/ha')
    
    ax5.set_ylabel('Cumulative\nBiomass (kg/ha)', fontsize=11, fontweight='bold')
    ax5.set_xlabel('Date', fontsize=11, fontweight='bold')
    ax5.set_title('Cumulative Biomass & Grain Yield', fontsize=11, loc='left')
    ax5.grid(True, alpha=0.3)
    ax5.legend(loc='lower right', fontsize=9)
    
    # Add phenology stages with labels on bottom plot
    stage_colors = {
        'Emergence': '#8B4513',
        'Tillering': '#006400',
        'Stem_Extension': '#4169E1',
        'Heading': '#FFD700',
        'Grain_Fill': '#FF8C00',
        'Maturity': '#8B0000'
    }
    
    for stage_name, stage_date in stages.items():
        display_name = stage_name.replace('_', ' ')
        color = stage_colors.get(stage_name, 'red')
        ax5.axvline(stage_date, color=color, linestyle='--', alpha=0.5, linewidth=1.5,
                   label=display_name)
    
    # Format x-axis
    ax5.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax5.xaxis.set_major_locator(mdates.MonthLocator())
    plt.setp(ax5.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # Add legend for phenology stages
    handles, labels = ax5.get_legend_handles_labels()
    if len(handles) > 1:  # If we have stages
        ax5.legend(handles, labels, loc='upper left', fontsize=8, ncol=2)
    
    plt.tight_layout()
    
    # Save
    safe_filename = field_name.replace('/', '_').replace(' ', '_')
    output_file = output_dir / f"{safe_filename}_timeseries.png"
    plt.savefig(output_file, dpi=200, bbox_inches='tight')
    plt.close()
    
    return True


def create_all_timeseries():
    """Create time series plots for all fields."""
    
    # Load data
    data = load_all_data()
    
    # Create output directory
    output_dir = Path('field_timeseries_plots')
    output_dir.mkdir(exist_ok=True)
    
    print("\n" + "=" * 80)
    print("CREATING TIME SERIES PLOTS")
    print("=" * 80)
    print(f"\nOutput directory: {output_dir}")
    
    # Get fields with complete data
    complete_fields = set(data['ndvi_fapar'].keys()) & \
                     set(data['par'].keys()) & \
                     set(data['biomass'].keys()) & \
                     set(data['yield'].keys())
    
    print(f"\nProcessing {len(complete_fields)} fields with complete data")
    
    # Process each field
    total_fields = len(complete_fields)
    success_count = 0
    failed_fields = []
    
    for i, field_name in enumerate(sorted(complete_fields), 1):
        print(f"\n[{i}/{total_fields}] Processing: {field_name}")
        
        try:
            if create_field_timeseries(field_name, data, output_dir):
                success_count += 1
                print(f"  ✓ Created timeseries plot")
            else:
                failed_fields.append(field_name)
        except Exception as e:
            print(f"  ✗ Error: {e}")
            failed_fields.append(field_name)
    
    # Summary
    print("\n" + "=" * 80)
    print("✓ TIME SERIES PLOTS COMPLETE")
    print("=" * 80)
    print(f"\nSuccessfully created: {success_count}/{total_fields} plots")
    print(f"Output directory: {output_dir.absolute()}")
    
    if failed_fields:
        print(f"\n⚠️ Failed fields ({len(failed_fields)}):")
        for field in failed_fields:
            print(f"  - {field}")
    
    print(f"\nEach plot contains:")
    print("  1. NDVI time series")
    print("  2. fAPAR time series")
    print("  3. PAR (solar radiation) time series")
    print("  4. Daily biomass accumulation")
    print("  5. Cumulative biomass with grain yield")
    print("  + Phenological stages marked as vertical lines")


if __name__ == "__main__":
    try:
        create_all_timeseries()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

