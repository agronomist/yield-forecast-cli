"""
Integrate NDVI data with phenology analysis

This script combines Sentinel-2 NDVI time series with the phenology model
to validate predictions and provide insights.
"""

import json
import csv
from datetime import datetime
from typing import Dict, List
import statistics


def load_data():
    """Load NDVI and phenology data."""
    try:
        with open('sentinel_ndvi_data.json', 'r') as f:
            ndvi_data = json.load(f)
    except FileNotFoundError:
        print("Error: sentinel_ndvi_data.json not found")
        print("Please run sentinel_ndvi_fetcher.py first")
        return None, None
    
    try:
        with open('phenology_analysis_results.json', 'r') as f:
            phenology_data = json.load(f)
    except FileNotFoundError:
        print("Error: phenology_analysis_results.json not found")
        print("Please run weather_phenology_analyzer.py first")
        return None, None
    
    return ndvi_data, phenology_data


def match_ndvi_to_phenology(ndvi_data: Dict, phenology_data: Dict) -> List[Dict]:
    """Match NDVI time series with phenology predictions."""
    combined = []
    
    ndvi_fields = ndvi_data.get('fields', {})
    phenology_fields = {f['field_name']: f for f in phenology_data.get('fields', [])}
    
    for field_name, ndvi_info in ndvi_fields.items():
        if field_name not in phenology_fields:
            continue
        
        pheno = phenology_fields[field_name]
        
        # Combine data
        field_combined = {
            'field_name': field_name,
            'variety': ndvi_info.get('variety'),
            'sowing_date': ndvi_info.get('sowing_date'),
            'phenology': {
                'current_stage': pheno.get('current_stage'),
                'accumulated_gdd': pheno.get('accumulated_gdd'),
                'stage_dates': pheno.get('stage_dates'),
                'days_since_sowing': pheno.get('days_since_sowing')
            },
            'ndvi_time_series': ndvi_info.get('ndvi_time_series', [])
        }
        
        combined.append(field_combined)
    
    return combined


def analyze_ndvi_by_stage(combined_data: List[Dict]) -> Dict:
    """Analyze NDVI values by phenological stage."""
    stage_ndvi = {}
    
    for field in combined_data:
        stage = field['phenology']['current_stage']
        stage_dates = field['phenology']['stage_dates']
        
        # Get recent NDVI values (last 2 weeks)
        recent_ndvi = []
        for period in field['ndvi_time_series'][-2:]:
            if period.get('ndvi_mean') and period.get('clear_percentage', 0) > 50:
                recent_ndvi.append(period['ndvi_mean'])
        
        if recent_ndvi:
            avg_ndvi = statistics.mean(recent_ndvi)
            
            if stage not in stage_ndvi:
                stage_ndvi[stage] = []
            
            stage_ndvi[stage].append(avg_ndvi)
    
    # Calculate statistics per stage
    stage_stats = {}
    for stage, values in stage_ndvi.items():
        if values:
            stage_stats[stage] = {
                'mean': statistics.mean(values),
                'median': statistics.median(values),
                'min': min(values),
                'max': max(values),
                'count': len(values)
            }
    
    return stage_stats


def detect_ndvi_anomalies(combined_data: List[Dict]) -> List[Dict]:
    """Detect fields with anomalous NDVI patterns."""
    anomalies = []
    
    for field in combined_data:
        issues = []
        
        ndvi_series = field['ndvi_time_series']
        if not ndvi_series:
            continue
        
        # Check for recent clear observations
        recent_clear = [p for p in ndvi_series[-4:] 
                       if p.get('clear_percentage', 0) > 50]
        
        if len(recent_clear) < 2:
            issues.append('Insufficient clear observations (cloudy)')
        
        # Check for declining NDVI during growth stages
        if len(recent_clear) >= 2:
            ndvi_values = [p['ndvi_mean'] for p in recent_clear if p.get('ndvi_mean')]
            
            if len(ndvi_values) >= 2:
                # Check if NDVI is declining unexpectedly
                current_stage = field['phenology']['current_stage']
                
                if 'Grain Fill' in current_stage:
                    # NDVI should be high but stable or slightly declining
                    if ndvi_values[-1] < 0.5:
                        issues.append('Low NDVI during grain fill (expected >0.5)')
                
                elif 'Heading' in current_stage or 'Stem Extension' in current_stage:
                    # NDVI should be increasing or high
                    if ndvi_values[-1] < 0.6:
                        issues.append('Low NDVI during active growth (expected >0.6)')
                
                # Check for sharp decline
                if len(ndvi_values) >= 2:
                    decline = ndvi_values[-2] - ndvi_values[-1]
                    if decline > 0.15:
                        issues.append(f'Sharp NDVI decline: {decline:.2f}')
        
        if issues:
            anomalies.append({
                'field_name': field['field_name'],
                'variety': field['variety'],
                'current_stage': field['phenology']['current_stage'],
                'issues': issues,
                'recent_ndvi': [p.get('ndvi_mean') for p in recent_clear]
            })
    
    return anomalies


def print_integrated_report(combined_data: List[Dict]):
    """Print comprehensive integrated analysis report."""
    print("\n" + "=" * 80)
    print("INTEGRATED NDVI & PHENOLOGY ANALYSIS REPORT")
    print("=" * 80)
    
    # Overall statistics
    print(f"\nTotal fields analyzed: {len(combined_data)}")
    
    # NDVI by growth stage
    print("\n" + "─" * 80)
    print("NDVI VALUES BY GROWTH STAGE")
    print("─" * 80)
    
    stage_stats = analyze_ndvi_by_stage(combined_data)
    
    print(f"\n{'Stage':35} {'Mean NDVI':12} {'Range':20} {'Fields':8}")
    print("─" * 80)
    
    for stage, stats in sorted(stage_stats.items()):
        print(f"{stage:35} {stats['mean']:12.3f} "
              f"{stats['min']:.3f} - {stats['max']:.3f}      {stats['count']:8}")
    
    # Field-by-field summary
    print("\n" + "─" * 80)
    print("FIELD-BY-FIELD NDVI TRENDS")
    print("─" * 80)
    
    # Sort by variety and current NDVI
    combined_sorted = sorted(combined_data, key=lambda x: (
        x['variety'],
        -max([p.get('ndvi_mean', 0) for p in x['ndvi_time_series'][-2:]] + [0])
    ))
    
    print(f"\n{'Field':30} {'Variety':15} {'Stage':25} {'Recent NDVI':15} {'Trend':10}")
    print("─" * 80)
    
    for field in combined_sorted[:30]:  # Show top 30
        recent_ndvi = [p for p in field['ndvi_time_series'][-2:] 
                      if p.get('ndvi_mean') and p.get('clear_percentage', 0) > 50]
        
        if recent_ndvi:
            latest = recent_ndvi[-1]['ndvi_mean']
            
            # Calculate trend
            if len(recent_ndvi) >= 2:
                prev = recent_ndvi[-2]['ndvi_mean']
                trend = '↑' if latest > prev else '↓' if latest < prev else '→'
                trend_val = latest - prev
                trend_str = f"{trend} {trend_val:+.3f}"
            else:
                trend_str = "—"
            
            # NDVI quality indicator
            ndvi_bar = '█' * int(latest * 10) + '░' * (10 - int(latest * 10))
            ndvi_str = f"{ndvi_bar} {latest:.3f}"
            
            print(f"{field['field_name'][:30]:30} "
                  f"{field['variety'][:15]:15} "
                  f"{field['phenology']['current_stage'][:25]:25} "
                  f"{ndvi_str:15} "
                  f"{trend_str:10}")
    
    if len(combined_sorted) > 30:
        print(f"\n... and {len(combined_sorted) - 30} more fields")
    
    # Anomaly detection
    print("\n" + "─" * 80)
    print("POTENTIAL ISSUES DETECTED")
    print("─" * 80)
    
    anomalies = detect_ndvi_anomalies(combined_data)
    
    if anomalies:
        for anomaly in anomalies:
            print(f"\n⚠️  {anomaly['field_name']} ({anomaly['variety']})")
            print(f"    Current Stage: {anomaly['current_stage']}")
            for issue in anomaly['issues']:
                print(f"    • {issue}")
            if anomaly['recent_ndvi']:
                print(f"    Recent NDVI values: {', '.join([f'{v:.3f}' for v in anomaly['recent_ndvi']])}")
    else:
        print("\n✓ No significant anomalies detected")
        print("  All fields showing expected NDVI patterns for their growth stage")
    
    # Data quality summary
    print("\n" + "─" * 80)
    print("DATA QUALITY SUMMARY")
    print("─" * 80)
    
    total_observations = sum(len(f['ndvi_time_series']) for f in combined_data)
    clear_observations = sum(
        sum(1 for p in f['ndvi_time_series'] if p.get('clear_percentage', 0) > 50)
        for f in combined_data
    )
    
    print(f"\nTotal NDVI observations: {total_observations}")
    print(f"Clear observations (>50% clear): {clear_observations}")
    print(f"Cloud-free percentage: {(clear_observations/total_observations*100):.1f}%")
    
    # Variety comparison
    print("\n" + "─" * 80)
    print("VARIETY NDVI COMPARISON")
    print("─" * 80)
    
    by_variety = {}
    for field in combined_data:
        variety = field['variety']
        recent_ndvi = [p['ndvi_mean'] for p in field['ndvi_time_series'][-2:] 
                      if p.get('ndvi_mean') and p.get('clear_percentage', 0) > 50]
        
        if recent_ndvi:
            if variety not in by_variety:
                by_variety[variety] = []
            by_variety[variety].extend(recent_ndvi)
    
    print(f"\n{'Variety':20} {'Avg NDVI':12} {'Fields':8}")
    print("─" * 80)
    
    for variety, values in sorted(by_variety.items(), key=lambda x: -statistics.mean(x[1])):
        print(f"{variety:20} {statistics.mean(values):12.3f} {len(values):8}")


def export_integrated_csv(combined_data: List[Dict], output_path: str):
    """Export integrated data to CSV."""
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            'Field Name', 'Variety', 'Sowing Date', 'Days Since Sowing',
            'Current Stage', 'Accumulated GDD',
            'Latest NDVI', 'Avg NDVI (Last 2 Weeks)', 'NDVI Trend',
            'Clear Observations', 'Total Observations'
        ])
        
        # Data
        for field in combined_data:
            recent_ndvi = [p for p in field['ndvi_time_series'][-2:] 
                          if p.get('ndvi_mean') and p.get('clear_percentage', 0) > 50]
            
            latest_ndvi = recent_ndvi[-1]['ndvi_mean'] if recent_ndvi else None
            avg_ndvi = statistics.mean([p['ndvi_mean'] for p in recent_ndvi]) if recent_ndvi else None
            
            # Calculate trend
            if len(recent_ndvi) >= 2:
                trend = recent_ndvi[-1]['ndvi_mean'] - recent_ndvi[-2]['ndvi_mean']
            else:
                trend = None
            
            clear_obs = sum(1 for p in field['ndvi_time_series'] 
                           if p.get('clear_percentage', 0) > 50)
            total_obs = len(field['ndvi_time_series'])
            
            writer.writerow([
                field['field_name'],
                field['variety'],
                field['sowing_date'],
                field['phenology']['days_since_sowing'],
                field['phenology']['current_stage'],
                round(field['phenology']['accumulated_gdd'], 1),
                round(latest_ndvi, 4) if latest_ndvi else '',
                round(avg_ndvi, 4) if avg_ndvi else '',
                round(trend, 4) if trend else '',
                clear_obs,
                total_obs
            ])


def main():
    """Main analysis function."""
    print("\n" + "=" * 80)
    print("LOADING DATA")
    print("=" * 80)
    
    ndvi_data, phenology_data = load_data()
    
    if not ndvi_data or not phenology_data:
        return
    
    print(f"\n✓ Loaded NDVI data: {len(ndvi_data.get('fields', {}))} fields")
    print(f"✓ Loaded phenology data: {len(phenology_data.get('fields', []))} fields")
    
    # Combine datasets
    combined_data = match_ndvi_to_phenology(ndvi_data, phenology_data)
    print(f"✓ Matched {len(combined_data)} fields with both NDVI and phenology data")
    
    # Generate reports
    print_integrated_report(combined_data)
    
    # Export to CSV
    output_path = 'integrated_ndvi_phenology.csv'
    export_integrated_csv(combined_data, output_path)
    
    print("\n" + "=" * 80)
    print(f"✓ Integrated data exported to: {output_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()

