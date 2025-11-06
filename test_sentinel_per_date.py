"""
Test Sentinel Hub per-date NDVI fetch for a sample field
"""

import json
from sentinel_ndvi_per_date import SentinelHubNDVIPerDateFetcher


def test_per_date_fetch():
    """Test NDVI fetch per date for one sample field."""
    import os
    CLIENT_ID = os.getenv("SENTINEL_HUB_CLIENT_ID")
    CLIENT_SECRET = os.getenv("SENTINEL_HUB_CLIENT_SECRET")
    
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Error: SENTINEL_HUB_CLIENT_ID and SENTINEL_HUB_CLIENT_SECRET must be set as environment variables")
        return
    GEOJSON_PATH = "agricultural_fields_with_data.geojson"
    
    print("=" * 80)
    print("TEST: SENTINEL-2 NDVI PER DATE")
    print("=" * 80)
    
    # Load GeoJSON
    with open(GEOJSON_PATH, 'r') as f:
        data = json.load(f)
    
    # Find first field with valid sowing date
    test_field = None
    for feature in data['features']:
        sowing_date = feature['properties'].get('sowing_date')
        if sowing_date and sowing_date != 'N/A':
            test_field = feature
            break
    
    if not test_field:
        print("✗ No valid test field found")
        return
    
    props = test_field['properties']
    geom = test_field['geometry']
    
    field_name = props.get('field_name', 'Test Field')
    sowing_date = props.get('sowing_date')
    variety = props.get('wheat_variety', 'Unknown')
    
    print(f"\nTest Field: {field_name}")
    print(f"Variety: {variety}")
    print(f"Sowing Date: {sowing_date}")
    print("\n" + "─" * 80)
    
    # Initialize fetcher
    fetcher = SentinelHubNDVIPerDateFetcher(CLIENT_ID, CLIENT_SECRET)
    
    # Fetch NDVI per date
    try:
        ndvi_data = fetcher.fetch_ndvi_per_date(
            field_name,
            geom,
            sowing_date
        )
        
        if ndvi_data:
            print(f"\n✓ Successfully fetched {len(ndvi_data)} cloud-free observations")
            
            # Show all observations
            print("\n" + "─" * 80)
            print("SENTINEL-2 OBSERVATIONS (Cloud Coverage < 30%)")
            print("─" * 80)
            print(f"{'Date':12} {'Days':6} {'NDVI':8} {'Std':8} {'Min':8} {'Max':8} {'Samples':8}")
            print("─" * 80)
            
            from datetime import datetime
            sowing_dt = datetime.strptime(sowing_date, '%Y-%m-%d')
            
            for obs in ndvi_data:
                obs_date = obs['date']
                obs_dt = datetime.strptime(obs_date, '%Y-%m-%d')
                days = (obs_dt - sowing_dt).days
                
                print(f"{obs_date:12} {days:6} "
                      f"{obs['ndvi_mean']:8.4f} "
                      f"{obs['ndvi_std']:8.4f} "
                      f"{obs['ndvi_min']:8.4f} "
                      f"{obs['ndvi_max']:8.4f} "
                      f"{obs['sample_count']:8}")
            
            # Show statistics
            print("\n" + "─" * 80)
            print("SUMMARY")
            print("─" * 80)
            
            ndvi_values = [obs['ndvi_mean'] for obs in ndvi_data]
            print(f"Total observations: {len(ndvi_data)}")
            print(f"NDVI range: {min(ndvi_values):.3f} - {max(ndvi_values):.3f}")
            print(f"Latest NDVI: {ndvi_values[-1]:.3f} (on {ndvi_data[-1]['date']})")
            print(f"Peak NDVI: {max(ndvi_values):.3f}")
            
            # Show NDVI trend
            print(f"\nNDVI Trend:")
            if len(ndvi_data) >= 2:
                early = ndvi_values[0]
                late = ndvi_values[-1]
                change = late - early
                print(f"  First: {early:.3f}")
                print(f"  Latest: {late:.3f}")
                print(f"  Change: {change:+.3f}")
            
            print("\n" + "=" * 80)
            print("✅ TEST PASSED")
            print("=" * 80)
            print("\nReady to run full fetch:")
            print("  python3 sentinel_ndvi_per_date.py")
            
        else:
            print("\n✗ No cloud-free observations found")
            print("This could mean:")
            print("  - Very cloudy period")
            print("  - No Sentinel-2 acquisitions")
            print("  - Try lowering min_clear_percentage")
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_per_date_fetch()

