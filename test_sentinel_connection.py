"""
Test Sentinel Hub connection and fetch NDVI for a few sample fields

Run this before processing all fields to verify your credentials and API access.
"""

import json
from sentinel_ndvi_fetcher import SentinelHubNDVIFetcher


def test_authentication(client_id: str, client_secret: str):
    """Test authentication with Sentinel Hub."""
    print("=" * 80)
    print("TEST 1: AUTHENTICATION")
    print("=" * 80)
    
    fetcher = SentinelHubNDVIFetcher(client_id, client_secret)
    
    try:
        token = fetcher.authenticate()
        print(f"✓ Authentication successful!")
        print(f"  Token: {token[:20]}...{token[-20:]}")
        return fetcher
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        return None


def test_single_field(fetcher: SentinelHubNDVIFetcher, geojson_path: str):
    """Test NDVI fetch for a single field."""
    print("\n" + "=" * 80)
    print("TEST 2: FETCH NDVI FOR SAMPLE FIELD")
    print("=" * 80)
    
    # Load GeoJSON
    with open(geojson_path, 'r') as f:
        data = json.load(f)
    
    # Find a field with valid sowing date
    test_field = None
    for feature in data['features']:
        sowing_date = feature['properties'].get('sowing_date')
        if sowing_date and sowing_date != 'N/A':
            test_field = feature
            break
    
    if not test_field:
        print("✗ No valid test field found")
        return False
    
    props = test_field['properties']
    geom = test_field['geometry']
    
    field_name = props.get('field_name', 'Test Field')
    sowing_date = props.get('sowing_date')
    variety = props.get('wheat_variety', 'Unknown')
    
    print(f"\nTest Field: {field_name}")
    print(f"Variety: {variety}")
    print(f"Sowing Date: {sowing_date}")
    
    try:
        ndvi_data = fetcher.fetch_ndvi_time_series(
            field_name,
            geom,
            sowing_date
        )
        
        if ndvi_data:
            print(f"\n✓ Successfully fetched {len(ndvi_data)} time periods")
            
            # Show sample data
            print("\nSample NDVI data:")
            print("─" * 80)
            print(f"{'Period':25} {'NDVI Mean':12} {'Clear %':10} {'Samples':10}")
            print("─" * 80)
            
            for period in ndvi_data[:5]:  # Show first 5 periods
                period_str = f"{period['from']} to {period['to']}"
                ndvi = period.get('ndvi_mean', 0)
                clear = period.get('clear_percentage', 0)
                samples = period.get('sample_count', 0)
                
                print(f"{period_str:25} {ndvi:12.4f} {clear:10.1f} {samples:10}")
            
            if len(ndvi_data) > 5:
                print(f"... and {len(ndvi_data) - 5} more periods")
            
            # Show latest NDVI
            if ndvi_data:
                latest = ndvi_data[-1]
                print(f"\n📊 Latest NDVI: {latest.get('ndvi_mean', 0):.3f}")
                print(f"   Period: {latest['from']} to {latest['to']}")
                print(f"   Clear pixels: {latest.get('clear_percentage', 0):.1f}%")
            
            return True
        else:
            print("✗ No NDVI data returned")
            return False
            
    except Exception as e:
        print(f"✗ Error fetching NDVI: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_fields(fetcher: SentinelHubNDVIFetcher, geojson_path: str, num_fields: int = 3):
    """Test NDVI fetch for multiple fields."""
    print("\n" + "=" * 80)
    print(f"TEST 3: FETCH NDVI FOR {num_fields} SAMPLE FIELDS")
    print("=" * 80)
    
    with open(geojson_path, 'r') as f:
        data = json.load(f)
    
    # Get first N fields with valid sowing dates
    test_fields = []
    for feature in data['features']:
        sowing_date = feature['properties'].get('sowing_date')
        if sowing_date and sowing_date != 'N/A':
            test_fields.append(feature)
            if len(test_fields) >= num_fields:
                break
    
    success_count = 0
    
    for idx, feature in enumerate(test_fields, 1):
        props = feature['properties']
        geom = feature['geometry']
        
        field_name = props.get('field_name', f'Field {idx}')
        sowing_date = props.get('sowing_date')
        
        print(f"\n[{idx}/{num_fields}] Testing {field_name}...")
        
        try:
            ndvi_data = fetcher.fetch_ndvi_time_series(
                field_name,
                geom,
                sowing_date
            )
            
            if ndvi_data:
                success_count += 1
                latest = ndvi_data[-1]
                print(f"  ✓ Success - Latest NDVI: {latest.get('ndvi_mean', 0):.3f}")
            else:
                print(f"  ✗ No data returned")
        
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print(f"\n{'─' * 80}")
    print(f"Results: {success_count}/{num_fields} fields successful")
    
    return success_count == num_fields


def main():
    """Run all tests."""
    # Configuration - load from environment variables
    import os
    CLIENT_ID = os.getenv("SENTINEL_HUB_CLIENT_ID")
    CLIENT_SECRET = os.getenv("SENTINEL_HUB_CLIENT_SECRET")
    
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Error: SENTINEL_HUB_CLIENT_ID and SENTINEL_HUB_CLIENT_SECRET must be set as environment variables")
        return
    GEOJSON_PATH = "agricultural_fields_with_data.geojson"
    
    print("\n" + "=" * 80)
    print("SENTINEL HUB CONNECTION TEST")
    print("=" * 80)
    print("\nThis script will:")
    print("1. Test authentication with Sentinel Hub")
    print("2. Fetch NDVI for one sample field")
    print("3. Fetch NDVI for three sample fields")
    print("\nIf all tests pass, you can proceed with fetching data for all fields.")
    print("=" * 80)
    
    # Test 1: Authentication
    fetcher = test_authentication(CLIENT_ID, CLIENT_SECRET)
    if not fetcher:
        print("\n" + "=" * 80)
        print("❌ TESTS FAILED - Authentication issue")
        print("=" * 80)
        print("\nPlease check your credentials:")
        print("  - CLIENT_ID: Are you using the correct OAuth client ID?")
        print("  - CLIENT_SECRET: Are you using the correct OAuth client secret?")
        print("\nYou can find these at: https://apps.sentinel-hub.com/dashboard/#/account/settings")
        return
    
    # Test 2: Single field
    try:
        single_success = test_single_field(fetcher, GEOJSON_PATH)
    except FileNotFoundError:
        print(f"\n✗ Error: Could not find {GEOJSON_PATH}")
        print("Make sure you're running this script from the project directory")
        return
    
    if not single_success:
        print("\n" + "=" * 80)
        print("❌ TESTS FAILED - Could not fetch NDVI for test field")
        print("=" * 80)
        print("\nPossible issues:")
        print("  - No Sentinel-2 data available for the time period")
        print("  - Too much cloud coverage")
        print("  - Field geometry is invalid")
        print("  - API quota exceeded")
        return
    
    # Test 3: Multiple fields
    multi_success = test_multiple_fields(fetcher, GEOJSON_PATH, num_fields=3)
    
    # Summary
    print("\n" + "=" * 80)
    if single_success and multi_success:
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        print("\nYour Sentinel Hub connection is working correctly!")
        print("\nNext steps:")
        print("1. Run the full NDVI fetch:")
        print("   python3 sentinel_ndvi_fetcher.py")
        print("\n2. This will process all 69 fields (~30-60 minutes)")
        print("\n3. After completion, integrate with phenology:")
        print("   python3 integrate_ndvi_phenology.py")
    else:
        print("❌ SOME TESTS FAILED")
        print("=" * 80)
        print("\nPlease review the errors above before proceeding.")
    
    print("=" * 80)


if __name__ == "__main__":
    main()

