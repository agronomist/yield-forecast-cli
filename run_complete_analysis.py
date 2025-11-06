"""
Complete Analysis Pipeline for New Fields

Automatically runs all analysis steps:
1. Phenology analysis
2. NDVI/fAPAR data collection
3. Solar radiation (PAR) data
4. Biomass and yield prediction
5. Visualizations
"""

import subprocess
import json
import os
from pathlib import Path


def run_step(step_name, command, description):
    """
    Run a single analysis step.
    
    Args:
        step_name: Name of the step for logging
        command: Command to run  
        description: Description of what the step does
    """
    print("\n" + "=" * 80)
    print(f"STEP: {step_name}")
    print("=" * 80)
    print(f"Description: {description}")
    print(f"Command: {command}")
    print("─" * 80)
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout per step
        )
        
        if result.returncode == 0:
            print(f"✓ {step_name} completed successfully")
            if result.stdout:
                print("\nOutput:")
                # Print last 20 lines
                lines = result.stdout.strip().split('\n')
                for line in lines[-20:]:
                    print(line)
            return True
        else:
            print(f"✗ {step_name} failed with return code {result.returncode}")
            if result.stderr:
                print("\nError:")
                print(result.stderr)
            return False
    
    except subprocess.TimeoutExpired:
        print(f"✗ {step_name} timed out")
        return False
    except Exception as e:
        print(f"✗ {step_name} failed: {e}")
        return False


def create_analysis_scripts_for_new_fields(geojson_file, output_prefix):
    """
    Create modified versions of analysis scripts for new fields.
    
    Args:
        geojson_file: Path to GeoJSON file with new fields
        output_prefix: Prefix for output files (e.g., "new_fields")
    """
    
    print("\n" + "=" * 80)
    print("RUNNING COMPLETE ANALYSIS PIPELINE")
    print("=" * 80)
    print(f"\nInput: {geojson_file}")
    print(f"Output prefix: {output_prefix}")
    
    # Check if input file exists
    if not os.path.exists(geojson_file):
        print(f"\n✗ Input file not found: {geojson_file}")
        return False
    
    # Load GeoJSON to count fields
    with open(geojson_file, 'r') as f:
        data = json.load(f)
        num_fields = len(data['features'])
    
    print(f"✓ Found {num_fields} fields to process")
    
    success = True
    
    # Step 1: Phenology Analysis
    # Note: This requires modifying weather_phenology_analyzer.py to accept input file argument
    # For now, we'll copy the GeoJSON to the expected location
    print("\n" + "─" * 80)
    print("Preparing data files...")
    
    # Backup original file if it exists
    original_geojson = "agricultural_fields_with_data.geojson"
    backup_geojson = f"{original_geojson}.backup"
    
    if os.path.exists(original_geojson):
        subprocess.run(f"cp {original_geojson} {backup_geojson}", shell=True)
        print(f"✓ Backed up {original_geojson} to {backup_geojson}")
    
    # Copy new fields to main location
    subprocess.run(f"cp {geojson_file} {original_geojson}", shell=True)
    print(f"✓ Copied {geojson_file} to {original_geojson}")
    
    # Step 1: Phenology Analysis
    success = success and run_step(
        "1. Phenology Analysis",
        "python3 weather_phenology_analyzer.py",
        "Calculates phenological stages based on weather data and thermal time"
    )
    
    # Step 2: NDVI/fAPAR Data (weekly aggregated)
    if success:
        # Create a simple script to fetch weekly NDVI for all fields
        script_content = """
import json
import subprocess

# Load fields
with open('agricultural_fields_with_data.geojson', 'r') as f:
    data = json.load(f)

print(f"Processing {len(data['features'])} fields for NDVI data...")

# Run sentinel_ndvi_fetcher.py (weekly aggregated data)
result = subprocess.run(['python3', 'sentinel_ndvi_fetcher.py'], 
                       capture_output=True, text=True)
print(result.stdout)

# Calculate fAPAR
print("\\nCalculating fAPAR...")
result = subprocess.run(['python3', 'calculate_fapar.py'],
                       capture_output=True, text=True)
print(result.stdout)
"""
        with open('_temp_ndvi_fetch.py', 'w') as f:
            f.write(script_content)
        
        success = success and run_step(
            "2. NDVI/fAPAR Data Collection",
            "python3 _temp_ndvi_fetch.py",
            "Fetches weekly NDVI data from Sentinel Hub and calculates fAPAR"
        )
        
        # Clean up temp script
        if os.path.exists('_temp_ndvi_fetch.py'):
            os.remove('_temp_ndvi_fetch.py')
    
    # Step 3: Solar Radiation (PAR) Data
    if success:
        success = success and run_step(
            "3. Solar Radiation (PAR) Data",
            "python3 fetch_solar_radiation.py",
            "Fetches daily solar radiation data and converts to PAR"
        )
    
    # Step 4: Yield Prediction
    if success:
        success = success and run_step(
            "4. Biomass and Yield Prediction",
            "python3 predict_yield.py",
            "Calculates biomass accumulation and predicts grain yield"
        )
    
    # Step 5: Visualizations
    if success:
        success = success and run_step(
            "5. Yield Visualization",
            "python3 visualize_yield_predictions.py",
            "Creates yield prediction plots and boxplots"
        )
    
    # Move output files to new_fields directory
    if success:
        print("\n" + "─" * 80)
        print("Organizing output files...")
        
        output_dir = f"output_{output_prefix}"
        os.makedirs(output_dir, exist_ok=True)
        
        # List of output files to move
        output_files = [
            'phenology_analysis_results.json',
            'phenology_analysis_results.csv',
            'sentinel_ndvi_fapar_data.json',
            'sentinel_ndvi_fapar_data.csv',
            'solar_radiation_par_data.json',
            'solar_radiation_par_data.csv',
            'yield_predictions.json',
            'yield_predictions.csv',
            'yield_predictions_boxplot.png',
            'yield_predictions_boxplot.pdf',
            'yield_by_variety_boxplot.png',
            'yield_by_variety_boxplot.pdf',
        ]
        
        for filename in output_files:
            if os.path.exists(filename):
                subprocess.run(f"mv {filename} {output_dir}/", shell=True)
                print(f"  Moved {filename} to {output_dir}/")
        
        print(f"\n✓ Output files saved to: {output_dir}/")
    
    # Restore original GeoJSON
    if os.path.exists(backup_geojson):
        subprocess.run(f"mv {backup_geojson} {original_geojson}", shell=True)
        print(f"✓ Restored original {original_geojson}")
    
    return success


def main():
    """Main function."""
    
    geojson_file = "more_fields/new_fields_data.geojson"
    output_prefix = "new_fields"
    
    print("\n" + "=" * 80)
    print("AUTOMATED COMPLETE ANALYSIS PIPELINE")
    print("=" * 80)
    print("\nThis will run the complete analysis on new fields:")
    print("  1. Phenology analysis (thermal time, growth stages)")
    print("  2. NDVI/fAPAR data (weekly aggregated from Sentinel-2)")
    print("  3. Solar radiation (PAR) data")
    print("  4. Biomass accumulation and yield prediction")
    print("  5. Visualizations")
    print(f"\nInput: {geojson_file}")
    print(f"Output directory: output_{output_prefix}/")
    print("\n⚠️  This will temporarily replace agricultural_fields_with_data.geojson")
    print("   (original will be backed up and restored)")
    
    response = input("\nProceed? (yes/no): ").lower()
    
    if response == 'yes' or response == 'y':
        success = create_analysis_scripts_for_new_fields(geojson_file, output_prefix)
        
        if success:
            print("\n" + "=" * 80)
            print("✓✓✓ COMPLETE ANALYSIS FINISHED SUCCESSFULLY ✓✓✓")
            print("=" * 80)
            print(f"\nAll results saved to: output_{output_prefix}/")
        else:
            print("\n" + "=" * 80)
            print("✗✗✗ ANALYSIS FAILED ✗✗✗")
            print("=" * 80)
            print("\nSome steps failed. Check the output above for errors.")
    else:
        print("\nAnalysis cancelled.")


if __name__ == "__main__":
    main()

