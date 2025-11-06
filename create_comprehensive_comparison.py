"""
Create comprehensive comparison visualization:
1. Sentinel-2 vs ARPS yield predictions for 80 fields
2. NDVI time series comparisons for example fields
3. fAPAR time series comparisons for example fields
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import json
from datetime import datetime
import os


def load_ndvi_data(field_name, data_source='sentinel2'):
    """Load NDVI time series data for a field."""
    if data_source == 'sentinel2':
        # Try to load from sentinel NDVI data
        try:
            with open('sentinel_ndvi_fapar_data_cleaned.json', 'r') as f:
                data = json.load(f)
                for field_data in data['fields']:
                    if field_data['field_name'] == field_name:
                        observations = field_data.get('observations', [])
                        dates = [obs['date'] for obs in observations]
                        ndvi = [obs.get('ndvi_mean', obs.get('ndvi', np.nan)) for obs in observations]
                        return pd.DataFrame({'date': dates, 'ndvi': ndvi})
        except:
            pass
    elif data_source == 'arps':
        # Try to load from ARPS data
        arps_path = f"arps_ndvi_data_cleaned/arps_ndvi_{field_name.replace(' ', '_')}.json"
        if os.path.exists(arps_path):
            with open(arps_path, 'r') as f:
                data = json.load(f)
                observations = data.get('observations', [])
                dates = [obs['date'] for obs in observations]
                ndvi = [obs.get('ndvi_mean', np.nan) for obs in observations]
                return pd.DataFrame({'date': dates, 'ndvi': ndvi})
    
    return None


def calculate_fapar(ndvi):
    """Convert NDVI to fAPAR."""
    if pd.isna(ndvi):
        return np.nan
    return 0.013 * np.exp(4.48 * ndvi)


def main():
    """Create comprehensive comparison visualization."""
    
    print("=" * 80)
    print("CREATING COMPREHENSIVE SENTINEL-2 VS ARPS COMPARISON")
    print("=" * 80)
    
    # Load yield predictions
    print("\n1. Loading yield predictions...")
    
    # Try to load Sentinel-2 predictions
    s2_df = None
    s2_files = [
        'yield_predictions_all_80_fields_cleaned_final.csv',
        'yield_predictions_all_80_fields_final.csv',
        'yield_predictions_cleaned_all68.csv'
    ]
    
    for filename in s2_files:
        if os.path.exists(filename):
            try:
                s2_df = pd.read_csv(filename)
                if 'Grain Yield (ton/ha)' in s2_df.columns:
                    s2_df = s2_df.rename(columns={'Grain Yield (ton/ha)': 'Yield_S2'})
                    print(f"   ✓ Loaded Sentinel-2 predictions from {filename}")
                    break
            except:
                continue
    
    # Load ARPS predictions
    arps_df = pd.read_csv('yield_predictions_arps_all_fields.csv')
    arps_df = arps_df.rename(columns={'Grain Yield (ton/ha)': 'Yield_ARPS'})
    print(f"   ✓ Loaded ARPS predictions: {len(arps_df)} fields")
    
    if s2_df is None:
        print("   ✗ Could not find Sentinel-2 predictions")
        return
    
    # Merge on field name
    comparison_df = pd.merge(
        s2_df[['Field Name', 'Yield_S2']],
        arps_df[['Field Name', 'Yield_ARPS']],
        on='Field Name',
        how='inner'
    )
    
    print(f"   ✓ {len(comparison_df)} fields with both predictions")
    
    # Calculate statistics
    comparison_df['Difference'] = comparison_df['Yield_ARPS'] - comparison_df['Yield_S2']
    correlation = comparison_df['Yield_S2'].corr(comparison_df['Yield_ARPS'])
    rmse = np.sqrt(((comparison_df['Yield_ARPS'] - comparison_df['Yield_S2'])**2).mean())
    
    # Create comprehensive figure
    fig = plt.figure(figsize=(22, 14))
    gs = fig.add_gridspec(4, 3, hspace=0.35, wspace=0.3)
    
    # ===== ROW 1: Yield Comparison Plots =====
    
    # 1.1 Scatter plot
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.scatter(comparison_df['Yield_S2'], comparison_df['Yield_ARPS'], 
               alpha=0.7, s=100, c='steelblue', edgecolors='black', linewidth=0.8, zorder=3)
    min_val = min(comparison_df['Yield_S2'].min(), comparison_df['Yield_ARPS'].min())
    max_val = max(comparison_df['Yield_S2'].max(), comparison_df['Yield_ARPS'].max())
    ax1.plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=2.5, label='1:1 line', alpha=0.8)
    z = np.polyfit(comparison_df['Yield_S2'], comparison_df['Yield_ARPS'], 1)
    p = np.poly1d(z)
    ax1.plot(comparison_df['Yield_S2'].sort_values(), p(comparison_df['Yield_S2'].sort_values()), 
            "g-", alpha=0.7, linewidth=2, label=f'Fit: y={z[0]:.2f}x+{z[1]:.2f}')
    ax1.set_xlabel('Sentinel-2 Yield (ton/ha)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('ARPS Yield (ton/ha)', fontsize=12, fontweight='bold')
    ax1.set_title(f'Yield Comparison\nCorrelation: {correlation:.3f}, RMSE: {rmse:.2f} ton/ha', 
                 fontsize=13, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # 1.2 Box plot
    ax2 = fig.add_subplot(gs[0, 1])
    bp = ax2.boxplot([comparison_df['Yield_S2'], comparison_df['Yield_ARPS']], 
                     labels=['Sentinel-2\n(10m, ~5-day)', 'ARPS\n(3m, daily)'],
                     patch_artist=True,
                     medianprops=dict(color='red', linewidth=2.5),
                     boxprops=dict(facecolor='lightblue', alpha=0.7, linewidth=1.5),
                     whiskerprops=dict(linewidth=1.5),
                     capprops=dict(linewidth=1.5))
    ax2.set_ylabel('Yield (ton/ha)', fontsize=12, fontweight='bold')
    ax2.set_title('Yield Distribution Comparison', fontsize=13, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')
    
    # 1.3 Difference histogram
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.hist(comparison_df['Difference'], bins=25, alpha=0.7, color='coral', edgecolor='black', linewidth=1)
    ax3.axvline(0, color='red', linestyle='--', linewidth=2.5, label='Zero difference')
    ax3.axvline(comparison_df['Difference'].mean(), color='green', linestyle='-', linewidth=2.5,
               label=f'Mean: {comparison_df["Difference"].mean():.2f} ton/ha')
    ax3.set_xlabel('Difference (ARPS - S2) ton/ha', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Frequency', fontsize=12, fontweight='bold')
    ax3.set_title('Yield Difference Distribution', fontsize=13, fontweight='bold')
    ax3.legend(fontsize=10)
    ax3.grid(True, alpha=0.3, axis='y')
    
    # ===== ROW 2-3: NDVI and fAPAR Time Series =====
    
    # Select example fields (diverse yields)
    example_fields = [
        comparison_df.nsmallest(1, 'Yield_S2')['Field Name'].iloc[0],  # Low yield
        comparison_df.nlargest(1, 'Yield_S2')['Field Name'].iloc[0],    # High yield
        comparison_df.iloc[len(comparison_df)//2]['Field Name']          # Medium yield
    ]
    
    print(f"\n2. Creating NDVI/fAPAR comparisons for example fields:")
    
    for i, field_name in enumerate(example_fields):
        print(f"   {i+1}. {field_name}")
        
        # Load NDVI data
        s2_ndvi = load_ndvi_data(field_name, 'sentinel2')
        arps_ndvi = load_ndvi_data(field_name, 'arps')
        
        # NDVI plot
        ax_ndvi = fig.add_subplot(gs[1, i])
        
        if s2_ndvi is not None:
            s2_ndvi['date'] = pd.to_datetime(s2_ndvi['date'])
            s2_ndvi = s2_ndvi.sort_values('date')
            ax_ndvi.plot(s2_ndvi['date'], s2_ndvi['ndvi'], 'o-', color='steelblue', 
                       linewidth=2, markersize=6, label='Sentinel-2', alpha=0.8)
        
        if arps_ndvi is not None:
            arps_ndvi['date'] = pd.to_datetime(arps_ndvi['date'])
            arps_ndvi = arps_ndvi.sort_values('date')
            ax_ndvi.plot(arps_ndvi['date'], arps_ndvi['ndvi'], 'o-', color='#2ecc71', 
                       linewidth=2, markersize=4, label='ARPS', alpha=0.8)
        
        ax_ndvi.set_ylabel('NDVI', fontsize=11, fontweight='bold')
        ax_ndvi.set_title(f'NDVI Time Series\n{field_name}', fontsize=11, fontweight='bold')
        ax_ndvi.legend(fontsize=9)
        ax_ndvi.grid(True, alpha=0.3)
        ax_ndvi.set_ylim([0, 1])
        
        # fAPAR plot
        ax_fapar = fig.add_subplot(gs[2, i])
        
        if s2_ndvi is not None:
            s2_fapar = s2_ndvi.copy()
            s2_fapar['fapar'] = s2_fapar['ndvi'].apply(calculate_fapar)
            ax_fapar.plot(s2_fapar['date'], s2_fapar['fapar'], 'o-', color='steelblue', 
                        linewidth=2, markersize=6, label='Sentinel-2', alpha=0.8)
        
        if arps_ndvi is not None:
            arps_fapar = arps_ndvi.copy()
            arps_fapar['fapar'] = arps_fapar['ndvi'].apply(calculate_fapar)
            ax_fapar.plot(arps_fapar['date'], arps_fapar['fapar'], 'o-', color='#2ecc71', 
                        linewidth=2, markersize=4, label='ARPS', alpha=0.8)
        
        ax_fapar.set_xlabel('Date', fontsize=11, fontweight='bold')
        ax_fapar.set_ylabel('fAPAR', fontsize=11, fontweight='bold')
        ax_fapar.set_title(f'fAPAR Time Series\n{field_name}', fontsize=11, fontweight='bold')
        ax_fapar.legend(fontsize=9)
        ax_fapar.grid(True, alpha=0.3)
        ax_fapar.set_ylim([0, 1])
    
    # ===== ROW 4: Ranked Comparison =====
    
    ax4 = fig.add_subplot(gs[3, :])
    comparison_df = comparison_df.sort_values('Yield_S2')
    x = np.arange(len(comparison_df))
    width = 0.35
    
    ax4.bar(x - width/2, comparison_df['Yield_S2'], width, label='Sentinel-2', 
           alpha=0.8, color='steelblue', edgecolor='black', linewidth=0.5)
    ax4.bar(x + width/2, comparison_df['Yield_ARPS'], width, label='ARPS', 
           alpha=0.8, color='#2ecc71', edgecolor='black', linewidth=0.5)
    
    ax4.set_xlabel('Field (ordered by Sentinel-2 yield)', fontsize=12, fontweight='bold')
    ax4.set_ylabel('Yield (ton/ha)', fontsize=12, fontweight='bold')
    ax4.set_title(f'Field-by-Field Comparison - All {len(comparison_df)} Fields', 
                 fontsize=14, fontweight='bold')
    ax4.legend(fontsize=12, loc='upper left')
    ax4.grid(True, alpha=0.3, axis='y')
    ax4.set_xticks([])
    
    # Add statistics text box
    stats_text = (f'Statistics:\n'
                 f'Mean S2: {comparison_df["Yield_S2"].mean():.2f} ton/ha\n'
                 f'Mean ARPS: {comparison_df["Yield_ARPS"].mean():.2f} ton/ha\n'
                 f'Correlation: {correlation:.3f}\n'
                 f'RMSE: {rmse:.2f} ton/ha')
    ax4.text(0.02, 0.98, stats_text, transform=ax4.transAxes, 
            fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    # Main title
    plt.suptitle('Comprehensive Sentinel-2 vs ARPS Comparison - 80 Fields',
                fontsize=18, fontweight='bold', y=0.995)
    
    # Save
    output_file = 'sentinel2_vs_arps_comprehensive_comparison.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Saved comprehensive comparison to: {output_file}")
    
    output_pdf = 'sentinel2_vs_arps_comprehensive_comparison.pdf'
    plt.savefig(output_pdf, bbox_inches='tight')
    print(f"✓ Saved PDF to: {output_pdf}")
    
    plt.close()
    
    # Print summary statistics
    print("\n" + "=" * 80)
    print("COMPARISON SUMMARY")
    print("=" * 80)
    print(f"\nFields compared: {len(comparison_df)}")
    print(f"\nSentinel-2 Statistics:")
    print(f"  Mean: {comparison_df['Yield_S2'].mean():.2f} ton/ha")
    print(f"  Std: {comparison_df['Yield_S2'].std():.2f} ton/ha")
    print(f"  Range: {comparison_df['Yield_S2'].min():.2f} - {comparison_df['Yield_S2'].max():.2f} ton/ha")
    
    print(f"\nARPS Statistics:")
    print(f"  Mean: {comparison_df['Yield_ARPS'].mean():.2f} ton/ha")
    print(f"  Std: {comparison_df['Yield_ARPS'].std():.2f} ton/ha")
    print(f"  Range: {comparison_df['Yield_ARPS'].min():.2f} - {comparison_df['Yield_ARPS'].max():.2f} ton/ha")
    
    print(f"\nComparison Metrics:")
    print(f"  Correlation: {correlation:.3f}")
    print(f"  RMSE: {rmse:.2f} ton/ha")
    print(f"  Mean difference (ARPS - S2): {comparison_df['Difference'].mean():.2f} ton/ha")
    print(f"  Std of difference: {comparison_df['Difference'].std():.2f} ton/ha")
    
    print("=" * 80)


if __name__ == "__main__":
    main()

