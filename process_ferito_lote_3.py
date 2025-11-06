"""
Process Ferito Lote 3 - fetch solar radiation and phenology data
"""

import json
import os
import requests
from datetime import datetime
from wheat_phenology_model import WheatPhenologyModel


def fetch_solar_radiation(latitude, longitude, sowing_date, end_date):
    """Fetch solar radiation data."""
    url = "https://archive-api.open-meteo.com/v1/archive"
    
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": sowing_date,
        "end_date": end_date,
        "daily": "shortwave_radiation_sum",
        "timezone": "America/Argentina/Buenos_Aires"
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        radiation_records = []
        daily = data.get('daily', {})
        dates = daily.get('time', [])
        radiation_list = daily.get('shortwave_radiation_sum', [])
        
        for i, date in enumerate(dates):
            total_radiation = radiation_list[i] if radiation_list[i] is not None else None
            par = total_radiation * 0.45 if total_radiation is not None else None
            
            radiation_records.append({
                'date': date,
                'total_radiation_MJ': total_radiation,
                'PAR_MJ': par
            })
        
        return radiation_records
    except Exception as e:
        print(f"  ✗ Error fetching solar radiation: {e}")
        return None


def fetch_weather(latitude, longitude, sowing_date, end_date):
    """Fetch weather data for phenology."""
    url = "https://archive-api.open-meteo.com/v1/archive"
    
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": sowing_date,
        "end_date": end_date,
        "daily": "temperature_2m_min,temperature_2m_max",
        "timezone": "America/Argentina/Buenos_Aires"
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        weather_records = []
        daily = data.get('daily', {})
        dates = daily.get('time', [])
        tmin_list = daily.get('temperature_2m_min', [])
        tmax_list = daily.get('temperature_2m_max', [])
        
        for i, date in enumerate(dates):
            weather_records.append({
                'date': date,
                'tmin': tmin_list[i] if tmin_list[i] is not None else 0,
                'tmax': tmax_list[i] if tmax_list[i] is not None else 0
            })
        
        return weather_records
    except Exception as e:
        print(f"  ✗ Error fetching weather data: {e}")
        return None


def main():
    print("=" * 80)
    print("PROCESSING FERITO LOTE 3")
    print("=" * 80)
    
    # Field info
    field_name = "Ferito Lote 3"
    sowing_date = "2025-06-10"
    variety = "DM Pehuen"
    center_lat = -32.22
    center_lon = -61.41
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    print(f"\nField: {field_name}")
    print(f"Variety: {variety}")
    print(f"Sowing: {sowing_date}")
    print(f"Location: {center_lat:.4f}, {center_lon:.4f}")
    
    # Create directories
    solar_dir = "more_fields/solar_radiation_data"
    phenology_dir = "more_fields/phenology_predictions"
    os.makedirs(solar_dir, exist_ok=True)
    os.makedirs(phenology_dir, exist_ok=True)
    
    # Fetch solar radiation
    print("\n📡 Fetching solar radiation...")
    radiation_data = fetch_solar_radiation(center_lat, center_lon, sowing_date, end_date)
    
    if radiation_data:
        solar_output = {
            'field_name': field_name,
            'sowing_date': sowing_date,
            'latitude': center_lat,
            'longitude': center_lon,
            'radiation_data': radiation_data
        }
        
        solar_filename = f"solar_radiation_{field_name.replace(' ', '_')}.json"
        solar_path = os.path.join(solar_dir, solar_filename)
        with open(solar_path, 'w') as f:
            json.dump(solar_output, f, indent=2)
        
        print(f"✓ Saved solar radiation data ({len(radiation_data)} days)")
    else:
        print("✗ Failed to fetch solar radiation")
        return
    
    # Fetch weather and generate phenology
    print("🌡️  Fetching weather data...")
    weather_data = fetch_weather(center_lat, center_lon, sowing_date, end_date)
    
    if weather_data:
        model = WheatPhenologyModel(variety, sowing_date, center_lat)
        phenology = model.estimate_phenology(weather_data)
        
        phenology_filename = f"phenology_{field_name.replace(' ', '_')}.json"
        phenology_path = os.path.join(phenology_dir, phenology_filename)
        
        with open(phenology_path, 'w') as f:
            json.dump({'stages': phenology}, f, indent=2)
        
        print(f"✓ Phenology: {phenology['current_stage']}")
        print(f"✓ GDD: {phenology['accumulated_gdd']}")
    else:
        print("✗ Failed to fetch weather data")
        return
    
    print("\n" + "=" * 80)
    print("✓ Ferito Lote 3 processed successfully")
    print("=" * 80)


if __name__ == "__main__":
    main()

