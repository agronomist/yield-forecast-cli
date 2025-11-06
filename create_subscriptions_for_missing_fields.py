"""
Create ARPS subscriptions for the 2 missing fields:
- El 21 Lote 5
- Las Casuarinas 1
"""

import json
import requests
from datetime import datetime, timedelta

# Configuration
PLANET_API_KEY = "ef27e53777ca46d6b79a8bac10f02321"

# Field definitions
MISSING_FIELDS = {
    "El 21 Lote 5": {
        "sowing_date": "2025-06-06",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-60.85442555488483, -33.20861307812412, 0],
                [-60.84469962014776, -33.21043208091229, 0],
                [-60.84256054915575, -33.20218870500533, 0],
                [-60.85227068088382, -33.20041323509318, 0],
                [-60.85442555488483, -33.20861307812412, 0]
            ]]
        }
    },
    "Las Casuarinas 1": {
        "sowing_date": "2025-05-28",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-61.72844308885055, -32.78485763204343, 0],
                [-61.73034935125317, -32.78456420675647, 0],
                [-61.73105488782622, -32.78737299603718, 0],
                [-61.72309067296688, -32.7887746854564, 0],
                [-61.71943410869143, -32.77378599368141, 0],
                [-61.72925977625915, -32.77988063007435, 0],
                [-61.72985601502577, -32.78249862521688, 0],
                [-61.7272529802043, -32.7828852459436, 0],
                [-61.72751616251702, -32.78418834437843, 0],
                [-61.72720321720413, -32.7845372958411, 0],
                [-61.72697251731194, -32.78492536078408, 0],
                [-61.727152561027, -32.78592452640957, 0],
                [-61.7277922682367, -32.78596113611673, 0],
                [-61.72848349375308, -32.78584509609797, 0],
                [-61.72844308885055, -32.78485763204343, 0]
            ]]
        }
    }
}


def create_subscription_for_field(field_name, field_data):
    """Create an ARPS subscription for a single field."""
    
    print(f"\n{'=' * 80}")
    print(f"Creating subscription for: {field_name}")
    print('=' * 80)
    
    sowing_date = datetime.strptime(field_data['sowing_date'], '%Y-%m-%d')
    
    # Date range: 1 week before sowing to 1 week from today
    start_date = sowing_date - timedelta(days=7)
    end_date = datetime.now() + timedelta(days=7)
    
    start_time = start_date.strftime('%Y-%m-%dT00:00:00.0Z')
    end_time = end_date.strftime('%Y-%m-%dT23:59:59.0Z')
    
    # Format geometry for Planet API (convert to GeoJSON format expected by Planet)
    # Planet API expects coordinates as [lon, lat] pairs
    polygon_coords = field_data['geometry']['coordinates'][0]
    # Remove altitude (3rd element) if present
    formatted_coords = [[coord[0], coord[1]] for coord in polygon_coords]
    
    subscription_request = {
        "name": f"ARPS Subscription - {field_name}",
        "source": {
            "parameters": {
                "id": "PS_ARD_SR_DAILY",
                "start_time": start_time,
                "end_time": end_time,
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [formatted_coords]
                }
            }
        },
        "hosting": {
            "type": "sentinel_hub"
        }
    }
    
    # Save request
    request_filename = f"arps_subscription_request_{field_name.replace(' ', '_')}.json"
    with open(request_filename, 'w') as f:
        json.dump(subscription_request, f, indent=2)
    print(f"✓ Saved request to: {request_filename}")
    
    # Make API request
    headers = {
        "Authorization": f"api-key {PLANET_API_KEY}",
        "Content-Type": "application/json"
    }
    
    url = "https://api.planet.com/subscriptions/v1"
    
    try:
        print(f"  📡 Submitting subscription request...")
        response = requests.post(url, json=subscription_request, headers=headers)
        
        if response.status_code in [200, 201]:
            subscription_data = response.json()
            print(f"  ✓ Subscription created successfully!")
            print(f"    Subscription ID: {subscription_data.get('id', 'N/A')}")
            print(f"    Status: {subscription_data.get('status', 'N/A')}")
            
            # Extract collection_id if returned
            collection_id = None
            if 'hosting' in subscription_data and 'parameters' in subscription_data['hosting']:
                collection_id = subscription_data['hosting']['parameters'].get('collection_id')
                if collection_id:
                    print(f"    Collection ID: {collection_id}")
            
            return {
                'field_name': field_name,
                'subscription_id': subscription_data.get('id'),
                'status': subscription_data.get('status'),
                'collection_id': collection_id,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'subscription_data': subscription_data
            }
        else:
            print(f"  ✗ Failed to create subscription")
            print(f"    Status Code: {response.status_code}")
            print(f"    Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Create subscriptions for both missing fields."""
    
    print("\n" + "=" * 80)
    print("CREATING ARPS SUBSCRIPTIONS FOR 2 MISSING FIELDS")
    print("=" * 80)
    
    subscriptions = []
    
    for field_name, field_data in MISSING_FIELDS.items():
        result = create_subscription_for_field(field_name, field_data)
        if result:
            subscriptions.append(result)
    
    # Save summary
    summary = {
        'created_at': datetime.now().isoformat(),
        'subscriptions': subscriptions,
        'total_created': len(subscriptions)
    }
    
    with open('arps_subscriptions_missing_fields.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print("\n" + "=" * 80)
    print("SUBSCRIPTION CREATION SUMMARY")
    print("=" * 80)
    print(f"\nSuccessfully created {len(subscriptions)} subscriptions:")
    
    for sub in subscriptions:
        print(f"\n  • {sub['field_name']}:")
        print(f"    Subscription ID: {sub['subscription_id']}")
        print(f"    Status: {sub['status']}")
        if sub['collection_id']:
            print(f"    Collection ID: {sub['collection_id']}")
        print(f"    Date range: {sub['start_date']} to {sub['end_date']}")
    
    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("1. Monitor subscription status at: https://www.planet.com/account/#/subscriptions")
    print("2. Data will be delivered to Sentinel Hub once subscription is active")
    print("3. Once data is available, run:")
    print("   - fetch_arps_missing_3_fields.py (will fetch for El 21 and Las Casuarinas)")
    print("   - clean_arps_ndvi.py")
    print("   - predict_yield_arps.py")
    print("\n✓ Saved subscription summary to: arps_subscriptions_missing_fields.json")


if __name__ == "__main__":
    main()

