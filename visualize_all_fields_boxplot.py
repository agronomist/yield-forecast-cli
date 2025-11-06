"""
Create a single boxplot for all fields combined (no dataset distinction)
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def create_combined_boxplot():
    """Create a single boxplot for all fields."""
    
    print("\n" + "=" * 80)
    print("ALL FIELDS COMBINED BOXPLOT")
    print("=" * 80)
    
    # Load combined data
    df = pd.read_csv('yield_predictions_combined_all.csv')
    
    print(f"\n✓ Loaded {len(df)} fields")
    print(f"  Mean:    {df['Grain Yield (ton/ha)'].mean():.2f} ton/ha")
    print(f"  Median:  {df['Grain Yield (ton/ha)'].median():.2f} ton/ha")
    print(f"  Std Dev: {df['Grain Yield (ton/ha)'].std():.2f} ton/ha")
    print(f"  Min:     {df['Grain Yield (ton/ha)'].min():.2f} ton/ha")
    print(f"  Max:     {df['Grain Yield (ton/ha)'].max():.2f} ton/ha")
    print(f"  Q1:      {df['Grain Yield (ton/ha)'].quantile(0.25):.2f} ton/ha")
    print(f"  Q3:      {df['Grain Yield (ton/ha)'].quantile(0.75):.2f} ton/ha")
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 12))
    
    # Sort by yield
    df_sorted = df.sort_values('Grain Yield (ton/ha)', ascending=True)
    
    # Create horizontal boxplot with individual points
    bp = ax.boxplot([df_sorted['Grain Yield (ton/ha)']], 
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
    y = np.ones(len(df_sorted)) + np.random.normal(0, 0.04, len(df_sorted))
    ax.scatter(df_sorted['Grain Yield (ton/ha)'], y, 
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
    ax.set_title(f'Predicted Grain Yield Distribution - All Fields (n={len(df)})',
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
    output_png = 'yield_all_fields_combined_boxplot.png'
    output_pdf = 'yield_all_fields_combined_boxplot.pdf'
    
    plt.savefig(output_png, dpi=300, bbox_inches='tight')
    print(f"\n✓ Saved plot to: {output_png}")
    
    plt.savefig(output_pdf, bbox_inches='tight')
    print(f"✓ Saved PDF to: {output_pdf}")
    
    plt.close()
    
    # Create a second plot: vertical boxplot with field names
    create_ranked_fields_plot(df_sorted)


def create_ranked_fields_plot(df_sorted):
    """Create a plot showing all fields as individual bars."""
    
    fig, ax = plt.subplots(figsize=(16, 20))
    
    # Create positions
    y = np.arange(len(df_sorted))
    
    # Color gradient based on yield
    colors = plt.cm.RdYlGn(
        (df_sorted['Grain Yield (ton/ha)'] - df_sorted['Grain Yield (ton/ha)'].min()) / 
        (df_sorted['Grain Yield (ton/ha)'].max() - df_sorted['Grain Yield (ton/ha)'].min())
    )
    
    # Plot bars
    bars = ax.barh(y, df_sorted['Grain Yield (ton/ha)'], 
                   color=colors, alpha=0.8, edgecolor='black', linewidth=0.5)
    
    # Add field names
    ax.set_yticks(y)
    ax.set_yticklabels([f"{name[:30]}" for name in df_sorted['Field Name']], fontsize=7)
    
    # Add yield values on bars
    for i, (idx, row) in enumerate(df_sorted.iterrows()):
        ax.text(row['Grain Yield (ton/ha)'] + 0.05, i, f"{row['Grain Yield (ton/ha)']:.2f}",
               va='center', fontsize=6, alpha=0.7)
    
    # Mean line
    mean_val = df_sorted['Grain Yield (ton/ha)'].mean()
    ax.axvline(mean_val, color='black', linestyle='--', linewidth=2.5, 
              label=f'Mean: {mean_val:.2f} ton/ha', alpha=0.8)
    
    # Labels and title
    ax.set_xlabel('Grain Yield (ton/ha)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Field Name', fontsize=13, fontweight='bold')
    ax.set_title(f'All Fields Ranked by Predicted Yield (n={len(df_sorted)})',
                fontsize=15, fontweight='bold', pad=20)
    
    ax.legend(loc='lower right', fontsize=11, framealpha=0.9)
    ax.grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout()
    
    output_png = 'yield_all_fields_ranked.png'
    output_pdf = 'yield_all_fields_ranked.pdf'
    
    plt.savefig(output_png, dpi=300, bbox_inches='tight')
    print(f"✓ Saved ranked plot to: {output_png}")
    
    plt.savefig(output_pdf, bbox_inches='tight')
    print(f"✓ Saved PDF to: {output_pdf}")
    
    plt.close()


if __name__ == "__main__":
    try:
        create_combined_boxplot()
        
        print("\n" + "=" * 80)
        print("✓ VISUALIZATION COMPLETE")
        print("=" * 80)
        print("\nFiles created:")
        print("  - yield_all_fields_combined_boxplot.png")
        print("  - yield_all_fields_combined_boxplot.pdf")
        print("  - yield_all_fields_ranked.png")
        print("  - yield_all_fields_ranked.pdf")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

