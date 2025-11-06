"""
Clean ARPS NDVI data by detecting outliers and filling gaps.
Similar to clean_ndvi_outliers.py but optimized for daily ARPS data.
"""

import json
import os
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from datetime import datetime


def detect_outliers_arps(ndvi_series, window=7, threshold=0.15):
    """
    Detect outliers in daily ARPS NDVI using rolling statistics.
    
    Args:
        ndvi_series: List of NDVI values
        window: Rolling window size (days)
        threshold: Z-score threshold for outlier detection
    
    Returns:
        Boolean mask indicating outliers
    """
    if len(ndvi_series) < window:
        return np.zeros(len(ndvi_series), dtype=bool)
    
    # Convert to pandas series for rolling operations
    series = pd.Series(ndvi_series)
    
    # Calculate rolling median and std
    rolling_median = series.rolling(window=window, center=True, min_periods=3).median()
    rolling_std = series.rolling(window=window, center=True, min_periods=3).std()
    
    # Detect outliers: values that deviate significantly from rolling median
    # Also flag very low NDVI values (< 0.2) as potential cloud contamination
    outliers = np.zeros(len(ndvi_series), dtype=bool)
    
    for i in range(len(ndvi_series)):
        # Flag if NDVI < 0.2 (likely clouds)
        if ndvi_series[i] < 0.2:
            outliers[i] = True
            continue
        
        # Flag if deviation from rolling median is too large
        if not pd.isna(rolling_median[i]) and not pd.isna(rolling_std[i]):
            if rolling_std[i] > 0:
                z_score = abs(ndvi_series[i] - rolling_median[i]) / rolling_std[i]
                if z_score > threshold / rolling_std[i]:
                    outliers[i] = True
            
            # Also flag sudden drops (> 0.2 NDVI decrease from rolling median)
            if ndvi_series[i] < rolling_median[i] - 0.2:
                outliers[i] = True
    
    return outliers


def fill_gaps_arps(dates, ndvi_values, outlier_mask):
    """
    Fill gaps in ARPS NDVI using interpolation.
    
    Args:
        dates: List of date strings
        ndvi_values: List of NDVI values
        outlier_mask: Boolean mask indicating outliers
    
    Returns:
        Cleaned NDVI values with gaps filled
    """
    if not any(outlier_mask):
        return ndvi_values.copy()
    
    # Convert dates to numeric (days since first observation)
    date_objects = [datetime.strptime(d, '%Y-%m-%d') for d in dates]
    first_date = date_objects[0]
    days_numeric = [(d - first_date).days for d in date_objects]
    
    # Get clean data (not outliers)
    clean_indices = ~outlier_mask
    clean_days = [days_numeric[i] for i in range(len(days_numeric)) if clean_indices[i]]
    clean_ndvi = [ndvi_values[i] for i in range(len(ndvi_values)) if clean_indices[i]]
    
    if len(clean_days) < 2:
        print("    ⚠️  Not enough clean data for interpolation")
        return ndvi_values.copy()
    
    # Interpolate using cubic spline (smooth for daily data)
    interpolator = interp1d(
        clean_days, 
        clean_ndvi, 
        kind='cubic',
        bounds_error=False,
        fill_value='extrapolate'
    )
    
    # Fill outliers with interpolated values
    filled_ndvi = ndvi_values.copy()
    for i in range(len(ndvi_values)):
        if outlier_mask[i]:
            filled_ndvi[i] = float(interpolator(days_numeric[i]))
            # Ensure NDVI stays in valid range
            filled_ndvi[i] = max(0.0, min(1.0, filled_ndvi[i]))
    
    return filled_ndvi


def clean_arps_field(input_path, output_path):
    """
    Clean ARPS NDVI data for a single field.
    
    Args:
        input_path: Path to input ARPS NDVI JSON file
        output_path: Path to save cleaned data
    
    Returns:
        Number of outliers detected and filled
    """
    # Load ARPS data
    with open(input_path, 'r') as f:
        data = json.load(f)
    
    field_name = data['field_name']
    observations = data['observations']
    
    if len(observations) < 5:
        print(f"    ⚠️  Too few observations ({len(observations)}), skipping")
        return 0
    
    # Extract dates and NDVI values
    dates = [obs['date'] for obs in observations]
    ndvi_values = [obs['ndvi_mean'] for obs in observations]
    
    # Detect outliers
    outlier_mask = detect_outliers_arps(ndvi_values, window=7, threshold=0.15)
    n_outliers = sum(outlier_mask)
    
    if n_outliers == 0:
        print(f"    ✓ No outliers detected")
        # Still save the file
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        return 0
    
    print(f"    🔍 Detected {n_outliers} outliers ({n_outliers/len(observations)*100:.1f}%)")
    
    # Fill gaps
    filled_ndvi = fill_gaps_arps(dates, ndvi_values, outlier_mask)
    
    # Update observations with cleaned NDVI
    for i, obs in enumerate(observations):
        obs['ndvi_mean_original'] = obs['ndvi_mean']
        obs['ndvi_mean'] = float(filled_ndvi[i])
        obs['was_outlier'] = bool(outlier_mask[i])
    
    # Add cleaning metadata
    data['cleaning_applied'] = True
    data['cleaning_date'] = datetime.now().isoformat()
    data['outliers_detected'] = int(n_outliers)
    data['outliers_percentage'] = float(n_outliers/len(observations)*100)
    
    # Save cleaned data
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"    ✓ Cleaned and saved to {output_path}")
    
    return n_outliers


def main():
    """Main execution function."""
    print("=" * 80)
    print("CLEANING ARPS NDVI DATA - OUTLIER DETECTION & GAP FILLING")
    print("=" * 80)
    
    # Process original fields
    original_input_dir = "arps_ndvi_data"
    original_output_dir = "arps_ndvi_data_cleaned"
    os.makedirs(original_output_dir, exist_ok=True)
    
    # Process new fields
    new_input_dir = "more_fields/arps_ndvi_data"
    new_output_dir = "more_fields/arps_ndvi_data_cleaned"
    os.makedirs(new_output_dir, exist_ok=True)
    
    total_outliers = 0
    total_fields = 0
    
    for input_dir, output_dir, label in [
        (original_input_dir, original_output_dir, "Original"),
        (new_input_dir, new_output_dir, "New")
    ]:
        if not os.path.exists(input_dir):
            continue
        
        files = [f for f in os.listdir(input_dir) if f.endswith('.json')]
        
        print(f"\n{'=' * 80}")
        print(f"PROCESSING {label.upper()} FIELDS - {len(files)} files")
        print('=' * 80)
        
        for i, filename in enumerate(sorted(files), 1):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename)
            
            # Extract field name from filename
            field_name = filename.replace('arps_ndvi_', '').replace('.json', '').replace('_', ' ')
            
            print(f"\n{i}/{len(files)}: {field_name}")
            
            try:
                n_outliers = clean_arps_field(input_path, output_path)
                total_outliers += n_outliers
                total_fields += 1
            except Exception as e:
                print(f"    ✗ Error: {e}")
    
    print("\n" + "=" * 80)
    print("CLEANING COMPLETE")
    print("=" * 80)
    print(f"Total fields processed: {total_fields}")
    print(f"Total outliers removed: {total_outliers}")
    print(f"Average outliers per field: {total_outliers/total_fields:.1f}")
    print("=" * 80)


if __name__ == "__main__":
    main()

