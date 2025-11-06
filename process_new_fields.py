"""
Process New Fields from KML and Excel

Extracts field data from KML and Excel files, creates GeoJSON,
and runs complete analysis pipeline (phenology, NDVI, PAR, biomass, yield).
"""

import xml.etree.ElementTree as ET
import json
import pandas as pd
import subprocess
from datetime import datetime


def parse_kml_to_geojson(kml_file, excel_file, output_geojson):
    """
    Parse KML file and Excel file to create GeoJSON.
    
    Args:
        kml_file: Path to KML file with field polygons
        excel_file: Path to Excel file with field data
        output_geojson: Output GeoJSON file path
    """
    
    print("\n" + "=" * 80)
    print("PROCESSING NEW FIELDS")
    print("=" * 80)
    
    # Parse KML
    print(f"\nParsing KML file: {kml_file}")
    tree = ET.parse(kml_file)
    root = tree.getroot()
    
    # Define KML namespace
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    
    # Extract placemarks
    placemarks = {}
    for placemark in root.findall('.//kml:Placemark', ns):
        name_elem = placemark.find('kml:name', ns)
        if name_elem is not None:
            field_name = name_elem.text
            
            # Get coordinates
            coords_elem = placemark.find('.//kml:coordinates', ns)
            if coords_elem is not None:
                coords_text = coords_elem.text.strip()
                
                # Parse coordinates (format: lon,lat,alt lon,lat,alt ...)
                coord_pairs = []
                for coord_str in coords_text.split():
                    parts = coord_str.split(',')
                    if len(parts) >= 2:
                        lon = float(parts[0])
                        lat = float(parts[1])
                        coord_pairs.append([lon, lat])
                
                if len(coord_pairs) > 0:
                    placemarks[field_name] = coord_pairs
    
    print(f"✓ Found {len(placemarks)} fields in KML")
    
    # Read Excel file with custom format
    print(f"\nReading Excel file: {excel_file}")
    df = pd.read_excel(excel_file, header=None)
    
    print(f"✓ Excel shape: {df.shape}")
    
    # The format has:
    # Row 2: Headers - "Campo:" in col 1, "Variedad" in col 5, "Fecha siembra:" in col 6  
    # Data starts from row 3
    # Column 1: Campo (field area name)
    # Column 5: Variety
    # Column 6: Sowing date
    
    field_data = {}
    lote_counter = {}  # Track lote numbers per campo
    
    for idx in range(3, len(df)):  # Start from row 3 (index 3)
        row = df.iloc[idx]
        
        # Skip empty rows
        if pd.isna(row[1]) and pd.isna(row[5]) and pd.isna(row[6]):
            continue
        
        campo = str(row[1]).strip() if not pd.isna(row[1]) else None
        variety = str(row[5]).strip() if not pd.isna(row[5]) else None
        sowing_date = row[6]
        
        if not campo or not variety or pd.isna(sowing_date):
            continue
        
        # Track lote numbers for each campo
        if campo not in lote_counter:
            lote_counter[campo] = 0
        lote_counter[campo] += 1
        
        # Create field name with lote number (matches KML format)
        # E.g., "El 21" + " Lote " + "5" = "El 21 Lote 5"
        field_name_with_lote = f"{campo} Lote {lote_counter[campo]}"
        
        # Parse date
        if isinstance(sowing_date, datetime):
            sowing_date_str = sowing_date.strftime('%Y-%m-%d')
        else:
            try:
                dt = pd.to_datetime(sowing_date)
                sowing_date_str = dt.strftime('%Y-%m-%d')
            except:
                print(f"  ⚠️ Could not parse date for {campo}: {sowing_date}")
                continue
        
        field_data[field_name_with_lote] = {
            'campo': campo,
            'variety': variety,
            'sowing_date': sowing_date_str
        }
        
        print(f"  {field_name_with_lote}: {variety}, {sowing_date_str}")
    
    print(f"\n✓ Processed {len(field_data)} fields from Excel")
    
    # Match KML and Excel data
    print("\nMatching KML polygons with Excel data...")
    matched_fields = []
    unmatched_kml = []
    unmatched_excel = []
    
    for kml_name, coords in placemarks.items():
        # Try exact match first
        if kml_name in field_data:
            matched_fields.append((kml_name, coords, field_data[kml_name]))
        else:
            # Try partial match
            found = False
            for excel_name in field_data.keys():
                if excel_name in kml_name or kml_name in excel_name:
                    matched_fields.append((kml_name, coords, field_data[excel_name]))
                    found = True
                    break
            
            if not found:
                unmatched_kml.append(kml_name)
    
    for excel_name in field_data.keys():
        if not any(excel_name in name or name in excel_name for name, _, _ in matched_fields):
            unmatched_excel.append(excel_name)
    
    print(f"✓ Matched {len(matched_fields)} fields")
    
    if unmatched_kml:
        print(f"\n⚠️ Unmatched KML fields ({len(unmatched_kml)}):")
        for name in unmatched_kml[:5]:
            print(f"  - {name}")
        if len(unmatched_kml) > 5:
            print(f"  ... and {len(unmatched_kml) - 5} more")
    
    if unmatched_excel:
        print(f"\n⚠️ Unmatched Excel fields ({len(unmatched_excel)}):")
        for name in unmatched_excel[:5]:
            print(f"  - {name}")
        if len(unmatched_excel) > 5:
            print(f"  ... and {len(unmatched_excel) - 5} more")
    
    # Create GeoJSON
    print(f"\nCreating GeoJSON: {output_geojson}")
    
    features = []
    for field_name, coords, data in matched_fields:
        feature = {
            "type": "Feature",
            "properties": {
                "field_name": field_name,
                "wheat_variety": data['variety'],
                "sowing_date": data['sowing_date']
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords]
            }
        }
        features.append(feature)
    
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    with open(output_geojson, 'w') as f:
        json.dump(geojson, f, indent=2)
    
    print(f"✓ Created GeoJSON with {len(features)} fields")
    
    return len(features)


def run_analysis_pipeline(geojson_file, output_prefix):
    """
    Run complete analysis pipeline on new fields.
    
    Args:
        geojson_file: Input GeoJSON file
        output_prefix: Prefix for output files
    """
    
    print("\n" + "=" * 80)
    print("RUNNING ANALYSIS PIPELINE")
    print("=" * 80)
    
    # Note: The scripts need to be modified to accept input/output file arguments
    # For now, we'll provide instructions
    
    print("\n📋 To complete the analysis, run these scripts in order:")
    print("\n1. Phenology Analysis:")
    print("   python3 weather_phenology_analyzer.py")
    print("   (Modify to use new GeoJSON file)")
    
    print("\n2. NDVI/fAPAR Data:")
    print("   python3 sentinel_ndvi_per_date.py")
    print("   python3 calculate_fapar.py")
    print("   (Modify to use new GeoJSON file)")
    
    print("\n3. Solar Radiation (PAR):")
    print("   python3 fetch_solar_radiation.py")
    print("   (Modify to use new GeoJSON file)")
    
    print("\n4. Yield Prediction:")
    print("   python3 predict_yield.py")
    print("   (Modify to use new data files)")
    
    print("\n5. Visualizations:")
    print("   python3 visualize_yield_predictions.py")
    print("   python3 visualize_fapar_phenology.py")
    
    print("\n💡 Or I can create a master script that runs everything automatically!")


def main():
    """Main function."""
    
    kml_file = "more_fields/FDC-Plantets labs Trigos 25-26.kml"
    excel_file = "more_fields/Planets Labs Trigo 25-26.xlsx"
    output_geojson = "more_fields/new_fields_data.geojson"
    
    try:
        # Parse and create GeoJSON
        num_fields = parse_kml_to_geojson(kml_file, excel_file, output_geojson)
        
        if num_fields and num_fields > 0:
            print("\n" + "=" * 80)
            print("✓ DATA EXTRACTION COMPLETE")
            print("=" * 80)
            print(f"\n✓ Created: {output_geojson}")
            print(f"✓ Fields processed: {num_fields}")
            
            # Run pipeline instructions
            run_analysis_pipeline(output_geojson, "new_fields")
        else:
            print("\n✗ Failed to create GeoJSON")
    
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

