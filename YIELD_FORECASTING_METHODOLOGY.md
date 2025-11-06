# Wheat Yield Forecasting Methodology: Sentinel-2 Statistical API

## Overview

This document provides a detailed, step-by-step description of the wheat yield forecasting methodology using Sentinel-2 satellite imagery via the Sentinel Hub Statistical API. The approach combines remote sensing data, meteorological data, and crop growth modeling to predict final grain yield.

---

## Table of Contents

1. [Data Acquisition](#1-data-acquisition)
2. [NDVI Calculation](#2-ndvi-calculation)
3. [fAPAR Calculation](#3-fapar-calculation)
4. [Solar Radiation (PAR) Data](#4-solar-radiation-par-data)
5. [Phenology Modeling](#5-phenology-modeling)
6. [Biomass Accumulation](#6-biomass-accumulation)
7. [Yield Prediction](#7-yield-prediction)
8. [Complete Workflow](#8-complete-workflow)

---

## 1. Data Acquisition

### 1.1 Sentinel-2 Statistical API Overview

The Sentinel Hub Statistical API provides aggregated statistics (mean, min, max, percentiles) for satellite imagery over specified areas and time periods. This is more efficient than downloading full image tiles and processing them locally.

**Key Advantages:**
- Cloud-filtered statistics (only clear pixels)
- Pre-aggregated data (no need to download full images)
- Multiple statistical metrics (mean, std, percentiles)
- Time-series ready format

### 1.2 Authentication

**Step 1:** Authenticate with Sentinel Hub using OAuth 2.0 client credentials.

```python
# OAuth token request
POST https://services.sentinel-hub.com/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
&client_id={CLIENT_ID}
&client_secret={CLIENT_SECRET}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600
}
```

### 1.3 Field Geometry Definition

Each agricultural field is defined as a polygon in GeoJSON format:

```json
{
  "type": "Polygon",
  "coordinates": [[
    [lon1, lat1],
    [lon2, lat2],
    [lon3, lat3],
    [lon4, lat4],
    [lon1, lat1]
  ]]
}
```

**Field Metadata Required:**
- Field name
- Sowing date (YYYY-MM-DD)
- Wheat variety
- Geographic coordinates (latitude, longitude)

### 1.4 Statistical API Request

**Step 2:** Create a Statistical API request for Sentinel-2 data.

**Request Structure:**
```json
{
  "input": {
    "bounds": {
      "bbox": [min_lon, min_lat, max_lon, max_lat],
      "properties": {
        "crs": "http://www.opengis.net/def/crs/EPSG/0/4326"
      }
    },
    "data": [{
      "type": "sentinel-2-l2a",
      "dataFilter": {
        "timeRange": {
          "from": "2024-05-01T00:00:00Z",
          "to": "2024-12-01T00:00:00Z"
        },
        "mosaickingOrder": "mostRecent"
      }
    }]
  },
  "aggregation": {
    "timeRange": {
      "from": "2024-05-01T00:00:00Z",
      "to": "2024-12-01T00:00:00Z"
    },
    "aggregationInterval": {
      "of": "P1W"  # Weekly intervals
    },
    "evalscript": "NDVI_CALCULATION_SCRIPT"
  },
  "calculations": {
    "default": {
      "statistics": {
        "default": {
          "percentiles": [10, 25, 50, 75, 90]
        }
      }
    }
  }
}
```

### 1.5 NDVI Calculation Script (evalscript)

The `evalscript` calculates NDVI directly in Sentinel Hub:

```javascript
//VERSION=3
function setup() {
  return {
    input: [{
      bands: ["B04", "B08"],  // Red and NIR bands
      units: "DN"
    }],
    output: {
      bands: 1,
      sampleType: "FLOAT32"
    }
  };
}

function evaluatePixel(samples) {
  // Sentinel-2 L2A provides reflectance values (0-1)
  let red = samples.B04;
  let nir = samples.B08;
  
  // Calculate NDVI
  let ndvi = (nir - red) / (nir + red);
  
  // Return NDVI value
  return [ndvi];
}
```

### 1.6 Response Processing

**Response Format:**
```json
{
  "data": [{
    "interval": {
      "from": "2024-05-01T00:00:00Z",
      "to": "2024-05-08T00:00:00Z"
    },
    "outputs": [{
      "bands": {
        "default": {
          "statistics": {
            "min": 0.15,
            "max": 0.85,
            "mean": 0.65,
            "std": 0.12,
            "percentiles": {
              "p10": 0.45,
              "p25": 0.55,
              "p50": 0.65,
              "p75": 0.75,
              "p90": 0.80
            },
            "sampleCount": 12345,
            "noDataCount": 234
          }
        }
      }
    }]
  }]
}
```

**Key Metrics Extracted:**
- `ndvi_mean`: Average NDVI for the time period
- `ndvi_std`: Standard deviation (spatial variability)
- `ndvi_p50`: Median NDVI
- `clear_percentage`: Percentage of clear pixels
- `sample_count`: Number of valid pixels

---

## 2. NDVI Calculation

### 2.1 NDVI Formula

The Normalized Difference Vegetation Index (NDVI) is calculated from Sentinel-2 reflectance bands:

**Equation 1: NDVI Calculation**

\[
\text{NDVI} = \frac{\rho_{\text{NIR}} - \rho_{\text{Red}}}{\rho_{\text{NIR}} + \rho_{\text{Red}}}
\]

Where:
- \(\rho_{\text{NIR}}\) = Near-Infrared reflectance (Band 8, ~842 nm)
- \(\rho_{\text{Red}}\) = Red reflectance (Band 4, ~665 nm)
- NDVI ranges from -1 to +1 (vegetation typically 0.2 to 0.9)

### 2.2 NDVI Interpretation

| NDVI Range | Interpretation | Growth Stage |
|-----------|----------------|--------------|
| < 0.2 | Bare soil / No vegetation | Pre-emergence |
| 0.2 - 0.4 | Low vegetation / Early growth | Emergence / Tillering |
| 0.4 - 0.6 | Moderate vegetation | Tillering / Stem Extension |
| 0.6 - 0.8 | High vegetation | Stem Extension / Heading |
| 0.8 - 0.9 | Peak vegetation | Heading / Anthesis |
| > 0.9 | Very dense vegetation | Peak growth / Grain Fill |

### 2.3 Time-Series Processing

**Weekly Aggregation:**
- Statistical API returns weekly aggregated NDVI values
- Each observation covers a 7-day period
- Only cloud-free pixels are included in statistics
- Missing weeks are handled through interpolation

**Data Quality:**
- Minimum clear pixel percentage: 50%
- Remove observations with very low sample counts
- Flag outliers (NDVI > 1.0 or < -0.2)

---

## 3. fAPAR Calculation

### 3.1 fAPAR Definition

**fAPAR** (fraction of Absorbed Photosynthetically Active Radiation) represents the fraction of incoming solar radiation in the PAR range (400-700 nm) that is absorbed by the vegetation canopy.

**Why fAPAR?**
- Directly relates to photosynthesis potential
- More physiologically meaningful than NDVI
- Required for biomass accumulation models

### 3.2 NDVI to fAPAR Conversion

**Equation 2: fAPAR from NDVI (Exponential Relationship)**

\[
\text{fAPAR}_g = 0.013 \times e^{4.48 \times \text{NDVI}}
\]

Where:
- \(\text{fAPAR}_g\) = Green fAPAR (fraction, 0-1)
- NDVI = Normalized Difference Vegetation Index (0-1)
- 0.013 and 4.48 are empirically derived coefficients

**Alternative Linear Relationship (for comparison):**

\[
\text{fAPAR} = 1.163 \times \text{NDVI} - 0.142
\]

**Note:** The exponential relationship is preferred as it better captures the saturation effect at high NDVI values.

### 3.3 fAPAR Values by Growth Stage

| Growth Stage | Typical NDVI | Calculated fAPAR | Interpretation |
|-------------|--------------|------------------|----------------|
| Emergence | 0.2 - 0.3 | 0.02 - 0.04 | Very low absorption |
| Tillering | 0.4 - 0.5 | 0.08 - 0.15 | Increasing absorption |
| Stem Extension | 0.6 - 0.7 | 0.25 - 0.45 | Rapid increase |
| Heading | 0.75 - 0.85 | 0.50 - 0.75 | Peak absorption |
| Anthesis | 0.80 - 0.90 | 0.65 - 0.85 | Maximum absorption |
| Grain Fill | 0.70 - 0.80 | 0.45 - 0.65 | Declining |
| Maturity | 0.40 - 0.60 | 0.15 - 0.35 | Low absorption |

### 3.4 Interpolation to Daily Values

**Step 3:** Interpolate weekly fAPAR to daily values for biomass calculations.

**Linear Interpolation:**

\[
\text{fAPAR}(t) = \text{fAPAR}_i + \frac{(\text{fAPAR}_{i+1} - \text{fAPAR}_i) \times (t - t_i)}{t_{i+1} - t_i}
\]

Where:
- \(t\) = Target date
- \(t_i\) = Start date of week \(i\)
- \(t_{i+1}\) = End date of week \(i+1\)
- \(\text{fAPAR}_i\) = fAPAR value for week \(i\)

**Boundary Conditions:**
- Before first observation: Use first fAPAR value
- After last observation: Use last fAPAR value
- Missing weeks: Linear interpolation between available weeks

---

## 4. Solar Radiation (PAR) Data

### 4.1 PAR Definition

**PAR** (Photosynthetically Active Radiation) is the portion of solar radiation in the wavelength range 400-700 nm that plants use for photosynthesis.

**Units:**
- MJ/m²/day (MegaJoules per square meter per day)
- mol/m²/day (moles per square meter per day)

**Conversion:**
\[
1 \text{ MJ/m²/day} \approx 2.06 \text{ mol/m²/day}
\]

### 4.2 PAR Data Acquisition

**Source:** Open-Meteo API (or similar meteorological service)

**Request Example:**
```
GET https://api.open-meteo.com/v1/forecast
  ?latitude=-32.5
  &longitude=-61.5
  &daily=shortwave_radiation_sum
  &start_date=2024-05-01
  &end_date=2024-12-01
  &timezone=America/Argentina/Cordoba
```

**Response:**
```json
{
  "daily": {
    "time": ["2024-05-01", "2024-05-02", ...],
    "shortwave_radiation_sum": [15.2, 16.8, 14.5, ...]
  }
}
```

### 4.3 Solar Radiation to PAR Conversion

**Equation 3: Shortwave Radiation to PAR**

\[
\text{PAR} = \text{SW}_{\text{rad}} \times 0.48
\]

Where:
- \(\text{SW}_{\text{rad}}\) = Shortwave radiation (MJ/m²/day)
- 0.48 = Fraction of shortwave radiation in PAR range (400-700 nm)
- PAR = Photosynthetically Active Radiation (MJ/m²/day)

**Typical Values:**
- Summer: 15-20 MJ/m²/day
- Winter: 8-12 MJ/m²/day
- Annual average: ~12 MJ/m²/day

### 4.4 Daily PAR Data Processing

**Data Requirements:**
- Daily values from sowing date to harvest date
- Consistent time series (no gaps)
- Units: MJ/m²/day

**Quality Checks:**
- Remove negative values
- Flag unrealistic values (> 25 MJ/m²/day)
- Handle missing days (interpolate or use climatological average)

---

## 5. Phenology Modeling

### 5.1 Phenology Overview

**Phenology** is the study of plant growth stages and their timing. For wheat yield forecasting, we need to know:
- When each growth stage occurs
- Which Radiation Use Efficiency (RUE) value to apply
- How growth stages affect biomass accumulation

### 5.2 Thermal Time (Growing Degree Days)

**Equation 4: Growing Degree Days (GDD)**

\[
\text{GDD} = \sum_{d=1}^{n} \max\left(0, \frac{T_{\text{max}} + T_{\text{min}}}{2} - T_{\text{base}}\right)
\]

Where:
- \(T_{\text{max}}\) = Maximum daily temperature (°C)
- \(T_{\text{min}}\) = Minimum daily temperature (°C)
- \(T_{\text{base}}\) = Base temperature for wheat (0°C)
- \(d\) = Day index
- \(n\) = Total number of days

**Alternative (with upper limit):**

\[
\text{GDD} = \sum_{d=1}^{n} \max\left(0, \min\left(\frac{T_{\text{max}} + T_{\text{min}}}{2} - T_{\text{base}}, T_{\text{opt}} - T_{\text{base}}\right)\right)
\]

Where:
- \(T_{\text{opt}}\) = Optimal temperature (20°C for wheat)
- Growth is capped at optimal temperature

### 5.3 Growth Stage Thresholds

**Wheat Growth Stages (Typical Argentine Varieties):**

| Growth Stage | GDD Range | Days After Sowing | Zadoks Scale |
|-------------|-----------|-------------------|--------------|
| Emergence | 0 - 150 | 0 - 20 | 10 - 19 |
| Tillering | 150 - 400 | 20 - 45 | 20 - 29 |
| Stem Extension | 400 - 900 | 45 - 75 | 30 - 39 |
| Heading | 900 - 1450 | 75 - 105 | 40 - 59 |
| Anthesis | 1450 - 1650 | 105 - 115 | 60 - 69 |
| Grain Fill | 1650 - 1850 | 115 - 140 | 70 - 85 |
| Maturity | 1850 - 2200 | 140 - 160 | 85 - 92 |

**Variety-Specific Adjustments:**
- Early-maturing varieties: Lower GDD thresholds
- Late-maturing varieties: Higher GDD thresholds
- Photoperiod sensitivity affects heading stage

### 5.4 Phenology Model Implementation

**Step 4:** Estimate growth stages for each day.

```python
def get_growth_stage(days_since_sowing, gdd_accumulated):
    if days_since_sowing < 20 or gdd_accumulated < 150:
        return 'Emergence'
    elif days_since_sowing < 45 or gdd_accumulated < 400:
        return 'Tillering'
    elif days_since_sowing < 75 or gdd_accumulated < 900:
        return 'Stem Extension'
    elif days_since_sowing < 105 or gdd_accumulated < 1450:
        return 'Heading/Anthesis'
    elif days_since_sowing < 140 or gdd_accumulated < 1850:
        return 'Grain Fill'
    else:
        return 'Maturity'
```

---

## 6. Biomass Accumulation

### 6.1 Radiation Use Efficiency (RUE)

**RUE** is the efficiency with which plants convert absorbed PAR into dry matter (biomass).

**Equation 5: RUE Definition**

\[
\text{RUE} = \frac{\Delta \text{Biomass}}{\text{APAR}}
\]

Where:
- \(\Delta \text{Biomass}\) = Biomass increment (g DM/m²)
- APAR = Absorbed PAR (MJ/m²)
- RUE = Radiation Use Efficiency (g DM/MJ PAR)

**Units:**
- RUE: g dry matter / MJ absorbed PAR
- Typical wheat RUE: 2.0 - 2.8 g DM/MJ PAR

### 6.2 RUE by Growth Stage

**Literature-Based RUE Values:**

| Growth Stage | RUE (g DM/MJ PAR) | Notes |
|-------------|-------------------|-------|
| Emergence | 2.0 | Low efficiency, establishment |
| Tillering | 2.4 | Increasing efficiency |
| Stem Extension | 2.7 | Peak efficiency |
| Heading/Anthesis | 2.6 | High efficiency maintained |
| Grain Fill | 2.2 | Declining efficiency |
| Maturity | 1.8 | Lowest efficiency |

**Source:** Sinclair & Muchow (1999), Kiniry et al. (1989)

### 6.3 Daily Biomass Calculation

**Equation 6: Daily Biomass Accumulation**

\[
\text{Biomass}_{\text{daily}} = \text{APAR} \times \text{RUE}
\]

Where:
\[
\text{APAR} = \text{fAPAR} \times \text{PAR}
\]

Therefore:

\[
\text{Biomass}_{\text{daily}} = \text{fAPAR} \times \text{PAR} \times \text{RUE}
\]

**Units:**
- fAPAR: dimensionless (0-1)
- PAR: MJ/m²/day
- RUE: g DM/MJ PAR
- Biomass: g DM/m²/day

**Example Calculation:**
- fAPAR = 0.75
- PAR = 12 MJ/m²/day
- RUE = 2.6 g DM/MJ PAR

\[
\text{APAR} = 0.75 \times 12 = 9.0 \text{ MJ/m²/day}
\]
\[
\text{Biomass}_{\text{daily}} = 9.0 \times 2.6 = 23.4 \text{ g DM/m²/day}
\]

### 6.4 Cumulative Biomass

**Equation 7: Total Above-Ground Biomass**

\[
\text{Biomass}_{\text{total}} = \sum_{d=\text{sowing}}^{\text{harvest}} \text{Biomass}_{\text{daily}}(d)
\]

Where:
- \(d\) = Day index
- Sowing = Sowing date
- Harvest = Harvest date (or maturity)

**Conversion to Common Units:**

\[
\text{Biomass}_{\text{kg/ha}} = \text{Biomass}_{\text{g/m²}} \times 10
\]

\[
\text{Biomass}_{\text{ton/ha}} = \frac{\text{Biomass}_{\text{kg/ha}}}{1000}
\]

**Example:**
- Total biomass = 1500 g DM/m²
- Biomass in kg/ha = 1500 × 10 = 15,000 kg DM/ha
- Biomass in ton/ha = 15,000 / 1000 = 15.0 ton DM/ha

---

## 7. Yield Prediction

### 7.1 Harvest Index

**Harvest Index (HI)** is the ratio of grain weight to total above-ground biomass.

**Equation 8: Harvest Index**

\[
\text{HI} = \frac{\text{Grain Weight}}{\text{Total Above-Ground Biomass}}
\]

**Typical Values:**
- Modern wheat varieties: 0.40 - 0.50
- Recommended default: 0.45
- Range used in uncertainty: 0.40 - 0.50

**Factors Affecting HI:**
- Variety genetics
- Environmental conditions
- Management practices
- Stress events (drought, heat)

### 7.2 Grain Yield Calculation

**Equation 9: Grain Yield from Biomass**

\[
\text{Yield} = \text{Biomass}_{\text{total}} \times \text{HI}
\]

**In Units:**

\[
\text{Yield}_{\text{kg/ha}} = \text{Biomass}_{\text{kg/ha}} \times \text{HI}
\]

\[
\text{Yield}_{\text{ton/ha}} = \frac{\text{Yield}_{\text{kg/ha}}}{1000}
\]

**Example:**
- Total biomass = 15.0 ton DM/ha
- Harvest Index = 0.45

\[
\text{Yield} = 15.0 \times 0.45 = 6.75 \text{ ton/ha}
\]

### 7.3 Yield Uncertainty

**Equation 10: Yield Range**

\[
\text{Yield}_{\text{low}} = \text{Biomass}_{\text{total}} \times \text{HI}_{\text{min}}
\]

\[
\text{Yield}_{\text{high}} = \text{Biomass}_{\text{total}} \times \text{HI}_{\text{max}}
\]

**Example:**
- Total biomass = 15.0 ton DM/ha
- HI_min = 0.40
- HI_max = 0.50

\[
\text{Yield}_{\text{low}} = 15.0 \times 0.40 = 6.0 \text{ ton/ha}
\]

\[
\text{Yield}_{\text{high}} = 15.0 \times 0.50 = 7.5 \text{ ton/ha}
\]

---

## 8. Complete Workflow

### 8.1 Step-by-Step Process

**Step 1: Data Preparation**
1. Define field geometry (polygon coordinates)
2. Collect field metadata (sowing date, variety, location)
3. Authenticate with Sentinel Hub API
4. Authenticate with meteorological API

**Step 2: NDVI Data Acquisition**
1. Create Statistical API request for Sentinel-2 L2A
2. Specify time range (sowing to harvest)
3. Set weekly aggregation interval
4. Execute NDVI calculation script
5. Extract NDVI statistics (mean, std, percentiles)
6. Filter by data quality (clear pixel percentage)

**Step 3: fAPAR Calculation**
1. Convert weekly NDVI to fAPAR using exponential formula:
   \[
   \text{fAPAR} = 0.013 \times e^{4.48 \times \text{NDVI}}
   \]
2. Interpolate weekly fAPAR to daily values
3. Validate fAPAR range (0-1)

**Step 4: PAR Data Acquisition**
1. Request daily solar radiation from meteorological API
2. Convert shortwave radiation to PAR:
   \[
   \text{PAR} = \text{SW}_{\text{rad}} \times 0.48
   \]
3. Validate PAR values (0-25 MJ/m²/day)

**Step 5: Phenology Modeling**
1. Calculate daily GDD:
   \[
   \text{GDD} = \sum \max\left(0, \frac{T_{\text{max}} + T_{\text{min}}}{2} - T_{\text{base}}\right)
   \]
2. Determine growth stage for each day
3. Assign RUE value based on growth stage

**Step 6: Daily Biomass Calculation**
For each day from sowing to harvest:
1. Calculate APAR:
   \[
   \text{APAR} = \text{fAPAR} \times \text{PAR}
   \]
2. Get RUE for current growth stage
3. Calculate daily biomass:
   \[
   \text{Biomass}_{\text{daily}} = \text{APAR} \times \text{RUE}
   \]

**Step 7: Total Biomass**
1. Sum all daily biomass values:
   \[
   \text{Biomass}_{\text{total}} = \sum \text{Biomass}_{\text{daily}}
   \]
2. Convert to kg/ha or ton/ha

**Step 8: Yield Prediction**
1. Apply harvest index:
   \[
   \text{Yield} = \text{Biomass}_{\text{total}} \times \text{HI}
   \]
2. Calculate yield range using HI uncertainty
3. Convert to final units (ton/ha)

### 8.2 Complete Mathematical Model

**Combined Equation:**

\[
\text{Yield}_{\text{ton/ha}} = \frac{\text{HI}}{1000} \times \sum_{d=1}^{n} \left[ \text{fAPAR}(d) \times \text{PAR}(d) \times \text{RUE}(d) \right] \times 10
\]

Where:
- \(d\) = Day index (1 to n)
- \(n\) = Total number of days from sowing to harvest
- \(\text{fAPAR}(d)\) = fAPAR value on day \(d\) (from NDVI)
- \(\text{PAR}(d)\) = PAR value on day \(d\) (MJ/m²/day)
- \(\text{RUE}(d)\) = RUE value on day \(d\) (g DM/MJ PAR)
- HI = Harvest Index (0.45 typical)
- 10 = Conversion factor (g/m² to kg/ha)
- 1000 = Conversion factor (kg/ha to ton/ha)

### 8.3 Data Flow Diagram

```
Field Geometry + Metadata
        ↓
Sentinel-2 Statistical API → NDVI (weekly)
        ↓
fAPAR Calculation (exponential formula)
        ↓
Meteorological API → PAR (daily)
        ↓
Phenology Model → Growth Stages → RUE values
        ↓
Daily Biomass = fAPAR × PAR × RUE
        ↓
Cumulative Biomass (sum over season)
        ↓
Yield = Biomass × Harvest Index
```

### 8.4 Key Assumptions

1. **fAPAR Relationship:**
   - Exponential relationship with NDVI is valid
   - No significant bias from soil background
   - Canopy closure assumptions hold

2. **RUE Values:**
   - Literature-based RUE values are appropriate
   - Growth stage classification is accurate
   - No significant stress effects unaccounted for

3. **Harvest Index:**
   - HI = 0.45 is representative for the varieties
   - Environmental conditions are favorable
   - No major yield-limiting stress events

4. **Data Quality:**
   - Sentinel-2 data is cloud-filtered correctly
   - PAR data is spatially representative
   - Phenology model is calibrated for the region

### 8.5 Limitations and Considerations

1. **Spatial Resolution:**
   - Sentinel-2: 10-20m resolution
   - Field boundaries may include non-crop areas
   - Mixed pixels at field edges

2. **Temporal Resolution:**
   - Weekly NDVI aggregation may miss rapid changes
   - Interpolation assumes smooth transitions
   - Missing weeks reduce accuracy

3. **Model Assumptions:**
   - Linear relationship between APAR and biomass
   - No water or nutrient limitations
   - Optimal temperature conditions

4. **Uncertainty Sources:**
   - NDVI to fAPAR conversion (±10%)
   - RUE estimation (±15%)
   - Harvest Index (±11%)
   - **Total uncertainty: ~±20%**

### 8.6 Validation and Calibration

**Recommended Validation:**
1. Compare predicted vs. actual yield for historical seasons
2. Calibrate RUE values based on local conditions
3. Adjust HI based on variety-specific data
4. Validate fAPAR conversion with field measurements

**Calibration Parameters:**
- RUE values (adjust for local conditions)
- Harvest Index (variety-specific)
- fAPAR conversion coefficients (if field data available)

---

## Summary

This methodology provides a comprehensive approach to wheat yield forecasting using Sentinel-2 Statistical API data. The key steps are:

1. **Acquire NDVI** from Sentinel-2 via Statistical API
2. **Convert to fAPAR** using exponential relationship
3. **Get PAR** from meteorological data
4. **Model phenology** to determine growth stages
5. **Calculate daily biomass** using RUE approach
6. **Sum biomass** over growing season
7. **Predict yield** using harvest index

The complete equation combines all these components:

\[
\text{Yield} = \text{HI} \times \sum \left[ 0.013 \times e^{4.48 \times \text{NDVI}} \times \text{PAR} \times \text{RUE} \right] \times 10 / 1000
\]

This approach provides a physically-based, transparent method for yield prediction that can be validated and improved with additional field data.

---

## References

1. **NDVI to fAPAR Conversion:**
   - Sellers, P. J. (1985). Canopy reflectance, photosynthesis and transpiration. *International Journal of Remote Sensing*, 6(8), 1335-1372.

2. **Radiation Use Efficiency:**
   - Sinclair, T. R., & Muchow, R. C. (1999). Radiation use efficiency. *Advances in Agronomy*, 65, 215-265.
   - Kiniry, J. R., et al. (1989). Radiation-use efficiency in biomass accumulation prior to grain-filling for five grain-crop species. *Field Crops Research*, 20(1), 51-64.

3. **Phenology Modeling:**
   - McMaster, G. S., & Wilhelm, W. W. (1997). Growing degree-days: one equation, two interpretations. *Agricultural and Forest Meteorology*, 87(4), 291-300.

4. **Sentinel-2 Data:**
   - Drusch, M., et al. (2012). Sentinel-2: ESA's optical high-resolution mission for GMES operational services. *Remote Sensing of Environment*, 120, 25-36.

---

**Document Version:** 1.0  
**Last Updated:** 2024  
**Author:** Yield Forecasting System


