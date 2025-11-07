# Wheat Yield Forecasting CLI

A command-line tool for forecasting wheat yield using Sentinel-2 satellite imagery, meteorological data, and phenological modeling. Works with any agricultural field defined in GeoJSON format.

## 🌾 Overview

This CLI tool provides accurate wheat yield predictions by:
- Fetching NDVI data from Sentinel-2 via Sentinel Hub Statistical API
- Calculating fAPAR (fraction of Absorbed Photosynthetically Active Radiation)
- Tracking phenological growth stages using thermal time accumulation
- Estimating biomass accumulation using Radiation Use Efficiency (RUE)
- Predicting final yield using harvest index

## 🚀 Quick Start

### Installation

1. Clone the repository:
```bash
git clone https://github.com/agronomist/yield-forecast-cli.git
cd yield-forecast-cli
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up credentials:
```bash
cp .env.example .env
# Edit .env and add your Sentinel Hub credentials
```

### Using the CLI Tool

The main entry point is the interactive CLI tool:

```bash
python forecast_yield_cli.py field.geojson
```

The tool will:
1. Load the field geometry from GeoJSON
2. Prompt for planting date and wheat variety
3. Fetch Sentinel-2 NDVI data (up to day before yesterday)
4. Fetch solar radiation (PAR) data from Open-Meteo
5. Calculate phenology stages and biomass accumulation
6. Predict final yield

**Example:**
```bash
python forecast_yield_cli.py example_field.geojson
```

## 📋 Requirements

- Python 3.8+
- Sentinel Hub OAuth credentials (Client ID and Client Secret)
- GeoJSON file with field polygon geometry
- Internet connection for API calls

### Python Dependencies

See `requirements.txt` for the complete list. Key dependencies:
- `requests` - API calls
- `pandas` - Data processing
- `numpy` - Numerical calculations
- `rich` - Beautiful CLI formatting
- `inquirer` - Interactive prompts
- `python-dotenv` - Environment variable management

## 🔑 Credentials Setup

### Option 1: .env File (Recommended)

Create a `.env` file in the project root:

```bash
# .env
SENTINEL_HUB_CLIENT_ID=your_client_id
SENTINEL_HUB_CLIENT_SECRET=your_client_secret
```

The `.env` file is automatically loaded and is excluded from version control.

### Option 2: Environment Variables

```bash
export SENTINEL_HUB_CLIENT_ID="your_client_id"
export SENTINEL_HUB_CLIENT_SECRET="your_client_secret"
```

### Getting Sentinel Hub Credentials

1. Sign up at [Sentinel Hub](https://www.sentinel-hub.com/)
2. Create an OAuth application in the dashboard
3. Copy your Client ID and Client Secret
4. Add them to your `.env` file

## 📁 Project Structure

```
.
├── forecast_yield_cli.py          # Main CLI tool
├── wheat_phenology_model.py       # Phenology model with 50+ varieties
├── calculate_fapar.py             # fAPAR calculation utilities
├── fetch_solar_radiation.py       # PAR data fetching
├── sentinel_ndvi_fetcher.py      # Sentinel-2 NDVI data fetching
├── example_field.geojson          # Example GeoJSON file
├── .env.example                   # Credentials template
├── requirements.txt               # Python dependencies
├── CLI_TOOL_README.md             # Detailed CLI documentation
├── YIELD_FORECASTING_METHODOLOGY.md  # Complete methodology
└── WHEAT_VARIETIES_PHENOLOGY.md   # Variety database documentation
```

## 🌾 Supported Wheat Varieties

The system includes **50+ Argentine wheat varieties** organized by breeder:

- **Don Mario (DM)**: 12 varieties (DM Alerce, DM Pehuen, DM Ceibo, etc.)
- **ACA**: 8 varieties (ACA 303, ACA 304, ACA Fresno, etc.)
- **Buck (BG)**: 5 varieties (BG 610, BG 620, BG 750, etc.)
- **Baguette**: 3 varieties
- **Bio4**: 2 varieties
- **Klein**: 5 varieties
- **Syngenta (SY)**: 3 varieties
- **Other**: 5 common varieties

See `WHEAT_VARIETIES_PHENOLOGY.md` for the complete list and phenological parameters.

## 📊 Methodology

The yield forecasting methodology is based on:

1. **NDVI to fAPAR Conversion**: Using empirical relationships
2. **Phenology Modeling**: Thermal time accumulation (GDD) with variety-specific parameters
3. **Biomass Calculation**: Daily APAR × RUE (Radiation Use Efficiency)
4. **Yield Prediction**: Biomass × Harvest Index

For detailed equations and methodology, see `YIELD_FORECASTING_METHODOLOGY.md`.

## 📝 GeoJSON Format

Your GeoJSON file should contain a Feature with a Polygon geometry:

```json
{
  "type": "Feature",
  "properties": {
    "field_name": "My Field"
  },
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[lon1, lat1], [lon2, lat2], ...]]
  }
}
```

The CLI will prompt you for planting date and wheat variety if they're not in the properties.

## 📖 Documentation

- **CLI_TOOL_README.md**: Complete CLI tool documentation
- **YIELD_FORECASTING_METHODOLOGY.md**: Step-by-step methodology with equations
- **WHEAT_VARIETIES_PHENOLOGY.md**: Complete variety database and phenology model

## 🔒 Security

**Important**: Never commit your `.env` file or hardcode credentials in scripts. The repository is configured to exclude:
- `.env` files
- All credential-related files
- Data files (CSV, JSON, logs)

## 🛠️ Development

### Adding New Varieties

Varieties are defined in `wheat_phenology_model.py` in the `VARIETY_PARAMS` dictionary. See `WHEAT_VARIETIES_PHENOLOGY.md` for parameter estimation guidelines.

## 📄 License

[Add your license here]

## 🙏 Acknowledgments

- **CRONOTRIGO Model**: FAUBA - School of Agronomy, University of Buenos Aires
- **Sentinel Hub**: For satellite data access
- **Open-Meteo**: For meteorological data

## 📧 Contact

[Add your contact information]

---

**Note**: This tool fetches data up to "day before yesterday" to ensure only historical data is requested from archive APIs.
