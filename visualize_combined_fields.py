"""
Visualize Combined Yield Predictions (Original + New Fields)

Creates comprehensive visualizations showing all fields together.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def create_combined_visualizations():
    """Create visualizations for all fields combined."""
    
    print("\n" + "=" * 80)
    print("COMBINED YIELD VISUALIZATION (ALL FIELDS)")
    print("=" * 80)
    
    # Load combined data (already prepared)
    print("\nLoading datasets...")
    try:
        df_combined = pd.read_csv('yield_predictions_combined_all.csv')
        df_original = df_combined[df_combined['dataset'] == 'Original']
        df_new = df_combined[df_combined['dataset'] == 'New Fields']
        print(f"✓ Loaded {len(df_original)} original fields")
        print(f"✓ Loaded {len(df_new)} new fields")
        print(f"✓ Combined: {len(df_combined)} total fields")
    except FileNotFoundError:
        print("✗ Combined data file not found: yield_predictions_combined_all.csv")
        return
    
    # Summary statistics
    print("\n" + "─" * 80)
    print("SUMMARY STATISTICS")
    print("─" * 80)
    
    print(f"\nOriginal fields:")
    if len(df_original) > 0:
        print(f"  Count:   {len(df_original)}")
        print(f"  Mean:    {df_original['Grain Yield (ton/ha)'].mean():.2f} ton/ha")
        print(f"  Median:  {df_original['Grain Yield (ton/ha)'].median():.2f} ton/ha")
        print(f"  Range:   {df_original['Grain Yield (ton/ha)'].min():.2f} - {df_original['Grain Yield (ton/ha)'].max():.2f} ton/ha")
    
    print(f"\nNew fields:")
    print(f"  Count:   {len(df_new)}")
    print(f"  Mean:    {df_new['Grain Yield (ton/ha)'].mean():.2f} ton/ha")
    print(f"  Median:  {df_new['Grain Yield (ton/ha)'].median():.2f} ton/ha")
    print(f"  Range:   {df_new['Grain Yield (ton/ha)'].min():.2f} - {df_new['Grain Yield (ton/ha)'].max():.2f} ton/ha")
    
    print(f"\nCombined (all {len(df_combined)} fields):")
    print(f"  Mean:    {df_combined['Grain Yield (ton/ha)'].mean():.2f} ton/ha")
    print(f"  Median:  {df_combined['Grain Yield (ton/ha)'].median():.2f} ton/ha")
    print(f"  Std Dev: {df_combined['Grain Yield (ton/ha)'].std():.2f} ton/ha")
    print(f"  Range:   {df_combined['Grain Yield (ton/ha)'].min():.2f} - {df_combined['Grain Yield (ton/ha)'].max():.2f} ton/ha")
    
    # Create visualizations
    print("\n" + "─" * 80)
    print("Creating visualizations...")
    print("─" * 80)
    
    # Plot 1: All fields ranked
    create_all_fields_plot(df_combined, df_original, df_new)
    
    # Plot 2: Dataset comparison
    create_dataset_comparison(df_original, df_new, df_combined)
    
    # Plot 3: Variety comparison (all fields)
    create_combined_variety_plot(df_combined)
    
    # Save combined CSV
    df_combined.to_csv('yield_predictions_combined.csv', index=False)
    print(f"\n✓ Saved combined data to: yield_predictions_combined.csv")


def create_all_fields_plot(df_combined, df_original, df_new):
    """Create plot showing all fields ranked by yield."""
    
    fig, ax = plt.subplots(figsize=(20, 10))
    
    # Sort by yield
    df_sorted = df_combined.sort_values('Grain Yield (ton/ha)', ascending=True)
    
    # Create positions
    x = np.arange(len(df_sorted))
    
    # Colors based on dataset
    colors = ['#2E86AB' if dataset == 'Original' else '#A23B72' 
              for dataset in df_sorted['dataset']]
    
    # Plot bars
    bars = ax.barh(x, df_sorted['Grain Yield (ton/ha)'], color=colors, alpha=0.7, edgecolor='black', linewidth=0.5)
    
    # Add field names (show every nth name to avoid clutter)
    step = max(1, len(df_sorted) // 40)  # Show ~40 names max
    for i in range(0, len(df_sorted), step):
        row = df_sorted.iloc[i]
        ax.text(row['Grain Yield (ton/ha)'] + 0.1, i, 
               f"{row['Field Name'][:25]}", 
               va='center', fontsize=6, alpha=0.7)
    
    # Mean lines
    if len(df_original) > 0:
        mean_original = df_original['Grain Yield (ton/ha)'].mean()
        ax.axvline(mean_original, color='#2E86AB', linestyle='--', linewidth=2, 
                  label=f'Original mean: {mean_original:.2f} ton/ha', alpha=0.8)
    
    mean_new = df_new['Grain Yield (ton/ha)'].mean()
    ax.axvline(mean_new, color='#A23B72', linestyle='--', linewidth=2,
              label=f'New fields mean: {mean_new:.2f} ton/ha', alpha=0.8)
    
    mean_combined = df_combined['Grain Yield (ton/ha)'].mean()
    ax.axvline(mean_combined, color='black', linestyle='-', linewidth=2.5,
              label=f'Combined mean: {mean_combined:.2f} ton/ha', alpha=0.8)
    
    # Labels and title
    ax.set_xlabel('Grain Yield (ton/ha)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Fields (ranked)', fontsize=13, fontweight='bold')
    ax.set_title(f'All Fields Ranked by Predicted Yield (n={len(df_combined)})',
                fontsize=15, fontweight='bold', pad=20)
    
    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#2E86AB', alpha=0.7, label=f'Original fields (n={len(df_original)})'),
        Patch(facecolor='#A23B72', alpha=0.7, label=f'New fields (n={len(df_new)})')
    ]
    ax.legend(handles=legend_elements + ax.get_legend_handles_labels()[0], 
             loc='lower right', fontsize=10, framealpha=0.9)
    
    ax.grid(True, alpha=0.3, axis='x')
    ax.set_yticks([])
    
    plt.tight_layout()
    
    output_file = 'yield_predictions_all_fields.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved all fields plot to: {output_file}")
    
    plt.savefig('yield_predictions_all_fields.pdf', bbox_inches='tight')
    print(f"✓ Saved PDF to: yield_predictions_all_fields.pdf")
    
    plt.close()


def create_dataset_comparison(df_original, df_new, df_combined):
    """Create boxplot comparison between datasets."""
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    
    # Plot 1: Boxplot comparison
    ax1 = axes[0]
    
    data_to_plot = []
    labels = []
    colors = []
    
    if len(df_original) > 0:
        data_to_plot.append(df_original['Grain Yield (ton/ha)'])
        labels.append(f'Original\n(n={len(df_original)})')
        colors.append('#2E86AB')
    
    data_to_plot.append(df_new['Grain Yield (ton/ha)'])
    labels.append(f'New Fields\n(n={len(df_new)})')
    colors.append('#A23B72')
    
    data_to_plot.append(df_combined['Grain Yield (ton/ha)'])
    labels.append(f'Combined\n(n={len(df_combined)})')
    colors.append('#06A77D')
    
    bp = ax1.boxplot(data_to_plot, labels=labels, patch_artist=True, 
                     showmeans=True, meanprops=dict(marker='D', markerfacecolor='red', markersize=10))
    
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    ax1.set_ylabel('Grain Yield (ton/ha)', fontsize=12, fontweight='bold')
    ax1.set_title('Yield Distribution by Dataset', fontsize=13, fontweight='bold')
    ax1.grid(True, alpha=0.3, axis='y')
    
    # Plot 2: Histogram comparison
    ax2 = axes[1]
    
    bins = np.linspace(df_combined['Grain Yield (ton/ha)'].min(), 
                      df_combined['Grain Yield (ton/ha)'].max(), 25)
    
    if len(df_original) > 0:
        ax2.hist(df_original['Grain Yield (ton/ha)'], bins=bins, alpha=0.5, 
                label=f'Original (n={len(df_original)})', color='#2E86AB', edgecolor='black')
    
    ax2.hist(df_new['Grain Yield (ton/ha)'], bins=bins, alpha=0.5,
            label=f'New Fields (n={len(df_new)})', color='#A23B72', edgecolor='black')
    
    ax2.set_xlabel('Grain Yield (ton/ha)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Number of Fields', fontsize=12, fontweight='bold')
    ax2.set_title('Yield Distribution Comparison', fontsize=13, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3, axis='y')
    
    plt.suptitle('Original vs New Fields Comparison', fontsize=15, fontweight='bold', y=0.98)
    plt.tight_layout()
    
    output_file = 'yield_comparison_datasets.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved dataset comparison to: {output_file}")
    
    plt.savefig('yield_comparison_datasets.pdf', bbox_inches='tight')
    print(f"✓ Saved PDF to: yield_comparison_datasets.pdf")
    
    plt.close()


def create_combined_variety_plot(df_combined):
    """Create variety comparison with all fields."""
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Group by variety
    varieties = df_combined.groupby('Variety')['Grain Yield (ton/ha)'].apply(list).to_dict()
    varieties_sorted = sorted(varieties.items(), key=lambda x: np.mean(x[1]), reverse=True)
    
    data_to_plot = [yields for _, yields in varieties_sorted]
    labels = [f"{var}\n(n={len(yields)})" for var, yields in varieties_sorted]
    
    bp = ax.boxplot(data_to_plot, labels=labels, patch_artist=True,
                   showmeans=True, meanprops=dict(marker='D', markerfacecolor='red', markersize=8))
    
    # Color by performance
    colors = plt.cm.RdYlGn(np.linspace(0.3, 0.9, len(bp['boxes'])))
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    # Add mean values as text
    for i, (var, yields) in enumerate(varieties_sorted, 1):
        mean_val = np.mean(yields)
        ax.text(i, mean_val, f'{mean_val:.2f}', 
               ha='center', va='bottom', fontweight='bold', fontsize=9)
    
    ax.set_ylabel('Grain Yield (ton/ha)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Variety', fontsize=12, fontweight='bold')
    ax.set_title(f'Yield by Variety - All Fields (n={len(df_combined)})',
                fontsize=14, fontweight='bold', pad=15)
    
    # Rotate labels if many varieties
    if len(labels) > 8:
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    output_file = 'yield_by_variety_combined.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved combined variety plot to: {output_file}")
    
    plt.savefig('yield_by_variety_combined.pdf', bbox_inches='tight')
    print(f"✓ Saved PDF to: yield_by_variety_combined.pdf")
    
    plt.close()


if __name__ == "__main__":
    try:
        create_combined_visualizations()
        
        print("\n" + "=" * 80)
        print("✓ COMBINED VISUALIZATION COMPLETE")
        print("=" * 80)
        print("\nFiles created:")
        print("  - yield_predictions_all_fields.png (all fields ranked)")
        print("  - yield_predictions_all_fields.pdf")
        print("  - yield_comparison_datasets.png (original vs new)")
        print("  - yield_comparison_datasets.pdf")
        print("  - yield_by_variety_combined.png (variety comparison)")
        print("  - yield_by_variety_combined.pdf")
        print("  - yield_predictions_combined.csv (combined data)")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

