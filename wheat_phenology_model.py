"""
Wheat Phenology Model for Yield Forecasting
Based on thermal time accumulation, photoperiod, and variety-specific parameters

This model estimates wheat growth stages similar to the CronoTrigo approach
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import math


class WheatPhenologyModel:
    """
    Wheat phenology model based on thermal time accumulation.
    
    The model tracks key growth stages:
    - Emergence
    - Tillering
    - Stem Extension (Zadoks 30)
    - Heading/Anthesis (Zadoks 60)
    - Grain Fill (Zadoks 70)
    - Maturity (Zadoks 90)
    """
    
    # Base temperatures for wheat development
    BASE_TEMP = 0.0  # Base temperature (°C)
    OPT_TEMP = 20.0  # Optimal temperature (°C)
    MAX_TEMP = 35.0  # Maximum temperature (°C)
    
    # Variety parameters (thermal time requirements in °C·days)
    # Based on CRONOTRIGO model (FAUBA) and typical Argentine wheat varieties
    # Parameters estimated from maturity groups: Early (~2100 GDD), Medium (~2150-2200 GDD), Late (~2230+ GDD)
    VARIETY_PARAMS = {
        # ===== DON MARIO (DM) VARIETIES =====
        "DM Alerce": {
            "vernalization_requirement": "medium",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 150,
            "gdd_tillering": 400,
            "gdd_stem_extension": 900,
            "gdd_heading": 1450,
            "gdd_grain_fill": 1850,
            "gdd_maturity": 2200,
        },
        "DM Pehuen": {
            "vernalization_requirement": "medium",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 145,
            "gdd_tillering": 390,
            "gdd_stem_extension": 880,
            "gdd_heading": 1420,
            "gdd_grain_fill": 1820,
            "gdd_maturity": 2150,
        },
        "DM Algarrobo": {
            "vernalization_requirement": "medium",
            "photoperiod_sensitivity": "medium-high",
            "gdd_emergence": 140,
            "gdd_tillering": 380,
            "gdd_stem_extension": 870,
            "gdd_heading": 1400,
            "gdd_grain_fill": 1800,
            "gdd_maturity": 2130,
        },
        "DM Aromo": {
            "vernalization_requirement": "low",
            "photoperiod_sensitivity": "low",
            "gdd_emergence": 135,
            "gdd_tillering": 370,
            "gdd_stem_extension": 850,
            "gdd_heading": 1380,
            "gdd_grain_fill": 1780,
            "gdd_maturity": 2100,
        },
        "DM Ceibo": {
            "vernalization_requirement": "medium",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 148,
            "gdd_tillering": 398,
            "gdd_stem_extension": 895,
            "gdd_heading": 1445,
            "gdd_grain_fill": 1845,
            "gdd_maturity": 2195,
        },
        "DM Cóndor": {
            "vernalization_requirement": "medium-high",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 152,
            "gdd_tillering": 405,
            "gdd_stem_extension": 910,
            "gdd_heading": 1465,
            "gdd_grain_fill": 1865,
            "gdd_maturity": 2215,
        },
        "DM Guatambú": {
            "vernalization_requirement": "medium",
            "photoperiod_sensitivity": "medium-high",
            "gdd_emergence": 142,
            "gdd_tillering": 385,
            "gdd_stem_extension": 875,
            "gdd_heading": 1410,
            "gdd_grain_fill": 1810,
            "gdd_maturity": 2140,
        },
        "DM Quebracho": {
            "vernalization_requirement": "medium",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 147,
            "gdd_tillering": 395,
            "gdd_stem_extension": 885,
            "gdd_heading": 1435,
            "gdd_grain_fill": 1835,
            "gdd_maturity": 2185,
        },
        "DM Yaguareté": {
            "vernalization_requirement": "low-medium",
            "photoperiod_sensitivity": "low",
            "gdd_emergence": 138,
            "gdd_tillering": 375,
            "gdd_stem_extension": 860,
            "gdd_heading": 1390,
            "gdd_grain_fill": 1790,
            "gdd_maturity": 2115,
        },
        "DM Ñandubay": {
            "vernalization_requirement": "medium",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 146,
            "gdd_tillering": 392,
            "gdd_stem_extension": 882,
            "gdd_heading": 1425,
            "gdd_grain_fill": 1825,
            "gdd_maturity": 2160,
        },
        "DM Timbó": {
            "vernalization_requirement": "medium-high",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 151,
            "gdd_tillering": 403,
            "gdd_stem_extension": 905,
            "gdd_heading": 1460,
            "gdd_grain_fill": 1860,
            "gdd_maturity": 2210,
        },
        "DM Ñire": {
            "vernalization_requirement": "medium",
            "photoperiod_sensitivity": "medium-high",
            "gdd_emergence": 143,
            "gdd_tillering": 388,
            "gdd_stem_extension": 878,
            "gdd_heading": 1415,
            "gdd_grain_fill": 1815,
            "gdd_maturity": 2145,
        },
        # ===== ACA VARIETIES =====
        "ACA Fresno": {
            "vernalization_requirement": "medium",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 148,
            "gdd_tillering": 400,
            "gdd_stem_extension": 900,
            "gdd_heading": 1450,
            "gdd_grain_fill": 1850,
            "gdd_maturity": 2200,
        },
        "ACA 303": {
            "vernalization_requirement": "medium",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 147,
            "gdd_tillering": 397,
            "gdd_stem_extension": 892,
            "gdd_heading": 1442,
            "gdd_grain_fill": 1842,
            "gdd_maturity": 2192,
        },
        "ACA 304": {
            "vernalization_requirement": "medium",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 149,
            "gdd_tillering": 402,
            "gdd_stem_extension": 908,
            "gdd_heading": 1458,
            "gdd_grain_fill": 1858,
            "gdd_maturity": 2208,
        },
        "ACA 315": {
            "vernalization_requirement": "medium-high",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 151,
            "gdd_tillering": 406,
            "gdd_stem_extension": 912,
            "gdd_heading": 1462,
            "gdd_grain_fill": 1862,
            "gdd_maturity": 2212,
        },
        "ACA 360": {
            "vernalization_requirement": "medium",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 146,
            "gdd_tillering": 393,
            "gdd_stem_extension": 888,
            "gdd_heading": 1438,
            "gdd_grain_fill": 1838,
            "gdd_maturity": 2188,
        },
        "ACA 365": {
            "vernalization_requirement": "medium",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 148,
            "gdd_tillering": 399,
            "gdd_stem_extension": 898,
            "gdd_heading": 1448,
            "gdd_grain_fill": 1848,
            "gdd_maturity": 2198,
        },
        "ACA 601": {
            "vernalization_requirement": "medium-high",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 152,
            "gdd_tillering": 408,
            "gdd_stem_extension": 915,
            "gdd_heading": 1465,
            "gdd_grain_fill": 1865,
            "gdd_maturity": 2215,
        },
        "ACA 602": {
            "vernalization_requirement": "medium-high",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 153,
            "gdd_tillering": 410,
            "gdd_stem_extension": 918,
            "gdd_heading": 1468,
            "gdd_grain_fill": 1868,
            "gdd_maturity": 2218,
        },
        # ===== BUCK (BG) VARIETIES =====
        "BG 610": {
            "vernalization_requirement": "medium",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 145,
            "gdd_tillering": 395,
            "gdd_stem_extension": 890,
            "gdd_heading": 1430,
            "gdd_grain_fill": 1830,
            "gdd_maturity": 2170,
        },
        "BG 620": {
            "vernalization_requirement": "medium-high",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 150,
            "gdd_tillering": 410,
            "gdd_stem_extension": 920,
            "gdd_heading": 1480,
            "gdd_grain_fill": 1880,
            "gdd_maturity": 2230,
        },
        "BG 630": {
            "vernalization_requirement": "medium-high",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 151,
            "gdd_tillering": 412,
            "gdd_stem_extension": 922,
            "gdd_heading": 1482,
            "gdd_grain_fill": 1882,
            "gdd_maturity": 2232,
        },
        "BG 720": {
            "vernalization_requirement": "medium-high",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 152,
            "gdd_tillering": 414,
            "gdd_stem_extension": 925,
            "gdd_heading": 1485,
            "gdd_grain_fill": 1885,
            "gdd_maturity": 2235,
        },
        "BG 750": {
            "vernalization_requirement": "high",
            "photoperiod_sensitivity": "medium-high",
            "gdd_emergence": 154,
            "gdd_tillering": 416,
            "gdd_stem_extension": 928,
            "gdd_heading": 1488,
            "gdd_grain_fill": 1888,
            "gdd_maturity": 2238,
        },
        # ===== BAGUETTE VARIETIES =====
        "Baguette 620": {
            "vernalization_requirement": "medium-high",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 150,
            "gdd_tillering": 410,
            "gdd_stem_extension": 920,
            "gdd_heading": 1480,
            "gdd_grain_fill": 1880,
            "gdd_maturity": 2230,
        },
        "Baguette 601": {
            "vernalization_requirement": "medium",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 147,
            "gdd_tillering": 397,
            "gdd_stem_extension": 892,
            "gdd_heading": 1442,
            "gdd_grain_fill": 1842,
            "gdd_maturity": 2192,
        },
        "Baguette 750": {
            "vernalization_requirement": "high",
            "photoperiod_sensitivity": "medium-high",
            "gdd_emergence": 154,
            "gdd_tillering": 416,
            "gdd_stem_extension": 928,
            "gdd_heading": 1488,
            "gdd_grain_fill": 1888,
            "gdd_maturity": 2238,
        },
        # ===== KLEIN VARIETIES =====
        "Klein Cacique": {
            "vernalization_requirement": "medium",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 146,
            "gdd_tillering": 394,
            "gdd_stem_extension": 889,
            "gdd_heading": 1439,
            "gdd_grain_fill": 1839,
            "gdd_maturity": 2189,
        },
        "Klein Guerrero": {
            "vernalization_requirement": "medium",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 148,
            "gdd_tillering": 398,
            "gdd_stem_extension": 896,
            "gdd_heading": 1446,
            "gdd_grain_fill": 1846,
            "gdd_maturity": 2196,
        },
        "Klein Proteo": {
            "vernalization_requirement": "medium-high",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 151,
            "gdd_tillering": 404,
            "gdd_stem_extension": 909,
            "gdd_heading": 1459,
            "gdd_grain_fill": 1859,
            "gdd_maturity": 2209,
        },
        "Klein Rayén": {
            "vernalization_requirement": "medium",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 147,
            "gdd_tillering": 396,
            "gdd_stem_extension": 891,
            "gdd_heading": 1441,
            "gdd_grain_fill": 1841,
            "gdd_maturity": 2191,
        },
        "Klein Sagitario": {
            "vernalization_requirement": "medium-high",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 152,
            "gdd_tillering": 407,
            "gdd_stem_extension": 913,
            "gdd_heading": 1463,
            "gdd_grain_fill": 1863,
            "gdd_maturity": 2213,
        },
        # ===== BIO4 VARIETIES =====
        "Bio4 Baguette 601": {
            "vernalization_requirement": "medium",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 147,
            "gdd_tillering": 397,
            "gdd_stem_extension": 892,
            "gdd_heading": 1442,
            "gdd_grain_fill": 1842,
            "gdd_maturity": 2192,
        },
        "Bio4 Baguette 620": {
            "vernalization_requirement": "medium-high",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 150,
            "gdd_tillering": 410,
            "gdd_stem_extension": 920,
            "gdd_heading": 1480,
            "gdd_grain_fill": 1880,
            "gdd_maturity": 2230,
        },
        # ===== SYNGENTA VARIETIES =====
        "SY 100": {
            "vernalization_requirement": "medium",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 146,
            "gdd_tillering": 393,
            "gdd_stem_extension": 888,
            "gdd_heading": 1438,
            "gdd_grain_fill": 1838,
            "gdd_maturity": 2188,
        },
        "SY 200": {
            "vernalization_requirement": "medium",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 148,
            "gdd_tillering": 399,
            "gdd_stem_extension": 898,
            "gdd_heading": 1448,
            "gdd_grain_fill": 1848,
            "gdd_maturity": 2198,
        },
        "SY 300": {
            "vernalization_requirement": "medium-high",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 151,
            "gdd_tillering": 405,
            "gdd_stem_extension": 910,
            "gdd_heading": 1460,
            "gdd_grain_fill": 1860,
            "gdd_maturity": 2210,
        },
        # ===== OTHER COMMON ARGENTINE VARIETIES =====
        "Bienvenido": {
            "vernalization_requirement": "medium",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 147,
            "gdd_tillering": 396,
            "gdd_stem_extension": 891,
            "gdd_heading": 1441,
            "gdd_grain_fill": 1841,
            "gdd_maturity": 2191,
        },
        "Cronox": {
            "vernalization_requirement": "medium",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 149,
            "gdd_tillering": 401,
            "gdd_stem_extension": 906,
            "gdd_heading": 1456,
            "gdd_grain_fill": 1856,
            "gdd_maturity": 2206,
        },
        "Relmo": {
            "vernalization_requirement": "medium",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 146,
            "gdd_tillering": 394,
            "gdd_stem_extension": 889,
            "gdd_heading": 1439,
            "gdd_grain_fill": 1839,
            "gdd_maturity": 2189,
        },
        "Sursem": {
            "vernalization_requirement": "medium",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 148,
            "gdd_tillering": 398,
            "gdd_stem_extension": 896,
            "gdd_heading": 1446,
            "gdd_grain_fill": 1846,
            "gdd_maturity": 2196,
        },
        "Taita": {
            "vernalization_requirement": "medium-high",
            "photoperiod_sensitivity": "medium",
            "gdd_emergence": 152,
            "gdd_tillering": 408,
            "gdd_stem_extension": 915,
            "gdd_heading": 1465,
            "gdd_grain_fill": 1865,
            "gdd_maturity": 2215,
        },
    }
    
    def __init__(self, variety: str, sowing_date: str, latitude: float):
        """
        Initialize the phenology model for a specific field.
        
        Args:
            variety: Wheat variety name
            sowing_date: Sowing date in format 'YYYY-MM-DD'
            latitude: Field latitude for photoperiod calculation
        """
        self.variety = variety
        self.sowing_date = datetime.strptime(sowing_date, '%Y-%m-%d')
        self.latitude = latitude
        
        # Get variety parameters or use default
        if variety in self.VARIETY_PARAMS:
            self.params = self.VARIETY_PARAMS[variety]
        else:
            # Default parameters for unknown varieties
            self.params = {
                "vernalization_requirement": "medium",
                "photoperiod_sensitivity": "medium",
                "gdd_emergence": 145,
                "gdd_tillering": 395,
                "gdd_stem_extension": 890,
                "gdd_heading": 1440,
                "gdd_grain_fill": 1840,
                "gdd_maturity": 2180,
            }
    
    def calculate_gdd(self, tmin: float, tmax: float) -> float:
        """
        Calculate Growing Degree Days using the average temperature method.
        
        Args:
            tmin: Minimum daily temperature (°C)
            tmax: Maximum daily temperature (°C)
            
        Returns:
            Growing degree days for the day
        """
        tavg = (tmin + tmax) / 2.0
        
        # Constrain to valid range
        if tavg < self.BASE_TEMP:
            return 0.0
        elif tavg > self.MAX_TEMP:
            tavg = self.MAX_TEMP
        
        gdd = tavg - self.BASE_TEMP
        return max(0.0, gdd)
    
    def calculate_photoperiod(self, date: datetime) -> float:
        """
        Calculate day length (photoperiod) in hours.
        
        Args:
            date: Date for calculation
            
        Returns:
            Day length in hours
        """
        lat_rad = math.radians(self.latitude)
        day_of_year = date.timetuple().tm_yday
        
        # Solar declination
        declination = 23.45 * math.sin(math.radians(360 / 365 * (day_of_year - 81)))
        dec_rad = math.radians(declination)
        
        # Hour angle at sunrise/sunset
        cos_hour_angle = -math.tan(lat_rad) * math.tan(dec_rad)
        
        # Handle polar day/night
        if cos_hour_angle > 1:
            return 0.0
        elif cos_hour_angle < -1:
            return 24.0
        
        hour_angle = math.acos(cos_hour_angle)
        photoperiod = 2 * math.degrees(hour_angle) / 15.0
        
        return photoperiod
    
    def estimate_phenology(
        self, 
        weather_data: List[Dict],
        current_date: datetime = None
    ) -> Dict:
        """
        Estimate phenological stages based on weather data.
        
        Args:
            weather_data: List of daily weather records with 'date', 'tmin', 'tmax'
            current_date: Current date for estimation (defaults to today)
            
        Returns:
            Dictionary with phenological stage information
        """
        if current_date is None:
            current_date = datetime.now()
        
        accumulated_gdd = 0.0
        current_stage = "Sowing"
        stage_dates = {
            "sowing": self.sowing_date.strftime('%Y-%m-%d'),
            "emergence": None,
            "tillering": None,
            "stem_extension": None,
            "heading": None,
            "grain_fill": None,
            "maturity": None,
        }
        
        # Process each day from sowing
        for weather in weather_data:
            date = datetime.strptime(weather['date'], '%Y-%m-%d')
            
            if date < self.sowing_date:
                continue
            if date > current_date:
                break
            
            # Calculate daily GDD
            daily_gdd = self.calculate_gdd(weather['tmin'], weather['tmax'])
            accumulated_gdd += daily_gdd
            
            # Determine current stage based on accumulated GDD
            if accumulated_gdd >= self.params['gdd_maturity'] and stage_dates['maturity'] is None:
                current_stage = "Maturity (Zadoks 90)"
                stage_dates['maturity'] = date.strftime('%Y-%m-%d')
            elif accumulated_gdd >= self.params['gdd_grain_fill'] and stage_dates['grain_fill'] is None:
                current_stage = "Grain Fill (Zadoks 70)"
                stage_dates['grain_fill'] = date.strftime('%Y-%m-%d')
            elif accumulated_gdd >= self.params['gdd_heading'] and stage_dates['heading'] is None:
                current_stage = "Heading/Anthesis (Zadoks 60)"
                stage_dates['heading'] = date.strftime('%Y-%m-%d')
            elif accumulated_gdd >= self.params['gdd_stem_extension'] and stage_dates['stem_extension'] is None:
                current_stage = "Stem Extension (Zadoks 30)"
                stage_dates['stem_extension'] = date.strftime('%Y-%m-%d')
            elif accumulated_gdd >= self.params['gdd_tillering'] and stage_dates['tillering'] is None:
                current_stage = "Tillering"
                stage_dates['tillering'] = date.strftime('%Y-%m-%d')
            elif accumulated_gdd >= self.params['gdd_emergence'] and stage_dates['emergence'] is None:
                current_stage = "Emergence"
                stage_dates['emergence'] = date.strftime('%Y-%m-%d')
        
        # Calculate progress to next stage
        next_stage_gdd = self._get_next_stage_gdd(accumulated_gdd)
        if next_stage_gdd:
            stage_progress = (accumulated_gdd / next_stage_gdd) * 100
        else:
            stage_progress = 100.0
        
        return {
            "variety": self.variety,
            "sowing_date": self.sowing_date.strftime('%Y-%m-%d'),
            "current_stage": current_stage,
            "accumulated_gdd": round(accumulated_gdd, 1),
            "stage_progress": round(stage_progress, 1),
            "stage_dates": stage_dates,
            "days_since_sowing": (current_date - self.sowing_date).days,
        }
    
    def _get_next_stage_gdd(self, current_gdd: float) -> float:
        """Get the GDD requirement for the next phenological stage."""
        stages = [
            self.params['gdd_emergence'],
            self.params['gdd_tillering'],
            self.params['gdd_stem_extension'],
            self.params['gdd_heading'],
            self.params['gdd_grain_fill'],
            self.params['gdd_maturity'],
        ]
        
        for stage_gdd in stages:
            if current_gdd < stage_gdd:
                return stage_gdd
        
        return None
    
    def predict_future_stages(
        self,
        weather_data: List[Dict],
        forecast_data: List[Dict] = None
    ) -> Dict:
        """
        Predict future phenological stage dates.
        
        Args:
            weather_data: Historical weather data
            forecast_data: Forecasted weather data (optional)
            
        Returns:
            Predicted dates for all phenological stages
        """
        all_data = weather_data.copy()
        if forecast_data:
            all_data.extend(forecast_data)
        
        return self.estimate_phenology(all_data, datetime.now() + timedelta(days=180))


def process_all_fields(geojson_path: str, weather_data: List[Dict]) -> List[Dict]:
    """
    Process all fields in the GeoJSON file and estimate phenology for each.
    
    Args:
        geojson_path: Path to the GeoJSON file with field data
        weather_data: Weather data for the region
        
    Returns:
        List of phenology estimates for each field
    """
    with open(geojson_path, 'r') as f:
        data = json.load(f)
    
    results = []
    
    for feature in data['features']:
        props = feature['properties']
        geom = feature['geometry']
        
        # Get field center coordinates (approximate)
        coords = geom['coordinates'][0]
        lats = [c[1] for c in coords]
        lons = [c[0] for c in coords]
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        
        field_name = props.get('field_name', 'Unknown')
        variety = props.get('wheat_variety', 'Unknown')
        sowing_date = props.get('sowing_date')
        
        if not sowing_date or variety == 'Unknown':
            print(f"Skipping {field_name}: missing sowing date or variety")
            continue
        
        # Create model and estimate phenology
        model = WheatPhenologyModel(variety, sowing_date, center_lat)
        phenology = model.estimate_phenology(weather_data)
        
        results.append({
            "field_name": field_name,
            "coordinates": {"lat": center_lat, "lon": center_lon},
            **phenology
        })
    
    return results


if __name__ == "__main__":
    print("Wheat Phenology Model")
    print("=" * 60)
    print("\nThis model estimates wheat growth stages based on:")
    print("- Variety-specific thermal time requirements")
    print("- Sowing date")
    print("- Daily temperature data")
    print("\nNext steps:")
    print("1. Obtain weather data for your location")
    print("2. Run the model using weather_phenology_analyzer.py")

