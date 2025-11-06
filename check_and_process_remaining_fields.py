"""
Check ARPS subscription status and process the 2 remaining fields if ready.
"""

import json
import requests
import os
from datetime import datetime

# Planet API configuration
PLANET_API_KEY = "ef27e53777ca46d6b79a8bac10f02321"

# Subscription IDs from previous creation
SUBSCRIPTIONS = {
    "El 21 Lote 5": {
        "subscription_id": "266559b7-f68b-43dd-b76d-2fef2f1beab6",
        "collection_id": "91231ad9-94eb-49f0-8b4e-d6b45635b5a6"
    },
    "Las Casuarinas 1": {
        "subscription_id": "af0728f6-c13d-4615-a264-8419129435df",
        "collection_id": "7ff1183f-301a-4759-bbd4-a4888df8af3b"
    }
}


def check_subscription_status(subscription_id):
    """Check the status of a Planet subscription."""
    url = f"https://api.planet.com/subscriptions/v1/{subscription_id}"
    headers = {
        "Authorization": f"api-key {PLANET_API_KEY}"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        subscription_data = response.json()
        return subscription_data
    except Exception as e:
        print(f"  ✗ Error checking status: {e}")
        return None


def main():
    """Check subscriptions and process fields if ready."""
    
    print("=" * 80)
    print("CHECKING ARPS SUBSCRIPTION STATUS")
    print("=" * 80)
    
    # Check status of both subscriptions
    subscription_statuses = {}
    all_ready = True
    
    for field_name, sub_info in SUBSCRIPTIONS.items():
        print(f"\n{field_name}:")
        print(f"  Subscription ID: {sub_info['subscription_id']}")
        print(f"  Collection ID: {sub_info['collection_id']}")
        
        subscription_data = check_subscription_status(sub_info['subscription_id'])
        
        if subscription_data:
            status = subscription_data.get('status', 'unknown')
            print(f"  Status: {status}")
            
            subscription_statuses[field_name] = {
                'status': status,
                'subscription_data': subscription_data,
                **sub_info
            }
            
            if status in ['active', 'completed']:
                print(f"  ✓ Ready for data fetching!")
            elif status == 'preparing':
                print(f"  ⏳ Still preparing...")
                all_ready = False
            else:
                print(f"  ⚠️  Status: {status}")
                all_ready = False
        else:
            print(f"  ✗ Could not retrieve status")
            all_ready = False
    
    # Save status report
    status_report = {
        'checked_at': datetime.now().isoformat(),
        'subscriptions': subscription_statuses,
        'all_ready': all_ready
    }
    
    with open('arps_subscription_status_check.json', 'w') as f:
        json.dump(status_report, f, indent=2)
    
    print("\n" + "=" * 80)
    print("STATUS SUMMARY")
    print("=" * 80)
    
    if all_ready:
        print("\n✓ All subscriptions are active! Ready to process fields.")
        print("\nNext steps:")
        print("  1. Fetch ARPS NDVI data")
        print("  2. Clean NDVI data")
        print("  3. Fetch solar radiation")
        print("  4. Generate phenology predictions")
        print("  5. Run yield predictions")
        print("\nRun: python process_remaining_2_fields.py")
    else:
        print("\n⏳ Some subscriptions are not ready yet.")
        print("\nSubscription statuses:")
        for field_name, info in subscription_statuses.items():
            print(f"  • {field_name}: {info['status']}")
        print("\nPlease check back later or monitor at:")
        print("  https://www.planet.com/account/#/subscriptions")
    
    print("\n✓ Saved status check to: arps_subscription_status_check.json")
    print("=" * 80)
    
    return all_ready, subscription_statuses


if __name__ == "__main__":
    main()

