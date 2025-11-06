"""
Fetch NDVI data for original 68 fields, clean outliers for ALL 80 fields,
and re-run complete yield predictions.
"""

import subprocess
import os
import json
import sys


def fetch_ndvi_for_original_fields():
    """Fetch NDVI data for the original 68 fields."""
    
    print("\n" + "=" * 80)
    print("STEP 1: FETCHING NDVI DATA FOR ORIGINAL 68 FIELDS")
    print("=" * 80)
    
    print("\nThis will take approximately 10-15 minutes...")
    print("Fetching weekly NDVI from Sentinel Hub for all 68 fields...")
    
    # Run the NDVI fetcher
    result = subprocess.run(
        ['python3', 'sentinel_ndvi_fetcher.py'],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("✗ Error fetching NDVI:")
        print(result.stderr)
        print("\nStdout:")
        print(result.stdout)
        return False
    
    print("✓ NDVI fetch complete")
    
    # Show summary
    output_lines = result.stdout.strip().split('\n')
    for line in output_lines[-15:]:
        print(line)
    
    return True


def calculate_fapar_for_original():
    """Calculate fAPAR from NDVI for original fields."""
    
    print("\n" + "=" * 80)
    print("STEP 2: CALCULATING fAPAR FOR ORIGINAL 68 FIELDS")
    print("=" * 80)
    
    result = subprocess.run(
        ['python3', 'calculate_fapar.py'],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("✗ Error calculating fAPAR:")
        print(result.stderr)
        return False
    
    print("✓ fAPAR calculation complete")
    
    # Show summary
    output_lines = result.stdout.strip().split('\n')
    for line in output_lines[-10:]:
        print(line)
    
    return True


def clean_ndvi_all_fields():
    """Clean NDVI outliers for ALL 80 fields."""
    
    print("\n" + "=" * 80)
    print("STEP 3: CLEANING NDVI OUTLIERS FOR ALL 80 FIELDS")
    print("=" * 80)
    
    # First, check if we have NDVI data in root
    if not os.path.exists('sentinel_ndvi_fapar_data.json'):
        print("✗ sentinel_ndvi_fapar_data.json not found in root directory")
        print("  Make sure NDVI fetch completed successfully")
        return False
    
    # Update clean_ndvi_outliers.py to work with both datasets
    print("\nCleaning original 68 fields...")
    result1 = subprocess.run(
        ['python3', '-c', '''
import sys
sys.path.insert(0, ".")
from clean_ndvi_outliers import clean_all_fields

# Clean original fields
clean_all_fields(
    "sentinel_ndvi_fapar_data.json",
    "sentinel_ndvi_fapar_data_cleaned.json"
)
'''],
        capture_output=True,
        text=True
    )
    
    if result1.returncode != 0:
        print("✗ Error cleaning original fields:")
        print(result1.stderr)
        return False
    
    print(result1.stdout)
    
    # New fields already cleaned
    print("\n✓ New 12 fields already cleaned")
    
    return True


def run_predictions_all_fields():
    """Run yield predictions for all fields with cleaned data."""
    
    print("\n" + "=" * 80)
    print("STEP 4: RUNNING YIELD PREDICTIONS WITH CLEANED DATA")
    print("=" * 80)
    
    # Backup and use cleaned data for original fields
    import shutil
    if os.path.exists('sentinel_ndvi_fapar_data_cleaned.json'):
        shutil.copy('sentinel_ndvi_fapar_data.json', 'sentinel_ndvi_fapar_data_original_backup.json')
        shutil.copy('sentinel_ndvi_fapar_data_cleaned.json', 'sentinel_ndvi_fapar_data.json')
        print("✓ Using cleaned NDVI data for predictions")
    
    # Run predictions for original fields
    print("\nRunning predictions for original 68 fields...")
    result = subprocess.run(
        ['python3', 'predict_yield.py'],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("✗ Error in predictions:")
        print(result.stderr)
        # Restore original data
        if os.path.exists('sentinel_ndvi_fapar_data_original_backup.json'):
            shutil.copy('sentinel_ndvi_fapar_data_original_backup.json', 'sentinel_ndvi_fapar_data.json')
        return False
    
    print("✓ Predictions complete")
    
    # Show summary
    output_lines = result.stdout.strip().split('\n')
    for line in output_lines[-20:]:
        print(line)
    
    # Save cleaned predictions
    if os.path.exists('yield_predictions.csv'):
        shutil.copy('yield_predictions.csv', 'yield_predictions_cleaned_all68.csv')
        print("\n✓ Saved cleaned predictions: yield_predictions_cleaned_all68.csv")
    
    # Restore original data
    if os.path.exists('sentinel_ndvi_fapar_data_original_backup.json'):
        shutil.copy('sentinel_ndvi_fapar_data_original_backup.json', 'sentinel_ndvi_fapar_data.json')
        print("✓ Restored original NDVI data")
    
    return True


def create_final_analysis():
    """Create final combined analysis with all cleaned data."""
    
    print("\n" + "=" * 80)
    print("STEP 5: CREATING FINAL COMBINED ANALYSIS")
    print("=" * 80)
    
    result = subprocess.run(
        ['python3', 'create_final_combined_analysis.py'],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("✗ Error in final analysis:")
        print(result.stderr)
        return False
    
    print(result.stdout)
    
    return True


def main():
    """Main execution."""
    
    print("\n" + "=" * 80)
    print("COMPREHENSIVE NDVI CLEANING AND YIELD PREDICTION")
    print("FOR ALL 80 FIELDS")
    print("=" * 80)
    
    print("\nThis process will:")
    print("  1. Fetch NDVI data for original 68 fields (~15 min)")
    print("  2. Calculate fAPAR from NDVI")
    print("  3. Clean outliers for ALL 80 fields")
    print("  4. Re-run yield predictions with cleaned data")
    print("  5. Create final combined visualizations")
    
    print("\n⏱️  Estimated total time: 20-30 minutes")
    
    input("\nPress Enter to continue or Ctrl+C to cancel...")
    
    # Step 1: Fetch NDVI
    if not fetch_ndvi_for_original_fields():
        print("\n✗ Failed at Step 1: NDVI fetch")
        return
    
    # Step 2: Calculate fAPAR
    if not calculate_fapar_for_original():
        print("\n✗ Failed at Step 2: fAPAR calculation")
        return
    
    # Step 3: Clean NDVI
    if not clean_ndvi_all_fields():
        print("\n✗ Failed at Step 3: NDVI cleaning")
        return
    
    # Step 4: Run predictions
    if not run_predictions_all_fields():
        print("\n✗ Failed at Step 4: Yield predictions")
        return
    
    # Step 5: Final analysis
    if not create_final_analysis():
        print("\n✗ Failed at Step 5: Final analysis")
        return
    
    print("\n" + "=" * 80)
    print("✓✓✓ COMPLETE ANALYSIS FINISHED SUCCESSFULLY ✓✓✓")
    print("=" * 80)
    
    print("\nAll 80 fields now have:")
    print("  ✓ Cloud-free NDVI data")
    print("  ✓ Outlier detection and gap filling")
    print("  ✓ Updated yield predictions")
    print("  ✓ Comprehensive visualizations")
    
    print("\nKey files:")
    print("  - sentinel_ndvi_fapar_data_cleaned.json (original 68)")
    print("  - output_new_fields/sentinel_ndvi_fapar_data_cleaned.json (new 12)")
    print("  - yield_predictions_cleaned_all68.csv (original with cleaning)")
    print("  - yield_predictions_all_80_fields_final.csv (combined)")
    print("  - yield_all_80_fields_ranked_final.png (visualization)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✗ Process cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

