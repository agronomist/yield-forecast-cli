"""
Extract and Analyze NDVI Pixel Values from Sentinel Hub

Uses Processing API to get actual pixel-level NDVI values for each field
and analyze the distributions to understand yield differences.
"""

import json
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from io import BytesIO
from PIL import Image
import seaborn as sns


class SentinelHubPixelAnalyzer:
    """Extract and analyze NDVI pixel values from Sentinel Hub."""
    
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
        
        resolution = 10  # 10m resolution
        
        width_px = int(width_m / resolution)
        height_px = int(height_m / resolution)
        
        max_dim = 2500
        if width_px > max_dim or height_px > max_dim:
            scale = max_dim / max(width_px, height_px)
            width_px = int(width_px * scale)
            height_px = int(height_px * scale)
        
        width_px = max(width_px, 50)
        height_px = max(height_px, 50)
        
        return width_px, height_px
    
    def fetch_ndvi_pixels(self, bbox, date_from, date_to, width, height):
        """
        Fetch NDVI pixel values from Sentinel Hub Processing API.
        Returns array of NDVI values (masked for clouds).
        """
        token = self.get_access_token()
        
        url = "https://services.sentinel-hub.com/api/v1/process"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Evalscript that returns scaled NDVI values (0-250 scale, 255=cloud)
        evalscript = """
//VERSION=3

function setup() {
  return {
    input: [{
      bands: ["B04", "B08", "SCL"],
      units: "DN"
    }],
    output: {
      bands: 1,
      sampleType: "UINT8"
    }
  }
}

function evaluatePixel(sample) {
    // Calculate NDVI
    let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);
    
    // Mask clouds
    let is_cloud = (sample.SCL == 3 || sample.SCL == 8 || sample.SCL == 9 || sample.SCL == 10);
    
    if (is_cloud) {
        return [255];  // Mark clouds as 255
    }
    
    // Scale NDVI from [-1, 1] to [0, 250]
    // NDVI = -1 -> 0, NDVI = 0 -> 125, NDVI = 1 -> 250
    let scaled = Math.round((ndvi + 1) * 125);
    scaled = Math.max(0, Math.min(250, scaled));
    
    return [scaled];
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
            
            # Read PNG data
            img = Image.open(BytesIO(response.content))
            scaled_array = np.array(img, dtype=np.uint8)
            
            # If RGB, take first channel
            if len(scaled_array.shape) == 3:
                scaled_array = scaled_array[:, :, 0]
            
            # Mask cloud pixels (255) and convert back to NDVI
            valid_mask = scaled_array < 255
            valid_pixels = scaled_array[valid_mask]
            
            # Convert from [0, 250] back to [-1, 1]
            # scaled = (ndvi + 1) * 125, so ndvi = (scaled / 125) - 1
            ndvi_pixels = (valid_pixels / 125.0) - 1.0
            
            return ndvi_pixels
            
        except Exception as e:
            print(f"      Error: {e}")
            return None
    
    def fetch_ndvi_with_retry(self, bbox, peak_date, width, height):
        """Try to fetch NDVI pixels with multiple date windows."""
        peak_dt = datetime.strptime(peak_date, '%Y-%m-%d')
        
        strategies = [
            (3, 3),
            (7, 7),
            (14, 14),
            (21, 21),
        ]
        
        for attempt, (days_before, days_after) in enumerate(strategies, 1):
            date_from = peak_dt - timedelta(days=days_before)
            date_to = peak_dt + timedelta(days=days_after)
            
            ndvi_pixels = self.fetch_ndvi_pixels(
                bbox,
                date_from.strftime('%Y-%m-%d'),
                date_to.strftime('%Y-%m-%d'),
                width,
                height
            )
            
            if ndvi_pixels is not None and len(ndvi_pixels) > 100:  # Need reasonable sample
                return ndvi_pixels, f"{date_from.strftime('%Y-%m-%d')} to {date_to.strftime('%Y-%m-%d')}"
        
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


def analyze_field_pixels():
    """Analyze NDVI pixel distributions for all fields."""
    
    print("\n" + "=" * 80)
    print("NDVI PIXEL-LEVEL ANALYSIS")
    print("=" * 80)
    
    # Credentials - load from environment variables
    import os
    CLIENT_ID = os.getenv("SENTINEL_HUB_CLIENT_ID")
    CLIENT_SECRET = os.getenv("SENTINEL_HUB_CLIENT_SECRET")
    
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Error: SENTINEL_HUB_CLIENT_ID and SENTINEL_HUB_CLIENT_SECRET must be set as environment variables")
        return
    
    analyzer = SentinelHubPixelAnalyzer(CLIENT_ID, CLIENT_SECRET)
    
    print("\n✓ Authenticating...")
    analyzer.get_access_token()
    print("✓ Authenticated")
    
    # Load data
    print("\nLoading data...")
    with open('agricultural_fields_with_data.geojson', 'r') as f:
        geojson_data = json.load(f)
    
    with open('sentinel_ndvi_fapar_data.json', 'r') as f:
        fapar_data = json.load(f)
    
    df_yield = pd.read_csv('yield_predictions.csv')
    
    # Get top and bottom fields
    top_fields = df_yield.nlargest(10, 'Grain Yield (ton/ha)')['Field Name'].values
    bottom_fields = df_yield.nsmallest(10, 'Grain Yield (ton/ha)')['Field Name'].values
    
    all_fields = list(top_fields) + list(bottom_fields)
    
    print(f"\nAnalyzing {len(all_fields)} fields (top 10 and bottom 10)...")
    
    results = []
    
    for idx, field_name in enumerate(all_fields, 1):
        print(f"\n[{idx}/{len(all_fields)}] {field_name}")
        
        # Find field
        feature = None
        for f in geojson_data['features']:
            if f['properties'].get('field_name') == field_name:
                feature = f
                break
        
        if not feature:
            print(f"  ✗ Not found")
            continue
        
        geometry = feature['geometry']
        variety = feature['properties'].get('wheat_variety', 'Unknown')
        
        # Get peak NDVI date
        field_fapar = fapar_data['fields'].get(field_name, {})
        peak_obs, peak_ndvi = find_peak_ndvi_date(field_fapar)
        
        if not peak_obs:
            print(f"  ✗ No NDVI data")
            continue
        
        peak_date = peak_obs['from']
        print(f"  Peak NDVI (aggregated): {peak_ndvi:.3f} on {peak_date}")
        
        # Get bbox and dimensions
        bbox = analyzer.get_bbox_from_geometry(geometry)
        width, height = analyzer.calculate_field_dimensions(bbox)
        
        print(f"  Fetching pixel values ({width}x{height} pixels)...")
        
        # Fetch pixel values
        ndvi_pixels, date_range = analyzer.fetch_ndvi_with_retry(bbox, peak_date, width, height)
        
        if ndvi_pixels is None or len(ndvi_pixels) < 100:
            print(f"  ✗ Failed to fetch valid pixels")
            continue
        
        print(f"  ✓ Got {len(ndvi_pixels)} valid pixels")
        
        # Calculate statistics
        stats = {
            'field_name': field_name,
            'variety': variety,
            'yield_ton_ha': df_yield[df_yield['Field Name'] == field_name]['Grain Yield (ton/ha)'].values[0],
            'peak_ndvi_aggregated': peak_ndvi,
            'pixel_count': len(ndvi_pixels),
            'pixel_mean': np.mean(ndvi_pixels),
            'pixel_median': np.median(ndvi_pixels),
            'pixel_std': np.std(ndvi_pixels),
            'pixel_min': np.min(ndvi_pixels),
            'pixel_max': np.max(ndvi_pixels),
            'pixel_p10': np.percentile(ndvi_pixels, 10),
            'pixel_p25': np.percentile(ndvi_pixels, 25),
            'pixel_p75': np.percentile(ndvi_pixels, 75),
            'pixel_p90': np.percentile(ndvi_pixels, 90),
            'date_range': date_range,
            'ndvi_pixels': ndvi_pixels  # Store for later analysis
        }
        
        print(f"  Pixel NDVI: mean={stats['pixel_mean']:.3f}, std={stats['pixel_std']:.3f}, range=[{stats['pixel_min']:.3f}, {stats['pixel_max']:.3f}]")
        
        results.append(stats)
    
    return results


def create_analysis_plots(results):
    """Create comprehensive analysis plots."""
    
    print("\n" + "=" * 80)
    print("CREATING ANALYSIS VISUALIZATIONS")
    print("=" * 80)
    
    df = pd.DataFrame([{k: v for k, v in r.items() if k != 'ndvi_pixels'} for r in results])
    
    # Separate high and low yielders
    df_high = df.nlargest(10, 'yield_ton_ha')
    df_low = df.nsmallest(10, 'yield_ton_ha')
    
    # Create figure with multiple subplots
    fig = plt.figure(figsize=(20, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
    
    # Plot 1: Mean NDVI vs Yield
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.scatter(df_high['pixel_mean'], df_high['yield_ton_ha'], 
               s=100, c='green', alpha=0.6, label='High yielders', edgecolors='black')
    ax1.scatter(df_low['pixel_mean'], df_low['yield_ton_ha'],
               s=100, c='red', alpha=0.6, label='Low yielders', edgecolors='black')
    
    # Add correlation line
    z = np.polyfit(df['pixel_mean'], df['yield_ton_ha'], 1)
    p = np.poly1d(z)
    x_line = np.linspace(df['pixel_mean'].min(), df['pixel_mean'].max(), 100)
    ax1.plot(x_line, p(x_line), "k--", alpha=0.5, linewidth=2)
    
    corr = np.corrcoef(df['pixel_mean'], df['yield_ton_ha'])[0, 1]
    ax1.text(0.05, 0.95, f'R = {corr:.3f}', transform=ax1.transAxes,
            fontsize=11, verticalalignment='top', 
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    ax1.set_xlabel('Mean Pixel NDVI', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Grain Yield (ton/ha)', fontsize=11, fontweight='bold')
    ax1.set_title('Mean Pixel NDVI vs Yield', fontsize=12, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: NDVI Std Dev vs Yield
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.scatter(df_high['pixel_std'], df_high['yield_ton_ha'],
               s=100, c='green', alpha=0.6, label='High yielders', edgecolors='black')
    ax2.scatter(df_low['pixel_std'], df_low['yield_ton_ha'],
               s=100, c='red', alpha=0.6, label='Low yielders', edgecolors='black')
    
    ax2.set_xlabel('NDVI Standard Deviation', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Grain Yield (ton/ha)', fontsize=11, fontweight='bold')
    ax2.set_title('NDVI Variability vs Yield', fontsize=12, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Aggregated vs Pixel Mean NDVI
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.scatter(df['peak_ndvi_aggregated'], df['pixel_mean'],
               s=100, c=df['yield_ton_ha'], cmap='RdYlGn', 
               alpha=0.7, edgecolors='black')
    
    # 1:1 line
    min_val = min(df['peak_ndvi_aggregated'].min(), df['pixel_mean'].min())
    max_val = max(df['peak_ndvi_aggregated'].max(), df['pixel_mean'].max())
    ax3.plot([min_val, max_val], [min_val, max_val], 'k--', linewidth=2, alpha=0.5)
    
    ax3.set_xlabel('Aggregated NDVI (Statistical API)', fontsize=11, fontweight='bold')
    ax3.set_ylabel('Pixel Mean NDVI (Processing API)', fontsize=11, fontweight='bold')
    ax3.set_title('Statistical vs Processing API Comparison', fontsize=12, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    
    cbar = plt.colorbar(ax3.collections[0], ax=ax3)
    cbar.set_label('Yield (ton/ha)', fontsize=10, fontweight='bold')
    
    # Plot 4: NDVI Distribution - High yielders
    ax4 = fig.add_subplot(gs[1, :])
    
    for idx, row in df_high.iterrows():
        result = [r for r in results if r['field_name'] == row['field_name']][0]
        pixels = result['ndvi_pixels']
        
        ax4.hist(pixels, bins=50, alpha=0.3, label=f"{row['field_name'][:20]} ({row['yield_ton_ha']:.1f})",
                density=True)
    
    ax4.set_xlabel('NDVI Value', fontsize=11, fontweight='bold')
    ax4.set_ylabel('Density', fontsize=11, fontweight='bold')
    ax4.set_title('NDVI Pixel Distribution - Top 10 High-Yielding Fields', 
                 fontsize=12, fontweight='bold', color='green')
    ax4.legend(fontsize=7, ncol=2)
    ax4.grid(True, alpha=0.3, axis='y')
    ax4.set_xlim(0, 1)
    
    # Plot 5: NDVI Distribution - Low yielders
    ax5 = fig.add_subplot(gs[2, :])
    
    for idx, row in df_low.iterrows():
        result = [r for r in results if r['field_name'] == row['field_name']][0]
        pixels = result['ndvi_pixels']
        
        ax5.hist(pixels, bins=50, alpha=0.3, label=f"{row['field_name'][:20]} ({row['yield_ton_ha']:.1f})",
                density=True)
    
    ax5.set_xlabel('NDVI Value', fontsize=11, fontweight='bold')
    ax5.set_ylabel('Density', fontsize=11, fontweight='bold')
    ax5.set_title('NDVI Pixel Distribution - Bottom 10 Low-Yielding Fields',
                 fontsize=12, fontweight='bold', color='red')
    ax5.legend(fontsize=7, ncol=2)
    ax5.grid(True, alpha=0.3, axis='y')
    ax5.set_xlim(0, 1)
    
    plt.suptitle('NDVI Pixel-Level Analysis: High vs Low Yielding Fields',
                fontsize=16, fontweight='bold', y=0.995)
    
    output_file = 'ndvi_pixel_analysis.png'
    plt.savefig(output_file, dpi=200, bbox_inches='tight')
    print(f"\n✓ Saved analysis to: {output_file}")
    
    plt.savefig('ndvi_pixel_analysis.pdf', bbox_inches='tight')
    print(f"✓ Saved PDF to: ndvi_pixel_analysis.pdf")


def print_summary_statistics(results):
    """Print summary statistics."""
    
    df = pd.DataFrame([{k: v for k, v in r.items() if k != 'ndvi_pixels'} for r in results])
    
    df_high = df.nlargest(10, 'yield_ton_ha')
    df_low = df.nsmallest(10, 'yield_ton_ha')
    
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    
    print(f"\n{'Metric':30} {'High Yielders':20} {'Low Yielders':20} {'Difference':15}")
    print("─" * 90)
    
    metrics = [
        ('Mean NDVI', 'pixel_mean'),
        ('Median NDVI', 'pixel_median'),
        ('Std Dev NDVI', 'pixel_std'),
        ('Min NDVI', 'pixel_min'),
        ('Max NDVI', 'pixel_max'),
        ('10th Percentile', 'pixel_p10'),
        ('90th Percentile', 'pixel_p90'),
    ]
    
    for label, col in metrics:
        high_val = df_high[col].mean()
        low_val = df_low[col].mean()
        diff = high_val - low_val
        diff_pct = (diff / low_val * 100) if low_val != 0 else 0
        
        print(f"{label:30} {high_val:20.3f} {low_val:20.3f} {diff:+.3f} ({diff_pct:+.1f}%)")
    
    print("\n" + "─" * 90)
    print("KEY FINDINGS")
    print("─" * 90)
    
    mean_diff = df_high['pixel_mean'].mean() - df_low['pixel_mean'].mean()
    print(f"\n1. Mean NDVI difference: {mean_diff:.3f} ({mean_diff/df_low['pixel_mean'].mean()*100:.1f}%)")
    print(f"   → High yielders have significantly higher NDVI")
    
    std_high = df_high['pixel_std'].mean()
    std_low = df_low['pixel_std'].mean()
    print(f"\n2. Within-field variability:")
    print(f"   High yielders std: {std_high:.3f}")
    print(f"   Low yielders std:  {std_low:.3f}")
    if std_low > std_high:
        print(f"   → Low yielders are MORE variable (poor uniformity)")
    else:
        print(f"   → Similar variability")
    
    # Save detailed CSV
    df.to_csv('ndvi_pixel_statistics.csv', index=False)
    print(f"\n✓ Saved detailed statistics to: ndvi_pixel_statistics.csv")


if __name__ == "__main__":
    try:
        # Analyze fields
        results = analyze_field_pixels()
        
        if len(results) > 0:
            # Print statistics
            print_summary_statistics(results)
            
            # Create visualizations
            create_analysis_plots(results)
            
            print("\n" + "=" * 80)
            print("✓ PIXEL-LEVEL ANALYSIS COMPLETE")
            print("=" * 80)
            print("\nFiles created:")
            print("  - ndvi_pixel_analysis.png")
            print("  - ndvi_pixel_analysis.pdf")
            print("  - ndvi_pixel_statistics.csv")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

