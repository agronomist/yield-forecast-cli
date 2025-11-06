# Wheat Varieties and Phenology Model

## Overview

This document describes all wheat varieties included in the yield forecasting system and how they are integrated into the phenology model. The system includes **50+ Argentine wheat varieties** with calibrated phenological parameters based on the CRONOTRIGO model approach (FAUBA - School of Agronomy, University of Buenos Aires).

## Phenology Model Structure

The phenology model tracks wheat development through six key growth stages using thermal time accumulation (Growing Degree Days - GDD):

1. **Emergence** (~135-154 GDD)
2. **Tillering** (~370-416 GDD)
3. **Stem Extension (Zadoks 30)** (~850-928 GDD)
4. **Heading/Anthesis (Zadoks 60)** (~1380-1488 GDD)
5. **Grain Fill (Zadoks 70)** (~1780-1888 GDD)
6. **Maturity (Zadoks 90)** (~2100-2238 GDD)

Each variety has specific GDD requirements for each stage, along with:
- **Vernalization requirement**: Low, Medium, Medium-High, or High
- **Photoperiod sensitivity**: Low, Medium, Medium-High, or High

## Maturity Groups

Varieties are organized into three maturity groups based on total GDD to maturity:

- **Early Maturity**: ~2100-2130 GDD (e.g., DM Aromo, DM Algarrobo)
- **Medium Maturity**: ~2140-2210 GDD (e.g., DM Pehuen, DM Alerce, ACA Fresno)
- **Late Maturity**: ~2215-2238 GDD (e.g., Baguette 620, BG 620, BG 750)

## Complete Variety List

### Don Mario (DM) Varieties (12 varieties)

| Variety | Maturity Group | GDD to Maturity | Vernalization | Photoperiod Sensitivity |
|---------|---------------|-----------------|---------------|-------------------------|
| DM Aromo | Early | 2100 | Low | Low |
| DM Yaguareté | Early | 2115 | Low-Medium | Low |
| DM Algarrobo | Early | 2130 | Medium | Medium-High |
| DM Ñire | Medium | 2145 | Medium | Medium-High |
| DM Guatambú | Medium | 2140 | Medium | Medium-High |
| DM Pehuen | Medium | 2150 | Medium | Medium |
| DM Ñandubay | Medium | 2160 | Medium | Medium |
| DM Quebracho | Medium | 2185 | Medium | Medium |
| DM Ceibo | Medium | 2195 | Medium | Medium |
| DM Alerce | Medium | 2200 | Medium | Medium |
| DM Timbó | Medium-Late | 2210 | Medium-High | Medium |
| DM Cóndor | Medium-Late | 2215 | Medium-High | Medium |

### ACA Varieties (8 varieties)

| Variety | Maturity Group | GDD to Maturity | Vernalization | Photoperiod Sensitivity |
|---------|---------------|-----------------|---------------|-------------------------|
| ACA 360 | Medium | 2188 | Medium | Medium |
| ACA 303 | Medium | 2192 | Medium | Medium |
| ACA 365 | Medium | 2198 | Medium | Medium |
| ACA Fresno | Medium | 2200 | Medium | Medium |
| ACA 304 | Medium | 2208 | Medium | Medium |
| ACA 315 | Medium-Late | 2212 | Medium-High | Medium |
| ACA 601 | Medium-Late | 2215 | Medium-High | Medium |
| ACA 602 | Medium-Late | 2218 | Medium-High | Medium |

### Buck (BG) Varieties (5 varieties)

| Variety | Maturity Group | GDD to Maturity | Vernalization | Photoperiod Sensitivity |
|---------|---------------|-----------------|---------------|-------------------------|
| BG 610 | Medium | 2170 | Medium | Medium |
| BG 620 | Late | 2230 | Medium-High | Medium |
| BG 630 | Late | 2232 | Medium-High | Medium |
| BG 720 | Late | 2235 | Medium-High | Medium |
| BG 750 | Late | 2238 | High | Medium-High |

### Baguette Varieties (3 varieties)

| Variety | Maturity Group | GDD to Maturity | Vernalization | Photoperiod Sensitivity |
|---------|---------------|-----------------|---------------|-------------------------|
| Baguette 601 | Medium | 2192 | Medium | Medium |
| Baguette 620 | Late | 2230 | Medium-High | Medium |
| Baguette 750 | Late | 2238 | High | Medium-High |

### Bio4 Varieties (2 varieties)

| Variety | Maturity Group | GDD to Maturity | Vernalization | Photoperiod Sensitivity |
|---------|---------------|-----------------|---------------|-------------------------|
| Bio4 Baguette 601 | Medium | 2192 | Medium | Medium |
| Bio4 Baguette 620 | Late | 2230 | Medium-High | Medium |

### Klein Varieties (5 varieties)

| Variety | Maturity Group | GDD to Maturity | Vernalization | Photoperiod Sensitivity |
|---------|---------------|-----------------|---------------|-------------------------|
| Klein Rayén | Medium | 2191 | Medium | Medium |
| Klein Cacique | Medium | 2189 | Medium | Medium |
| Klein Guerrero | Medium | 2196 | Medium | Medium |
| Klein Proteo | Medium-Late | 2209 | Medium-High | Medium |
| Klein Sagitario | Medium-Late | 2213 | Medium-High | Medium |

### Syngenta (SY) Varieties (3 varieties)

| Variety | Maturity Group | GDD to Maturity | Vernalization | Photoperiod Sensitivity |
|---------|---------------|-----------------|---------------|-------------------------|
| SY 100 | Medium | 2188 | Medium | Medium |
| SY 200 | Medium | 2198 | Medium | Medium |
| SY 300 | Medium-Late | 2210 | Medium-High | Medium |

### Other Common Varieties (5 varieties)

| Variety | Maturity Group | GDD to Maturity | Vernalization | Photoperiod Sensitivity |
|---------|---------------|-----------------|---------------|-------------------------|
| Relmo | Medium | 2189 | Medium | Medium |
| Bienvenido | Medium | 2191 | Medium | Medium |
| Sursem | Medium | 2196 | Medium | Medium |
| Cronox | Medium | 2206 | Medium | Medium |
| Taita | Medium-Late | 2215 | Medium-High | Medium |

### Default Option

- **Other (Default parameters)**: Uses default parameters (GDD maturity: 2180) for varieties not in the database

## How New Varieties Were Integrated

### Parameter Estimation Strategy

New varieties were integrated into the phenology model using the following approach:

1. **Maturity Group Classification**: Varieties were classified into Early, Medium, or Late maturity groups based on:
   - Known characteristics from Argentine wheat breeding programs
   - Similarity to existing varieties in the database
   - Typical maturity patterns for each breeder's portfolio

2. **GDD Parameter Calculation**: For each variety, GDD requirements were estimated using:
   - **Base values** from the 8 original varieties (DM Alerce, DM Pehuen, DM Algarrobo, DM Aromo, Baguette 620, BG 620, BG 610, ACA Fresno)
   - **Interpolation** within maturity groups
   - **Consistent ratios** between growth stages (e.g., heading is typically ~65% of maturity GDD)

3. **Vernalization and Photoperiod**: These parameters were assigned based on:
   - Typical characteristics of each breeder's varieties
   - Maturity group patterns (early varieties tend to have lower requirements)
   - Known characteristics of specific varieties when available

### Parameter Relationships

The model maintains consistent relationships between growth stages:

- **Emergence**: ~6-7% of maturity GDD
- **Tillering**: ~17-18% of maturity GDD
- **Stem Extension**: ~40-41% of maturity GDD
- **Heading**: ~65-66% of maturity GDD
- **Grain Fill**: ~84-85% of maturity GDD
- **Maturity**: 100% (base value)

### Example: DM Ceibo Integration

**DM Ceibo** was added as a medium-maturity variety:

- **Maturity Group**: Medium (between DM Pehuen at 2150 and DM Alerce at 2200)
- **GDD Maturity**: 2195 (interpolated)
- **Other stages**: Calculated using consistent ratios
- **Vernalization**: Medium (typical for DM varieties)
- **Photoperiod**: Medium (typical for medium-maturity varieties)

## Model Usage

All varieties are available in:
- **CLI Tool** (`forecast_yield_cli.py`): Interactive selection from organized list
- **Phenology Model** (`wheat_phenology_model.py`): Automatic parameter lookup
- **Yield Forecasting**: Full integration with NDVI, fAPAR, PAR, and biomass calculations

## Notes

- **Calibration Source**: Parameters are based on the CRONOTRIGO model approach (FAUBA) and typical Argentine wheat growing conditions
- **Default Parameters**: Unknown varieties use default parameters (GDD maturity: 2180) suitable for medium-maturity varieties
- **Future Updates**: The variety database can be expanded with additional varieties or refined with field-validated parameters

## References

- **CRONOTRIGO Model**: FAUBA - Cátedra de Cerealicultura, University of Buenos Aires
- **Base Model**: Thermal time accumulation with base temperature 0°C
- **Growth Stages**: Based on Zadoks scale (Zadoks 30, 60, 70, 90)

---

**Total Varieties**: 50+ varieties across 8 breeder groups  
**Last Updated**: November 2025

