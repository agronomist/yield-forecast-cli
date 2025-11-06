"""
Create final combined analysis with all 80 fields:
- Original 68 fields with existing predictions
- New 12 fields with cleaned NDVI predictions
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def create_final_combined_dataset():
    """Combine original 68 fields with cleaned predictions for 12 new fields."""
    
    print("\n" + "=" * 80)
    print("CREATING FINAL COMBINED DATASET (ALL 80 FIELDS)")
    print("=" * 80)
    
    # Load original 68 fields (from RUE comparison - stage-based method)
    print("\nLoading original 68 fields...")
    df_original = pd.read_csv('rue_method_comparison.csv')
    df_original_clean = pd.DataFrame({
        'Field Name': df_original['Field Name'],
        'Variety': df_original['Variety'],
        'Sowing Date': df_original['Sowing Date'],
        'Grain Yield (ton/ha)': df_original['Method 2: Stage-based (ton/ha)'],
        'Dataset': 'Original (68 fields)',
        'NDVI Cleaned': False
    })
    print(f"✓ Loaded {len(df_original_clean)} original fields")
    print(f"  Mean yield: {df_original_clean['Grain Yield (ton/ha)'].mean():.2f} ton/ha")
    
    # Load new 12 fields with cleaned NDVI
    print("\nLoading new 12 fields (with cleaned NDVI)...")
    df_new = pd.read_csv('output_new_fields/yield_predictions_cleaned.csv')
    df_new_clean = pd.DataFrame({
        'Field Name': df_new['Field Name'],
        'Variety': df_new['Variety'],
        'Sowing Date': df_new['Sowing Date'],
        'Grain Yield (ton/ha)': df_new['Grain Yield (ton/ha)'],
        'Dataset': 'New (12 fields - cleaned)',
        'NDVI Cleaned': True
    })
    print(f"✓ Loaded {len(df_new_clean)} new fields")
    print(f"  Mean yield: {df_new_clean['Grain Yield (ton/ha)'].mean():.2f} ton/ha")
    
    # Combine
    df_combined = pd.concat([df_original_clean, df_new_clean], ignore_index=True)
    
    print(f"\n✓ Combined dataset: {len(df_combined)} total fields")
    print(f"  Overall mean yield: {df_combined['Grain Yield (ton/ha)'].mean():.2f} ton/ha")
    print(f"  Std dev: {df_combined['Grain Yield (ton/ha)'].std():.2f} ton/ha")
    print(f"  Range: {df_combined['Grain Yield (ton/ha)'].min():.2f} - {df_combined['Grain Yield (ton/ha)'].max():.2f} ton/ha")
    
    # Save
    output_file = 'yield_predictions_all_80_fields_final.csv'
    df_combined.to_csv(output_file, index=False)
    print(f"\n✓ Saved to: {output_file}")
    
    return df_combined


def create_comprehensive_boxplot(df):
    """Create boxplot with all 80 fields ordered by yield."""
    
    print("\n" + "=" * 80)
    print("CREATING COMPREHENSIVE BOXPLOT")
    print("=" * 80)
    
    # Sort by yield
    df_sorted = df.sort_values('Grain Yield (ton/ha)', ascending=True).reset_index(drop=True)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(16, 20))
    
    # Create color gradient based on yield
    colors = plt.cm.RdYlGn(
        (df_sorted['Grain Yield (ton/ha)'] - df_sorted['Grain Yield (ton/ha)'].min()) / 
        (df_sorted['Grain Yield (ton/ha)'].max() - df_sorted['Grain Yield (ton/ha)'].min())
    )
    
    # Create horizontal bars
    y_positions = np.arange(len(df_sorted))
    bars = ax.barh(y_positions, df_sorted['Grain Yield (ton/ha)'], 
                   color=colors, alpha=0.8, edgecolor='black', linewidth=0.5)
    
    # Add field names
    ax.set_yticks(y_positions)
    ax.set_yticklabels([f"{name[:35]}" for name in df_sorted['Field Name']], fontsize=7)
    
    # Add yield values on bars
    for i, (idx, row) in enumerate(df_sorted.iterrows()):
        yield_val = row['Grain Yield (ton/ha)']
        ax.text(yield_val + 0.05, i, f"{yield_val:.2f}",
               va='center', fontsize=6, alpha=0.8)
    
    # Add mean line
    mean_val = df_sorted['Grain Yield (ton/ha)'].mean()
    ax.axvline(mean_val, color='black', linestyle='--', linewidth=2.5, 
              label=f'Mean: {mean_val:.2f} ton/ha', alpha=0.8)
    
    # Add quartile lines
    q1 = df_sorted['Grain Yield (ton/ha)'].quantile(0.25)
    q3 = df_sorted['Grain Yield (ton/ha)'].quantile(0.75)
    ax.axvline(q1, color='blue', linestyle=':', linewidth=2, 
              label=f'Q1: {q1:.2f} ton/ha', alpha=0.6)
    ax.axvline(q3, color='blue', linestyle=':', linewidth=2,
              label=f'Q3: {q3:.2f} ton/ha', alpha=0.6)
    
    # Labels and title
    ax.set_xlabel('Grain Yield (ton/ha)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Field Name', fontsize=13, fontweight='bold')
    ax.set_title(f'All Fields Ranked by Predicted Yield (n={len(df_sorted)})\n' + 
                 f'Mean: {mean_val:.2f} ton/ha | Range: {df_sorted["Grain Yield (ton/ha)"].min():.2f} - {df_sorted["Grain Yield (ton/ha)"].max():.2f} ton/ha',
                fontsize=15, fontweight='bold', pad=20)
    
    # Legend
    ax.legend(loc='lower right', fontsize=11, framealpha=0.9)
    ax.grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout()
    
    # Save
    output_png = 'yield_all_80_fields_ranked_final.png'
    output_pdf = 'yield_all_80_fields_ranked_final.pdf'
    
    plt.savefig(output_png, dpi=300, bbox_inches='tight')
    print(f"✓ Saved plot to: {output_png}")
    
    plt.savefig(output_pdf, bbox_inches='tight')
    print(f"✓ Saved PDF to: {output_pdf}")
    
    plt.close()


def create_simple_boxplot(df):
    """Create a simple boxplot showing distribution."""
    
    print("\nCreating distribution boxplot...")
    
    fig, ax = plt.subplots(figsize=(10, 12))
    
    # Create horizontal boxplot
    bp = ax.boxplot([df['Grain Yield (ton/ha)']], 
                    vert=False,
                    patch_artist=True,
                    showmeans=True,
                    meanprops=dict(marker='D', markerfacecolor='red', markersize=12, 
                                  markeredgecolor='darkred', markeredgewidth=1.5),
                    medianprops=dict(color='darkblue', linewidth=2.5),
                    boxprops=dict(facecolor='lightblue', alpha=0.7, linewidth=2),
                    whiskerprops=dict(linewidth=2),
                    capprops=dict(linewidth=2),
                    flierprops=dict(marker='o', markerfacecolor='red', markersize=8, 
                                   alpha=0.6, markeredgecolor='darkred'))
    
    # Add individual field points with jitter
    y = np.ones(len(df)) + np.random.normal(0, 0.04, len(df))
    ax.scatter(df['Grain Yield (ton/ha)'], y, 
              alpha=0.3, s=50, color='steelblue', edgecolors='navy', linewidth=0.5,
              label='Individual fields')
    
    # Add statistical annotations
    mean_val = df['Grain Yield (ton/ha)'].mean()
    median_val = df['Grain Yield (ton/ha)'].median()
    q1 = df['Grain Yield (ton/ha)'].quantile(0.25)
    q3 = df['Grain Yield (ton/ha)'].quantile(0.75)
    
    # Annotations
    ax.text(mean_val, 1.35, f'Mean: {mean_val:.2f}', 
           ha='center', va='bottom', fontsize=11, fontweight='bold',
           bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7))
    
    ax.text(median_val, 0.65, f'Median: {median_val:.2f}', 
           ha='center', va='top', fontsize=11, fontweight='bold',
           bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.7))
    
    ax.text(q1, 1.25, f'Q1: {q1:.2f}', 
           ha='center', va='bottom', fontsize=9, alpha=0.8)
    
    ax.text(q3, 1.25, f'Q3: {q3:.2f}', 
           ha='center', va='bottom', fontsize=9, alpha=0.8)
    
    # Labels and title
    ax.set_xlabel('Grain Yield (ton/ha)', fontsize=14, fontweight='bold')
    ax.set_title(f'Predicted Grain Yield Distribution - All 80 Fields\n' +
                f'Mean: {mean_val:.2f} ± {df["Grain Yield (ton/ha)"].std():.2f} ton/ha',
                fontsize=16, fontweight='bold', pad=20)
    
    # Remove y-axis labels
    ax.set_yticks([])
    ax.set_ylabel('')
    
    # Grid
    ax.grid(True, alpha=0.3, axis='x', linestyle='--')
    ax.set_xlim(0, df['Grain Yield (ton/ha)'].max() * 1.1)
    
    # Legend
    legend_elements = [
        plt.Line2D([0], [0], marker='D', color='w', markerfacecolor='red', 
                  markersize=10, label='Mean', markeredgecolor='darkred'),
        plt.Line2D([0], [0], color='darkblue', linewidth=2.5, label='Median'),
        plt.scatter([], [], alpha=0.3, s=50, color='steelblue', 
                   edgecolors='navy', linewidth=0.5, label='Individual fields')
    ]
    ax.legend(handles=legend_elements, loc='upper left', fontsize=10, framealpha=0.9)
    
    plt.tight_layout()
    
    # Save
    output_png = 'yield_all_80_fields_boxplot_final.png'
    output_pdf = 'yield_all_80_fields_boxplot_final.pdf'
    
    plt.savefig(output_png, dpi=300, bbox_inches='tight')
    print(f"✓ Saved boxplot to: {output_png}")
    
    plt.savefig(output_pdf, bbox_inches='tight')
    print(f"✓ Saved PDF to: {output_pdf}")
    
    plt.close()


def print_summary_statistics(df):
    """Print comprehensive summary statistics."""
    
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS - ALL 80 FIELDS")
    print("=" * 80)
    
    print(f"\nOverall:")
    print(f"  Total fields: {len(df)}")
    print(f"  Mean yield: {df['Grain Yield (ton/ha)'].mean():.2f} ton/ha")
    print(f"  Median yield: {df['Grain Yield (ton/ha)'].median():.2f} ton/ha")
    print(f"  Std deviation: {df['Grain Yield (ton/ha)'].std():.2f} ton/ha")
    print(f"  Min yield: {df['Grain Yield (ton/ha)'].min():.2f} ton/ha")
    print(f"  Max yield: {df['Grain Yield (ton/ha)'].max():.2f} ton/ha")
    print(f"  Range: {df['Grain Yield (ton/ha)'].max() - df['Grain Yield (ton/ha)'].min():.2f} ton/ha")
    
    print(f"\nQuartiles:")
    print(f"  Q1 (25%): {df['Grain Yield (ton/ha)'].quantile(0.25):.2f} ton/ha")
    print(f"  Q2 (50%): {df['Grain Yield (ton/ha)'].quantile(0.50):.2f} ton/ha")
    print(f"  Q3 (75%): {df['Grain Yield (ton/ha)'].quantile(0.75):.2f} ton/ha")
    
    print(f"\nTop 10 fields:")
    top10 = df.nlargest(10, 'Grain Yield (ton/ha)')
    for i, row in top10.iterrows():
        print(f"  {i+1}. {row['Field Name'][:40]:<40} {row['Grain Yield (ton/ha)']:.2f} ton/ha ({row['Variety']})")
    
    print(f"\nBottom 10 fields:")
    bottom10 = df.nsmallest(10, 'Grain Yield (ton/ha)')
    for i, row in bottom10.iterrows():
        print(f"  {i+1}. {row['Field Name'][:40]:<40} {row['Grain Yield (ton/ha)']:.2f} ton/ha ({row['Variety']})")
    
    print(f"\nBy variety:")
    variety_stats = df.groupby('Variety')['Grain Yield (ton/ha)'].agg(['count', 'mean', 'std', 'min', 'max'])
    variety_stats = variety_stats.sort_values('mean', ascending=False)
    print(variety_stats.to_string())


def main():
    """Main execution function."""
    
    print("\n" + "=" * 80)
    print("FINAL COMBINED ANALYSIS - ALL 80 FIELDS")
    print("=" * 80)
    print("\nCombining:")
    print("  • 68 original fields (existing predictions)")
    print("  • 12 new fields (with cleaned NDVI)")
    
    # Create combined dataset
    df_combined = create_final_combined_dataset()
    
    # Print statistics
    print_summary_statistics(df_combined)
    
    # Create visualizations
    create_comprehensive_boxplot(df_combined)
    create_simple_boxplot(df_combined)
    
    print("\n" + "=" * 80)
    print("✓ FINAL ANALYSIS COMPLETE")
    print("=" * 80)
    print("\nFiles created:")
    print("  - yield_predictions_all_80_fields_final.csv")
    print("  - yield_all_80_fields_ranked_final.png/pdf")
    print("  - yield_all_80_fields_boxplot_final.png/pdf")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

