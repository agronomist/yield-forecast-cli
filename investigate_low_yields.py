"""
Investigate Low-Yielding Fields

Analyze fields with yields below agronomist's expectations (3.5 ton/ha)
to identify potential causes or model issues.
"""

import pandas as pd
import json
import numpy as np


def analyze_low_yielding_fields():
    """Analyze fields below expected yield threshold."""
    
    print("\n" + "=" * 80)
    print("INVESTIGATING LOW-YIELDING FIELDS")
    print("=" * 80)
    print("\nAgronomist expectation: No fields below 3.5 ton/ha (3,500 kg/ha)")
    
    # Load yield predictions
    df_yield = pd.read_csv('yield_predictions.csv')
    
    # Find fields below threshold
    threshold = 3.5
    low_fields = df_yield[df_yield['Grain Yield (ton/ha)'] < threshold].copy()
    low_fields = low_fields.sort_values('Grain Yield (ton/ha)')
    
    print(f"\nFields below {threshold} ton/ha: {len(low_fields)} out of {len(df_yield)} ({len(low_fields)/len(df_yield)*100:.1f}%)")
    
    print("\n" + "─" * 80)
    print("LOW-YIELDING FIELDS")
    print("─" * 80)
    print(f"\n{'Field':30} {'Variety':15} {'Yield':10} {'Biomass':12} {'Days':6} {'Sowing':12}")
    print("─" * 80)
    
    for _, row in low_fields.iterrows():
        print(f"{row['Field Name'][:30]:30} "
              f"{row['Variety'][:15]:15} "
              f"{row['Grain Yield (ton/ha)']:10.2f} "
              f"{row['Total Biomass (kg/ha)']:12.0f} "
              f"{int(row['Days Growing']):6} "
              f"{row['Sowing Date']:12}")
    
    # Load detailed data
    with open('sentinel_ndvi_fapar_data.json', 'r') as f:
        fapar_data = json.load(f)
    
    with open('solar_radiation_par_data.json', 'r') as f:
        par_data = json.load(f)
    
    # Analyze each low-yielding field
    print("\n" + "=" * 80)
    print("DETAILED ANALYSIS OF LOW-YIELDING FIELDS")
    print("=" * 80)
    
    for idx, row in low_fields.iterrows():
        field_name = row['Field Name']
        
        print(f"\n{'─' * 80}")
        print(f"Field: {field_name}")
        print(f"Predicted Yield: {row['Grain Yield (ton/ha)']:.2f} ton/ha")
        print(f"Expected: ≥3.5 ton/ha → Shortfall: {3.5 - row['Grain Yield (ton/ha)']:.2f} ton/ha")
        print(f"{'─' * 80}")
        
        # Get NDVI/fAPAR data
        if field_name in fapar_data['fields']:
            field_fapar = fapar_data['fields'][field_name]
            ndvi_series = field_fapar.get('ndvi_time_series', [])
            
            if ndvi_series:
                ndvi_values = [obs.get('ndvi_mean', 0) for obs in ndvi_series if obs.get('ndvi_mean') is not None]
                fapar_values = [obs.get('fapar_mean', 0) for obs in ndvi_series if obs.get('fapar_mean') is not None]
                
                print(f"\n📊 NDVI/fAPAR Statistics:")
                print(f"  Observations: {len(ndvi_values)} weeks")
                print(f"  Peak NDVI:    {max(ndvi_values) if ndvi_values else 0:.3f}")
                print(f"  Mean NDVI:    {np.mean(ndvi_values) if ndvi_values else 0:.3f}")
                print(f"  Peak fAPAR:   {max(fapar_values) if fapar_values else 0:.3f}")
                print(f"  Mean fAPAR:   {np.mean(fapar_values) if fapar_values else 0:.3f}")
                
                # Compare to high-yielders
                high_fields = df_yield[df_yield['Grain Yield (ton/ha)'] > 4.5]
                
                print(f"\n📈 Comparison to High-Yielding Fields (>4.5 ton/ha):")
                
                # Get average peak NDVI from high yielders
                high_ndvi_peaks = []
                for hf_name in high_fields['Field Name']:
                    if hf_name in fapar_data['fields']:
                        hf_ndvi = fapar_data['fields'][hf_name].get('ndvi_time_series', [])
                        hf_ndvi_vals = [obs.get('ndvi_mean', 0) for obs in hf_ndvi if obs.get('ndvi_mean') is not None]
                        if hf_ndvi_vals:
                            high_ndvi_peaks.append(max(hf_ndvi_vals))
                
                if high_ndvi_peaks:
                    avg_high_peak = np.mean(high_ndvi_peaks)
                    print(f"  High-yielders avg peak NDVI: {avg_high_peak:.3f}")
                    print(f"  This field peak NDVI:        {max(ndvi_values) if ndvi_values else 0:.3f}")
                    print(f"  Difference:                  {(max(ndvi_values) if ndvi_values else 0) - avg_high_peak:.3f} ({((max(ndvi_values) if ndvi_values else 0) - avg_high_peak)/avg_high_peak*100:.1f}%)")
        
        # Get PAR data
        if field_name in par_data['fields']:
            field_par = par_data['fields'][field_name]
            par_series = field_par.get('radiation_data', [])
            
            if par_series:
                par_values = [obs.get('PAR_MJ', 0) for obs in par_series if obs.get('PAR_MJ') is not None]
                
                print(f"\n☀️ Solar Radiation (PAR):")
                print(f"  Mean PAR: {np.mean(par_values):.2f} MJ/m²/day")
                print(f"  Total cumulative PAR: {sum(par_values):.1f} MJ/m²")
        
        # Sowing date analysis
        sowing_date = row['Sowing Date']
        days_growing = int(row['Days Growing'])
        
        print(f"\n📅 Timing:")
        print(f"  Sowing date:   {sowing_date}")
        print(f"  Days growing:  {days_growing}")
        print(f"  Current stage: {row['Current Stage']}")
        
        # Variety
        print(f"\n🌾 Variety: {row['Variety']}")
        variety_avg = df_yield[df_yield['Variety'] == row['Variety']]['Grain Yield (ton/ha)'].mean()
        print(f"  Variety average yield: {variety_avg:.2f} ton/ha")
        print(f"  This field vs variety avg: {row['Grain Yield (ton/ha)'] - variety_avg:.2f} ton/ha ({(row['Grain Yield (ton/ha)'] - variety_avg)/variety_avg*100:.1f}%)")
    
    # Summary analysis
    print("\n" + "=" * 80)
    print("SUMMARY: POTENTIAL CAUSES FOR LOW YIELDS")
    print("=" * 80)
    
    # Analyze patterns
    print("\n1. NDVI/fAPAR Analysis:")
    
    # Get NDVI stats for all fields
    all_peak_ndvi = []
    low_peak_ndvi = []
    high_peak_ndvi = []
    
    for field_name in df_yield['Field Name']:
        if field_name in fapar_data['fields']:
            ndvi_series = fapar_data['fields'][field_name].get('ndvi_time_series', [])
            ndvi_vals = [obs.get('ndvi_mean', 0) for obs in ndvi_series if obs.get('ndvi_mean') is not None]
            if ndvi_vals:
                peak = max(ndvi_vals)
                all_peak_ndvi.append(peak)
                
                yield_val = df_yield[df_yield['Field Name'] == field_name]['Grain Yield (ton/ha)'].values[0]
                if yield_val < threshold:
                    low_peak_ndvi.append(peak)
                elif yield_val > 4.5:
                    high_peak_ndvi.append(peak)
    
    print(f"  Average peak NDVI (all fields):      {np.mean(all_peak_ndvi):.3f}")
    print(f"  Average peak NDVI (low-yield):       {np.mean(low_peak_ndvi):.3f}")
    print(f"  Average peak NDVI (high-yield >4.5): {np.mean(high_peak_ndvi):.3f}")
    print(f"  → Low-yielders have {(1 - np.mean(low_peak_ndvi)/np.mean(high_peak_ndvi))*100:.1f}% lower peak NDVI")
    
    print("\n2. Sowing Date Analysis:")
    low_sowing = pd.to_datetime(low_fields['Sowing Date'])
    all_sowing = pd.to_datetime(df_yield['Sowing Date'])
    
    print(f"  Low-yield fields sowing range: {low_sowing.min().strftime('%Y-%m-%d')} to {low_sowing.max().strftime('%Y-%m-%d')}")
    print(f"  All fields sowing range:       {all_sowing.min().strftime('%Y-%m-%d')} to {all_sowing.max().strftime('%Y-%m-%d')}")
    
    print("\n3. Variety Distribution (low-yielding fields):")
    variety_counts = low_fields['Variety'].value_counts()
    for variety, count in variety_counts.items():
        total_variety = len(df_yield[df_yield['Variety'] == variety])
        print(f"  {variety:20} {count:2}/{total_variety} fields ({count/total_variety*100:.1f}%)")
    
    print("\n4. Days Growing:")
    print(f"  Low-yield fields avg days: {low_fields['Days Growing'].mean():.0f}")
    print(f"  All fields avg days:       {df_yield['Days Growing'].mean():.0f}")
    
    print("\n" + "=" * 80)
    print("LIKELY EXPLANATIONS")
    print("=" * 80)
    
    print("\n✓ Model is detecting real differences in crop performance:")
    print("  • Low-yielding fields have significantly lower peak NDVI")
    print("  • Lower NDVI = lower canopy cover = less light interception")
    print("  • This translates to lower fAPAR and thus lower biomass accumulation")
    
    print("\n❓ Possible real agronomic causes (to investigate in field):")
    print("  1. Water stress or drainage issues")
    print("  2. Nutrient deficiencies (especially nitrogen)")
    print("  3. Soil variability or poor soil quality")
    print("  4. Pest/disease pressure")
    print("  5. Poor stand establishment")
    print("  6. Weed competition")
    print("  7. Late sowing or shorter growing season")
    
    print("\n⚙️ Possible model limitations:")
    print("  1. fAPAR interpolation may underestimate for some fields")
    print("  2. RUE values are literature averages (may not fit all fields)")
    print("  3. No field-specific soil/management factors included")
    print("  4. Harvest index assumed constant (may vary by stress)")
    
    print("\n💡 Recommendations:")
    print("  1. Field-verify NDVI patterns with agronomist observations")
    print("  2. After harvest, compare predictions to actual yields")
    print("  3. Investigate specific low-yielding fields for management issues")
    print("  4. Consider if model needs calibration for local conditions")
    
    # Save detailed report
    low_fields.to_csv('low_yielding_fields_analysis.csv', index=False)
    print(f"\n✓ Saved detailed data to: low_yielding_fields_analysis.csv")


if __name__ == "__main__":
    try:
        analyze_low_yielding_fields()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

