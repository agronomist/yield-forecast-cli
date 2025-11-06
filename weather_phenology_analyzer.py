"""
Weather Data Fetcher and Phenology Analyzer

This script:
1. Fetches weather data for the Las Petacas region
2. Runs the phenology model for all wheat fields
3. Generates a comprehensive report
"""

import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict
import csv
from wheat_phenology_model import WheatPhenologyModel, process_all_fields


def fetch_weather_data_open_meteo(latitude: float, longitude: float, 
                                   start_date: str, end_date: str) -> List[Dict]:
    """
    Fetch historical weather data from Open-Meteo API (free, no API key required).
    
    Args:
        latitude: Latitude of location
        longitude: Longitude of location
        start_date: Start date in 'YYYY-MM-DD' format
        end_date: End date in 'YYYY-MM-DD' format
        
    Returns:
        List of daily weather records
    """
    url = "https://archive-api.open-meteo.com/v1/archive"
    
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": "America/Argentina/Buenos_Aires"
    }
    
    print(f"Fetching weather data from {start_date} to {end_date}...")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Parse the response
        weather_records = []
        daily = data.get('daily', {})
        dates = daily.get('time', [])
        tmax_list = daily.get('temperature_2m_max', [])
        tmin_list = daily.get('temperature_2m_min', [])
        precip_list = daily.get('precipitation_sum', [])
        
        for i, date in enumerate(dates):
            weather_records.append({
                'date': date,
                'tmax': tmax_list[i] if tmax_list[i] is not None else 20.0,
                'tmin': tmin_list[i] if tmin_list[i] is not None else 10.0,
                'precipitation': precip_list[i] if precip_list[i] is not None else 0.0
            })
        
        print(f"✓ Successfully fetched {len(weather_records)} days of weather data")
        return weather_records
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        print("Using synthetic weather data instead...")
        return generate_synthetic_weather(start_date, end_date)


def generate_synthetic_weather(start_date: str, end_date: str) -> List[Dict]:
    """
    Generate synthetic weather data for testing purposes.
    Based on typical Argentine winter wheat growing season temperatures.
    
    Args:
        start_date: Start date in 'YYYY-MM-DD' format
        end_date: End date in 'YYYY-MM-DD' format
        
    Returns:
        List of synthetic daily weather records
    """
    import math
    
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    weather_records = []
    current = start
    
    print("Generating synthetic weather data...")
    
    while current <= end:
        # Day of year (for seasonal variation)
        doy = current.timetuple().tm_yday
        
        # Simulate seasonal temperature variation (Southern Hemisphere)
        # Winter (June-August): cooler
        # Spring (September-November): warming
        # Summer starts in December
        
        # Base temperature varies by season
        if 152 <= doy <= 243:  # June-August (winter)
            base_tmax = 16.0
            base_tmin = 6.0
        elif 244 <= doy <= 334:  # September-November (spring)
            base_tmax = 22.0 + (doy - 244) * 0.1  # Warming trend
            base_tmin = 10.0 + (doy - 244) * 0.06
        else:  # December onwards (summer)
            base_tmax = 28.0
            base_tmin = 18.0
        
        # Add some random variation
        import random
        daily_variation_max = random.gauss(0, 3)
        daily_variation_min = random.gauss(0, 2)
        
        tmax = base_tmax + daily_variation_max
        tmin = base_tmin + daily_variation_min
        
        # Ensure tmin < tmax
        if tmin >= tmax:
            tmin = tmax - 3
        
        # Random precipitation (typical for the region)
        precip = max(0, random.gauss(2, 5)) if random.random() < 0.3 else 0
        
        weather_records.append({
            'date': current.strftime('%Y-%m-%d'),
            'tmax': round(tmax, 1),
            'tmin': round(tmin, 1),
            'precipitation': round(precip, 1)
        })
        
        current += timedelta(days=1)
    
    print(f"✓ Generated {len(weather_records)} days of synthetic weather data")
    return weather_records


def analyze_fields(geojson_path: str, output_path: str = None):
    """
    Analyze all fields and generate phenology report.
    
    Args:
        geojson_path: Path to GeoJSON file
        output_path: Path for output JSON file (optional)
    """
    print("\n" + "=" * 70)
    print("WHEAT PHENOLOGY ANALYSIS - Las Petacas Fields")
    print("=" * 70)
    
    # Load field data to determine date range
    with open(geojson_path, 'r') as f:
        data = json.load(f)
    
    # Get earliest sowing date
    sowing_dates = []
    for feature in data['features']:
        sowing_date = feature['properties'].get('sowing_date')
        if sowing_date and sowing_date != 'N/A':
            sowing_dates.append(datetime.strptime(sowing_date, '%Y-%m-%d'))
    
    if not sowing_dates:
        print("Error: No valid sowing dates found in the data")
        return
    
    earliest_sowing = min(sowing_dates)
    today = datetime.now()
    
    # Get approximate center coordinates for weather data
    # Using approximate center of Las Petacas region
    center_lat = -32.51
    center_lon = -61.43
    
    print(f"\nField Location: {center_lat}°S, {abs(center_lon)}°W")
    print(f"Analysis Period: {earliest_sowing.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}")
    print(f"Days of Growth: {(today - earliest_sowing).days} days")
    
    # Fetch weather data
    weather_data = fetch_weather_data_open_meteo(
        center_lat, 
        center_lon,
        earliest_sowing.strftime('%Y-%m-%d'),
        today.strftime('%Y-%m-%d')
    )
    
    if not weather_data:
        print("Failed to obtain weather data")
        return
    
    print(f"\n{'─' * 70}")
    print("Processing fields...")
    print(f"{'─' * 70}\n")
    
    # Process all fields
    results = process_all_fields(geojson_path, weather_data)
    
    # Generate summary statistics
    stage_counts = {}
    variety_stages = {}
    
    for result in results:
        stage = result['current_stage']
        variety = result['variety']
        
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
        
        if variety not in variety_stages:
            variety_stages[variety] = {}
        variety_stages[variety][stage] = variety_stages[variety].get(stage, 0) + 1
    
    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY REPORT")
    print("=" * 70)
    print(f"\nTotal Fields Analyzed: {len(results)}")
    print(f"\nCurrent Growth Stage Distribution:")
    print("─" * 50)
    for stage, count in sorted(stage_counts.items(), key=lambda x: -x[1]):
        percentage = (count / len(results)) * 100
        print(f"  {stage:35} {count:3} fields ({percentage:5.1f}%)")
    
    print(f"\n{'─' * 70}")
    print("Growth Stages by Variety:")
    print(f"{'─' * 70}")
    for variety, stages in sorted(variety_stages.items()):
        print(f"\n{variety}:")
        for stage, count in sorted(stages.items()):
            print(f"  → {stage:30} {count} field(s)")
    
    # Print detailed field information
    print(f"\n{'=' * 70}")
    print("DETAILED FIELD ANALYSIS")
    print("=" * 70)
    
    for result in sorted(results, key=lambda x: x['accumulated_gdd'], reverse=True):
        print(f"\n{result['field_name']}")
        print(f"  Variety: {result['variety']}")
        print(f"  Sowing Date: {result['sowing_date']}")
        print(f"  Days Since Sowing: {result['days_since_sowing']}")
        print(f"  Accumulated GDD: {result['accumulated_gdd']}°C·days")
        print(f"  Current Stage: {result['current_stage']} ({result['stage_progress']:.1f}% progress)")
        
        # Print achieved stages with dates
        stages_achieved = []
        for stage_name, stage_date in result['stage_dates'].items():
            if stage_date and stage_name != 'sowing':
                stages_achieved.append(f"{stage_name.title()}: {stage_date}")
        
        if stages_achieved:
            print(f"  Stages Achieved:")
            for stage_info in stages_achieved:
                print(f"    - {stage_info}")
    
    # Save results to JSON
    if output_path is None:
        output_path = 'phenology_analysis_results.json'
    
    output_data = {
        'analysis_date': today.strftime('%Y-%m-%d'),
        'location': {'latitude': center_lat, 'longitude': center_lon},
        'summary': {
            'total_fields': len(results),
            'stage_distribution': stage_counts,
            'variety_stages': variety_stages
        },
        'fields': results
    }
    
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n{'=' * 70}")
    print(f"✓ Analysis complete! Results saved to: {output_path}")
    print("=" * 70)
    
    # Also create a CSV for easy viewing in spreadsheet software
    csv_path = output_path.replace('.json', '.csv')
    export_to_csv(results, csv_path)
    print(f"✓ CSV export saved to: {csv_path}")
    
    return results


def export_to_csv(results: List[Dict], csv_path: str):
    """Export results to CSV format."""
    if not results:
        return
    
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            'Field Name', 'Variety', 'Sowing Date', 'Days Since Sowing',
            'Accumulated GDD', 'Current Stage', 'Stage Progress %',
            'Emergence Date', 'Tillering Date', 'Stem Extension Date',
            'Heading Date', 'Grain Fill Date', 'Maturity Date'
        ])
        
        # Data rows
        for result in results:
            stages = result['stage_dates']
            writer.writerow([
                result['field_name'],
                result['variety'],
                result['sowing_date'],
                result['days_since_sowing'],
                result['accumulated_gdd'],
                result['current_stage'],
                result['stage_progress'],
                stages.get('emergence', ''),
                stages.get('tillering', ''),
                stages.get('stem_extension', ''),
                stages.get('heading', ''),
                stages.get('grain_fill', ''),
                stages.get('maturity', '')
            ])


if __name__ == "__main__":
    # Run the analysis
    geojson_path = 'agricultural_fields_with_data.geojson'
    
    try:
        analyze_fields(geojson_path)
    except FileNotFoundError:
        print(f"Error: Could not find {geojson_path}")
        print("Make sure you're running this script from the project directory")
    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()

