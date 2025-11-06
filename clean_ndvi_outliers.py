"""
Clean NDVI time series by detecting and removing outliers (likely cloud contamination)
and filling gaps with interpolation.

Strategy:
1. Detect outliers: NDVI drops below threshold after being above it
2. Use rolling median to detect anomalous dips
3. Interpolate missing values using neighboring clean data
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt


def detect_ndvi_outliers(dates, ndvi_values, threshold=0.2, window=3):
    """
    Detect NDVI outliers based on:
    1. Sudden drops below threshold after being above it
    2. Values that deviate significantly from rolling median
    
    Args:
        dates: List of datetime objects
        ndvi_values: List of NDVI values
        threshold: Minimum NDVI threshold (default 0.2)
        window: Window size for rolling statistics (default 3)
        
    Returns:
        Boolean array where True indicates outlier
    """
    if len(ndvi_values) < 3:
        return np.zeros(len(ndvi_values), dtype=bool)
    
    ndvi_array = np.array(ndvi_values)
    outliers = np.zeros(len(ndvi_values), dtype=bool)
    
    # Calculate rolling median
    df = pd.DataFrame({'ndvi': ndvi_values})
    rolling_median = df['ndvi'].rolling(window=window, center=True, min_periods=1).median().values
    
    # Method 1: Detect sudden drops
    for i in range(1, len(ndvi_values) - 1):
        prev_val = ndvi_values[i-1]
        curr_val = ndvi_values[i]
        next_val = ndvi_values[i+1]
        
        # If we've been above threshold and suddenly drop below, then recover
        if prev_val > threshold and curr_val < threshold and next_val > threshold:
            outliers[i] = True
            
        # Or if current value drops significantly below neighbors
        if prev_val > threshold and next_val > threshold:
            expected = (prev_val + next_val) / 2
            if curr_val < expected * 0.7:  # More than 30% drop
                outliers[i] = True
    
    # Method 2: Detect values far from rolling median
    deviation = np.abs(ndvi_array - rolling_median)
    median_deviation = np.median(deviation[deviation > 0])
    
    if not np.isnan(median_deviation) and median_deviation > 0:
        # Flag as outlier if deviation is > 3x median deviation
        threshold_dev = 3 * median_deviation
        outliers |= (deviation > threshold_dev) & (ndvi_array < rolling_median)
    
    return outliers


def interpolate_gaps(dates, values, outliers):
    """
    Interpolate values at outlier positions using neighboring clean data.
    
    Args:
        dates: List of datetime objects
        values: List of values
        outliers: Boolean array indicating outliers
        
    Returns:
        Cleaned values with interpolated data
    """
    if not any(outliers):
        return values
    
    # Convert dates to numeric (days since first date)
    dates_numeric = np.array([(d - dates[0]).days for d in dates])
    values_array = np.array(values)
    
    # Get clean (non-outlier) indices
    clean_mask = ~outliers
    
    if np.sum(clean_mask) < 2:
        # Not enough clean data to interpolate
        return values
    
    # Interpolate using linear interpolation
    clean_dates = dates_numeric[clean_mask]
    clean_values = values_array[clean_mask]
    
    # Create interpolation function
    interp_func = interp1d(clean_dates, clean_values, 
                           kind='linear', 
                           fill_value='extrapolate',
                           bounds_error=False)
    
    # Fill outlier positions with interpolated values
    values_cleaned = values_array.copy()
    values_cleaned[outliers] = interp_func(dates_numeric[outliers])
    
    # Ensure values stay within valid range [0, 1]
    values_cleaned = np.clip(values_cleaned, 0, 1)
    
    return values_cleaned.tolist()


def clean_field_ndvi(field_data, field_name):
    """
    Clean NDVI data for a single field.
    
    Args:
        field_data: Dictionary with field NDVI observations
        field_name: Name of the field
        
    Returns:
        Cleaned field data with outliers removed and gaps filled
    """
    if 'ndvi_time_series' not in field_data:
        return field_data, 0, 0
    
    observations = field_data['ndvi_time_series']
    
    if len(observations) < 3:
        return field_data, 0, 0
    
    # Extract dates and NDVI values
    dates = [datetime.strptime(obs['from'], '%Y-%m-%d') for obs in observations]
    ndvi_values = [obs['ndvi_mean'] for obs in observations]
    
    # Detect outliers
    outliers = detect_ndvi_outliers(dates, ndvi_values)
    n_outliers = np.sum(outliers)
    
    if n_outliers == 0:
        return field_data, 0, 0
    
    # Interpolate gaps
    ndvi_cleaned = interpolate_gaps(dates, ndvi_values, outliers)
    
    # Update observations with cleaned values
    cleaned_field_data = field_data.copy()
    cleaned_observations = []
    
    for i, obs in enumerate(observations):
        cleaned_obs = obs.copy()
        
        if outliers[i]:
            # Update NDVI mean and recalculate fAPAR
            old_ndvi = cleaned_obs['ndvi_mean']
            new_ndvi = float(ndvi_cleaned[i])
            cleaned_obs['ndvi_mean'] = new_ndvi
            
            # Recalculate fAPAR with cleaned NDVI
            cleaned_obs['fapar_mean'] = float(0.013 * np.exp(4.48 * new_ndvi))
            
            # Mark as interpolated
            cleaned_obs['interpolated'] = True
            cleaned_obs['original_ndvi'] = float(old_ndvi)
        else:
            cleaned_obs['ndvi_mean'] = float(ndvi_cleaned[i])
            cleaned_obs['interpolated'] = False
        
        cleaned_observations.append(cleaned_obs)
    
    cleaned_field_data['ndvi_time_series'] = cleaned_observations
    
    return cleaned_field_data, n_outliers, len(observations)


def clean_all_fields(input_file, output_file):
    """
    Clean NDVI data for all fields in the dataset.
    
    Args:
        input_file: Path to input JSON file with NDVI data
        output_file: Path to save cleaned JSON file
    """
    print("\n" + "=" * 80)
    print("NDVI OUTLIER DETECTION AND CLEANING")
    print("=" * 80)
    
    # Load data
    print(f"\nLoading data from: {input_file}")
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    if 'fields' not in data:
        print("✗ No 'fields' key found in data")
        return
    
    fields = data['fields']
    print(f"✓ Loaded {len(fields)} fields")
    
    # Clean each field
    print("\n" + "─" * 80)
    print("Cleaning fields...")
    print("─" * 80)
    
    cleaned_fields = {}
    total_outliers = 0
    total_observations = 0
    fields_with_outliers = 0
    
    for field_name, field_data in fields.items():
        cleaned_data, n_outliers, n_obs = clean_field_ndvi(field_data, field_name)
        cleaned_fields[field_name] = cleaned_data
        
        if n_outliers > 0:
            fields_with_outliers += 1
            total_outliers += n_outliers
            total_observations += n_obs
            print(f"  {field_name}: {n_outliers}/{n_obs} outliers removed ({n_outliers/n_obs*100:.1f}%)")
    
    # Update data
    data['fields'] = cleaned_fields
    data['cleaning_metadata'] = {
        'cleaned_at': datetime.now().isoformat(),
        'total_fields': int(len(fields)),
        'fields_with_outliers': int(fields_with_outliers),
        'total_outliers_removed': int(total_outliers),
        'total_observations': int(total_observations),
        'outlier_percentage': float((total_outliers / total_observations * 100)) if total_observations > 0 else 0.0
    }
    
    # Save cleaned data
    print("\n" + "─" * 80)
    print("Saving cleaned data...")
    print("─" * 80)
    
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✓ Saved to: {output_file}")
    
    # Summary
    print("\n" + "=" * 80)
    print("CLEANING SUMMARY")
    print("=" * 80)
    print(f"\nTotal fields: {len(fields)}")
    print(f"Fields with outliers: {fields_with_outliers}")
    print(f"Total outliers removed: {total_outliers}")
    print(f"Total observations: {total_observations}")
    print(f"Outlier rate: {(total_outliers / total_observations * 100):.2f}%")
    
    return data


def create_comparison_plot(original_file, cleaned_file, field_name, output_file):
    """
    Create a comparison plot showing original vs cleaned NDVI data for a field.
    """
    # Load both datasets
    with open(original_file, 'r') as f:
        original_data = json.load(f)
    
    with open(cleaned_file, 'r') as f:
        cleaned_data = json.load(f)
    
    if field_name not in original_data['fields'] or field_name not in cleaned_data['fields']:
        print(f"Field {field_name} not found in data")
        return
    
    orig_obs = original_data['fields'][field_name]['ndvi_time_series']
    clean_obs = cleaned_data['fields'][field_name]['ndvi_time_series']
    
    # Extract data
    dates = [datetime.strptime(obs['from'], '%Y-%m-%d') for obs in orig_obs]
    orig_ndvi = [obs['ndvi_mean'] for obs in orig_obs]
    clean_ndvi = [obs['ndvi_mean'] for obs in clean_obs]
    interpolated = [obs.get('interpolated', False) for obs in clean_obs]
    
    # Create plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    
    # Plot 1: Original NDVI
    ax1.plot(dates, orig_ndvi, 'o-', color='darkgreen', linewidth=2, markersize=8, label='Original NDVI')
    ax1.axhline(0.2, color='red', linestyle='--', alpha=0.5, label='Threshold (0.2)')
    ax1.set_ylabel('NDVI', fontsize=12, fontweight='bold')
    ax1.set_title(f'{field_name} - Original NDVI Time Series', fontsize=13, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    ax1.set_ylim(0, 1)
    
    # Plot 2: Cleaned NDVI
    ax2.plot(dates, clean_ndvi, 'o-', color='darkblue', linewidth=2, markersize=8, label='Cleaned NDVI')
    
    # Highlight interpolated points
    interp_dates = [d for d, i in zip(dates, interpolated) if i]
    interp_values = [v for v, i in zip(clean_ndvi, interpolated) if i]
    if interp_dates:
        ax2.scatter(interp_dates, interp_values, color='red', s=150, marker='x', 
                   linewidths=3, label='Interpolated', zorder=5)
    
    ax2.axhline(0.2, color='red', linestyle='--', alpha=0.5, label='Threshold (0.2)')
    ax2.set_ylabel('NDVI', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Date', fontsize=12, fontweight='bold')
    ax2.set_title(f'{field_name} - Cleaned NDVI Time Series', fontsize=13, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    ax2.set_ylim(0, 1)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=200, bbox_inches='tight')
    print(f"✓ Saved comparison plot to: {output_file}")
    plt.close()


if __name__ == "__main__":
    # Clean new fields data
    print("\n" + "=" * 80)
    print("CLEANING NEW FIELDS NDVI DATA")
    print("=" * 80)
    
    input_file = 'output_new_fields/sentinel_ndvi_fapar_data.json'
    output_file = 'output_new_fields/sentinel_ndvi_fapar_data_cleaned.json'
    
    cleaned_data = clean_all_fields(input_file, output_file)
    
    # Create comparison plots for fields with most outliers
    print("\n" + "=" * 80)
    print("CREATING COMPARISON PLOTS")
    print("=" * 80)
    
    # Find fields with outliers
    if cleaned_data:
        fields_with_outliers = []
        for field_name, field_data in cleaned_data['fields'].items():
            n_interpolated = sum(1 for obs in field_data['ndvi_time_series'] 
                               if obs.get('interpolated', False))
            if n_interpolated > 0:
                fields_with_outliers.append((field_name, n_interpolated))
        
        # Sort by number of outliers
        fields_with_outliers.sort(key=lambda x: x[1], reverse=True)
        
        # Plot top 3 fields with most outliers
        print(f"\nCreating plots for fields with most outliers...")
        for i, (field_name, n_outliers) in enumerate(fields_with_outliers[:3]):
            safe_name = field_name.replace('/', '_').replace(' ', '_')
            output_plot = f'ndvi_cleaning_comparison_{safe_name}.png'
            create_comparison_plot(input_file, output_file, field_name, output_plot)
    
    print("\n" + "=" * 80)
    print("✓ NDVI CLEANING COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Review comparison plots")
    print("  2. Re-run biomass/yield predictions with cleaned data")
    print("  3. Compare results with original predictions")

