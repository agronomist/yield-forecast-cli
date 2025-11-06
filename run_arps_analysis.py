"""
Master script to run complete ARPS analysis pipeline:
1. Clean ARPS NDVI (outlier detection & gap filling)
2. Predict yield using ARPS data
3. Compare with Sentinel-2 predictions
"""

import subprocess
import sys


def run_script(script_name, description):
    """Run a Python script and report status."""
    print("\n" + "=" * 80)
    print(f"STEP: {description}")
    print("=" * 80)
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=False,
            text=True,
            check=True
        )
        print(f"\n✅ {description} - COMPLETE")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} - FAILED")
        print(f"Error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ {description} - EXCEPTION")
        print(f"Error: {e}")
        return False


def main():
    """Run complete ARPS analysis pipeline."""
    
    print("=" * 80)
    print("COMPLETE ARPS ANALYSIS PIPELINE")
    print("=" * 80)
    print("\nThis will:")
    print("  1. Clean ARPS NDVI data (outlier detection & gap filling)")
    print("  2. Predict wheat yield using ARPS data")
    print("  3. Compare ARPS vs Sentinel-2 predictions")
    print("\n" + "=" * 80)
    
    steps = [
        ("clean_arps_ndvi.py", "Clean ARPS NDVI Data"),
        ("predict_yield_arps.py", "Predict Yield with ARPS"),
        ("compare_sentinel2_vs_arps.py", "Compare Sentinel-2 vs ARPS")
    ]
    
    results = []
    
    for script, description in steps:
        success = run_script(script, description)
        results.append((description, success))
        
        if not success:
            print(f"\n⚠️  Pipeline stopped due to failure in: {description}")
            break
    
    # Print summary
    print("\n" + "=" * 80)
    print("PIPELINE SUMMARY")
    print("=" * 80)
    
    for description, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{status}: {description}")
    
    all_success = all(success for _, success in results)
    
    if all_success:
        print("\n" + "=" * 80)
        print("🎉 COMPLETE ARPS ANALYSIS PIPELINE FINISHED SUCCESSFULLY!")
        print("=" * 80)
        print("\nGenerated files:")
        print("  • arps_ndvi_data_cleaned/ - Cleaned ARPS NDVI data")
        print("  • yield_predictions_arps_all_fields.csv - ARPS yield predictions")
        print("  • yield_comparison_sentinel2_vs_arps.csv - Detailed comparison")
        print("  • sentinel2_vs_arps_comparison.png - Visualization")
        print("=" * 80)
    else:
        print("\n⚠️  Pipeline completed with errors")
        sys.exit(1)


if __name__ == "__main__":
    main()

