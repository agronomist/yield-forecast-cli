"""
Calculate fAPARg (fraction of Absorbed Photosynthetically Active Radiation) 
from NDVI values using the exponential relationship.

Formula: fAPARg = 0.013 * e^(4.48 * NDVI)
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime


def calculate_fapar(ndvi):
    """
    Calculate fAPARg from NDVI using exponential relationship.
    
    Formula: fAPARg = 0.013 * e^(4.48 * NDVI)
    
    Args:
        ndvi: NDVI value (0-1 range)
        
    Returns:
        fAPARg value
    """
    if pd.isna(ndvi):
        return np.nan
    
    fapar = 0.013 * np.exp(4.48 * ndvi)
    return fapar


def process_ndvi_data(input_json_path, output_json_path, output_csv_path):
    """
    Process NDVI data and calculate fAPARg for all observations.
    
    Args:
        input_json_path: Path to input NDVI JSON file
        output_json_path: Path to save output JSON with fAPARg
        output_csv_path: Path to save output CSV with fAPARg
    """
    print("=" * 80)
    print("CALCULATING fAPARg FROM NDVI DATA")
    print("=" * 80)
    print("\nFormula: fAPARg = 0.013 × e^(4.48 × NDVI)")
    print("\nLoading NDVI data...")
    
    # Load JSON data
    with open(input_json_path, 'r') as f:
        data = json.load(f)
    
    print(f"✓ Loaded data for {len(data['fields'])} fields")
    
    # Process each field
    total_observations = 0
    
    for field_name, field_data in data['fields'].items():
        if 'ndvi_time_series' in field_data:
            for obs in field_data['ndvi_time_series']:
                # Calculate fAPARg from NDVI mean
                if obs.get('ndvi_mean') is not None:
                    obs['fapar_mean'] = calculate_fapar(obs['ndvi_mean'])
                    
                    # Also calculate for percentiles if they exist
                    for percentile in ['ndvi_p10', 'ndvi_p25', 'ndvi_p50', 'ndvi_p75', 'ndvi_p90']:
                        if obs.get(percentile) is not None:
                            fapar_key = percentile.replace('ndvi', 'fapar')
                            obs[fapar_key] = calculate_fapar(obs[percentile])
                    
                    # Calculate for min and max
                    if obs.get('ndvi_min') is not None:
                        obs['fapar_min'] = calculate_fapar(obs['ndvi_min'])
                    if obs.get('ndvi_max') is not None:
                        obs['fapar_max'] = calculate_fapar(obs['ndvi_max'])
                    
                    total_observations += 1
    
    print(f"✓ Calculated fAPARg for {total_observations} observations")
    
    # Save updated JSON
    with open(output_json_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✓ Saved JSON to: {output_json_path}")
    
    # Create CSV with all data
    rows = []
    for field_name, field_data in data['fields'].items():
        variety = field_data.get('variety', 'Unknown')
        sowing_date = field_data.get('sowing_date', 'N/A')
        
        if sowing_date != 'N/A':
            sowing_dt = datetime.strptime(sowing_date, '%Y-%m-%d')
        
        for obs in field_data.get('ndvi_time_series', []):
            period_start = obs.get('from', obs.get('date', ''))
            period_end = obs.get('to', '')
            
            # Calculate days since sowing
            if sowing_date != 'N/A' and period_start:
                obs_dt = datetime.strptime(period_start, '%Y-%m-%d')
                days_since_sowing = (obs_dt - sowing_dt).days
            else:
                days_since_sowing = ''
            
            rows.append({
                'Field Name': field_name,
                'Variety': variety,
                'Sowing Date': sowing_date,
                'Period Start': period_start,
                'Period End': period_end,
                'Days Since Sowing': days_since_sowing,
                'NDVI Mean': obs.get('ndvi_mean'),
                'NDVI Std': obs.get('ndvi_std'),
                'NDVI Min': obs.get('ndvi_min'),
                'NDVI Max': obs.get('ndvi_max'),
                'NDVI P50 (Median)': obs.get('ndvi_p50'),
                'fAPARg Mean': obs.get('fapar_mean'),
                'fAPARg Min': obs.get('fapar_min'),
                'fAPARg Max': obs.get('fapar_max'),
                'fAPARg P50 (Median)': obs.get('fapar_p50'),
                'Clear Pixel %': obs.get('clear_percentage', 0),
                'Sample Count': obs.get('sample_count', 0)
            })
    
    df = pd.DataFrame(rows)
    df.to_csv(output_csv_path, index=False)
    
    print(f"✓ Saved CSV to: {output_csv_path}")
    
    return df


def print_summary_statistics(df):
    """Print summary statistics for NDVI and fAPARg."""
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    
    print("\nNDVI Statistics:")
    print("─" * 80)
    print(f"  Mean: {df['NDVI Mean'].mean():.4f}")
    print(f"  Std:  {df['NDVI Mean'].std():.4f}")
    print(f"  Min:  {df['NDVI Mean'].min():.4f}")
    print(f"  Max:  {df['NDVI Mean'].max():.4f}")
    
    print("\nfAPARg Statistics:")
    print("─" * 80)
    print(f"  Mean: {df['fAPARg Mean'].mean():.4f}")
    print(f"  Std:  {df['fAPARg Mean'].std():.4f}")
    print(f"  Min:  {df['fAPARg Mean'].min():.4f}")
    print(f"  Max:  {df['fAPARg Mean'].max():.4f}")
    
    print("\n" + "─" * 80)
    print("NDVI to fAPARg Conversion Examples:")
    print("─" * 80)
    
    example_ndvi = [0.2, 0.4, 0.6, 0.8, 0.9]
    print(f"{'NDVI':>10} {'fAPARg':>12} {'Interpretation':30}")
    print("─" * 80)
    
    interpretations = {
        0.2: "Low vegetation/early growth",
        0.4: "Moderate vegetation/tillering",
        0.6: "Good vegetation/stem extension",
        0.8: "High vegetation/heading",
        0.9: "Peak vegetation/anthesis"
    }
    
    for ndvi in example_ndvi:
        fapar = calculate_fapar(ndvi)
        print(f"{ndvi:>10.2f} {fapar:>12.4f}   {interpretations[ndvi]:30}")
    
    # Field-level statistics
    print("\n" + "─" * 80)
    print("FIELD-LEVEL STATISTICS")
    print("─" * 80)
    
    field_stats = df.groupby('Field Name').agg({
        'NDVI Mean': ['mean', 'max'],
        'fAPARg Mean': ['mean', 'max'],
        'Days Since Sowing': 'max'
    }).round(4)
    
    print(f"\nTop 10 fields by peak fAPARg:")
    print("─" * 80)
    top_fields = field_stats.sort_values(('fAPARg Mean', 'max'), ascending=False).head(10)
    
    print(f"{'Field Name':30} {'Peak fAPARg':12} {'Peak NDVI':12} {'Days':6}")
    print("─" * 80)
    for field_name, row in top_fields.iterrows():
        print(f"{field_name[:30]:30} "
              f"{row[('fAPARg Mean', 'max')]:12.4f} "
              f"{row[('NDVI Mean', 'max')]:12.4f} "
              f"{row[('Days Since Sowing', 'max')]:6.0f}")
    
    # Variety comparison
    print("\n" + "─" * 80)
    print("VARIETY COMPARISON (Average fAPARg)")
    print("─" * 80)
    
    variety_stats = df.groupby('Variety').agg({
        'fAPARg Mean': ['mean', 'max', 'count']
    }).round(4)
    
    variety_stats = variety_stats.sort_values(('fAPARg Mean', 'mean'), ascending=False)
    
    print(f"{'Variety':20} {'Avg fAPARg':12} {'Peak fAPARg':12} {'Obs':6}")
    print("─" * 80)
    for variety, row in variety_stats.iterrows():
        print(f"{variety[:20]:20} "
              f"{row[('fAPARg Mean', 'mean')]:12.4f} "
              f"{row[('fAPARg Mean', 'max')]:12.4f} "
              f"{row[('fAPARg Mean', 'count')]:6.0f}")


def analyze_fapar_trends(df):
    """Analyze fAPARg trends for sample fields."""
    print("\n" + "=" * 80)
    print("SAMPLE FIELD: fAPARg TIME SERIES")
    print("=" * 80)
    
    # Show La germania nuevo as example
    sample = df[df['Field Name'] == 'La germania nuevo'].sort_values('Period Start')
    
    if len(sample) > 0:
        print("\nField: La germania nuevo (DM Pehuen)")
        print("─" * 80)
        print(f"{'Date':12} {'Days':6} {'NDVI':8} {'fAPARg':10} {'Growth Stage':20}")
        print("─" * 80)
        
        for _, row in sample.iterrows():
            days = row['Days Since Sowing']
            ndvi = row['NDVI Mean']
            fapar = row['fAPARg Mean']
            
            # Estimate growth stage from days
            if days < 20:
                stage = "Emergence"
            elif days < 45:
                stage = "Tillering"
            elif days < 75:
                stage = "Stem Extension"
            elif days < 100:
                stage = "Heading"
            elif days < 130:
                stage = "Grain Fill"
            else:
                stage = "Maturity"
            
            print(f"{row['Period Start']:12} {days:6.0f} "
                  f"{ndvi:8.3f} {fapar:10.4f} {stage:20}")
        
        # Calculate cumulative fAPARg (proxy for total photosynthesis)
        cumulative_fapar = sample['fAPARg Mean'].sum()
        print(f"\nCumulative fAPARg: {cumulative_fapar:.2f}")
        print("(Higher cumulative fAPARg typically correlates with higher yield)")


if __name__ == "__main__":
    # Input and output paths
    INPUT_JSON = "sentinel_ndvi_data.json"
    OUTPUT_JSON = "sentinel_ndvi_fapar_data.json"
    OUTPUT_CSV = "sentinel_ndvi_fapar_data.csv"
    
    try:
        # Process data
        df = process_ndvi_data(INPUT_JSON, OUTPUT_JSON, OUTPUT_CSV)
        
        # Print statistics
        print_summary_statistics(df)
        
        # Analyze trends
        analyze_fapar_trends(df)
        
        print("\n" + "=" * 80)
        print("✓ fAPARg CALCULATION COMPLETE")
        print("=" * 80)
        print("\nOutput files:")
        print(f"  - {OUTPUT_JSON} (JSON with NDVI and fAPARg)")
        print(f"  - {OUTPUT_CSV} (CSV with NDVI and fAPARg)")
        print("\nYou can now use fAPARg values for:")
        print("  • Yield prediction models")
        print("  • Photosynthesis estimation")
        print("  • Growth rate analysis")
        print("  • Variety comparison")
        
    except FileNotFoundError:
        print(f"\n✗ Error: Could not find {INPUT_JSON}")
        print("Please run sentinel_ndvi_fetcher.py first to generate NDVI data")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

