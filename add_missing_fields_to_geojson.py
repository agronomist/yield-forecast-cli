"""
Add the 3 missing fields from KML to the GeoJSON file.
Extracts: El 21 Lote 5, Las Casuarinas 1, Ferito Lote 3
"""

import json
import xml.etree.ElementTree as ET

# Parse KML file
kml_path = "more_fields/FDC-Plantets labs Trigos 25-26.kml"
geojson_path = "more_fields/new_fields_data.geojson"

# Define namespace for KML
ns = {'kml': 'http://www.opengis.net/kml/2.2'}

# Field metadata from Excel
field_metadata = {
    "El 21 Lote 5": {
        "wheat_variety": "DM Pehuen",
        "sowing_date": "2025-06-06"
    },
    "Las Casuarinas 1": {
        "wheat_variety": "Baguette 620",
        "sowing_date": "2025-05-28"
    },
    "Ferito Lote 3": {
        "wheat_variety": "DM Pehuen",
        "sowing_date": "2025-06-10"
    }
}

def parse_coordinates(coord_string):
    """Parse KML coordinate string to GeoJSON format."""
    coords = []
    for point in coord_string.strip().split():
        if point:
            lon, lat, alt = point.split(',')
            coords.append([float(lon), float(lat)])
    return coords

# Parse KML
tree = ET.parse(kml_path)
root = tree.getroot()

# Load existing GeoJSON
with open(geojson_path, 'r') as f:
    geojson = json.load(f)

print("=" * 80)
print("ADDING MISSING FIELDS TO GEOJSON")
print("=" * 80)

# Find and add missing fields
for placemark in root.findall('.//kml:Placemark', ns):
    name_elem = placemark.find('kml:name', ns)
    if name_elem is not None:
        field_name = name_elem.text
        
        if field_name in field_metadata:
            print(f"\n✓ Found: {field_name}")
            
            # Extract coordinates
            coord_elem = placemark.find('.//kml:coordinates', ns)
            if coord_elem is not None:
                coord_string = coord_elem.text
                coordinates = parse_coordinates(coord_string)
                
                # Create GeoJSON feature
                feature = {
                    "type": "Feature",
                    "properties": {
                        "field_name": field_name,
                        "wheat_variety": field_metadata[field_name]["wheat_variety"],
                        "sowing_date": field_metadata[field_name]["sowing_date"]
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [coordinates]
                    }
                }
                
                # Add to GeoJSON
                geojson['features'].append(feature)
                print(f"  Variety: {field_metadata[field_name]['wheat_variety']}")
                print(f"  Sowing: {field_metadata[field_name]['sowing_date']}")
                print(f"  Coordinates: {len(coordinates)} points")

# Save updated GeoJSON
with open(geojson_path, 'w') as f:
    json.dump(geojson, f, indent=2)

print("\n" + "=" * 80)
print(f"✓ Updated GeoJSON saved: {geojson_path}")
print(f"✓ Total fields now: {len(geojson['features'])}")
print("=" * 80)

