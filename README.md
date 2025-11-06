# Las Petacas Wheat Yield Forecasting

A wheat phenology modeling system for agricultural fields in Las Petacas, Argentina. This project implements a phenological model similar to CronoTrigo (University of Buenos Aires) to estimate growth stages and predict harvest timing based on variety characteristics and weather data.

## 📊 Project Overview

This system analyzes **69 wheat fields** covering approximately **5,640 hectares** in the Las Petacas region (Córdoba/Santa Fe, Argentina) and tracks their growth stages from sowing to maturity.

### Current Status (as of October 29, 2025)
- **40 fields (58.8%)** have reached maturity and are ready for harvest
- **28 fields (41.2%)** are in grain fill stage
- Sowing period: May 21 - June 13, 2025
- Growing season: 138-161 days

## 🌾 Wheat Varieties Analyzed

The model includes calibration for 8 Argentine wheat varieties:

| Variety | Fields | Maturity Rate | Notes |
|---------|--------|---------------|-------|
| DM Alerce | 18 | 100% | Early maturity, fully ready |
| DM Pehuen | 18 | 22% | Later maturity, mostly in grain fill |
| DM Algarrobo | 14 | 79% | Good progress |
| Baguette 620 | 6 | 0% | Later sowing, still developing |
| ACA Fresno | 4 | 100% | Early maturity |
| BG 620 | 4 | 0% | Later sowing |
| DM Aromo | 3 | 100% | Fast maturity |
| BG 610 | 1 | 0% | Later sowing |

## 🔬 Model Description

### Phenological Stages Tracked

The model tracks the following wheat growth stages using the Zadoks scale:

1. **Emergence** (~145-150 GDD)
2. **Tillering** (~380-410 GDD)
3. **Stem Extension** (Zadoks 30, ~870-920 GDD)
4. **Heading/Anthesis** (Zadoks 60, ~1380-1480 GDD)
5. **Grain Fill** (Zadoks 70, ~1780-1880 GDD)
6. **Maturity** (Zadoks 90, ~2100-2230 GDD)

### Model Approach

The model uses:
- **Thermal Time Accumulation**: Growing Degree Days (GDD) with base temperature of 0°C
- **Variety-Specific Parameters**: Different thermal requirements for each wheat variety
- **Daily Weather Data**: Actual temperature data from Open-Meteo API
- **Photoperiod Calculation**: Day length based on latitude and date

**Note**: This is a simplified implementation based on standard wheat phenology principles. For research-grade predictions, contact the University of Buenos Aires for the official CronoTrigo model parameters and calibration data.

## 🚀 Getting Started

### Prerequisites

```bash
python3 (Python 3.7+)
requests library
```

### Installation

1. Clone or download this repository
2. Install dependencies:

```bash
pip install requests
```

### Usage

#### 1. Run Phenology Analysis

```bash
python3 weather_phenology_analyzer.py
```

This will:
- Fetch historical weather data from Open-Meteo API (free, no API key needed)
- Calculate thermal time accumulation for each field
- Estimate current growth stages
- Generate output files:
  - `phenology_analysis_results.json` - Complete analysis data
  - `phenology_analysis_results.csv` - Spreadsheet-friendly format

#### 2. Visualize Results

```bash
python3 visualize_phenology.py
```

This generates:
- Variety performance comparison
- Growth stage timelines
- Sowing date impact analysis
- Harvest readiness forecast
- Management recommendations

## 📁 File Structure

```
Las-Petacas-yield-forecasting/
├── agricultural_fields_with_data.geojson   # Field boundaries and metadata
├── wheat_phenology_model.py                # Core phenology model
├── weather_phenology_analyzer.py           # Main analysis script
├── visualize_phenology.py                  # Visualization and reporting
├── sentinel_ndvi_fetcher.py                # Sentinel-2 NDVI data fetcher
├── integrate_ndvi_phenology.py             # NDVI + phenology integration
├── test_sentinel_connection.py             # Test Sentinel Hub API
├── requirements.txt                        # Python dependencies
├── README.md                               # This file
├── NDVI_GUIDE.md                           # NDVI integration guide
├── update_analysis.sh                      # Daily update script
├── phenology_analysis_results.json         # Analysis output (generated)
├── phenology_analysis_results.csv          # CSV export (generated)
├── sentinel_ndvi_data.json                 # NDVI time series (generated)
├── sentinel_ndvi_data.csv                  # NDVI CSV export (generated)
└── integrated_ndvi_phenology.csv           # Combined analysis (generated)
```

## 📈 Output Files

### phenology_analysis_results.json

Complete analysis results including:
- Field-by-field phenology data
- Accumulated GDD for each field
- Dates of achieved growth stages
- Current development stage and progress
- Summary statistics by variety and stage

### phenology_analysis_results.csv

Spreadsheet format with columns:
- Field Name, Variety, Sowing Date
- Days Since Sowing
- Accumulated GDD
- Current Stage, Stage Progress %
- Dates for: Emergence, Tillering, Stem Extension, Heading, Grain Fill, Maturity

## 🔧 Customization

### Adding New Varieties

Edit `wheat_phenology_model.py` and add variety parameters to the `VARIETY_PARAMS` dictionary:

```python
"New Variety Name": {
    "vernalization_requirement": "medium",
    "photoperiod_sensitivity": "medium",
    "gdd_emergence": 145,
    "gdd_tillering": 395,
    "gdd_stem_extension": 890,
    "gdd_heading": 1440,
    "gdd_grain_fill": 1840,
    "gdd_maturity": 2180,
}
```

### Using Different Weather Data

The system uses Open-Meteo API by default. To use your own weather data, modify the `fetch_weather_data_open_meteo()` function in `weather_phenology_analyzer.py` to load from your data source.

Weather data format required:
```python
[
    {
        'date': 'YYYY-MM-DD',
        'tmax': 25.5,  # Maximum temperature (°C)
        'tmin': 12.3,  # Minimum temperature (°C)
        'precipitation': 5.0  # Optional
    },
    ...
]
```

## 📊 Key Findings

### Current Season Analysis

1. **Early-sown fields (May 21-23)** have reached maturity:
   - DM Alerce: All 18 fields mature
   - DM Algarrobo: 11/14 fields mature
   - Average: 159 days from sowing to maturity

2. **Later-sown fields (June 1-13)** are in grain fill:
   - DM Pehuen: 14/18 fields still developing
   - Baguette 620: All 6 fields in grain fill
   - Average: 142-150 days since sowing

3. **Variety Performance**:
   - Fastest: DM Aromo (~150 days to maturity)
   - Medium: DM Alerce, ACA Fresno (~159 days)
   - Slower: DM Pehuen, Baguette 620 (>160 days projected)

## 🌤️ Weather Data

The system automatically fetches historical weather data from the [Open-Meteo Archive API](https://open-meteo.com), which provides:
- Daily maximum and minimum temperatures
- Historical weather back to 1940
- Free access with no API key required
- Location: Las Petacas region (-32.51°S, -61.43°W)

## 📚 Scientific Background

### CronoTrigo Model

CronoTrigo is a wheat phenology model developed by the School of Agronomy at the University of Buenos Aires (FAUBA). It predicts wheat development stages based on:

- **Thermal Time**: Growing degree day accumulation
- **Photoperiod**: Day length sensitivity by variety
- **Vernalization**: Cold temperature requirements
- **Variety Genetics**: Cultivar-specific parameters

For the official CronoTrigo model and calibrated parameters for Argentine varieties, contact:
- **FAUBA - Cátedra de Cerealicultura**
- University of Buenos Aires, School of Agronomy
- Website: http://www.agro.uba.ar

### Model References

This implementation is based on standard wheat phenology modeling approaches:
- Growing Degree Day (GDD) calculation using base temperature
- Zadoks scale for growth stage classification
- Thermal time requirements calibrated for Argentine varieties

## 🎯 Use Cases

1. **Harvest Planning**
   - Identify fields ready for harvest
   - Optimize equipment scheduling
   - Plan storage and logistics

2. **Crop Management**
   - Time fertilizer and pesticide applications
   - Irrigation scheduling during critical stages
   - Disease and pest monitoring

3. **Yield Forecasting**
   - Estimate harvest timing
   - Predict yield potential based on stage progression
   - Early warning for delayed development

4. **Research & Planning**
   - Compare variety performance
   - Analyze sowing date impact
   - Optimize next season's planting decisions

## ⚠️ Limitations

1. **Model Simplifications**:
   - Does not account for water stress
   - Simplified vernalization treatment
   - No explicit pest/disease effects
   - Weather data is historical, not forecasted

2. **Variety Parameters**:
   - Thermal time requirements are approximations
   - Official CronoTrigo calibration would improve accuracy
   - May need local calibration for your specific conditions

3. **Weather Data**:
   - Uses regional weather (single point for all fields)
   - Microclimate variations not captured
   - Future predictions require weather forecasts

## 🛰️ Satellite NDVI Integration

The system now includes **Sentinel-2 NDVI monitoring** using Sentinel Hub's Statistical API:

### Features
- ✅ Weekly NDVI time series from sowing to present
- ✅ Cloud filtering and scene classification masking
- ✅ Safe handling of large fields (dynamic resolution)
- ✅ Integration with phenology predictions
- ✅ Anomaly detection for crop stress

### Quick Start

**1. Test connection (recommended first):**
```bash
python3 test_sentinel_connection.py
```

**2. Fetch NDVI for all fields (~30-60 min):**
```bash
python3 sentinel_ndvi_fetcher.py
```

**3. Integrate with phenology analysis:**
```bash
python3 integrate_ndvi_phenology.py
```

See [NDVI_GUIDE.md](NDVI_GUIDE.md) for complete documentation.

## 🔮 Future Enhancements

Potential improvements:
- Soil moisture modeling
- Yield prediction algorithms based on NDVI trends
- Weather forecast integration for future stage predictions
- Disease risk modeling
- Water stress impact on development rate
- Integration with official CronoTrigo parameters
- LAI estimation from Sentinel-2

## 📝 License

This project is provided for educational and research purposes. Weather data is provided by Open-Meteo under their terms of service.

## 🤝 Contributing

Suggestions and improvements are welcome! Areas for contribution:
- Local calibration with field observations
- Integration with other data sources
- Yield prediction models
- Visualization improvements

## 📧 Contact

For questions about this implementation, please open an issue on the project repository.

For questions about the official CronoTrigo model, contact the University of Buenos Aires School of Agronomy.

---

**Last Updated**: October 29, 2025

**Analysis Status**: Active growing season, harvest in progress
