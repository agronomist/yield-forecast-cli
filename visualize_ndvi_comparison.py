"""
Compare NDVI Rasters: High vs Low Yielding Fields

Creates side-by-side comparison of top and bottom performing fields.
Implements retry logic for cloudy dates.
"""

import json
import requests
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from datetime import datetime, timedelta
from io import BytesIO
from PIL import Image
import pandas as pd


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
        lon_diff = bbox[2] - bbox[0]
        lat_diff = bbox[3] - bbox[1]
        
        meters_per_degree_lon = 96500
        meters_per_degree_lat = 111000
        
        width_m = lon_diff * meters_per_degree_lon
        height_m = lat_diff * meters_per_degree_lat
        
        resolution = 10
        
        width_px = int(width_m / resolution)
        height_px = int(height_m / resolution)
        
        max_dim = 2500
        if width_px > max_dim or height_px > max_dim:
            scale = max_dim / max(width_px, height_px)
            width_px = int(width_px * scale)
            height_px = int(height_px * scale)
        
        width_px = max(width_px, 100)
        height_px = max(height_px, 100)
        
        return width_px, height_px
    
    def fetch_ndvi_image(self, bbox, date_from, date_to, width, height):
        """Fetch NDVI image from Sentinel Hub Processing API."""
        token = self.get_access_token()
        
        url = "https://services.sentinel-hub.com/api/v1/process"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
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
    let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);
    
    // More lenient cloud masking - only mask obvious clouds
    let is_cloud = (sample.SCL == 8 || sample.SCL == 9 || sample.SCL == 10);
    
    if (is_cloud) {
        return [0.1, 0.1, 0.1];  // Very dark gray for clouds (not pure black)
    }
    
    // Proper Red (0) to Yellow (0.5) to Green (1) gradient for NDVI
    let r, g, b;
    
    // Clamp NDVI to 0-1 range for visualization
    ndvi = Math.max(0, Math.min(1, ndvi));
    
    if (ndvi < 0.5) {
        // Red (0) to Yellow (0.5)
        let t = ndvi / 0.5;
        r = 1.0;
        g = t;
        b = 0.0;
    } else {
        // Yellow (0.5) to Green (1.0)
        let t = (ndvi - 0.5) / 0.5;
        r = 1.0 - t;
        g = 1.0;
        b = 0.0;
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
                        "maxCloudCoverage": 80
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
            
            img = Image.open(BytesIO(response.content))
            img_array = np.array(img)
            
            # Check if image is mostly black/dark gray (clouds or no data)
            # Consider pixels with any channel > 30 as valid data
            non_dark = np.sum(np.any(img_array > 30, axis=2))
            total_pixels = img_array.shape[0] * img_array.shape[1]
            
            if non_dark / total_pixels < 0.05:  # Less than 5% valid data
                return None
            
            return img_array
            
        except requests.exceptions.RequestException as e:
            return None
    
    def fetch_ndvi_with_retry(self, bbox, peak_date, width, height, max_attempts=5):
        """
        Try to fetch NDVI image with multiple date windows if cloudy.
        
        Args:
            bbox: Bounding box
            peak_date: Peak NDVI date (string YYYY-MM-DD)
            width, height: Image dimensions
            max_attempts: Number of attempts with different windows
        """
        peak_dt = datetime.strptime(peak_date, '%Y-%m-%d')
        
        # Try different window strategies
        strategies = [
            (3, 3),    # ±3 days around peak
            (7, 7),    # ±1 week
            (14, 14),  # ±2 weeks
            (21, 21),  # ±3 weeks
            (30, 30),  # ±1 month (last resort)
        ]
        
        for attempt, (days_before, days_after) in enumerate(strategies[:max_attempts], 1):
            date_from = peak_dt - timedelta(days=days_before)
            date_to = peak_dt + timedelta(days=days_after)
            
            print(f"    Attempt {attempt}: {date_from.strftime('%Y-%m-%d')} to {date_to.strftime('%Y-%m-%d')}", end="")
            
            img = self.fetch_ndvi_image(
                bbox,
                date_from.strftime('%Y-%m-%d'),
                date_to.strftime('%Y-%m-%d'),
                width,
                height
            )
            
            if img is not None:
                print(" ✓ Success")
                return img, f"{date_from.strftime('%Y-%m-%d')} to {date_to.strftime('%Y-%m-%d')}"
            else:
                print(" ✗ No clear imagery")
        
        print("    ✗ All attempts failed")
        return None, None


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


def visualize_field_comparison(
    ax,
    field_name,
    geometry,
    ndvi_image,
    bbox,
    peak_ndvi,
    variety,
    yield_val,
    date_range,
    is_high_yield=True
):
    """Visualize single field NDVI raster."""
    
    # Display image
    extent = [bbox[0], bbox[2], bbox[1], bbox[3]]
    ax.imshow(ndvi_image, extent=extent, origin='upper', aspect='auto')
    
    # Overlay field boundary
    coords = geometry['coordinates'][0]
    polygon = Polygon(coords, fill=False, edgecolor='red', linewidth=2)
    ax.add_patch(polygon)
    
    # Title with color coding
    label = "HIGH" if is_high_yield else "LOW"
    color = 'green' if is_high_yield else 'red'
    
    title = f'{label}: {field_name}\n{variety} | NDVI: {peak_ndvi:.3f} | Yield: {yield_val:.2f} ton/ha'
    ax.set_title(title, fontsize=10, fontweight='bold', color=color)
    
    ax.set_xlabel('Longitude', fontsize=8)
    ax.set_ylabel('Latitude', fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(True, alpha=0.3)
    
    # Add colorbar
    cbar_ax = ax.inset_axes([0.02, 0.02, 0.03, 0.25])
    gradient = np.linspace(0, 1, 256).reshape(256, 1)
    cbar_ax.imshow(gradient, aspect='auto', cmap='RdYlGn', extent=[0, 1, 0, 1])
    cbar_ax.set_xticks([])
    cbar_ax.set_yticks([0, 0.5, 1])
    cbar_ax.set_yticklabels(['0.0', '0.5', '1.0'], fontsize=6)
    cbar_ax.set_ylabel('NDVI', fontsize=7, fontweight='bold')
    
    # Add date annotation
    ax.text(0.98, 0.02, f'Date: {date_range}',
           transform=ax.transAxes, fontsize=6,
           verticalalignment='bottom', horizontalalignment='right',
           bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))


def create_high_vs_low_comparison():
    """Create comparison visualization of high vs low yielding fields."""
    
    print("\n" + "=" * 80)
    print("NDVI RASTER COMPARISON: HIGH VS LOW YIELDING FIELDS")
    print("=" * 80)
    
    # Credentials - load from environment variables
    import os
    CLIENT_ID = os.getenv("SENTINEL_HUB_CLIENT_ID")
    CLIENT_SECRET = os.getenv("SENTINEL_HUB_CLIENT_SECRET")
    
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Error: SENTINEL_HUB_CLIENT_ID and SENTINEL_HUB_CLIENT_SECRET must be set as environment variables")
        return
    
    visualizer = SentinelHubNDVIVisualizer(CLIENT_ID, CLIENT_SECRET)
    
    print("\n✓ Authenticating with Sentinel Hub...")
    visualizer.get_access_token()
    print("✓ Authentication successful")
    
    # Load data
    print("\nLoading data...")
    with open('agricultural_fields_with_data.geojson', 'r') as f:
        geojson_data = json.load(f)
    
    with open('sentinel_ndvi_fapar_data.json', 'r') as f:
        fapar_data = json.load(f)
    
    df_yield = pd.read_csv('yield_predictions.csv')
    
    # Get top and bottom fields
    top_fields = df_yield.nlargest(6, 'Grain Yield (ton/ha)')['Field Name'].values
    bottom_fields = df_yield.nsmallest(6, 'Grain Yield (ton/ha)')['Field Name'].values
    
    print(f"\nTop 6 fields (yields: {df_yield.nlargest(6, 'Grain Yield (ton/ha)')['Grain Yield (ton/ha)'].values})")
    print(f"Bottom 6 fields (yields: {df_yield.nsmallest(6, 'Grain Yield (ton/ha)')['Grain Yield (ton/ha)'].values})")
    
    # Create figure
    fig, axes = plt.subplots(2, 6, figsize=(24, 9))
    
    print(f"\n{'─' * 80}")
    print("FETCHING TOP 6 HIGH-YIELDING FIELDS")
    print(f"{'─' * 80}")
    
    # Top row: High yielding
    for idx, field_name in enumerate(top_fields):
        print(f"\n[{idx+1}/6] {field_name}")
        ax = axes[0, idx]
        
        # Find field
        feature = None
        for f in geojson_data['features']:
            if f['properties'].get('field_name') == field_name:
                feature = f
                break
        
        if not feature:
            print(f"  ✗ Not found")
            ax.text(0.5, 0.5, 'Field not found', ha='center', va='center')
            continue
        
        geometry = feature['geometry']
        variety = feature['properties'].get('wheat_variety', 'Unknown')
        
        # Get peak NDVI
        field_fapar = fapar_data['fields'].get(field_name, {})
        peak_obs, peak_ndvi = find_peak_ndvi_date(field_fapar)
        
        if not peak_obs:
            print(f"  ✗ No NDVI data")
            ax.text(0.5, 0.5, 'No NDVI data', ha='center', va='center')
            continue
        
        peak_date = peak_obs['from']
        print(f"  Peak NDVI: {peak_ndvi:.3f} on {peak_date}")
        
        # Get bbox and dimensions
        bbox = visualizer.get_bbox_from_geometry(geometry)
        width, height = visualizer.calculate_field_dimensions(bbox)
        
        # Fetch with retry
        print(f"  Fetching imagery (with retry logic)...")
        ndvi_image, date_range = visualizer.fetch_ndvi_with_retry(bbox, peak_date, width, height)
        
        if ndvi_image is None:
            ax.text(0.5, 0.5, 'No clear imagery\navailable', ha='center', va='center')
            ax.set_title(f'{field_name}\n(No imagery)', fontsize=9, color='gray')
            continue
        
        # Get yield
        yield_val = df_yield[df_yield['Field Name'] == field_name]['Grain Yield (ton/ha)'].values[0]
        
        # Visualize
        visualize_field_comparison(
            ax, field_name, geometry, ndvi_image, bbox,
            peak_ndvi, variety, yield_val, date_range, is_high_yield=True
        )
    
    print(f"\n{'─' * 80}")
    print("FETCHING BOTTOM 6 LOW-YIELDING FIELDS")
    print(f"{'─' * 80}")
    
    # Bottom row: Low yielding
    for idx, field_name in enumerate(bottom_fields):
        print(f"\n[{idx+1}/6] {field_name}")
        ax = axes[1, idx]
        
        # Find field
        feature = None
        for f in geojson_data['features']:
            if f['properties'].get('field_name') == field_name:
                feature = f
                break
        
        if not feature:
            print(f"  ✗ Not found")
            ax.text(0.5, 0.5, 'Field not found', ha='center', va='center')
            continue
        
        geometry = feature['geometry']
        variety = feature['properties'].get('wheat_variety', 'Unknown')
        
        # Get peak NDVI
        field_fapar = fapar_data['fields'].get(field_name, {})
        peak_obs, peak_ndvi = find_peak_ndvi_date(field_fapar)
        
        if not peak_obs:
            print(f"  ✗ No NDVI data")
            ax.text(0.5, 0.5, 'No NDVI data', ha='center', va='center')
            continue
        
        peak_date = peak_obs['from']
        print(f"  Peak NDVI: {peak_ndvi:.3f} on {peak_date}")
        
        # Get bbox and dimensions
        bbox = visualizer.get_bbox_from_geometry(geometry)
        width, height = visualizer.calculate_field_dimensions(bbox)
        
        # Fetch with retry
        print(f"  Fetching imagery (with retry logic)...")
        ndvi_image, date_range = visualizer.fetch_ndvi_with_retry(bbox, peak_date, width, height)
        
        if ndvi_image is None:
            ax.text(0.5, 0.5, 'No clear imagery\navailable', ha='center', va='center')
            ax.set_title(f'{field_name}\n(No imagery)', fontsize=9, color='gray')
            continue
        
        # Get yield
        yield_val = df_yield[df_yield['Field Name'] == field_name]['Grain Yield (ton/ha)'].values[0]
        
        # Visualize
        visualize_field_comparison(
            ax, field_name, geometry, ndvi_image, bbox,
            peak_ndvi, variety, yield_val, date_range, is_high_yield=False
        )
    
    # Overall title
    plt.suptitle('NDVI Raster Comparison: Top 6 High-Yielding vs Bottom 6 Low-Yielding Fields',
                 fontsize=14, fontweight='bold', y=0.98)
    
    plt.tight_layout()
    
    output_file = 'ndvi_comparison_high_vs_low.png'
    plt.savefig(output_file, dpi=200, bbox_inches='tight')
    print(f"\n✓ Saved comparison to: {output_file}")
    
    plt.savefig('ndvi_comparison_high_vs_low.pdf', bbox_inches='tight')
    print(f"✓ Saved PDF to: ndvi_comparison_high_vs_low.pdf")
    
    return fig


if __name__ == "__main__":
    try:
        create_high_vs_low_comparison()
        
        print("\n" + "=" * 80)
        print("✓ COMPARISON VISUALIZATION COMPLETE")
        print("=" * 80)
        print("\nFiles created:")
        print("  - ndvi_comparison_high_vs_low.png")
        print("  - ndvi_comparison_high_vs_low.pdf")
        print("\n💡 Top row = High yielders, Bottom row = Low yielders")
        print("   Black fields indicate no cloud-free imagery available")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

