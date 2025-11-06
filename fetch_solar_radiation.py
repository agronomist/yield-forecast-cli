"""
Fetch Solar Radiation Data and Calculate PAR

This script fetches daily solar radiation data from Open-Meteo API
and calculates Photosynthetically Active Radiation (PAR) for each field.

PAR is approximately 45% of total solar radiation.
"""

import json
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List
import time


def fetch_solar_radiation_data(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str
) -> List[Dict]:
    """
    Fetch solar radiation data from Open-Meteo API.
    
    Args:
        latitude: Latitude of location
        longitude: Longitude of location
        start_date: Start date in 'YYYY-MM-DD' format
        end_date: End date in 'YYYY-MM-DD' format
        
    Returns:
        List of daily solar radiation records
    """
    url = "https://archive-api.open-meteo.com/v1/archive"
    
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "shortwave_radiation_sum",  # Total solar radiation (MJ/m²)
        "timezone": "America/Argentina/Buenos_Aires"
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Parse the response
        radiation_records = []
        daily = data.get('daily', {})
        dates = daily.get('time', [])
        radiation_list = daily.get('shortwave_radiation_sum', [])
        
        for i, date in enumerate(dates):
            # Convert from MJ/m² to usable format
            total_radiation = radiation_list[i] if radiation_list[i] is not None else None
            
            # Calculate PAR (approximately 45% of total solar radiation)
            if total_radiation is not None:
                par = total_radiation * 0.45
            else:
                par = None
            
            radiation_records.append({
                'date': date,
                'total_radiation_MJ': total_radiation,  # Total solar radiation (MJ/m²/day)
                'PAR_MJ': par  # Photosynthetically Active Radiation (MJ/m²/day)
            })
        
        return radiation_records
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching solar radiation data: {e}")
        return []


def process_all_fields_radiation(geojson_path: str) -> Dict:
    """
    Fetch solar radiation data for all fields.
    
    Args:
        geojson_path: Path to GeoJSON file with field data
        
    Returns:
        Dictionary with radiation data for each field
    """
    print("=" * 80)
    print("SOLAR RADIATION DATA FETCHER")
    print("=" * 80)
    print("\nFetching daily solar radiation and calculating PAR...")
    print("PAR = Total Solar Radiation × 0.45")
    
    # Load field data
    with open(geojson_path, 'r') as f:
        data = json.load(f)
    
    # Get date range from all fields
    sowing_dates = []
    for feature in data['features']:
        sowing_date = feature['properties'].get('sowing_date')
        if sowing_date and sowing_date != 'N/A':
            sowing_dates.append(datetime.strptime(sowing_date, '%Y-%m-%d'))
    
    if not sowing_dates:
        print("Error: No valid sowing dates found")
        return {}
    
    earliest_sowing = min(sowing_dates)
    today = datetime.now()
    
    print(f"\nDate range: {earliest_sowing.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}")
    print(f"Total days: {(today - earliest_sowing).days}")
    
    # Get approximate center coordinates for Las Petacas region
    center_lat = -32.51
    center_lon = -61.43
    
    print(f"\nLocation: {center_lat}°S, {abs(center_lon)}°W (Las Petacas, Argentina)")
    print("\nFetching solar radiation data from Open-Meteo API...")
    
    # Fetch radiation data
    radiation_data = fetch_solar_radiation_data(
        center_lat,
        center_lon,
        earliest_sowing.strftime('%Y-%m-%d'),
        today.strftime('%Y-%m-%d')
    )
    
    if not radiation_data:
        print("✗ Failed to fetch radiation data")
        return {}
    
    print(f"✓ Fetched {len(radiation_data)} days of solar radiation data")
    
    # Calculate statistics
    valid_radiation = [r['total_radiation_MJ'] for r in radiation_data if r['total_radiation_MJ'] is not None]
    valid_par = [r['PAR_MJ'] for r in radiation_data if r['PAR_MJ'] is not None]
    
    if valid_radiation:
        print(f"\n{'─' * 80}")
        print("SOLAR RADIATION STATISTICS")
        print(f"{'─' * 80}")
        print(f"Total Radiation (MJ/m²/day):")
        print(f"  Mean:   {sum(valid_radiation)/len(valid_radiation):.2f}")
        print(f"  Min:    {min(valid_radiation):.2f}")
        print(f"  Max:    {max(valid_radiation):.2f}")
        print(f"\nPAR (MJ/m²/day):")
        print(f"  Mean:   {sum(valid_par)/len(valid_par):.2f}")
        print(f"  Min:    {min(valid_par):.2f}")
        print(f"  Max:    {max(valid_par):.2f}")
    
    # Create field-specific data
    results = {}
    
    for feature in data['features']:
        props = feature['properties']
        field_name = props.get('field_name', 'Unknown')
        sowing_date = props.get('sowing_date')
        variety = props.get('wheat_variety', 'Unknown')
        
        if not sowing_date or sowing_date == 'N/A':
            continue
        
        # Get coordinates for field (use center)
        geom = feature['geometry']
        coords = geom['coordinates'][0]
        lats = [c[1] for c in coords]
        lons = [c[0] for c in coords]
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        
        # Filter radiation data from sowing date onwards
        sowing_dt = datetime.strptime(sowing_date, '%Y-%m-%d')
        field_radiation = [
            r for r in radiation_data 
            if datetime.strptime(r['date'], '%Y-%m-%d') >= sowing_dt
        ]
        
        results[field_name] = {
            'variety': variety,
            'sowing_date': sowing_date,
            'latitude': center_lat,
            'longitude': center_lon,
            'radiation_data': field_radiation
        }
    
    print(f"\n✓ Processed radiation data for {len(results)} fields")
    
    return results


def save_radiation_data(results: Dict, output_json: str, output_csv: str):
    """
    Save radiation data to JSON and CSV files.
    
    Args:
        results: Dictionary with radiation data
        output_json: Path for JSON output
        output_csv: Path for CSV output
    """
    # Save JSON
    output_data = {
        'fetch_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'location': 'Las Petacas, Argentina (-32.51, -61.43)',
        'data_source': 'Open-Meteo Archive API',
        'par_calculation': 'PAR = Total Solar Radiation × 0.45',
        'units': {
            'total_radiation': 'MJ/m²/day',
            'PAR': 'MJ/m²/day'
        },
        'fields': results
    }
    
    with open(output_json, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n✓ Saved JSON to: {output_json}")
    
    # Create CSV
    rows = []
    for field_name, field_data in results.items():
        variety = field_data['variety']
        sowing_date = field_data['sowing_date']
        
        sowing_dt = datetime.strptime(sowing_date, '%Y-%m-%d')
        
        for rad in field_data['radiation_data']:
            date = rad['date']
            date_dt = datetime.strptime(date, '%Y-%m-%d')
            days_since_sowing = (date_dt - sowing_dt).days
            
            rows.append({
                'Field Name': field_name,
                'Variety': variety,
                'Sowing Date': sowing_date,
                'Date': date,
                'Days Since Sowing': days_since_sowing,
                'Total Radiation (MJ/m²)': rad['total_radiation_MJ'],
                'PAR (MJ/m²)': rad['PAR_MJ']
            })
    
    df = pd.DataFrame(rows)
    df.to_csv(output_csv, index=False)
    
    print(f"✓ Saved CSV to: {output_csv}")
    
    # Print summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    print(f"Total records: {len(df)}")
    print(f"Fields: {df['Field Name'].nunique()}")
    print(f"Date range: {df['Date'].min()} to {df['Date'].max()}")
    print(f"Average PAR: {df['PAR (MJ/m²)'].mean():.2f} MJ/m²/day")


def create_sample_analysis(csv_path: str):
    """Create a sample analysis showing PAR data."""
    df = pd.read_csv(csv_path)
    
    print(f"\n{'=' * 80}")
    print("SAMPLE FIELD: DAILY PAR VALUES")
    print(f"{'=' * 80}")
    
    # Show one field as example
    sample_field = df['Field Name'].iloc[0]
    sample = df[df['Field Name'] == sample_field].head(20)
    
    print(f"\nField: {sample_field}")
    print(f"\n{'Date':12} {'Days':6} {'Total Rad (MJ/m²)':18} {'PAR (MJ/m²)':15}")
    print("─" * 80)
    
    for _, row in sample.iterrows():
        print(f"{row['Date']:12} {int(row['Days Since Sowing']):6} "
              f"{row['Total Radiation (MJ/m²)']:18.2f} {row['PAR (MJ/m²)']:15.2f}")
    
    print(f"\n... (showing first 20 days)")
    
    # Monthly averages
    print(f"\n{'─' * 80}")
    print("MONTHLY PAR AVERAGES")
    print(f"{'─' * 80}")
    
    df['Date'] = pd.to_datetime(df['Date'])
    df['Month'] = df['Date'].dt.strftime('%Y-%m')
    monthly = df.groupby('Month')['PAR (MJ/m²)'].mean()
    
    print(f"\n{'Month':10} {'Avg PAR (MJ/m²/day)':20}")
    print("─" * 40)
    for month, par in monthly.items():
        print(f"{month:10} {par:20.2f}")


if __name__ == "__main__":
    GEOJSON_PATH = "agricultural_fields_with_data.geojson"
    OUTPUT_JSON = "solar_radiation_par_data.json"
    OUTPUT_CSV = "solar_radiation_par_data.csv"
    
    try:
        # Fetch radiation data
        results = process_all_fields_radiation(GEOJSON_PATH)
        
        if results:
            # Save data
            save_radiation_data(results, OUTPUT_JSON, OUTPUT_CSV)
            
            # Create sample analysis
            create_sample_analysis(OUTPUT_CSV)
            
            print(f"\n{'=' * 80}")
            print("✓ SOLAR RADIATION DATA FETCH COMPLETE")
            print(f"{'=' * 80}")
            print("\nYou now have:")
            print("  • Daily PAR values for each field")
            print("  • Data from sowing date to present")
            print("  • Ready for biomass/yield calculations")
            print("\nNext step: Combine PAR + fAPAR + RUE to estimate yield")
        
    except FileNotFoundError:
        print(f"Error: Could not find {GEOJSON_PATH}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

