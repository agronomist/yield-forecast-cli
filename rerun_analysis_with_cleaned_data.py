"""
Re-run biomass and yield predictions using cleaned NDVI data.
Compare results with original predictions.
"""

import json
import pandas as pd
import subprocess
import os


def backup_and_replace_data():
    """Backup original data and replace with cleaned version."""
    
    print("\n" + "=" * 80)
    print("PREPARING DATA FILES")
    print("=" * 80)
    
    import shutil
    
    # Backup original NDVI/fAPAR data
    original_file = 'output_new_fields/sentinel_ndvi_fapar_data.json'
    backup_file = 'output_new_fields/sentinel_ndvi_fapar_data_original_backup.json'
    cleaned_file = 'output_new_fields/sentinel_ndvi_fapar_data_cleaned.json'
    
    if not os.path.exists(backup_file):
        shutil.copy(original_file, backup_file)
        print(f"✓ Backed up original NDVI data to: {backup_file}")
    else:
        print(f"ℹ️  NDVI backup already exists: {backup_file}")
    
    # Copy cleaned version to main location
    shutil.copy(cleaned_file, original_file)
    print(f"✓ Replaced with cleaned data: {original_file}")
    
    # Backup original yield predictions if they exist
    yield_file = 'output_new_fields/yield_predictions.csv'
    yield_backup = 'output_new_fields/yield_predictions_original_backup.csv'
    
    if os.path.exists(yield_file) and not os.path.exists(yield_backup):
        shutil.copy(yield_file, yield_backup)
        print(f"✓ Backed up original predictions to: {yield_backup}")


def restore_original_data():
    """Restore original data after analysis."""
    
    original_file = 'output_new_fields/sentinel_ndvi_fapar_data.json'
    backup_file = 'output_new_fields/sentinel_ndvi_fapar_data_original_backup.json'
    
    if os.path.exists(backup_file):
        import shutil
        shutil.copy(backup_file, original_file)
        print(f"✓ Restored original data")


def run_yield_prediction():
    """Run yield prediction with cleaned data."""
    
    print("\n" + "=" * 80)
    print("RUNNING YIELD PREDICTION WITH CLEANED DATA")
    print("=" * 80)
    
    # Change to output_new_fields directory
    os.chdir('output_new_fields')
    
    # Run prediction script from parent directory
    result = subprocess.run(
        ['python3', '../predict_yield.py'],
        capture_output=True,
        text=True
    )
    
    # Change back
    os.chdir('..')
    
    if result.returncode == 0:
        print("✓ Yield prediction completed successfully")
        # Show last 30 lines of output
        output_lines = result.stdout.strip().split('\n')
        for line in output_lines[-30:]:
            print(line)
    else:
        print("✗ Error running yield prediction:")
        print(result.stderr)
        print("\nStdout:")
        print(result.stdout)
        return False
    
    return True


def compare_results():
    """Compare original vs cleaned data predictions."""
    
    print("\n" + "=" * 80)
    print("COMPARING ORIGINAL VS CLEANED PREDICTIONS")
    print("=" * 80)
    
    # Load original predictions (from backup)
    try:
        df_original = pd.read_csv('output_new_fields/yield_predictions_original_backup.csv')
        print(f"✓ Loaded original predictions: {len(df_original)} fields")
    except FileNotFoundError:
        print("⚠️ Original predictions backup not found")
        try:
            df_original = pd.read_csv('output_new_fields/yield_predictions.csv')
            print(f"✓ Loaded predictions from main file: {len(df_original)} fields")
        except FileNotFoundError:
            print("⚠️ No predictions found")
            return
    
    # Load cleaned predictions
    try:
        df_cleaned = pd.read_csv('output_new_fields/yield_predictions.csv')
        print(f"✓ Loaded cleaned predictions: {len(df_cleaned)} fields")
    except FileNotFoundError:
        print("⚠️ Cleaned predictions not found")
        return
    
    # Merge for comparison
    comparison = pd.merge(
        df_original[['Field Name', 'Grain Yield (ton/ha)']],
        df_cleaned[['Field Name', 'Grain Yield (ton/ha)']],
        on='Field Name',
        suffixes=('_original', '_cleaned')
    )
    
    # Calculate differences
    comparison['Difference (ton/ha)'] = comparison['Grain Yield (ton/ha)_cleaned'] - comparison['Grain Yield (ton/ha)_original']
    comparison['Difference (%)'] = (comparison['Difference (ton/ha)'] / comparison['Grain Yield (ton/ha)_original']) * 100
    
    # Sort by absolute difference
    comparison['Abs_Diff'] = comparison['Difference (ton/ha)'].abs()
    comparison = comparison.sort_values('Abs_Diff', ascending=False)
    
    # Display results
    print("\n" + "─" * 80)
    print("YIELD COMPARISON (Original vs Cleaned)")
    print("─" * 80)
    print(f"\n{'Field':<30} {'Original':<12} {'Cleaned':<12} {'Diff':<10} {'Diff %':<10}")
    print("─" * 80)
    
    for _, row in comparison.iterrows():
        field_name = row['Field Name'][:28]
        orig = row['Grain Yield (ton/ha)_original']
        clean = row['Grain Yield (ton/ha)_cleaned']
        diff = row['Difference (ton/ha)']
        diff_pct = row['Difference (%)']
        
        # Color code based on change
        symbol = '↑' if diff > 0 else '↓' if diff < 0 else '='
        print(f"{field_name:<30} {orig:>10.2f}  {clean:>10.2f}  {symbol} {diff:>7.2f}  {diff_pct:>7.1f}%")
    
    # Summary statistics
    print("\n" + "─" * 80)
    print("SUMMARY STATISTICS")
    print("─" * 80)
    
    print(f"\nOriginal predictions:")
    print(f"  Mean: {comparison['Grain Yield (ton/ha)_original'].mean():.2f} ton/ha")
    print(f"  Std:  {comparison['Grain Yield (ton/ha)_original'].std():.2f} ton/ha")
    
    print(f"\nCleaned predictions:")
    print(f"  Mean: {comparison['Grain Yield (ton/ha)_cleaned'].mean():.2f} ton/ha")
    print(f"  Std:  {comparison['Grain Yield (ton/ha)_cleaned'].std():.2f} ton/ha")
    
    print(f"\nChanges:")
    print(f"  Mean difference: {comparison['Difference (ton/ha)'].mean():.2f} ton/ha ({comparison['Difference (%)'].mean():.1f}%)")
    print(f"  Max increase: {comparison['Difference (ton/ha)'].max():.2f} ton/ha")
    print(f"  Max decrease: {comparison['Difference (ton/ha)'].min():.2f} ton/ha")
    print(f"  Avg absolute change: {comparison['Abs_Diff'].mean():.2f} ton/ha ({comparison['Difference (%)'].abs().mean():.1f}%)")
    
    # Save comparison
    comparison_file = 'output_new_fields/yield_comparison_original_vs_cleaned.csv'
    comparison.to_csv(comparison_file, index=False)
    print(f"\n✓ Saved comparison to: {comparison_file}")
    
    # Copy cleaned predictions with "_cleaned" suffix
    import shutil
    if os.path.exists('output_new_fields/yield_predictions.csv'):
        shutil.copy('output_new_fields/yield_predictions.csv', 'output_new_fields/yield_predictions_cleaned.csv')
        shutil.copy('output_new_fields/yield_predictions.json', 'output_new_fields/yield_predictions_cleaned.json')
        shutil.copy('output_new_fields/daily_biomass_accumulation.csv', 'output_new_fields/daily_biomass_accumulation_cleaned.csv')
        print(f"✓ Saved cleaned predictions to output_new_fields/")


def main():
    """Main execution function."""
    
    print("\n" + "=" * 80)
    print("RE-RUN ANALYSIS WITH CLEANED NDVI DATA")
    print("=" * 80)
    
    # Step 1: Backup and replace data
    backup_and_replace_data()
    
    # Step 2: Run yield prediction
    success = run_yield_prediction()
    
    if not success:
        print("\n✗ Analysis failed")
        restore_original_data()
        return
    
    # Step 3: Compare results
    compare_results()
    
    # Step 4: Restore original data
    print("\n" + "=" * 80)
    print("RESTORING ORIGINAL DATA")
    print("=" * 80)
    restore_original_data()
    
    print("\n" + "=" * 80)
    print("✓ ANALYSIS COMPLETE")
    print("=" * 80)
    print("\nFiles created:")
    print("  - output_new_fields/yield_predictions_cleaned.csv")
    print("  - output_new_fields/yield_predictions_cleaned.json")
    print("  - output_new_fields/daily_biomass_accumulation_cleaned.csv")
    print("  - output_new_fields/yield_comparison_original_vs_cleaned.csv")
    print("\nOriginal data has been restored.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Make sure to restore original data even if there's an error
        restore_original_data()

