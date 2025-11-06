"""
Fetch ARPS NDVI data for the 3 missing fields:
- El 21 Lote 5
- Las Casuarinas 1  
- Ferito Lote 3
"""

import json
import os
import sys

# Import the ARPS fetcher
from arps_ndvi_fetcher import ARPSNDVIFetcher

# Sentinel Hub credentials
CLIENT_ID = os.getenv("SENTINEL_HUB_CLIENT_ID")
CLIENT_SECRET = os.getenv("SENTINEL_HUB_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    raise ValueError("SENTINEL_HUB_CLIENT_ID and SENTINEL_HUB_CLIENT_SECRET must be set as environment variables")

# Field assignments based on geographic location
# Area_1: Western region (Las Casuarinas)
# Area_2: Central/Eastern region (Don Adolfo, Centeno, Ferito, Cassina, El 21)
# Area_3: Far west region (La Pobladora, Giuggia)
FIELD_AREAS = {
    "El 21 Lote 5": "Area_2",  # Close to Don Adolfo region
    "Las Casuarinas 1": "Area_1",  # Western region
    "Ferito Lote 3": "Area_2"  # Same region as Ferito Lote 2
}


def main():
    """Fetch ARPS data for 3 missing fields."""
    print("=" * 80)
    print("FETCHING ARPS NDVI DATA FOR 3 MISSING FIELDS")
    print("=" * 80)
    
    # Load GeoJSON with all 15 fields
    geojson_path = "more_fields/new_fields_data.geojson"
    with open(geojson_path, 'r') as f:
        geojson = json.load(f)
    
    # Initialize fetcher
    fetcher = ARPSNDVIFetcher(CLIENT_ID, CLIENT_SECRET)
    
    # Create output directories
    raw_dir = "more_fields/arps_ndvi_data"
    cleaned_dir = "more_fields/arps_ndvi_data_cleaned"
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(cleaned_dir, exist_ok=True)
    
    # Filter to only the 3 missing fields
    missing_fields = ["El 21 Lote 5", "Las Casuarinas 1", "Ferito Lote 3"]
    
    success_count = 0
    
    for i, feature in enumerate(geojson['features'], 1):
        props = feature['properties']
        field_name = props['field_name']
        
        if field_name not in missing_fields:
            continue
        
        sowing_date = props['sowing_date']
        variety = props['wheat_variety']
        geometry = feature['geometry']
        
        print(f"\n{i}. {field_name}")
        print(f"   Variety: {variety}")
        print(f"   Sowing: {sowing_date}")
        
        # Get area assignment
        field_area = FIELD_AREAS.get(field_name)
        if not field_area:
            print(f"   ✗ No area assignment found")
            continue
        
        print(f"   Area: {field_area}")
        
        # Get collection ID
        collection_id = fetcher.get_field_collection(field_area)
        if not collection_id:
            print(f"   ✗ No collection ID for {field_area}")
            continue
        
        print(f"   Collection: {collection_id}")
        
        try:
            # Fetch NDVI data
            print(f"   📡 Fetching ARPS NDVI data...")
            observations = fetcher.fetch_ndvi_daily(
                field_name=field_name,
                geometry=geometry,
                sowing_date=sowing_date,
                collection_id=collection_id
            )
            
            if not observations:
                print(f"   ✗ No observations returned")
                continue
            
            # Create output data structure
            output_data = {
                "field_name": field_name,
                "sowing_date": sowing_date,
                "area": field_area,
                "collection_id": collection_id,
                "data_source": "ARPS (PlanetScope 3m)",
                "observations": observations
            }
            
            # Save raw data
            output_filename = f"arps_ndvi_{field_name.replace(' ', '_')}.json"
            raw_path = os.path.join(raw_dir, output_filename)
            
            with open(raw_path, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            # Also save to cleaned directory (will be cleaned later)
            cleaned_path = os.path.join(cleaned_dir, output_filename)
            with open(cleaned_path, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            print(f"   ✓ Saved {len(observations)} observations")
            print(f"   ✓ Date range: {observations[0]['date']} to {observations[-1]['date']}")
            success_count += 1
            
        except Exception as e:
            print(f"   ✗ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print(f"✓ Successfully fetched ARPS data for {success_count}/3 fields")
    print("=" * 80)
    
    if success_count == 3:
        print("\nNext steps:")
        print("  1. Run clean_arps_ndvi.py to clean the new data")
        print("  2. Run process_new_12_fields_arps.py to get solar radiation")
        print("  3. Run predict_yield_arps.py to generate yield predictions")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

