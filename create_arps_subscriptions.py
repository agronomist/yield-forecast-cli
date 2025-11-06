"""
Create ARPS (Analysis-Ready PlanetScope) subscriptions for field clusters

This script:
1. Loads all 80 fields
2. Clusters them geographically into 2-3 areas
3. Creates convex hulls around each cluster
4. Creates Planet ARPS subscriptions delivered to Sentinel Hub
"""

import json
import requests
from datetime import datetime, timedelta
from sklearn.cluster import KMeans
import numpy as np
from shapely.geometry import Point, Polygon, MultiPoint, shape
from shapely.ops import unary_union
import pandas as pd


# Configuration
PLANET_API_KEY = "ef27e53777ca46d6b79a8bac10f02321"
SENTINEL_HUB_COLLECTION_ID = None  # Will be created/assigned by Sentinel Hub

# Number of clusters (areas)
N_CLUSTERS = 3


def load_all_fields():
    """Load all 80 fields from original and new data."""
    
    print("\n" + "=" * 80)
    print("LOADING ALL FIELDS")
    print("=" * 80)
    
    all_fields = []
    
    # Load original fields
    try:
        with open('agricultural_fields_with_data.geojson', 'r') as f:
            original_data = json.load(f)
            for i, feature in enumerate(original_data['features']):
                try:
                    all_fields.append({
                        'name': feature['properties'].get('field_name', f'Field_{i}'),
                        'sowing_date': feature['properties'].get('sowing_date', '2025-06-01'),
                        'geometry': feature['geometry'],
                        'coordinates': feature['geometry']['coordinates']
                    })
                except Exception as e:
                    print(f"  ⚠️ Error loading feature {i}: {e}")
        print(f"✓ Loaded {len(all_fields)} original fields")
    except FileNotFoundError:
        print("⚠️ Original fields file not found")
    
    # Load new fields
    try:
        with open('more_fields/new_fields_data.geojson', 'r') as f:
            new_data = json.load(f)
            original_count = len(all_fields)
            for i, feature in enumerate(new_data['features']):
                try:
                    all_fields.append({
                        'name': feature['properties'].get('field_name', f'NewField_{i}'),
                        'sowing_date': feature['properties'].get('sowing_date', '2025-06-01'),
                        'geometry': feature['geometry'],
                        'coordinates': feature['geometry']['coordinates']
                    })
                except Exception as e:
                    print(f"  ⚠️ Error loading new feature {i}: {e}")
            new_count = len(all_fields) - original_count
            print(f"✓ Loaded {new_count} new fields")
    except FileNotFoundError:
        print("⚠️ New fields file not found")
    
    print(f"\n✓ Total fields loaded: {len(all_fields)}")
    
    return all_fields


def get_field_centroid(coordinates):
    """Calculate centroid of a field polygon."""
    if isinstance(coordinates[0][0][0], list):
        # MultiPolygon - use first polygon
        coords = coordinates[0][0]
    else:
        # Polygon
        coords = coordinates[0]
    
    poly = Polygon(coords)
    centroid = poly.centroid
    return [centroid.x, centroid.y]


def create_field_clusters(fields, n_clusters=3):
    """Cluster fields geographically using K-means."""
    
    print("\n" + "=" * 80)
    print(f"CLUSTERING FIELDS INTO {n_clusters} AREAS")
    print("=" * 80)
    
    # Get centroids
    centroids = []
    for field in fields:
        centroid = get_field_centroid(field['coordinates'])
        centroids.append(centroid)
    
    centroids = np.array(centroids)
    
    # Perform K-means clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(centroids)
    
    # Group fields by cluster
    clusters = {i: [] for i in range(n_clusters)}
    for i, field in enumerate(fields):
        clusters[cluster_labels[i]].append(field)
    
    # Print cluster info
    for cluster_id, fields_in_cluster in clusters.items():
        print(f"\nCluster {cluster_id + 1}:")
        print(f"  Fields: {len(fields_in_cluster)}")
        print(f"  Sample fields: {', '.join([f['name'] for f in fields_in_cluster[:3]])}")
    
    return clusters


def create_cluster_polygon(cluster_fields, buffer_km=2):
    """Create a convex hull polygon around a cluster of fields with buffer."""
    
    # Collect all points from all fields
    all_points = []
    for field in cluster_fields:
        coords = field['coordinates']
        if isinstance(coords[0][0][0], list):
            # MultiPolygon
            coords = coords[0][0]
        else:
            # Polygon
            coords = coords[0]
        
        for point in coords:
            all_points.append(Point(point))
    
    # Create MultiPoint and get convex hull
    multipoint = MultiPoint(all_points)
    convex_hull = multipoint.convex_hull
    
    # Buffer the polygon (approximate: 1 degree ≈ 111 km at equator, less at higher latitudes)
    # For Argentina (around -33° lat), 1 degree ≈ 93 km
    buffer_degrees = buffer_km / 93.0
    buffered_polygon = convex_hull.buffer(buffer_degrees)
    
    # Convert to GeoJSON format
    return {
        'type': 'Polygon',
        'coordinates': [list(buffered_polygon.exterior.coords)]
    }


def get_date_range(fields):
    """Calculate start and end dates for subscription."""
    
    # Find earliest sowing date
    sowing_dates = [datetime.strptime(f['sowing_date'], '%Y-%m-%d') for f in fields]
    earliest_sowing = min(sowing_dates)
    
    # Start date: 1 week before earliest sowing
    start_date = earliest_sowing - timedelta(days=7)
    
    # End date: 1 week from today
    end_date = datetime.now() + timedelta(days=7)
    
    return start_date, end_date


def create_arps_subscription(polygon, area_name, start_date, end_date):
    """Create an ARPS subscription via Planet API."""
    
    print(f"\n  Creating subscription for {area_name}...")
    
    # Format dates for Planet API (ISO 8601)
    start_time = start_date.strftime('%Y-%m-%dT00:00:00.0Z')
    end_time = end_date.strftime('%Y-%m-%dT23:59:59.0Z')
    
    # Prepare subscription request
    # Note: When using sentinel_hub hosting, no delivery section is needed
    subscription_request = {
        "name": f"ARPS Subscription - {area_name}",
        "source": {
            "parameters": {
                "id": "PS_ARD_SR_DAILY",
                "start_time": start_time,
                "end_time": end_time,
                "geometry": polygon
            }
        },
        "hosting": {
            "type": "sentinel_hub"
        }
    }
    
    # Add collection_id if provided
    if SENTINEL_HUB_COLLECTION_ID:
        subscription_request["hosting"]["parameters"] = {
            "collection_id": SENTINEL_HUB_COLLECTION_ID
        }
    else:
        print(f"  ℹ️  No collection_id specified - Sentinel Hub will create one")
    
    # Save subscription request to file
    request_filename = f"arps_subscription_request_{area_name}.json"
    with open(request_filename, 'w') as f:
        json.dump(subscription_request, f, indent=2)
    print(f"  💾 Saved request to: {request_filename}")
    
    # Make API request
    headers = {
        "Authorization": f"api-key {PLANET_API_KEY}",
        "Content-Type": "application/json"
    }
    
    url = "https://api.planet.com/subscriptions/v1"
    
    try:
        response = requests.post(url, json=subscription_request, headers=headers)
        
        if response.status_code in [200, 201]:
            subscription_data = response.json()
            print(f"  ✓ Subscription created successfully!")
            print(f"    Subscription ID: {subscription_data.get('id', 'N/A')}")
            print(f"    Status: {subscription_data.get('status', 'N/A')}")
            
            # Save collection_id if returned
            if 'hosting' in subscription_data and 'parameters' in subscription_data['hosting']:
                collection_id = subscription_data['hosting']['parameters'].get('collection_id')
                if collection_id:
                    print(f"    Collection ID: {collection_id}")
            
            return subscription_data
        else:
            print(f"  ✗ Failed to create subscription")
            print(f"    Status Code: {response.status_code}")
            print(f"    Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None


def main():
    """Main execution function."""
    
    print("\n" + "=" * 80)
    print("ARPS SUBSCRIPTION CREATION FOR FIELD CLUSTERS")
    print("=" * 80)
    
    # Load all fields
    all_fields = load_all_fields()
    
    if not all_fields:
        print("\n✗ No fields loaded. Exiting.")
        return
    
    # Cluster fields
    clusters = create_field_clusters(all_fields, n_clusters=N_CLUSTERS)
    
    # Get date range
    start_date, end_date = get_date_range(all_fields)
    print(f"\n" + "=" * 80)
    print("DATE RANGE")
    print("=" * 80)
    print(f"Start Date: {start_date.strftime('%Y-%m-%d')}")
    print(f"End Date: {end_date.strftime('%Y-%m-%d')}")
    print(f"Duration: {(end_date - start_date).days} days")
    
    # Create polygons and subscriptions
    print("\n" + "=" * 80)
    print("CREATING CLUSTER POLYGONS AND SUBSCRIPTIONS")
    print("=" * 80)
    
    cluster_polygons = []
    subscriptions = []
    
    for cluster_id, cluster_fields in clusters.items():
        area_name = f"Area_{cluster_id + 1}"
        
        print(f"\n{area_name} ({len(cluster_fields)} fields):")
        
        # Create polygon
        polygon = create_cluster_polygon(cluster_fields, buffer_km=2)
        print(f"  ✓ Created polygon with 2 km buffer")
        
        # Calculate area (approximate)
        poly_shape = shape(polygon)
        area_sq_deg = poly_shape.area
        # Very rough approximation for Argentina latitude
        area_sq_km = area_sq_deg * (93 * 111)
        print(f"  Area: ~{area_sq_km:.1f} km²")
        
        cluster_polygons.append({
            'cluster_id': cluster_id,
            'area_name': area_name,
            'num_fields': len(cluster_fields),
            'polygon': polygon,
            'fields': [f['name'] for f in cluster_fields]
        })
        
        # Create ARPS subscription
        subscription = create_arps_subscription(polygon, area_name, start_date, end_date)
        if subscription:
            sub_info = {
                'area_name': area_name,
                'subscription_id': subscription.get('id'),
                'status': subscription.get('status'),
                'subscription_data': subscription
            }
            
            # Extract collection_id if present
            if 'hosting' in subscription and 'parameters' in subscription['hosting']:
                collection_id = subscription['hosting']['parameters'].get('collection_id')
                if collection_id:
                    sub_info['collection_id'] = collection_id
            
            subscriptions.append(sub_info)
    
    # Save cluster polygons as GeoJSON
    print("\n" + "=" * 80)
    print("SAVING OUTPUTS")
    print("=" * 80)
    
    geojson_features = []
    for cluster in cluster_polygons:
        feature = {
            'type': 'Feature',
            'geometry': cluster['polygon'],
            'properties': {
                'cluster_id': int(cluster['cluster_id']),
                'area_name': cluster['area_name'],
                'num_fields': cluster['num_fields'],
                'fields': ', '.join(cluster['fields'][:5]) + ('...' if len(cluster['fields']) > 5 else '')
            }
        }
        geojson_features.append(feature)
    
    geojson_output = {
        'type': 'FeatureCollection',
        'features': geojson_features
    }
    
    # Save GeoJSON
    with open('arps_cluster_polygons.geojson', 'w') as f:
        json.dump(geojson_output, f, indent=2)
    print(f"\n✓ Saved cluster polygons to: arps_cluster_polygons.geojson")
    
    # Save subscription details
    subscription_details = {
        'created_at': datetime.now().isoformat(),
        'date_range': {
            'start': start_date.strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d'),
            'duration_days': (end_date - start_date).days
        },
        'subscriptions': subscriptions,
        'cluster_info': [
            {
                'area_name': c['area_name'],
                'num_fields': c['num_fields'],
                'fields': c['fields']
            }
            for c in cluster_polygons
        ]
    }
    
    with open('arps_subscriptions.json', 'w') as f:
        json.dump(subscription_details, f, indent=2)
    print(f"✓ Saved subscription details to: arps_subscriptions.json")
    
    # Summary
    print("\n" + "=" * 80)
    print("✓ ARPS SUBSCRIPTION CREATION COMPLETE")
    print("=" * 80)
    print(f"\nCreated {len(subscriptions)} subscriptions:")
    for sub in subscriptions:
        print(f"  • {sub['area_name']}: {sub['subscription_id']} ({sub['status']})")
    
    print(f"\nFiles created:")
    print(f"  - arps_cluster_polygons.geojson (visualize clusters)")
    print(f"  - arps_subscriptions.json (subscription details)")
    print(f"  - arps_subscription_request_Area_*.json (API requests for each area)")
    
    if len(subscriptions) > 0:
        print(f"\n✓ Active subscriptions:")
        for sub in subscriptions:
            print(f"  • {sub['area_name']}: {sub['subscription_id']}")
            if 'collection_id' in sub:
                print(f"    Collection ID: {sub['collection_id']}")
    
    print(f"\nNext steps:")
    if len(subscriptions) > 0:
        print(f"  1. Monitor subscriptions at: https://www.planet.com/account/#/subscriptions")
        print(f"  2. Check Sentinel Hub dashboard for incoming ARPS data")
        print(f"  3. Collection IDs have been created and saved")
    else:
        print(f"  1. Review the saved subscription requests: arps_subscription_request_*.json")
        print(f"  2. Submit them manually via Planet API or web interface")
        print(f"  3. Or update SENTINEL_HUB_COLLECTION_ID in the script and rerun")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

