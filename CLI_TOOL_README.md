# Wheat Yield Forecasting CLI Tool

A command-line interface tool for forecasting wheat yield using Sentinel-2 satellite data and the methodology described in `YIELD_FORECASTING_METHODOLOGY.md`.

## Features

- 🌾 **Interactive CLI**: Next.js-style prompts with beautiful terminal output
- 🛰️ **Sentinel-2 Integration**: Automatically fetches NDVI data via Statistical API
- ☀️ **Meteorological Data**: Fetches solar radiation (PAR) from Open-Meteo API
- 📊 **Complete Pipeline**: From NDVI to yield prediction in one command
- 🌱 **Variety Support**: 9 pre-configured wheat varieties plus custom parameters
- 💾 **JSON Export**: Saves detailed results for further analysis
- 🎨 **Styled Output**: Color-coded prompts, progress indicators, and formatted results
- ⌨️ **Interactive Selection**: Arrow-key navigation for variety selection (when `inquirer` is installed)

## Requirements

- Python 3.7+
- Internet connection (for API calls)
- Sentinel Hub OAuth credentials
- GeoJSON file with field polygon

## Installation

1. Install required Python packages:
```bash
pip install requests pandas numpy rich inquirer python-dotenv
```

Or install from requirements.txt:
```bash
pip install -r requirements.txt
```

**Note**: The tool uses `rich` for beautiful terminal output (similar to Next.js prompts) and `inquirer` for interactive selection. If these packages are not installed, the tool will fall back to basic prompts.

2. Set up Sentinel Hub credentials (see below)

## Quick Start

### Basic Usage

```bash
python forecast_yield_cli.py field.geojson
```

The tool will:
1. Load the field geometry from GeoJSON
2. Prompt you for planting date
3. Prompt you to select a wheat variety
4. Fetch all required data (NDVI, PAR)
5. Calculate yield forecast
6. Display results and save to JSON

### With .env File (Recommended)

Create a `.env` file in the project root:
```bash
SENTINEL_HUB_CLIENT_ID=your_client_id
SENTINEL_HUB_CLIENT_SECRET=your_client_secret
```

Then simply run:
```bash
python forecast_yield_cli.py field.geojson
```

### With Environment Variables

```bash
export SENTINEL_HUB_CLIENT_ID="your_client_id"
export SENTINEL_HUB_CLIENT_SECRET="your_client_secret"
python forecast_yield_cli.py field.geojson
```

### With Command-Line Arguments

```bash
python forecast_yield_cli.py field.geojson \
  --client-id "your_client_id" \
  --client-secret "your_client_secret"
```

## Sentinel Hub Credentials

You need Sentinel Hub OAuth credentials to access the Statistical API.

### Getting Credentials

1. Sign up at [Sentinel Hub](https://www.sentinel-hub.com/)
2. Go to [Dashboard → Settings → OAuth Clients](https://apps.sentinel-hub.com/dashboard/#/account/settings)
3. Create a new OAuth client or use existing one
4. Copy the `Client ID` and `Client Secret`

### Setting Credentials

**Option 1: .env File (Recommended)**
Create a `.env` file in the project root directory:
```bash
# .env
SENTINEL_HUB_CLIENT_ID=your_client_id
SENTINEL_HUB_CLIENT_SECRET=your_client_secret
```

The `.env` file is automatically loaded when you run the tool. **Important**: The `.env` file is ignored by git for security, so your credentials won't be committed to version control.

**Option 2: Environment Variables**
```bash
export SENTINEL_HUB_CLIENT_ID="your_client_id"
export SENTINEL_HUB_CLIENT_SECRET="your_client_secret"
```

**Option 3: Command-Line Arguments**
```bash
python forecast_yield_cli.py field.geojson \
  --client-id "your_client_id" \
  --client-secret "your_client_secret"
```

**Option 4: Interactive Prompt**
If credentials are not found in `.env` or environment variables, the tool will prompt you to enter them.

## GeoJSON Format

The tool accepts GeoJSON files with field polygons. Supported formats:

### FeatureCollection (Recommended)
```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "geometry": {
      "type": "Polygon",
      "coordinates": [[
        [-61.5, -32.5],
        [-61.4, -32.5],
        [-61.4, -32.4],
        [-61.5, -32.4],
        [-61.5, -32.5]
      ]]
    },
    "properties": {
      "name": "Field Name",
      "variety": "DM Pehuen"
    }
  }]
}
```

### Feature
```json
{
  "type": "Feature",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[...]]
  },
  "properties": {
    "name": "Field Name"
  }
}
```

### Polygon (Direct Geometry)
```json
{
  "type": "Polygon",
  "coordinates": [[...]]
}
```

**Note**: Coordinates should be in [longitude, latitude] format (WGS84, EPSG:4326).

## Available Wheat Varieties

The tool includes **50+ pre-configured wheat varieties** based on the CRONOTRIGO model (FAUBA - School of Agronomy, University of Buenos Aires), organized by breeder:

### Don Mario (DM) Varieties (12)
- DM Alerce, DM Algarrobo, DM Aromo, DM Ceibo, DM Cóndor, DM Guatambú, DM Ñandubay, DM Ñire, DM Pehuen, DM Quebracho, DM Timbó, DM Yaguareté

### ACA Varieties (8)
- ACA 303, ACA 304, ACA 315, ACA 360, ACA 365, ACA 601, ACA 602, ACA Fresno

### Buck (BG) Varieties (5)
- BG 610, BG 620, BG 630, BG 720, BG 750

### Baguette Varieties (3)
- Baguette 601, Baguette 620, Baguette 750

### Bio4 Varieties (2)
- Bio4 Baguette 601, Bio4 Baguette 620

### Klein Varieties (5)
- Klein Cacique, Klein Guerrero, Klein Proteo, Klein Rayén, Klein Sagitario

### Syngenta (SY) Varieties (3)
- SY 100, SY 200, SY 300

### Other Common Varieties (5)
- Bienvenido, Cronox, Relmo, Sursem, Taita

### Default Option
- **Other (Default parameters)** - Uses default parameters for unknown varieties

**Note**: All varieties include phenological parameters (GDD requirements for emergence, tillering, stem extension, heading, grain fill, and maturity) calibrated for Argentine growing conditions. Parameters are based on maturity groups: Early (~2100 GDD), Medium (~2150-2200 GDD), and Late (~2230+ GDD).

## Output

The tool generates:

1. **Console Output**: Summary of yield forecast
2. **JSON File**: Detailed results saved as `yield_forecast_<field_name>.json`

### JSON Output Structure

```json
{
  "field_name": "Example Field",
  "variety": "DM Pehuen",
  "planting_date": "2024-05-15",
  "total_biomass_ton_ha": 15.234,
  "total_biomass_kg_ha": 15234.0,
  "grain_yield_ton_ha": 6.855,
  "grain_yield_kg_ha": 6855.0,
  "yield_range_ton_ha": [6.094, 7.617],
  "harvest_index": 0.45,
  "days_of_data": 180,
  "ndvi_observations": 25,
  "par_days": 180
}
```

## Example Workflow

```bash
# 1. Prepare your field GeoJSON
# (use QGIS, Google Earth, or any GIS software)

# 2. Set credentials (create .env file or use environment variables)
# Create .env file with:
#   SENTINEL_HUB_CLIENT_ID=your_id
#   SENTINEL_HUB_CLIENT_SECRET=your_secret

# 3. Run the tool
python forecast_yield_cli.py my_field.geojson

# 4. Follow prompts:
#    - Enter planting date: 2024-05-15
#    - Select variety: 2 (DM Pehuen)

# 5. Wait for data processing (may take 1-2 minutes)

# 6. View results in console and JSON file
```

## Methodology

The tool implements the complete yield forecasting methodology:

1. **NDVI Acquisition**: Fetches weekly Sentinel-2 NDVI via Statistical API
2. **fAPAR Calculation**: Converts NDVI to fAPAR using exponential relationship
3. **PAR Data**: Fetches daily solar radiation from Open-Meteo
4. **Phenology Modeling**: Estimates growth stages based on thermal time
5. **Biomass Accumulation**: Calculates daily biomass using RUE approach
6. **Yield Prediction**: Applies harvest index to estimate grain yield

See `YIELD_FORECASTING_METHODOLOGY.md` for detailed equations and explanations.

## Troubleshooting

### Error: "Authentication failed"
- Check your Sentinel Hub credentials
- Verify the credentials are correct at https://apps.sentinel-hub.com/dashboard
- Ensure you have sufficient API quota

### Error: "No NDVI data retrieved"
- Check that the planting date is within Sentinel-2 data availability (2015-present)
- Verify the field geometry is valid (closed polygon)
- Check for cloud coverage issues (may need to adjust time range)

### Error: "No PAR data retrieved"
- Verify the field coordinates are correct
- Check internet connection
- Open-Meteo API may be temporarily unavailable

### Error: "Invalid GeoJSON"
- Ensure the file is valid JSON
- Check that coordinates are in [lon, lat] format
- Verify the polygon is closed (first and last coordinates match)

## Advanced Usage

### Custom Harvest Index

The tool uses a default harvest index of 0.45. To modify, edit the `HARVEST_INDEX` constant in `forecast_yield_cli.py`.

### Custom Time Range

By default, the tool fetches data for 180 days after planting. To modify, change the `timedelta(days=180)` in the code.

### Batch Processing

For multiple fields, create a simple script:

```python
import subprocess
import json

fields = ["field1.geojson", "field2.geojson", "field3.geojson"]

for field in fields:
    subprocess.run(["python", "forecast_yield_cli.py", field])
```

## Limitations

1. **Temporal Resolution**: NDVI data is aggregated weekly
2. **Spatial Resolution**: Based on Sentinel-2 10-20m resolution
3. **Model Assumptions**: Assumes optimal conditions (no major stress events)
4. **Uncertainty**: Yield predictions have ~±20% uncertainty

## Support

For issues or questions:
- Check the methodology document: `YIELD_FORECASTING_METHODOLOGY.md`
- Review the code comments in `forecast_yield_cli.py`
- Check Sentinel Hub documentation: https://documentation.sentinel-hub.com/

## License

This tool is part of the Las-Petacas-yield-forecasting project.

---

**Version**: 1.0  
**Last Updated**: 2024

