"""
Sentinel-2 NDVI Data Fetcher - Per Date Version

Fetches NDVI for each individual cloud-free Sentinel-2 acquisition date.
This provides maximum temporal resolution compared to weekly aggregations.
"""

import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import math
import time


class SentinelHubNDVIPerDateFetcher:
    """Fetch NDVI statistics from Sentinel Hub for each cloud-free date."""
    
    def __init__(self, client_id: str, client_secret: str):
        """
        Initialize the Sentinel Hub client.
        
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
        
        print("Authenticating with Sentinel Hub...")
        
        url = f"{self.base_url}/oauth/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            response = requests.post(url, data=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            self.token = data['access_token']
            self.token_expiry = datetime.now() + timedelta(minutes=50)
            
            print("✓ Authentication successful")
            return self.token
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Authentication failed: {e}")
            raise
    
    def calculate_field_area(self, coordinates: List[List[float]]) -> float:
        """
        Calculate field area in hectares using shoelace formula.
        
        Args:
            coordinates: List of [lon, lat] pairs
            
        Returns:
            Area in hectares
        """
        if len(coordinates) < 3:
            return 0.0
        
        area = 0.0
        for i in range(len(coordinates) - 1):
            lon1, lat1 = coordinates[i]
            lon2, lat2 = coordinates[i + 1]
            area += lon1 * lat2 - lon2 * lat1
        
        area = abs(area) / 2.0
        
        lat_avg = sum(c[1] for c in coordinates) / len(coordinates)
        meters_per_degree_lat = 111320
        meters_per_degree_lon = 111320 * math.cos(math.radians(lat_avg))
        
        area_m2 = area * meters_per_degree_lat * meters_per_degree_lon
        area_ha = area_m2 / 10000
        
        return area_ha
    
    def calculate_safe_dimensions(
        self, 
        coordinates: List[List[float]],
        max_resolution: float = 1500.0
    ) -> Dict:
        """
        Calculate safe dimensions for large fields.
        
        Args:
            coordinates: List of [lon, lat] pairs
            max_resolution: Maximum resolution in meters per pixel (default: 1500)
            
        Returns:
            Dictionary with bounding box and resolution info
        """
        lons = [c[0] for c in coordinates]
        lats = [c[1] for c in coordinates]
        
        min_lon, max_lon = min(lons), max(lons)
        min_lat, max_lat = min(lats), max(lats)
        
        lat_avg = (min_lat + max_lat) / 2
        meters_per_degree_lat = 111320
        meters_per_degree_lon = 111320 * math.cos(math.radians(lat_avg))
        
        width_m = (max_lon - min_lon) * meters_per_degree_lon
        height_m = (max_lat - min_lat) * meters_per_degree_lat
        
        width_px = max(10, int(width_m / max_resolution))
        height_px = max(10, int(height_m / max_resolution))
        
        actual_resolution = max(width_m / width_px, height_m / height_px)
        
        return {
            'bbox': [min_lon, min_lat, max_lon, max_lat],
            'width': width_px,
            'height': height_px,
            'width_m': width_m,
            'height_m': height_m,
            'resolution': actual_resolution
        }
    
    def build_statistical_request_per_date(
        self,
        geometry: Dict,
        bbox: List[float],
        width: int,
        height: int,
        time_from: str,
        time_to: str
    ) -> Dict:
        """
        Build Statistical API request payload for per-date observations.
        
        Args:
            geometry: GeoJSON geometry
            bbox: Bounding box [minLon, minLat, maxLon, maxLat]
            width: Image width in pixels
            height: Image height in pixels
            time_from: Start date (YYYY-MM-DD)
            time_to: End date (YYYY-MM-DD)
            
        Returns:
            Request payload dictionary
        """
        return {
            "input": {
                "bounds": {
                    "bbox": bbox,
                    "properties": {
                        "crs": "http://www.opengis.net/def/crs/EPSG/0/4326"
                    }
                },
                "data": [
                    {
                        "type": "sentinel-2-l2a",
                        "dataFilter": {
                            "timeRange": {
                                "from": f"{time_from}T00:00:00Z",
                                "to": f"{time_to}T23:59:59Z"
                            },
                            "maxCloudCoverage": 30
                        }
                    }
                ]
            },
            "aggregation": {
                "timeRange": {
                    "from": f"{time_from}T00:00:00Z",
                    "to": f"{time_to}T23:59:59Z"
                },
                "aggregationInterval": {
                    "of": "P1D"  # 1-day intervals = per-date results
                },
                "resx": (bbox[2] - bbox[0]) / width,
                "resy": (bbox[3] - bbox[1]) / height,
                "evalscript": """
//VERSION=3

function setup() {
  return {
    input: [{
      bands: ["B04", "B08", "dataMask"],
      units: "DN"
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
  }
}

function evaluatePixel(samples) {
    // Calculate NDVI
    let ndvi = (samples.B08 - samples.B04) / (samples.B08 + samples.B04);
    
    return {
        ndvi: [ndvi],
        dataMask: [samples.dataMask]
    };
}
"""
            },
            "calculations": {
                "ndvi": {
                    "statistics": {
                        "default": {
                            "percentiles": {
                                "k": [10, 25, 50, 75, 90]
                            }
                        }
                    }
                }
            }
        }
    
    def fetch_ndvi_per_date(
        self,
        field_name: str,
        geometry: Dict,
        sowing_date: str,
        end_date: str = None
    ) -> List[Dict]:
        """
        Fetch NDVI for each individual cloud-free Sentinel-2 date.
        
        Args:
            field_name: Name of the field
            geometry: GeoJSON geometry
            sowing_date: Sowing date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD), defaults to today
            
        Returns:
            List of NDVI statistics by observation date (filtered by <30% cloud coverage)
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # Get authentication token
        token = self.authenticate()
        
        # Calculate field info
        coordinates = geometry['coordinates'][0]
        area_ha = self.calculate_field_area(coordinates)
        dims = self.calculate_safe_dimensions(coordinates)
        
        print(f"\n  Field: {field_name}")
        print(f"  Area: {area_ha:.2f} ha")
        print(f"  Dimensions: {dims['width']}x{dims['height']} pixels @ {dims['resolution']:.0f}m resolution")
        
        # Build request
        request_payload = self.build_statistical_request_per_date(
            geometry,
            dims['bbox'],
            dims['width'],
            dims['height'],
            sowing_date,
            end_date
        )
        
        # Make API request
        url = f"{self.base_url}/api/v1/statistics"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                url, 
                headers=headers, 
                json=request_payload,
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Parse results
            results = []
            
            if 'data' in data:
                for entry in data['data']:
                    interval = entry.get('interval', {})
                    outputs = entry.get('outputs', {})
                    
                    ndvi_stats = outputs.get('ndvi', {}).get('bands', {}).get('B0', {}).get('stats', {})
                    
                    # Only include if we have valid NDVI data
                    if ndvi_stats.get('mean') is not None:
                        observation_date = interval.get('from', '').split('T')[0]
                        
                        results.append({
                            'date': observation_date,
                            'ndvi_mean': ndvi_stats.get('mean'),
                            'ndvi_std': ndvi_stats.get('stDev'),
                            'ndvi_min': ndvi_stats.get('min'),
                            'ndvi_max': ndvi_stats.get('max'),
                            'ndvi_p10': ndvi_stats.get('percentiles', {}).get('10.0'),
                            'ndvi_p25': ndvi_stats.get('percentiles', {}).get('25.0'),
                            'ndvi_p50': ndvi_stats.get('percentiles', {}).get('50.0'),
                            'ndvi_p75': ndvi_stats.get('percentiles', {}).get('75.0'),
                            'ndvi_p90': ndvi_stats.get('percentiles', {}).get('90.0'),
                            'sample_count': ndvi_stats.get('sampleCount', 0)
                        })
            
            print(f"  ✓ Retrieved {len(results)} observations (cloud coverage <30%)")
            return results
            
        except requests.exceptions.RequestException as e:
            print(f"  ✗ Error fetching data: {e}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                print(f"  Response: {e.response.text[:500]}")
            return []


def process_all_fields(
    geojson_path: str, 
    client_id: str, 
    client_secret: str
) -> Dict:
    """
    Process all fields and fetch NDVI per date.
    
    Args:
        geojson_path: Path to GeoJSON file
        client_id: Sentinel Hub client ID
        client_secret: Sentinel Hub client secret
        
    Returns:
        Dictionary with NDVI data for all fields
    """
    print("=" * 80)
    print("SENTINEL-2 NDVI DATA FETCHER (PER-DATE MODE)")
    print("=" * 80)
    print(f"\nSettings:")
    print(f"  - Mode: Individual cloud-free observations")
    print(f"  - Max cloud coverage: 30%")
    print(f"  - Time resolution: Daily (one value per Sentinel-2 pass)")
    
    # Load field data
    with open(geojson_path, 'r') as f:
        data = json.load(f)
    
    # Initialize fetcher
    fetcher = SentinelHubNDVIPerDateFetcher(client_id, client_secret)
    
    # Process each field
    results = {}
    total_fields = len(data['features'])
    
    print(f"\nProcessing {total_fields} fields...")
    print("=" * 80)
    
    for idx, feature in enumerate(data['features'], 1):
        props = feature['properties']
        geom = feature['geometry']
        
        field_name = props.get('field_name', f'Field_{idx}')
        sowing_date = props.get('sowing_date')
        variety = props.get('wheat_variety', 'Unknown')
        
        if not sowing_date or sowing_date == 'N/A':
            print(f"\n[{idx}/{total_fields}] Skipping {field_name}: no sowing date")
            continue
        
        print(f"\n[{idx}/{total_fields}] Processing {field_name} ({variety})")
        print(f"  Sowing date: {sowing_date}")
        
        try:
            ndvi_data = fetcher.fetch_ndvi_per_date(
                field_name,
                geom,
                sowing_date
            )
            
            results[field_name] = {
                'variety': variety,
                'sowing_date': sowing_date,
                'ndvi_observations': ndvi_data,
                'coordinates': geom['coordinates'][0]
            }
            
            # Rate limiting
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  ✗ Error processing field: {e}")
            results[field_name] = {
                'variety': variety,
                'sowing_date': sowing_date,
                'ndvi_observations': [],
                'error': str(e)
            }
    
    return results


def save_results(results: Dict, output_path: str):
    """Save NDVI results to JSON file."""
    output_data = {
        'fetch_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'fetch_mode': 'per_date',
        'total_fields': len(results),
        'fields': results
    }
    
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n{'=' * 80}")
    print(f"✓ Results saved to: {output_path}")
    print(f"  Total fields processed: {len(results)}")
    
    # Calculate statistics
    successful = sum(1 for r in results.values() if r.get('ndvi_observations'))
    failed = len(results) - successful
    total_observations = sum(len(r.get('ndvi_observations', [])) for r in results.values())
    
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Total cloud-free observations: {total_observations}")
    
    if successful > 0:
        avg_obs_per_field = total_observations / successful
        print(f"  Average observations per field: {avg_obs_per_field:.1f}")


def export_to_csv(results: Dict, output_path: str):
    """Export NDVI data to CSV format."""
    import csv
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            'Field Name', 'Variety', 'Sowing Date', 'Observation Date',
            'Days Since Sowing', 'NDVI Mean', 'NDVI Std', 'NDVI Min', 'NDVI Max',
            'NDVI P50 (Median)', 'Sample Count'
        ])
        
        # Data rows
        for field_name, field_data in results.items():
            variety = field_data.get('variety', 'Unknown')
            sowing_date = field_data.get('sowing_date', 'N/A')
            
            if sowing_date != 'N/A':
                sowing_dt = datetime.strptime(sowing_date, '%Y-%m-%d')
            
            for obs in field_data.get('ndvi_observations', []):
                obs_date = obs.get('date', '')
                
                # Calculate days since sowing
                if sowing_date != 'N/A' and obs_date:
                    obs_dt = datetime.strptime(obs_date, '%Y-%m-%d')
                    days_since_sowing = (obs_dt - sowing_dt).days
                else:
                    days_since_sowing = ''
                
                writer.writerow([
                    field_name,
                    variety,
                    sowing_date,
                    obs_date,
                    days_since_sowing,
                    round(obs.get('ndvi_mean', 0), 4) if obs.get('ndvi_mean') else '',
                    round(obs.get('ndvi_std', 0), 4) if obs.get('ndvi_std') else '',
                    round(obs.get('ndvi_min', 0), 4) if obs.get('ndvi_min') else '',
                    round(obs.get('ndvi_max', 0), 4) if obs.get('ndvi_max') else '',
                    round(obs.get('ndvi_p50', 0), 4) if obs.get('ndvi_p50') else '',
                    obs.get('sample_count', 0)
                ])
    
    print(f"✓ CSV export saved to: {output_path}")


if __name__ == "__main__":
    # Configuration - load from environment variables
    import os
    CLIENT_ID = os.getenv("SENTINEL_HUB_CLIENT_ID")
    CLIENT_SECRET = os.getenv("SENTINEL_HUB_CLIENT_SECRET")
    
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Error: SENTINEL_HUB_CLIENT_ID and SENTINEL_HUB_CLIENT_SECRET must be set as environment variables")
        print("   Create a .env file or export them in your shell")
        exit(1)
    GEOJSON_PATH = "agricultural_fields_with_data.geojson"
    
    try:
        # Fetch NDVI data for all fields
        results = process_all_fields(
            GEOJSON_PATH, 
            CLIENT_ID, 
            CLIENT_SECRET
        )
        
        # Save results
        save_results(results, 'sentinel_ndvi_per_date.json')
        export_to_csv(results, 'sentinel_ndvi_per_date.csv')
        
        print("\n" + "=" * 80)
        print("NDVI DATA FETCH COMPLETE")
        print("=" * 80)
        
    except FileNotFoundError:
        print(f"Error: Could not find {GEOJSON_PATH}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

