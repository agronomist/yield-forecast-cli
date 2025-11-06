"""
Visualize Peak NDVI Rasters from Sentinel Hub Processing API

Uses Sentinel Hub Processing API to fetch and display actual NDVI imagery
for each field at their peak NDVI date.
"""

import json
import requests
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.colors import LinearSegmentedColormap
from datetime import datetime, timedelta
import base64
from io import BytesIO
from PIL import Image
from matplotlib.backends.backend_pdf import PdfPages


class SentinelHubNDVIVisualizer:
    """Fetch and visualize NDVI rasters from Sentinel Hub."""
    
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.token_expiry = None
    
    def get_access_token(self):
        """Get OAuth access token from Sentinel Hub."""
        if self.token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.token
        
        url = "https://services.sentinel-hub.com/oauth/token"
        
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        response = requests.post(url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        self.token = token_data['access_token']
        
        # Set expiry (subtract 60 seconds for safety)
        expires_in = token_data.get('expires_in', 3600)
        self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)
        
        return self.token
    
    def get_bbox_from_geometry(self, geometry):
        """Extract bounding box from field geometry."""
        coords = geometry['coordinates'][0]
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        
        return [min(lons), min(lats), max(lons), max(lats)]
    
    def calculate_field_dimensions(self, bbox):
        """Calculate appropriate dimensions for the field."""
        # Calculate rough size in meters
        lon_diff = bbox[2] - bbox[0]
        lat_diff = bbox[3] - bbox[1]
        
        # Approximate meters (at ~32°S latitude)
        meters_per_degree_lon = 96500  # varies with latitude
        meters_per_degree_lat = 111000
        
        width_m = lon_diff * meters_per_degree_lon
        height_m = lat_diff * meters_per_degree_lat
        
        # Use 10m resolution (Sentinel-2 native for B04, B08)
        # But limit to max 2500 pixels in any dimension
        resolution = 10  # meters/pixel
        
        width_px = int(width_m / resolution)
        height_px = int(height_m / resolution)
        
        # Limit dimensions
        max_dim = 2500
        if width_px > max_dim or height_px > max_dim:
            scale = max_dim / max(width_px, height_px)
            width_px = int(width_px * scale)
            height_px = int(height_px * scale)
            resolution = width_m / width_px
        
        # Ensure minimum dimensions
        width_px = max(width_px, 100)
        height_px = max(height_px, 100)
        
        return width_px, height_px, resolution
    
    def fetch_ndvi_image(self, bbox, date_from, date_to, width, height):
        """
        Fetch NDVI image from Sentinel Hub Processing API.
        
        Args:
            bbox: [min_lon, min_lat, max_lon, max_lat]
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            width: Image width in pixels
            height: Image height in pixels
        """
        token = self.get_access_token()
        
        url = "https://services.sentinel-hub.com/api/v1/process"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Evalscript to calculate NDVI and return as image
        evalscript = """
//VERSION=3

function setup() {
  return {
    input: [{
      bands: ["B04", "B08", "SCL"],
      units: "DN"
    }],
    output: {
      bands: 3,
      sampleType: "AUTO"
    }
  }
}

function evaluatePixel(sample) {
    // Calculate NDVI
    let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);
    
    // Mask clouds using Scene Classification Layer
    // SCL values: 3=cloud shadows, 8=cloud medium prob, 9=cloud high prob, 10=thin cirrus
    let is_cloud = (sample.SCL == 3 || sample.SCL == 8 || sample.SCL == 9 || sample.SCL == 10);
    
    if (is_cloud) {
        return [0, 0, 0];  // Black for clouds
    }
    
    // Color mapping for NDVI (-1 to 1)
    // Use RGB to create a color gradient
    let r, g, b;
    
    if (ndvi < 0) {
        // Water/bare soil: blue to brown
        r = 0.5;
        g = 0.3;
        b = 0.2;
    } else if (ndvi < 0.2) {
        // Very low vegetation: brown
        r = 0.6 + ndvi;
        g = 0.4 + ndvi;
        b = 0.2;
    } else if (ndvi < 0.4) {
        // Low vegetation: yellow-green
        let t = (ndvi - 0.2) / 0.2;
        r = 0.8 - 0.3 * t;
        g = 0.6 + 0.3 * t;
        b = 0.2;
    } else if (ndvi < 0.6) {
        // Medium vegetation: green
        let t = (ndvi - 0.4) / 0.2;
        r = 0.5 - 0.4 * t;
        g = 0.9;
        b = 0.2 - 0.1 * t;
    } else {
        // High vegetation: dark green
        let t = (ndvi - 0.6) / 0.4;
        r = 0.1 - 0.1 * t;
        g = 0.9 - 0.2 * t;
        b = 0.1;
    }
    
    return [r, g, b];
}
"""
        
        payload = {
            "input": {
                "bounds": {
                    "bbox": bbox,
                    "properties": {
                        "crs": "http://www.opengis.net/def/crs/EPSG/0/4326"
                    }
                },
                "data": [{
                    "type": "S2L2A",
                    "dataFilter": {
                        "timeRange": {
                            "from": f"{date_from}T00:00:00Z",
                            "to": f"{date_to}T23:59:59Z"
                        },
                        "maxCloudCoverage": 30
                    }
                }]
            },
            "output": {
                "width": width,
                "height": height,
                "responses": [{
                    "identifier": "default",
                    "format": {
                        "type": "image/png"
                    }
                }]
            },
            "evalscript": evalscript
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            
            # Response is PNG image
            img = Image.open(BytesIO(response.content))
            return np.array(img)
            
        except requests.exceptions.RequestException as e:
            print(f"    ✗ Error fetching image: {e}")
            return None


def find_peak_ndvi_date(field_data):
    """Find the date when NDVI was at peak for a field."""
    time_series = field_data.get('ndvi_time_series', [])
    
    if not time_series:
        return None, 0
    
    max_ndvi = -1
    best_obs = None
    
    for obs in time_series:
        ndvi = obs.get('ndvi_mean')
        if ndvi is not None and ndvi > max_ndvi:
            max_ndvi = ndvi
            best_obs = obs
    
    if best_obs:
        return best_obs, max_ndvi
    
    return None, 0


def visualize_field_ndvi_raster(
    field_name, 
    field_data, 
    geometry, 
    ndvi_image, 
    bbox,
    peak_date,
    peak_ndvi,
    variety,
    yield_val,
    ax=None
):
    """Visualize NDVI raster for a field."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 10))
    
    # Display image
    extent = [bbox[0], bbox[2], bbox[1], bbox[3]]
    ax.imshow(ndvi_image, extent=extent, origin='upper', aspect='auto')
    
    # Overlay field boundary
    coords = geometry['coordinates'][0]
    polygon = Polygon(coords, fill=False, edgecolor='red', linewidth=2)
    ax.add_patch(polygon)
    
    # Formatting
    ax.set_xlabel('Longitude', fontsize=10, fontweight='bold')
    ax.set_ylabel('Latitude', fontsize=10, fontweight='bold')
    
    title = f'{field_name}\n{variety} | Peak NDVI: {peak_ndvi:.3f} | Yield: {yield_val:.2f} ton/ha\nDate: {peak_date}'
    ax.set_title(title, fontsize=11, fontweight='bold')
    
    ax.grid(True, alpha=0.3)
    
    # Add colorbar legend
    cbar_ax = ax.inset_axes([0.02, 0.02, 0.03, 0.3])
    
    # Create colorbar showing NDVI scale
    gradient = np.linspace(0, 1, 256).reshape(256, 1)
    cbar_ax.imshow(gradient, aspect='auto', cmap='RdYlGn', extent=[0, 1, 0, 1])
    cbar_ax.set_xticks([])
    cbar_ax.set_yticks([0, 0.5, 1])
    cbar_ax.set_yticklabels(['0.0', '0.5', '1.0'], fontsize=8)
    cbar_ax.set_ylabel('NDVI', fontsize=8, fontweight='bold')


def create_ndvi_raster_visualizations():
    """Create NDVI raster visualizations for all fields."""
    
    print("\n" + "=" * 80)
    print("SENTINEL HUB PROCESSING API - NDVI RASTER VISUALIZATION")
    print("=" * 80)
    
    # Credentials - load from environment variables
    import os
    CLIENT_ID = os.getenv("SENTINEL_HUB_CLIENT_ID")
    CLIENT_SECRET = os.getenv("SENTINEL_HUB_CLIENT_SECRET")
    
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Error: SENTINEL_HUB_CLIENT_ID and SENTINEL_HUB_CLIENT_SECRET must be set as environment variables")
        return
    
    # Initialize visualizer
    visualizer = SentinelHubNDVIVisualizer(CLIENT_ID, CLIENT_SECRET)
    
    print("\n✓ Authenticating with Sentinel Hub...")
    try:
        visualizer.get_access_token()
        print("✓ Authentication successful")
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        return
    
    # Load data
    print("\nLoading data...")
    with open('agricultural_fields_with_data.geojson', 'r') as f:
        geojson_data = json.load(f)
    
    with open('sentinel_ndvi_fapar_data.json', 'r') as f:
        fapar_data = json.load(f)
    
    with open('yield_predictions.csv') as f:
        import pandas as pd
        df_yield = pd.read_csv(f)
    
    print(f"✓ Loaded data for {len(geojson_data['features'])} fields")
    
    # Get top fields to visualize
    top_fields = df_yield.nlargest(6, 'Grain Yield (ton/ha)')['Field Name'].values
    
    print(f"\n{'─' * 80}")
    print("FETCHING NDVI RASTERS FOR TOP 6 FIELDS")
    print(f"{'─' * 80}")
    
    fig, axes = plt.subplots(2, 3, figsize=(20, 14))
    axes = axes.flatten()
    
    for idx, field_name in enumerate(top_fields):
        print(f"\n[{idx+1}/6] {field_name}")
        
        # Find field in geojson
        feature = None
        for f in geojson_data['features']:
            if f['properties'].get('field_name') == field_name:
                feature = f
                break
        
        if not feature:
            print(f"  ✗ Field not found in GeoJSON")
            continue
        
        geometry = feature['geometry']
        variety = feature['properties'].get('wheat_variety', 'Unknown')
        
        # Get peak NDVI date
        field_fapar = fapar_data['fields'].get(field_name, {})
        peak_obs, peak_ndvi = find_peak_ndvi_date(field_fapar)
        
        if not peak_obs:
            print(f"  ✗ No peak NDVI data")
            continue
        
        peak_date = peak_obs['from']
        print(f"  Peak NDVI: {peak_ndvi:.3f} on {peak_date}")
        
        # Get bounding box
        bbox = visualizer.get_bbox_from_geometry(geometry)
        print(f"  BBox: {bbox}")
        
        # Calculate dimensions
        width, height, resolution = visualizer.calculate_field_dimensions(bbox)
        print(f"  Image size: {width}x{height} pixels (~{resolution:.0f}m resolution)")
        
        # Fetch image (use a week window around peak date)
        date_from = datetime.strptime(peak_date, '%Y-%m-%d') - timedelta(days=3)
        date_to = datetime.strptime(peak_date, '%Y-%m-%d') + timedelta(days=3)
        
        print(f"  Fetching imagery from {date_from.strftime('%Y-%m-%d')} to {date_to.strftime('%Y-%m-%d')}...")
        
        ndvi_image = visualizer.fetch_ndvi_image(
            bbox,
            date_from.strftime('%Y-%m-%d'),
            date_to.strftime('%Y-%m-%d'),
            width,
            height
        )
        
        if ndvi_image is None:
            print(f"  ✗ Failed to fetch image")
            continue
        
        print(f"  ✓ Image fetched successfully")
        
        # Get yield
        yield_val = df_yield[df_yield['Field Name'] == field_name]['Grain Yield (ton/ha)'].values[0]
        
        # Visualize
        visualize_field_ndvi_raster(
            field_name,
            field_fapar,
            geometry,
            ndvi_image,
            bbox,
            peak_date,
            peak_ndvi,
            variety,
            yield_val,
            axes[idx]
        )
    
    plt.suptitle('Peak NDVI Rasters - Top 6 Fields', fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    
    output_file = 'ndvi_rasters_top6_fields.png'
    plt.savefig(output_file, dpi=200, bbox_inches='tight')
    print(f"\n✓ Saved visualization to: {output_file}")
    
    plt.savefig('ndvi_rasters_top6_fields.pdf', bbox_inches='tight')
    print(f"✓ Saved PDF to: ndvi_rasters_top6_fields.pdf")
    
    return fig


if __name__ == "__main__":
    try:
        create_ndvi_raster_visualizations()
        
        print("\n" + "=" * 80)
        print("✓ NDVI RASTER VISUALIZATION COMPLETE")
        print("=" * 80)
        print("\nFiles created:")
        print("  - ndvi_rasters_top6_fields.png")
        print("  - ndvi_rasters_top6_fields.pdf")
        print("\n💡 These show actual satellite imagery at peak NDVI for each field")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

