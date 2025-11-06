"""
Compare NDVI data quality between Sentinel-2 and ARPS.
No yield prediction needed - just comparing the raw NDVI time series.
"""

import json
import os
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import pandas as pd


def load_sentinel2_ndvi(field_name):
    """Load Sentinel-2 NDVI for a field."""
    # Load from cleaned data
    with open('sentinel_ndvi_fapar_data_cleaned.json', 'r') as f:
        data = json.load(f)
    
    if field_name in data['fields']:
        field_data = data['fields'][field_name]
        dates = []
        ndvi_values = []
        
        for obs in field_data['ndvi_time_series']:
            # Use the 'from' date for weekly data
            dates.append(obs['from'])
            ndvi_values.append(obs['ndvi_mean'])
        
        return dates, ndvi_values
    
    return None, None


def load_arps_ndvi(field_name):
    """Load ARPS NDVI for a field."""
    # Try different filename formats
    filename_options = [
        f"arps_ndvi_data_cleaned/arps_ndvi_{field_name.replace(' ', '_')}.json",
        f"more_fields/arps_ndvi_data_cleaned/arps_ndvi_{field_name.replace(' ', '_')}.json"
    ]
    
    for filepath in filename_options:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            dates = [obs['date'] for obs in data['observations']]
            ndvi_values = [obs['ndvi_mean'] for obs in data['observations']]
            
            return dates, ndvi_values
    
    return None, None


def compare_field_ndvi(field_name):
    """Compare NDVI between Sentinel-2 and ARPS for a single field."""
    # Load data
    s2_dates, s2_ndvi = load_sentinel2_ndvi(field_name)
    arps_dates, arps_ndvi = load_arps_ndvi(field_name)
    
    if s2_dates is None or arps_dates is None:
        return None
    
    # Convert to datetime
    s2_dt = [datetime.strptime(d, '%Y-%m-%d') for d in s2_dates]
    arps_dt = [datetime.strptime(d, '%Y-%m-%d') for d in arps_dates]
    
    # Calculate statistics
    comparison = {
        'field_name': field_name,
        's2_observations': len(s2_dates),
        'arps_observations': len(arps_dates),
        's2_mean_ndvi': np.mean(s2_ndvi),
        's2_std_ndvi': np.std(s2_ndvi),
        's2_min_ndvi': np.min(s2_ndvi),
        's2_max_ndvi': np.max(s2_ndvi),
        'arps_mean_ndvi': np.mean(arps_ndvi),
        'arps_std_ndvi': np.std(arps_ndvi),
        'arps_min_ndvi': np.min(arps_ndvi),
        'arps_max_ndvi': np.max(arps_ndvi),
        'observation_ratio': len(arps_dates) / len(s2_dates),
        's2_dates': s2_dates,
        's2_ndvi': s2_ndvi,
        'arps_dates': arps_dates,
        'arps_ndvi': arps_ndvi
    }
    
    return comparison


def plot_field_comparison(comparison, output_dir='ndvi_comparisons'):
    """Plot NDVI comparison for a single field."""
    os.makedirs(output_dir, exist_ok=True)
    
    field_name = comparison['field_name']
    
    # Convert dates
    s2_dt = [datetime.strptime(d, '%Y-%m-%d') for d in comparison['s2_dates']]
    arps_dt = [datetime.strptime(d, '%Y-%m-%d') for d in comparison['arps_dates']]
    
    # Create figure
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10))
    
    # Plot 1: Time series
    ax1.plot(s2_dt, comparison['s2_ndvi'], 'o-', label='Sentinel-2 (10m, ~5-day)', 
             markersize=10, linewidth=2.5, alpha=0.8, color='steelblue', zorder=3)
    ax1.plot(arps_dt, comparison['arps_ndvi'], 'o-', label='ARPS (3m, daily)', 
             markersize=3, linewidth=1, alpha=0.7, color='#2ecc71')
    
    ax1.set_xlabel('Date', fontsize=12, fontweight='bold')
    ax1.set_ylabel('NDVI', fontsize=12, fontweight='bold')
    ax1.set_title(f'NDVI Time Series Comparison: {field_name}\n' + 
                 f'Sentinel-2: {comparison["s2_observations"]} obs | ARPS: {comparison["arps_observations"]} obs | ' +
                 f'Improvement: {comparison["observation_ratio"]:.1f}x',
                 fontsize=14, fontweight='bold', pad=20)
    ax1.legend(fontsize=11, loc='best')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(0, 1)
    
    # Plot 2: Distribution
    ax2.hist(comparison['s2_ndvi'], bins=20, alpha=0.7, label='Sentinel-2', 
            color='steelblue', edgecolor='black')
    ax2.hist(comparison['arps_ndvi'], bins=20, alpha=0.6, label='ARPS', 
            color='#2ecc71', edgecolor='black')
    
    ax2.axvline(comparison['s2_mean_ndvi'], color='steelblue', linestyle='--', linewidth=2.5,
               label=f'S2 Mean: {comparison["s2_mean_ndvi"]:.3f}')
    ax2.axvline(comparison['arps_mean_ndvi'], color='#2ecc71', linestyle='--', linewidth=2.5,
               label=f'ARPS Mean: {comparison["arps_mean_ndvi"]:.3f}')
    
    ax2.set_xlabel('NDVI Value', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Frequency', fontsize=12, fontweight='bold')
    ax2.set_title('NDVI Distribution', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    filename = f"{output_dir}/ndvi_comparison_{field_name.replace(' ', '_')}.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
    
    return filename


def main():
    """Main comparison function."""
    print("=" * 80)
    print("NDVI DATA QUALITY COMPARISON: SENTINEL-2 vs ARPS")
    print("=" * 80)
    
    # Load Sentinel-2 data to get field names
    with open('sentinel_ndvi_fapar_data_cleaned.json', 'r') as f:
        s2_data = json.load(f)
    
    field_names = list(s2_data['fields'].keys())
    
    print(f"\nProcessing {len(field_names)} fields...")
    
    comparisons = []
    successful = 0
    
    for i, field_name in enumerate(field_names, 1):
        print(f"\n{i}/{len(field_names)}: {field_name}")
        
        comparison = compare_field_ndvi(field_name)
        
        if comparison:
            comparisons.append(comparison)
            successful += 1
            print(f"  ✓ Sentinel-2: {comparison['s2_observations']} obs, ARPS: {comparison['arps_observations']} obs")
            print(f"  📊 ARPS provides {comparison['observation_ratio']:.1f}x more data")
        else:
            print(f"  ✗ Could not load data for comparison")
    
    if not comparisons:
        print("\n❌ No fields could be compared")
        return
    
    # Create summary statistics
    print("\n" + "=" * 80)
    print("OVERALL COMPARISON STATISTICS")
    print("=" * 80)
    
    df = pd.DataFrame([{
        'Field Name': c['field_name'],
        'S2 Observations': c['s2_observations'],
        'ARPS Observations': c['arps_observations'],
        'Obs Ratio': c['observation_ratio'],
        'S2 Mean NDVI': c['s2_mean_ndvi'],
        'ARPS Mean NDVI': c['arps_mean_ndvi'],
        'NDVI Difference': c['arps_mean_ndvi'] - c['s2_mean_ndvi']
    } for c in comparisons])
    
    print(f"\nFields compared: {len(comparisons)}")
    print(f"\nSentinel-2:")
    print(f"  Average observations: {df['S2 Observations'].mean():.1f}")
    print(f"  Average NDVI: {df['S2 Mean NDVI'].mean():.3f}")
    
    print(f"\nARPS:")
    print(f"  Average observations: {df['ARPS Observations'].mean():.1f}")
    print(f"  Average NDVI: {df['ARPS Mean NDVI'].mean():.3f}")
    
    print(f"\nImprovement:")
    print(f"  Average observation ratio: {df['Obs Ratio'].mean():.1f}x")
    print(f"  Mean NDVI difference: {df['NDVI Difference'].mean():.3f}")
    print(f"  Correlation: {df['S2 Mean NDVI'].corr(df['ARPS Mean NDVI']):.3f}")
    
    # Save comparison CSV
    df.to_csv('ndvi_comparison_sentinel2_vs_arps.csv', index=False)
    print(f"\n✓ Saved comparison to ndvi_comparison_sentinel2_vs_arps.csv")
    
    # Plot sample fields
    print(f"\n{'=' * 80}")
    print("CREATING VISUALIZATIONS")
    print('=' * 80)
    
    # Plot top 5 and bottom 5 by yield (if we have yield data), otherwise by NDVI
    df_sorted = df.sort_values('ARPS Mean NDVI', ascending=False)
    sample_fields = list(df_sorted.head(3)['Field Name']) + list(df_sorted.tail(3)['Field Name'])
    
    print(f"\nCreating detailed plots for {len(sample_fields)} sample fields...")
    
    for field in sample_fields:
        comparison = next(c for c in comparisons if c['field_name'] == field)
        filename = plot_field_comparison(comparison)
        print(f"  ✓ {field}")
    
    # Create overall summary plot
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Observation count comparison
    ax = axes[0, 0]
    ax.scatter(df['S2 Observations'], df['ARPS Observations'], 
              alpha=0.6, s=80, c='steelblue', edgecolors='black')
    ax.plot([0, df['S2 Observations'].max()], [0, df['S2 Observations'].max()], 
           'r--', linewidth=2, alpha=0.7, label='1:1 line')
    ax.set_xlabel('Sentinel-2 Observations', fontsize=11, fontweight='bold')
    ax.set_ylabel('ARPS Observations', fontsize=11, fontweight='bold')
    ax.set_title('Observation Count Comparison', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 2. Mean NDVI comparison
    ax = axes[0, 1]
    ax.scatter(df['S2 Mean NDVI'], df['ARPS Mean NDVI'], 
              alpha=0.6, s=80, c='#2ecc71', edgecolors='black')
    ax.plot([0, 1], [0, 1], 'r--', linewidth=2, alpha=0.7, label='1:1 line')
    ax.set_xlabel('Sentinel-2 Mean NDVI', fontsize=11, fontweight='bold')
    ax.set_ylabel('ARPS Mean NDVI', fontsize=11, fontweight='bold')
    ax.set_title(f'Mean NDVI Comparison (r={df["S2 Mean NDVI"].corr(df["ARPS Mean NDVI"]):.3f})', 
                fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    
    # 3. Observation ratio distribution
    ax = axes[1, 0]
    ax.hist(df['Obs Ratio'], bins=15, alpha=0.7, color='coral', edgecolor='black')
    ax.axvline(df['Obs Ratio'].mean(), color='red', linestyle='--', linewidth=2.5,
              label=f'Mean: {df["Obs Ratio"].mean():.1f}x')
    ax.set_xlabel('Observation Ratio (ARPS/S2)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Frequency', fontsize=11, fontweight='bold')
    ax.set_title('Temporal Resolution Improvement', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # 4. NDVI difference distribution
    ax = axes[1, 1]
    ax.hist(df['NDVI Difference'], bins=15, alpha=0.7, color='lightblue', edgecolor='black')
    ax.axvline(0, color='red', linestyle='--', linewidth=2, label='Zero difference')
    ax.axvline(df['NDVI Difference'].mean(), color='green', linestyle='-', linewidth=2.5,
              label=f'Mean: {df["NDVI Difference"].mean():.3f}')
    ax.set_xlabel('NDVI Difference (ARPS - S2)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Frequency', fontsize=11, fontweight='bold')
    ax.set_title('Mean NDVI Difference Distribution', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.suptitle(f'NDVI Comparison: Sentinel-2 vs ARPS - {len(comparisons)} Fields',
                fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig('ndvi_comparison_summary.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"\n✓ Saved summary visualization to ndvi_comparison_summary.png")
    
    print("\n" + "=" * 80)
    print("✅ NDVI COMPARISON COMPLETE")
    print("=" * 80)
    print("\nKey findings:")
    print(f"  • ARPS provides {df['Obs Ratio'].mean():.1f}x more temporal data")
    print(f"  • High correlation (r={df['S2 Mean NDVI'].corr(df['ARPS Mean NDVI']):.3f}) between sensors")
    print(f"  • Mean NDVI difference: {df['NDVI Difference'].mean():.3f}")
    print("=" * 80)


if __name__ == "__main__":
    main()

