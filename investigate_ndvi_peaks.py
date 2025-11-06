"""
Investigate NDVI values == 1.0 in ARPS data.
This script analyzes when and why NDVI values reach exactly 1.0.
"""

import json
import os
import pandas as pd
import numpy as np
from collections import defaultdict
import matplotlib.pyplot as plt


def analyze_ndvi_peaks(field_name, arps_data):
    """Analyze NDVI peaks for a single field."""
    
    observations = arps_data.get('observations', [])
    if not observations:
        return None
    
    peaks = []
    
    for obs in observations:
        ndvi_mean = obs.get('ndvi_mean')
        
        # Check if NDVI is exactly 1.0 or very close (>= 0.99)
        if ndvi_mean is not None and (ndvi_mean == 1.0 or ndvi_mean >= 0.99):
            peak_info = {
                'date': obs.get('date'),
                'ndvi_mean': ndvi_mean,
                'ndvi_std': obs.get('ndvi_std'),
                'ndvi_min': obs.get('ndvi_min'),
                'ndvi_max': obs.get('ndvi_max'),
                'ndvi_p10': obs.get('ndvi_p10'),
                'ndvi_p25': obs.get('ndvi_p25'),
                'ndvi_p50': obs.get('ndvi_p50'),
                'ndvi_p75': obs.get('ndvi_p75'),
                'ndvi_p90': obs.get('ndvi_p90'),
                'sample_count': obs.get('sample_count')
            }
            peaks.append(peak_info)
    
    return peaks


def main():
    """Investigate NDVI peaks across all fields."""
    
    print("=" * 80)
    print("INVESTIGATING NDVI PEAKS (== 1.0) IN ARPS DATA")
    print("=" * 80)
    
    # Find all ARPS data files
    arps_dirs = [
        'arps_ndvi_data_cleaned',
        'more_fields/arps_ndvi_data_cleaned'
    ]
    
    all_fields_with_peaks = []
    all_peak_details = []
    
    for arps_dir in arps_dirs:
        if not os.path.exists(arps_dir):
            continue
        
        print(f"\nScanning {arps_dir}...")
        
        for filename in os.listdir(arps_dir):
            if not filename.endswith('.json'):
                continue
            
            field_name = filename.replace('arps_ndvi_', '').replace('.json', '').replace('_', ' ')
            
            arps_path = os.path.join(arps_dir, filename)
            
            try:
                with open(arps_path, 'r') as f:
                    arps_data = json.load(f)
                
                peaks = analyze_ndvi_peaks(field_name, arps_data)
                
                if peaks:
                    all_fields_with_peaks.append({
                        'field_name': field_name,
                        'peak_count': len(peaks),
                        'peaks': peaks
                    })
                    
                    for peak in peaks:
                        all_peak_details.append({
                            'field_name': field_name,
                            **peak
                        })
                    
                    print(f"  ⚠️  {field_name}: {len(peaks)} peak(s) found")
            
            except Exception as e:
                print(f"  ✗ Error reading {filename}: {e}")
    
    print("\n" + "=" * 80)
    print("SUMMARY OF FINDINGS")
    print("=" * 80)
    
    print(f"\nTotal fields with NDVI >= 0.99: {len(all_fields_with_peaks)}")
    print(f"Total peak observations: {len(all_peak_details)}")
    
    if not all_peak_details:
        print("\n✓ No NDVI peaks (>= 0.99) found in ARPS data!")
        return
    
    # Create detailed analysis DataFrame
    df = pd.DataFrame(all_peak_details)
    
    # Analysis 1: Field distribution
    print("\n" + "-" * 80)
    print("FIELDS WITH PEAKS:")
    print("-" * 80)
    field_counts = df.groupby('field_name').size().sort_values(ascending=False)
    for field, count in field_counts.items():
        print(f"  {field}: {count} peak observation(s)")
    
    # Analysis 2: Date distribution
    print("\n" + "-" * 80)
    print("DATE DISTRIBUTION OF PEAKS:")
    print("-" * 80)
    df['date'] = pd.to_datetime(df['date'])
    date_counts = df.groupby(df['date'].dt.date).size().sort_values(ascending=False)
    print(f"\nTop 10 dates with most peaks:")
    for date, count in date_counts.head(10).items():
        print(f"  {date}: {count} peak(s)")
    
    # Analysis 3: Statistical analysis of peak observations
    print("\n" + "-" * 80)
    print("STATISTICAL ANALYSIS OF PEAK OBSERVATIONS:")
    print("-" * 80)
    
    print(f"\nNDVI Statistics:")
    print(f"  Mean NDVI: {df['ndvi_mean'].mean():.4f}")
    print(f"  Min NDVI: {df['ndvi_mean'].min():.4f}")
    print(f"  Max NDVI: {df['ndvi_mean'].max():.4f}")
    print(f"  Fields with NDVI == 1.0 exactly: {(df['ndvi_mean'] == 1.0).sum()}")
    print(f"  Fields with NDVI >= 0.99: {len(df)}")
    
    print(f"\nPixel Statistics (where available):")
    if 'ndvi_std' in df.columns:
        print(f"  Mean std dev: {df['ndvi_std'].mean():.4f}")
        print(f"  Min std dev: {df['ndvi_std'].min():.4f}")
        print(f"  Max std dev: {df['ndvi_std'].max():.4f}")
    
    if 'sample_count' in df.columns:
        print(f"  Mean sample count: {df['sample_count'].mean():.0f}")
        print(f"  Min sample count: {df['sample_count'].min()}")
        print(f"  Max sample count: {df['sample_count'].max()}")
    
    # Analysis 4: Check if peaks are clustered
    print("\n" + "-" * 80)
    print("PIXEL STATISTICS ANALYSIS:")
    print("-" * 80)
    
    # Check if min/max values are also 1.0
    if 'ndvi_min' in df.columns and 'ndvi_max' in df.columns:
        all_pixels_max = (df['ndvi_max'] == 1.0).sum()
        all_pixels_min = (df['ndvi_min'] == 1.0).sum()
        print(f"  Observations where max pixel == 1.0: {all_pixels_max}")
        print(f"  Observations where min pixel == 1.0: {all_pixels_min}")
        print(f"  Observations where all pixels == 1.0: {((df['ndvi_min'] == 1.0) & (df['ndvi_max'] == 1.0)).sum()}")
    
    # Analysis 5: Percentile analysis
    print("\n" + "-" * 80)
    print("PERCENTILE ANALYSIS:")
    print("-" * 80)
    
    if 'ndvi_p50' in df.columns:
        p50_equals_1 = (df['ndvi_p50'] == 1.0).sum()
        p75_equals_1 = (df['ndvi_p75'] == 1.0).sum() if 'ndvi_p75' in df.columns else 0
        p90_equals_1 = (df['ndvi_p90'] == 1.0).sum() if 'ndvi_p90' in df.columns else 0
        
        print(f"  Observations where median (p50) == 1.0: {p50_equals_1}")
        print(f"  Observations where p75 == 1.0: {p75_equals_1}")
        print(f"  Observations where p90 == 1.0: {p90_equals_1}")
    
    # Analysis 6: Detailed examples
    print("\n" + "-" * 80)
    print("DETAILED EXAMPLES OF PEAK OBSERVATIONS:")
    print("-" * 80)
    
    # Show first few examples
    print("\nFirst 5 peak observations:")
    for idx, row in df.head(5).iterrows():
        print(f"\n  Field: {row['field_name']}")
        print(f"  Date: {row['date']}")
        print(f"  NDVI mean: {row['ndvi_mean']:.4f}")
        if pd.notna(row.get('ndvi_std')):
            print(f"  NDVI std: {row['ndvi_std']:.4f}")
        if pd.notna(row.get('ndvi_min')) and pd.notna(row.get('ndvi_max')):
            print(f"  NDVI range: {row['ndvi_min']:.4f} - {row['ndvi_max']:.4f}")
        if pd.notna(row.get('sample_count')):
            print(f"  Sample count: {row['sample_count']}")
    
    # Analysis 7: Create visualization
    print("\n" + "-" * 80)
    print("CREATING VISUALIZATION...")
    print("-" * 80)
    
    if len(df) > 0:
        # Create visualization
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # 1. NDVI distribution
        ax1 = axes[0, 0]
        ax1.hist(df['ndvi_mean'], bins=20, edgecolor='black', alpha=0.7)
        ax1.axvline(1.0, color='red', linestyle='--', linewidth=2, label='NDVI = 1.0')
        ax1.set_xlabel('NDVI Value', fontweight='bold')
        ax1.set_ylabel('Frequency', fontweight='bold')
        ax1.set_title('Distribution of Peak NDVI Values', fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. Date distribution
        ax2 = axes[0, 1]
        date_counts = df.groupby(df['date'].dt.date).size()
        ax2.plot(date_counts.index, date_counts.values, 'o-', linewidth=2, markersize=6)
        ax2.set_xlabel('Date', fontweight='bold')
        ax2.set_ylabel('Number of Peak Observations', fontweight='bold')
        ax2.set_title('Peak Observations Over Time', fontweight='bold')
        ax2.tick_params(axis='x', rotation=45)
        ax2.grid(True, alpha=0.3)
        
        # 3. Field distribution
        ax3 = axes[1, 0]
        field_counts = df.groupby('field_name').size().sort_values(ascending=False).head(15)
        ax3.barh(range(len(field_counts)), field_counts.values)
        ax3.set_yticks(range(len(field_counts)))
        ax3.set_yticklabels(field_counts.index, fontsize=8)
        ax3.set_xlabel('Number of Peak Observations', fontweight='bold')
        ax3.set_title('Top 15 Fields with Most Peaks', fontweight='bold')
        ax3.grid(True, alpha=0.3, axis='x')
        
        # 4. Pixel statistics (if available)
        ax4 = axes[1, 1]
        if 'ndvi_std' in df.columns and df['ndvi_std'].notna().any():
            valid_std = df['ndvi_std'].dropna()
            ax4.hist(valid_std, bins=20, edgecolor='black', alpha=0.7, color='orange')
            ax4.set_xlabel('NDVI Standard Deviation', fontweight='bold')
            ax4.set_ylabel('Frequency', fontweight='bold')
            ax4.set_title('Standard Deviation of Peak Observations', fontweight='bold')
            ax4.grid(True, alpha=0.3)
        else:
            ax4.text(0.5, 0.5, 'No pixel statistics available', 
                    transform=ax4.transAxes, ha='center', va='center',
                    fontsize=12, bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))
        
        plt.suptitle('Analysis of NDVI Peaks (>= 0.99) in ARPS Data', 
                    fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        output_file = 'ndvi_peaks_analysis.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✓ Saved visualization to: {output_file}")
        
        plt.close()
    
    # Save detailed results
    df_sorted = df.sort_values(['field_name', 'date'])
    df_sorted.to_csv('ndvi_peaks_analysis.csv', index=False)
    print(f"✓ Saved detailed results to: ndvi_peaks_analysis.csv")
    
    # Save summary
    summary = {
        'total_fields_with_peaks': len(all_fields_with_peaks),
        'total_peak_observations': len(all_peak_details),
        'fields_affected': [f['field_name'] for f in all_fields_with_peaks],
        'peak_count_by_field': field_counts.to_dict() if len(field_counts) > 0 else {},
        'date_distribution': date_counts.to_dict() if len(date_counts) > 0 else {}
    }
    
    # Convert date objects to strings for JSON serialization
    summary['date_distribution'] = {str(k): int(v) for k, v in summary['date_distribution'].items()}
    
    with open('ndvi_peaks_summary.json', 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    print(f"✓ Saved summary to: ndvi_peaks_summary.json")
    
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    
    # Potential causes
    print("\n" + "-" * 80)
    print("POTENTIAL CAUSES OF NDVI = 1.0:")
    print("-" * 80)
    print("\n1. Data saturation/clipping:")
    print("   - Sensor may have saturated on very bright vegetation")
    print("   - Very dense, healthy vegetation can approach NDVI = 1.0")
    print("\n2. Data processing artifacts:")
    print("   - Possible clipping in ARPS processing pipeline")
    print("   - Quality flags or masked pixels")
    print("\n3. Cloud contamination:")
    print("   - Though unlikely, cloud edges can have high NDVI")
    print("   - Misclassified pixels")
    print("\n4. Field conditions:")
    print("   - Extremely dense, healthy wheat canopy")
    print("   - Peak growing season conditions")
    print("\n5. Pixel aggregation:")
    print("   - If all pixels in aggregation are high, mean could approach 1.0")
    print("   - Check pixel statistics (min, max, percentiles)")
    print("\n" + "-" * 80)


if __name__ == "__main__":
    main()

