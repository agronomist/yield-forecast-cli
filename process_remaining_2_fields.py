"""
Complete processing pipeline for the 2 remaining fields:
- El 21 Lote 5
- Las Casuarinas 1

This script:
1. Fetches ARPS NDVI data
2. Cleans NDVI data
3. Fetches solar radiation
4. Generates phenology predictions
5. Runs yield predictions
"""

import json
import os
import sys
import subprocess
from datetime import datetime

# Import modules
from arps_ndvi_fetcher import ARPSNDVIFetcher

# Planet API and Sentinel Hub configuration
# Load from environment variables
import os
PLANET_API_KEY = os.getenv("PLANET_API_KEY")
SENTINEL_HUB_CLIENT_ID = os.getenv("SENTINEL_HUB_CLIENT_ID")
SENTINEL_HUB_CLIENT_SECRET = os.getenv("SENTINEL_HUB_CLIENT_SECRET")

if not all([PLANET_API_KEY, SENTINEL_HUB_CLIENT_ID, SENTINEL_HUB_CLIENT_SECRET]):
    raise ValueError("Missing required environment variables: PLANET_API_KEY, SENTINEL_HUB_CLIENT_ID, SENTINEL_HUB_CLIENT_SECRET")

# Field configurations
REMAINING_FIELDS = {
    "El 21 Lote 5": {
        "sowing_date": "2025-06-06",
        "variety": "DM Pehuen",
        "collection_id": "91231ad9-94eb-49f0-8b4e-d6b45635b5a6",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-60.85442555488483, -33.20861307812412],
                [-60.84469962014776, -33.21043208091229],
                [-60.84256054915575, -33.20218870500533],
                [-60.85227068088382, -33.20041323509318],
                [-60.85442555488483, -33.20861307812412]
            ]]
        },
        "center_lat": -33.207,
        "center_lon": -60.854
    },
    "Las Casuarinas 1": {
        "sowing_date": "2025-05-28",
        "variety": "Baguette 620",
        "collection_id": "7ff1183f-301a-4759-bbd4-a4888df8af3b",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-61.72844308885055, -32.78485763204343],
                [-61.73034935125317, -32.78456420675647],
                [-61.73105488782622, -32.78737299603718],
                [-61.72309067296688, -32.7887746854564],
                [-61.71943410869143, -32.77378599368141],
                [-61.72925977625915, -32.77988063007435],
                [-61.72985601502577, -32.78249862521688],
                [-61.7272529802043, -32.7828852459436],
                [-61.72751616251702, -32.78418834437843],
                [-61.72720321720413, -32.7845372958411],
                [-61.72697251731194, -32.78492536078408],
                [-61.727152561027, -32.78592452640957],
                [-61.7277922682367, -32.78596113611673],
                [-61.72848349375308, -32.78584509609797],
                [-61.72844308885055, -32.78485763204343]
            ]]
        },
        "center_lat": -32.784,
        "center_lon": -61.717
    }
}


def step_1_fetch_arps_data():
    """Step 1: Fetch ARPS NDVI data."""
    print("\n" + "=" * 80)
    print("STEP 1: FETCHING ARPS NDVI DATA")
    print("=" * 80)
    
    fetcher = ARPSNDVIFetcher(SENTINEL_HUB_CLIENT_ID, SENTINEL_HUB_CLIENT_SECRET)
    
    raw_dir = "more_fields/arps_ndvi_data"
    cleaned_dir = "more_fields/arps_ndvi_data_cleaned"
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(cleaned_dir, exist_ok=True)
    
    success_count = 0
    
    for field_name, field_data in REMAINING_FIELDS.items():
        print(f"\n{field_name}:")
        print(f"  Sowing: {field_data['sowing_date']}")
        print(f"  Variety: {field_data['variety']}")
        print(f"  Collection: {field_data['collection_id']}")
        
        try:
            observations = fetcher.fetch_ndvi_daily(
                field_name=field_name,
                geometry=field_data['geometry'],
                sowing_date=field_data['sowing_date'],
                collection_id=field_data['collection_id']
            )
            
            if not observations or len(observations) == 0:
                print(f"  ✗ No observations returned")
                continue
            
            output_data = {
                "field_name": field_name,
                "sowing_date": field_data['sowing_date'],
                "area": "New_Subscription",
                "collection_id": field_data['collection_id'],
                "data_source": "ARPS (PlanetScope 3m)",
                "observations": observations
            }
            
            filename = f"arps_ndvi_{field_name.replace(' ', '_')}.json"
            raw_path = os.path.join(raw_dir, filename)
            cleaned_path = os.path.join(cleaned_dir, filename)
            
            with open(raw_path, 'w') as f:
                json.dump(output_data, f, indent=2)
            with open(cleaned_path, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            print(f"  ✓ Saved {len(observations)} observations")
            print(f"  ✓ Date range: {observations[0]['date']} to {observations[-1]['date']}")
            success_count += 1
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n✓ Fetched ARPS data for {success_count}/2 fields")
    return success_count == 2


def step_2_clean_ndvi():
    """Step 2: Clean ARPS NDVI data."""
    print("\n" + "=" * 80)
    print("STEP 2: CLEANING ARPS NDVI DATA")
    print("=" * 80)
    
    try:
        # Run the cleaning script on more_fields directory
        result = subprocess.run(
            [sys.executable, "clean_arps_ndvi.py"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✓ NDVI cleaning completed")
            return True
        else:
            print(f"✗ Cleaning failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Error running cleaning: {e}")
        return False


def step_3_solar_and_phenology():
    """Step 3: Fetch solar radiation and generate phenology."""
    print("\n" + "=" * 80)
    print("STEP 3: SOLAR RADIATION & PHENOLOGY")
    print("=" * 80)
    
    import requests
    from wheat_phenology_model import WheatPhenologyModel
    
    solar_dir = "more_fields/solar_radiation_data"
    phenology_dir = "more_fields/phenology_predictions"
    os.makedirs(solar_dir, exist_ok=True)
    os.makedirs(phenology_dir, exist_ok=True)
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    success_count = 0
    
    for field_name, field_data in REMAINING_FIELDS.items():
        print(f"\n{field_name}:")
        
        # Fetch solar radiation
        print("  📡 Fetching solar radiation...")
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": field_data['center_lat'],
            "longitude": field_data['center_lon'],
            "start_date": field_data['sowing_date'],
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
            
            solar_output = {
                'field_name': field_name,
                'sowing_date': field_data['sowing_date'],
                'latitude': field_data['center_lat'],
                'longitude': field_data['center_lon'],
                'radiation_data': radiation_records
            }
            
            solar_filename = f"solar_radiation_{field_name.replace(' ', '_')}.json"
            with open(os.path.join(solar_dir, solar_filename), 'w') as f:
                json.dump(solar_output, f, indent=2)
            
            print(f"    ✓ Saved {len(radiation_records)} days")
            
        except Exception as e:
            print(f"    ✗ Error: {e}")
            continue
        
        # Fetch weather and generate phenology
        print("  🌡️  Fetching weather data...")
        params['daily'] = "temperature_2m_min,temperature_2m_max"
        
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
            
            model = WheatPhenologyModel(field_data['variety'], field_data['sowing_date'], 
                                       field_data['center_lat'])
            phenology = model.estimate_phenology(weather_records)
            
            phenology_filename = f"phenology_{field_name.replace(' ', '_')}.json"
            with open(os.path.join(phenology_dir, phenology_filename), 'w') as f:
                json.dump({'stages': phenology}, f, indent=2)
            
            print(f"    ✓ Phenology: {phenology['current_stage']}")
            print(f"    ✓ GDD: {phenology['accumulated_gdd']}")
            success_count += 1
            
        except Exception as e:
            print(f"    ✗ Error: {e}")
    
    print(f"\n✓ Processed {success_count}/2 fields")
    return success_count == 2


def step_4_yield_predictions():
    """Step 4: Run yield predictions."""
    print("\n" + "=" * 80)
    print("STEP 4: YIELD PREDICTIONS")
    print("=" * 80)
    
    try:
        result = subprocess.run(
            [sys.executable, "predict_yield_arps.py"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✓ Yield predictions completed")
            print("\n" + result.stdout)
            return True
        else:
            print(f"✗ Yield predictions failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    """Main processing pipeline."""
    
    print("=" * 80)
    print("PROCESSING REMAINING 2 FIELDS - COMPLETE PIPELINE")
    print("=" * 80)
    print("\nFields to process:")
    for field_name, field_data in REMAINING_FIELDS.items():
        print(f"  • {field_name} ({field_data['variety']}, sown {field_data['sowing_date']})")
    
    results = {}
    
    # Step 1: Fetch ARPS data
    results['fetch_arps'] = step_1_fetch_arps_data()
    if not results['fetch_arps']:
        print("\n✗ Cannot proceed - ARPS data fetch failed")
        return
    
    # Step 2: Clean NDVI
    results['clean_ndvi'] = step_2_clean_ndvi()
    
    # Step 3: Solar radiation and phenology
    results['solar_phenology'] = step_3_solar_and_phenology()
    
    # Step 4: Yield predictions
    results['yield_predictions'] = step_4_yield_predictions()
    
    # Summary
    print("\n" + "=" * 80)
    print("PIPELINE SUMMARY")
    print("=" * 80)
    
    for step, success in results.items():
        status = "✓" if success else "✗"
        print(f"{status} {step}")
    
    all_success = all(results.values())
    
    if all_success:
        print("\n" + "=" * 80)
        print("🎉 ALL STEPS COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print("\nThe 2 remaining fields have been processed.")
        print("Next: Run visualization to include all 83 fields!")
    else:
        print("\n⚠️  Some steps failed. Check errors above.")


if __name__ == "__main__":
    main()

