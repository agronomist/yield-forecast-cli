"""
Create individual comprehensive plots for each field showing:
- NDVI time series
- fAPAR time series
- Solar radiation (PAR) time series
- Biomass accumulation
- Yield prediction
"""

import json
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from scipy.interpolate import interp1d


def calculate_fapar(ndvi):
    """Convert NDVI to fAPAR."""
    if pd.isna(ndvi) or ndvi is None:
        return np.nan
    return 0.013 * np.exp(4.48 * ndvi)


def load_arps_data(field_name):
    """Load ARPS NDVI data for a field."""
    # Try original fields first
    arps_paths = [
        f"arps_ndvi_data_cleaned/arps_ndvi_{field_name.replace(' ', '_')}.json",
        f"more_fields/arps_ndvi_data_cleaned/arps_ndvi_{field_name.replace(' ', '_')}.json"
    ]
    
    for arps_path in arps_paths:
        if os.path.exists(arps_path):
            with open(arps_path, 'r') as f:
                data = json.load(f)
                observations = data.get('observations', [])
                if observations:
                    dates = [obs['date'] for obs in observations]
                    ndvi = [obs.get('ndvi_mean', np.nan) for obs in observations]
                    sowing_date = data.get('sowing_date', dates[0] if dates else None)
                    return pd.DataFrame({
                        'date': dates,
                        'ndvi': ndvi,
                        'sowing_date': sowing_date
                    }), data
    
    return None, None


def load_solar_radiation(field_name):
    """Load solar radiation (PAR) data for a field."""
    # Try both directories
    par_paths = [
        f"solar_radiation_data/solar_radiation_{field_name.replace(' ', '_')}.json",
        f"more_fields/solar_radiation_data/solar_radiation_{field_name.replace(' ', '_')}.json"
    ]
    
    for par_path in par_paths:
        if os.path.exists(par_path):
            with open(par_path, 'r') as f:
                data = json.load(f)
                radiation_data = data.get('radiation_data', [])
                if radiation_data:
                    dates = [r['date'] for r in radiation_data]
                    par = [r.get('PAR_MJ', np.nan) for r in radiation_data]
                    return pd.DataFrame({
                        'date': dates,
                        'par_mj_m2': par
                    })
    
    return None


def load_biomass_data(field_name):
    """Load biomass accumulation data from yield detail JSON."""
    detail_paths = [
        f"yield_detail_arps_{field_name.replace(' ', '_')}.json",
        f"more_fields/yield_detail_arps_{field_name.replace(' ', '_')}.json"
    ]
    
    for detail_path in detail_paths:
        if os.path.exists(detail_path):
            with open(detail_path, 'r') as f:
                data = json.load(f)
                biomass_data = data.get('daily_biomass', [])
                if biomass_data:
                    dates = [b['date'] for b in biomass_data]
                    cumulative = [b.get('cumulative_biomass_g_m2', 0) for b in biomass_data]
                    daily = [b.get('daily_biomass_g_m2', 0) for b in biomass_data]
                    # Convert from g/m² to ton/ha
                    cumulative_ton_ha = [c * 10 / 1000 for c in cumulative]  # g/m² * 10 = kg/ha, /1000 = ton/ha
                    daily_ton_ha = [d * 10 / 1000 for d in daily]
                    
                    return pd.DataFrame({
                        'date': dates,
                        'cumulative_biomass_ton_ha': cumulative_ton_ha,
                        'daily_biomass_ton_ha': daily_ton_ha
                    }), data.get('grain_yield_ton_ha', None)
    
    return None, None


def create_field_plot(field_name, field_data, output_dir='field_plots'):
    """Create comprehensive plot for a single field."""
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Load all data sources
    arps_df, arps_raw = load_arps_data(field_name)
    par_df = load_solar_radiation(field_name)
    biomass_df, yield_pred = load_biomass_data(field_name)
    
    if arps_df is None:
        print(f"  ⚠️  Skipping {field_name}: No ARPS data found")
        return False
    
    # Convert dates to datetime
    arps_df['date'] = pd.to_datetime(arps_df['date'])
    if par_df is not None:
        par_df['date'] = pd.to_datetime(par_df['date'])
    if biomass_df is not None:
        biomass_df['date'] = pd.to_datetime(biomass_df['date'])
    
    # Calculate fAPAR from NDVI
    arps_df['fapar'] = arps_df['ndvi'].apply(calculate_fapar)
    
    # Get sowing date
    sowing_date = arps_raw.get('sowing_date') if arps_raw else arps_df['sowing_date'].iloc[0] if 'sowing_date' in arps_df.columns else None
    
    # Create figure with subplots
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)
    
    # ===== Plot 1: NDVI Time Series =====
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(arps_df['date'], arps_df['ndvi'], 'o-', color='#2ecc71', 
             linewidth=2, markersize=4, label='NDVI', alpha=0.8)
    ax1.set_ylabel('NDVI', fontsize=12, fontweight='bold')
    ax1.set_title('NDVI Time Series', fontsize=13, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim([0, 1])
    ax1.legend(fontsize=10)
    if sowing_date:
        ax1.axvline(pd.to_datetime(sowing_date), color='orange', linestyle='--', 
                   linewidth=2, alpha=0.7, label='Sowing')
    
    # ===== Plot 2: fAPAR Time Series =====
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(arps_df['date'], arps_df['fapar'], 'o-', color='#3498db', 
             linewidth=2, markersize=4, label='fAPAR', alpha=0.8)
    ax2.set_ylabel('fAPAR', fontsize=12, fontweight='bold')
    ax2.set_title('fAPAR Time Series', fontsize=13, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim([0, 1])
    ax2.legend(fontsize=10)
    if sowing_date:
        ax2.axvline(pd.to_datetime(sowing_date), color='orange', linestyle='--', 
                   linewidth=2, alpha=0.7, label='Sowing')
    
    # ===== Plot 3: Solar Radiation (PAR) =====
    ax3 = fig.add_subplot(gs[1, 0])
    if par_df is not None:
        ax3.plot(par_df['date'], par_df['par_mj_m2'], '-', color='#f39c12', 
                linewidth=2, label='PAR', alpha=0.8)
        ax3.fill_between(par_df['date'], par_df['par_mj_m2'], alpha=0.3, color='#f39c12')
    ax3.set_ylabel('PAR (MJ/m²/day)', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Date', fontsize=12, fontweight='bold')
    ax3.set_title('Photosynthetically Active Radiation (PAR)', fontsize=13, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.legend(fontsize=10)
    if sowing_date:
        ax3.axvline(pd.to_datetime(sowing_date), color='orange', linestyle='--', 
                   linewidth=2, alpha=0.7, label='Sowing')
    else:
        ax3.text(0.02, 0.98, 'No PAR data available', transform=ax3.transAxes,
                fontsize=10, verticalalignment='top', 
                bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))
    
    # ===== Plot 4: Biomass Accumulation =====
    ax4 = fig.add_subplot(gs[1, 1])
    if biomass_df is not None:
        ax4_twin = ax4.twinx()
        
        # Cumulative biomass
        ax4.plot(biomass_df['date'], biomass_df['cumulative_biomass_ton_ha'], 
                '-', color='#8e44ad', linewidth=2.5, label='Cumulative Biomass', alpha=0.9)
        
        # Daily biomass (secondary y-axis)
        ax4_twin.bar(biomass_df['date'], biomass_df['daily_biomass_ton_ha'], 
                    width=1, color='#95a5a6', alpha=0.5, label='Daily Biomass')
        
        ax4.set_ylabel('Cumulative Biomass (ton/ha)', fontsize=12, fontweight='bold', color='#8e44ad')
        ax4_twin.set_ylabel('Daily Biomass (ton/ha)', fontsize=12, fontweight='bold', color='#95a5a6')
        ax4.tick_params(axis='y', labelcolor='#8e44ad')
        ax4_twin.tick_params(axis='y', labelcolor='#95a5a6')
        
        # Add yield line
        if yield_pred is not None:
            final_date = biomass_df['date'].iloc[-1]
            grain_yield = yield_pred
            ax4.axhline(y=grain_yield, color='red', linestyle='--', linewidth=2.5,
                       label=f'Grain Yield: {grain_yield:.2f} ton/ha', alpha=0.8)
            ax4.text(biomass_df['date'].iloc[len(biomass_df)//2], grain_yield + 0.2,
                    f'Yield: {grain_yield:.2f} ton/ha', fontsize=11, fontweight='bold',
                    color='red', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    else:
        ax4.text(0.5, 0.5, 'No biomass data available', transform=ax4.transAxes,
                fontsize=12, ha='center', va='center',
                bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))
    
    ax4.set_xlabel('Date', fontsize=12, fontweight='bold')
    ax4.set_title('Biomass Accumulation & Yield', fontsize=13, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    ax4.legend(loc='upper left', fontsize=10)
    if biomass_df is not None:
        ax4_twin.legend(loc='upper right', fontsize=9)
    
    # ===== Plot 5: Combined View =====
    ax5 = fig.add_subplot(gs[2, :])
    
    # NDVI (left y-axis)
    ax5_ndvi = ax5
    ax5_ndvi.plot(arps_df['date'], arps_df['ndvi'], 'o-', color='#2ecc71', 
                 linewidth=2, markersize=3, label='NDVI', alpha=0.8)
    ax5_ndvi.set_ylabel('NDVI', fontsize=12, fontweight='bold', color='#2ecc71')
    ax5_ndvi.tick_params(axis='y', labelcolor='#2ecc71')
    ax5_ndvi.set_ylim([0, 1])
    
    # fAPAR (secondary y-axis)
    ax5_fapar = ax5_ndvi.twinx()
    ax5_fapar.plot(arps_df['date'], arps_df['fapar'], 's-', color='#3498db', 
                  linewidth=2, markersize=3, label='fAPAR', alpha=0.8)
    ax5_fapar.set_ylabel('fAPAR', fontsize=12, fontweight='bold', color='#3498db')
    ax5_fapar.tick_params(axis='y', labelcolor='#3498db')
    ax5_fapar.set_ylim([0, 1])
    
    ax5.set_xlabel('Date', fontsize=12, fontweight='bold')
    ax5.set_title('NDVI & fAPAR Combined View', fontsize=13, fontweight='bold')
    ax5.grid(True, alpha=0.3)
    
    # Combined legend
    lines1, labels1 = ax5_ndvi.get_legend_handles_labels()
    lines2, labels2 = ax5_fapar.get_legend_handles_labels()
    ax5_ndvi.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=10)
    
    if sowing_date:
        ax5.axvline(pd.to_datetime(sowing_date), color='orange', linestyle='--', 
                   linewidth=2, alpha=0.7, label='Sowing')
    
    # Main title
    title_text = f'{field_name}\n'
    if sowing_date:
        title_text += f'Sowing Date: {sowing_date} | '
    if yield_pred is not None:
        title_text += f'Predicted Yield: {yield_pred:.2f} ton/ha'
    else:
        title_text += 'Yield: N/A'
    
    plt.suptitle(title_text, fontsize=16, fontweight='bold', y=0.995)
    
    # Save figure
    safe_filename = field_name.replace(' ', '_').replace('/', '_').replace('.', '_')
    output_path = os.path.join(output_dir, f'field_plot_{safe_filename}.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return True


def main():
    """Create plots for all fields."""
    
    print("=" * 80)
    print("CREATING INDIVIDUAL FIELD PLOTS")
    print("=" * 80)
    
    # Load yield predictions to get list of all fields
    df = pd.read_csv('yield_predictions_arps_all_fields.csv')
    field_names = df['Field Name'].unique()
    
    print(f"\nTotal fields to process: {len(field_names)}")
    print("Creating plots...")
    
    success_count = 0
    failed_fields = []
    
    for i, field_name in enumerate(field_names, 1):
        print(f"\n{i}/{len(field_names)}: {field_name}")
        
        try:
            success = create_field_plot(field_name, df[df['Field Name'] == field_name].iloc[0])
            if success:
                success_count += 1
                print(f"  ✓ Plot created")
            else:
                failed_fields.append(field_name)
        except Exception as e:
            print(f"  ✗ Error: {e}")
            failed_fields.append(field_name)
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\n✓ Successfully created plots for {success_count}/{len(field_names)} fields")
    
    if failed_fields:
        print(f"\n⚠️  Failed fields ({len(failed_fields)}):")
        for field in failed_fields:
            print(f"  - {field}")
    
    print(f"\n✓ All plots saved to: field_plots/")
    print("=" * 80)


if __name__ == "__main__":
    main()


