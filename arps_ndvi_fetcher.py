"""
ARPS (Analysis-Ready PlanetScope) NDVI Data Fetcher

Fetches daily 3m resolution NDVI from PlanetScope imagery hosted in Sentinel Hub BYOC.
This provides higher resolution and temporal frequency compared to Sentinel-2.
"""

import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import time


class ARPSNDVIFetcher:
    """Fetch NDVI statistics from ARPS data in Sentinel Hub BYOC collections."""
    
    # Collection IDs from ARPS subscriptions
    COLLECTION_IDS = {
        "Area_1": "556557f3-d1eb-400b-8dfc-19de98d66729",
        "Area_2": "d36e4a88-6a74-4f9d-b585-10cfce72ef33",
        "Area_3": "2f9d8d9c-1a2b-47ea-8d10-0ff2c201c55c"
    }
    
    def __init__(self, client_id: str, client_secret: str):
        """
        Initialize the ARPS NDVI fetcher.
        
        Args:
            client_id: Sentinel Hub OAuth client ID
            client_secret: Sentinel Hub OAuth client secret
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.token_expiry = None
        self.base_url = "https://services.sentinel-hub.com"
        
    def authenticate(self):
        """Obtain OAuth token from Sentinel Hub."""
        if self.token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.token
        
        url = f"{self.base_url}/oauth/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            response = requests.post(url, data=payload, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            self.token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)
            
            return self.token
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Authentication failed: {e}")
    
    def get_field_collection(self, field_area: str) -> str:
        """
        Get the BYOC collection ID for a field based on its area assignment.
        
        Args:
            field_area: Area name (Area_1, Area_2, or Area_3)
        
        Returns:
            Collection ID for the field's area
        """
        return self.COLLECTION_IDS.get(field_area)
    
    def fetch_ndvi_daily(
        self, 
        field_name: str, 
        geometry: Dict, 
        sowing_date: str,
        collection_id: str,
        end_date: str = None
    ) -> List[Dict]:
        """
        Fetch daily NDVI statistics for a field from ARPS data.
        
        Args:
            field_name: Name of the agricultural field
            geometry: GeoJSON geometry (Polygon or MultiPolygon)
            sowing_date: Sowing date (YYYY-MM-DD format)
            collection_id: Sentinel Hub BYOC collection ID
            end_date: Optional end date (defaults to today)
        
        Returns:
            List of dictionaries with daily NDVI statistics
        """
        self.authenticate()
        
        # Parse dates
        sow_dt = datetime.strptime(sowing_date, '%Y-%m-%d')
        if end_date:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        else:
            end_dt = datetime.now()
        
        # Format for API
        from_date = sow_dt.strftime('%Y-%m-%dT00:00:00Z')
        to_date = end_dt.strftime('%Y-%m-%dT23:59:59Z')
        
        print(f"  Fetching ARPS NDVI from {sowing_date} to {end_dt.strftime('%Y-%m-%d')}...")
        
        # Statistical API request
        request_body = {
            "input": {
                "bounds": {
                    "geometry": geometry
                },
                "data": [{
                    "type": f"byoc-{collection_id}",
                    "dataFilter": {
                        "timeRange": {
                            "from": from_date,
                            "to": to_date
                        }
                    }
                }]
            },
            "aggregation": {
                "timeRange": {
                    "from": from_date,
                    "to": to_date
                },
                "aggregationInterval": {
                    "of": "P1D"  # Daily
                },
                "evalscript": """
//VERSION=3
function setup() {
    return {
        input: [{
            bands: ["red", "nir", "cloud_mask", "dataMask"]
        }],
        output: [
            {
                id: "ndvi",
                bands: 1,
                sampleType: "FLOAT32"
            },
            {
                id: "dataMask",
                bands: 1
            }
        ]
    };
}

function evaluatePixel(sample) {
    // ARPS cloud mask: 1 = clear, 0 = cloud
    var noCloudMask = 0;
    if (sample.cloud_mask == 1) {
        noCloudMask = 1;
    }
    
    // Combine dataMask with cloud mask
    const clear = sample.dataMask * noCloudMask;
    
    // Calculate NDVI
    var ndvi = (sample.nir - sample.red) / (sample.nir + sample.red);
    
    // Filter out invalid values
    if (!isFinite(ndvi) || ndvi < -1 || ndvi > 1) {
        return {
            ndvi: [NaN],
            dataMask: [0]
        };
    }
    
    return {
        ndvi: [ndvi],
        dataMask: [clear]
    };
}
                """
            }
        }
        
        url = f"{self.base_url}/api/v1/statistics"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(url, headers=headers, json=request_body, timeout=120)
            response.raise_for_status()
            
            data = response.json()
            observations = []
            
            for interval_data in data.get('data', []):
                date_str = interval_data['interval']['from'][:10]
                stats = interval_data['outputs']['ndvi']['bands']['B0']['stats']
                
                # Only include intervals with valid NDVI data
                if stats.get('mean') is not None:
                    observations.append({
                        'date': date_str,
                        'ndvi_mean': float(stats['mean']),
                        'ndvi_std': float(stats.get('stDev', 0.0)),
                        'ndvi_min': float(stats.get('min', stats['mean'])),
                        'ndvi_max': float(stats.get('max', stats['mean'])),
                        'ndvi_p10': float(stats.get('percentiles', {}).get('10.0', stats['mean'])),
                        'ndvi_p25': float(stats.get('percentiles', {}).get('25.0', stats['mean'])),
                        'ndvi_p50': float(stats.get('percentiles', {}).get('50.0', stats['mean'])),
                        'ndvi_p75': float(stats.get('percentiles', {}).get('75.0', stats['mean'])),
                        'ndvi_p90': float(stats.get('percentiles', {}).get('90.0', stats['mean'])),
                        'sample_count': int(stats.get('sampleCount', 0))
                    })
            
            print(f"  ✓ Found {len(observations)} daily ARPS observations")
            return observations
            
        except requests.exceptions.RequestException as e:
            print(f"  ✗ Error fetching ARPS data: {e}")
            if hasattr(e.response, 'text'):
                print(f"    Response: {e.response.text[:300]}")
            return []
    
    def fetch_all_fields(self, geojson_path: str, field_area_mapping: Dict[str, str], output_dir: str = "."):
        """
        Fetch ARPS NDVI for all fields and save to JSON.
        
        Args:
            geojson_path: Path to GeoJSON file with field data
            field_area_mapping: Dictionary mapping field names to their area assignments
            output_dir: Directory to save output files
        """
        # Load GeoJSON
        with open(geojson_path, 'r') as f:
            data = json.load(f)
        
        print("\n" + "=" * 80)
        print("FETCHING ARPS NDVI FOR ALL FIELDS")
        print("=" * 80)
        
        total_fields = len(data['features'])
        processed = 0
        skipped = 0
        errors = 0
        
        for feature in data['features']:
            props = feature['properties']
            geom = feature['geometry']
            
            field_name = props.get('field_name', 'Unknown')
            sowing_date = props.get('sowing_date')
            
            # Skip fields without sowing dates
            if not sowing_date or sowing_date == 'N/A':
                print(f"\n{processed + 1}/{total_fields}: {field_name}")
                print(f"  ⊘ Skipping (no sowing date)")
                skipped += 1
                continue
            
            # Get area assignment
            area = field_area_mapping.get(field_name)
            if not area:
                print(f"\n{processed + 1}/{total_fields}: {field_name}")
                print(f"  ⊘ Skipping (no area assignment)")
                skipped += 1
                continue
            
            # Get collection ID
            collection_id = self.get_field_collection(area)
            if not collection_id:
                print(f"\n{processed + 1}/{total_fields}: {field_name}")
                print(f"  ⊘ Skipping (invalid area: {area})")
                skipped += 1
                continue
            
            print(f"\n{processed + 1}/{total_fields}: {field_name} ({area})")
            
            try:
                # Fetch ARPS NDVI
                ndvi_data = self.fetch_ndvi_daily(
                    field_name,
                    geom,
                    sowing_date,
                    collection_id
                )
                
                if ndvi_data:
                    # Save to JSON
                    output_path = f"{output_dir}/arps_ndvi_{field_name.replace(' ', '_').replace('/', '_')}.json"
                    
                    output_data = {
                        'field_name': field_name,
                        'sowing_date': sowing_date,
                        'area': area,
                        'collection_id': collection_id,
                        'data_source': 'ARPS (PlanetScope 3m)',
                        'observations': ndvi_data,
                        'fetched_at': datetime.now().isoformat()
                    }
                    
                    with open(output_path, 'w') as f:
                        json.dump(output_data, f, indent=2)
                    
                    processed += 1
                    print(f"  ✓ Saved to {output_path}")
                else:
                    print(f"  ⚠ No data available (area might still be ingesting)")
                    skipped += 1
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                print(f"  ✗ Error: {e}")
                errors += 1
        
        print("\n" + "=" * 80)
        print("FETCH COMPLETE")
        print("=" * 80)
        print(f"Total fields: {total_fields}")
        print(f"Successfully processed: {processed}")
        print(f"Skipped: {skipped}")
        print(f"Errors: {errors}")
        print("=" * 80)


def main():
    """Main execution function."""
    import os
    CLIENT_ID = os.getenv("SENTINEL_HUB_CLIENT_ID")
    CLIENT_SECRET = os.getenv("SENTINEL_HUB_CLIENT_SECRET")
    
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Error: SENTINEL_HUB_CLIENT_ID and SENTINEL_HUB_CLIENT_SECRET must be set as environment variables")
        print("   Create a .env file or export them in your shell")
        return
    
    # Load field-to-area mapping from clustering
    print("Loading field-to-area mapping...")
    
    with open('field_area_mapping.json', 'r') as f:
        field_area_mapping = json.load(f)
    
    print(f"Loaded mapping for {len(field_area_mapping)} fields across 3 areas")
    
    # Count by area
    area_counts = {}
    for area in field_area_mapping.values():
        area_counts[area] = area_counts.get(area, 0) + 1
    
    for area, count in sorted(area_counts.items()):
        print(f"  {area}: {count} fields")
    
    # Initialize fetcher
    fetcher = ARPSNDVIFetcher(CLIENT_ID, CLIENT_SECRET)
    
    # Fetch ARPS NDVI for all fields
    import os
    
    # Create output directories
    os.makedirs('arps_ndvi_data', exist_ok=True)
    os.makedirs('more_fields/arps_ndvi_data', exist_ok=True)
    
    if os.path.exists('agricultural_fields_with_data.geojson'):
        print("\n" + "=" * 80)
        print("PROCESSING ORIGINAL FIELDS")
        print("=" * 80)
        fetcher.fetch_all_fields(
            'agricultural_fields_with_data.geojson',
            field_area_mapping,
            'arps_ndvi_data'
        )
    
    if os.path.exists('more_fields/new_fields_data.geojson'):
        print("\n" + "=" * 80)
        print("PROCESSING NEW FIELDS")
        print("=" * 80)
        fetcher.fetch_all_fields(
            'more_fields/new_fields_data.geojson',
            field_area_mapping,
            'more_fields/arps_ndvi_data'
        )


if __name__ == "__main__":
    main()

