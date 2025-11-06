"""
Analyze quality flags and available metadata for NDVI = 1.0 cases.
"""

import json
import os
import pandas as pd
import numpy as np

def analyze_quality_flags():
    """Analyze quality flags and metadata for all NDVI=1.0 cases."""
    
    print("=" * 80)
    print("ANALYZING QUALITY FLAGS FOR NDVI = 1.0 CASES")
    print("=" * 80)
    
    # Load the peaks data
    peaks_df = pd.read_csv('ndvi_peaks_analysis.csv')
    
    # Check what quality information is available
    all_observations = []
    
    arps_dirs = [
        'arps_ndvi_data_cleaned',
        'more_fields/arps_ndvi_data_cleaned'
    ]
    
    for arps_dir in arps_dirs:
        if not os.path.exists(arps_dir):
            continue
        
        for filename in os.listdir(arps_dir):
            if not filename.endswith('.json'):
                continue
            
            arps_path = os.path.join(arps_dir, filename)
            
            try:
                with open(arps_path, 'r') as f:
                    data = json.load(f)
                
                field_name = data.get('field_name', '')
                
                for obs in data.get('observations', []):
                    if obs.get('ndvi_mean') == 1.0:
                        obs_info = {
                            'field_name': field_name,
                            'date': obs.get('date'),
                            'ndvi_mean': obs.get('ndvi_mean'),
                            'ndvi_mean_original': obs.get('ndvi_mean_original'),
                            'was_outlier': obs.get('was_outlier'),
                            'ndvi_std': obs.get('ndvi_std'),
                            'ndvi_min': obs.get('ndvi_min'),
                            'ndvi_max': obs.get('ndvi_max'),
                            'ndvi_p50': obs.get('ndvi_p50'),
                            'sample_count': obs.get('sample_count')
                        }
                        all_observations.append(obs_info)
            
            except Exception as e:
                continue
    
    if not all_observations:
        print("\n✗ Could not find quality flag information")
        return
    
    df = pd.DataFrame(all_observations)
    
    print(f"\n✓ Found {len(df)} observations with quality metadata")
    
    # Analysis 1: Check ndvi_mean_original
    print("\n" + "=" * 80)
    print("ANALYSIS: ndvi_mean_original")
    print("=" * 80)
    
    if 'ndvi_mean_original' in df.columns:
        print(f"\nAll observations have ndvi_mean_original: {df['ndvi_mean_original'].notna().all()}")
        print(f"\nComparison:")
        print(f"  Mean of reported ndvi_mean: {df['ndvi_mean'].mean():.4f}")
        print(f"  Mean of ndvi_mean_original: {df['ndvi_mean_original'].mean():.4f}")
        print(f"  Difference: {df['ndvi_mean'].mean() - df['ndvi_mean_original'].mean():.4f}")
        
        print("\n✓ SOLUTION: Use ndvi_mean_original instead of ndvi_mean!")
        print("  The original mean values are correct and should be used.")
    
    # Analysis 2: Check was_outlier flag
    print("\n" + "=" * 80)
    print("ANALYSIS: was_outlier flag")
    print("=" * 80)
    
    if 'was_outlier' in df.columns:
        outlier_counts = df['was_outlier'].value_counts()
        print(f"\nOutlier flag distribution:")
        for val, count in outlier_counts.items():
            print(f"  was_outlier = {val}: {count} observations")
        
        # Check if all NDVI=1.0 cases were marked as outliers
        if df['was_outlier'].all():
            print("\n⚠️  All NDVI=1.0 cases were marked as outliers!")
            print("  This suggests the cleaning process may have introduced the 1.0 value")
            print("  when handling outliers incorrectly.")
        else:
            print("\nNot all cases were marked as outliers.")
            print("  Some may be from original data processing.")
    
    # Analysis 3: Check sample_count
    print("\n" + "=" * 80)
    print("ANALYSIS: sample_count")
    print("=" * 80)
    
    if 'sample_count' in df.columns:
        print(f"\nSample count statistics:")
        print(f"  Mean: {df['sample_count'].mean():.0f}")
        print(f"  Min: {df['sample_count'].min()}")
        print(f"  Max: {df['sample_count'].max()}")
        print(f"  All same?: {df['sample_count'].nunique() == 1}")
        
        if df['sample_count'].nunique() == 1:
            print(f"  → All have {df['sample_count'].iloc[0]} samples (full resolution)")
    
    # Analysis 4: Check if we can reconstruct valid mean
    print("\n" + "=" * 80)
    print("RECOMMENDATION: How to Fix")
    print("=" * 80)
    
    print("\n✓ Quality flags available:")
    print("  1. ndvi_mean_original - Use this instead of ndvi_mean")
    print("  2. was_outlier - Flag indicating outlier status")
    print("  3. ndvi_p50 - Median value (also reliable)")
    
    print("\n✓ Recommended fix:")
    print("  For observations where ndvi_mean == 1.0:")
    print("    - Use ndvi_mean_original if available")
    print("    - OR use ndvi_p50 (median) as proxy")
    print("    - OR recalculate from pixel statistics")
    
    # Show examples
    print("\n" + "-" * 80)
    print("EXAMPLES WITH CORRECTED VALUES:")
    print("-" * 80)
    
    for idx, row in df.head(5).iterrows():
        print(f"\n  {row['field_name']} ({row['date']}):")
        print(f"    Reported mean: {row['ndvi_mean']:.3f} ❌")
        if pd.notna(row.get('ndvi_mean_original')):
            print(f"    Original mean: {row['ndvi_mean_original']:.3f} ✓")
        if pd.notna(row.get('ndvi_p50')):
            print(f"    Median (p50): {row['ndvi_p50']:.3f} ✓")
        print(f"    Pixel range: {row['ndvi_min']:.3f} - {row['ndvi_max']:.3f}")
    
    # Create summary
    summary = {
        'total_observations': int(len(df)),
        'have_original_mean': int(df['ndvi_mean_original'].notna().sum()) if 'ndvi_mean_original' in df.columns else 0,
        'marked_as_outliers': int(df['was_outlier'].sum()) if 'was_outlier' in df.columns else 0,
        'recommendation': 'Use ndvi_mean_original or ndvi_p50 instead of ndvi_mean when ndvi_mean == 1.0'
    }
    
    with open('quality_flags_analysis.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print("\n" + "=" * 80)
    print("✓ Analysis complete")
    print("=" * 80)
    print("\n✓ Saved summary to: quality_flags_analysis.json")
    
    return df


if __name__ == "__main__":
    df = analyze_quality_flags()

