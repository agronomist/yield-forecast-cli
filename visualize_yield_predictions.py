"""
Visualize Yield Predictions with Box Plot

Creates a visualization showing predicted grain yield with uncertainty ranges
for all fields, ordered by yield.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def create_yield_boxplot():
    """Create a box plot showing yield predictions with uncertainty ranges."""
    
    # Read yield predictions
    df = pd.read_csv('yield_predictions.csv')
    
    # Sort by grain yield (descending)
    df = df.sort_values('Grain Yield (ton/ha)', ascending=False).reset_index(drop=True)
    
    # Create figure with larger size for all fields
    fig, ax = plt.subplots(figsize=(16, 12))
    
    # Prepare data for plotting
    field_names = df['Field Name'].values
    yields = df['Grain Yield (ton/ha)'].values
    yield_min = df['Yield Min (ton/ha)'].values
    yield_max = df['Yield Max (ton/ha)'].values
    varieties = df['Variety'].values
    
    # Create x positions
    x_pos = np.arange(len(field_names))
    
    # Color map by variety
    variety_colors = {
        'ACA Fresno': '#e41a1c',
        'BG 620': '#377eb8',
        'BG 610': '#4daf4a',
        'DM Algarrobo': '#984ea3',
        'DM Pehuen': '#ff7f00',
        'DM Alerce': '#a65628',
        'DM Aromo': '#f781bf',
        'Baguette 620': '#999999'
    }
    
    colors = [variety_colors.get(v, '#cccccc') for v in varieties]
    
    # Plot error bars (showing min-max range)
    for i, (x, y, ymin, ymax, color) in enumerate(zip(x_pos, yields, yield_min, yield_max, colors)):
        # Draw vertical line for range
        ax.plot([x, x], [ymin, ymax], color=color, linewidth=2, alpha=0.6, zorder=1)
        
        # Draw min and max caps
        ax.plot([x-0.15, x+0.15], [ymin, ymin], color=color, linewidth=2, alpha=0.6, zorder=1)
        ax.plot([x-0.15, x+0.15], [ymax, ymax], color=color, linewidth=2, alpha=0.6, zorder=1)
    
    # Plot central yield estimate as scatter
    ax.scatter(x_pos, yields, c=colors, s=80, zorder=2, edgecolors='black', linewidth=1)
    
    # Add horizontal line for mean yield
    mean_yield = yields.mean()
    ax.axhline(y=mean_yield, color='red', linestyle='--', linewidth=2, 
               label=f'Mean Yield: {mean_yield:.2f} ton/ha', alpha=0.7)
    
    # Customize plot
    ax.set_xticks(x_pos)
    ax.set_xticklabels(field_names, rotation=90, ha='right', fontsize=8)
    ax.set_xlabel('Field Name', fontsize=12, fontweight='bold')
    ax.set_ylabel('Grain Yield (ton/ha)', fontsize=12, fontweight='bold')
    ax.set_title('Predicted Wheat Grain Yield by Field\n(Ordered by Yield with Uncertainty Range)', 
                 fontsize=14, fontweight='bold', pad=20)
    
    # Add grid
    ax.grid(True, axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    # Set y-axis limits
    ax.set_ylim(0, max(yield_max) * 1.1)
    
    # Create legend for varieties
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=variety_colors[v], label=v) 
                       for v in sorted(variety_colors.keys())]
    legend_elements.append(plt.Line2D([0], [0], color='red', linestyle='--', 
                                      label=f'Mean: {mean_yield:.2f} ton/ha'))
    
    ax.legend(handles=legend_elements, loc='upper right', fontsize=9, 
              title='Variety', framealpha=0.9)
    
    # Tight layout
    plt.tight_layout()
    
    # Save figure
    output_file = 'yield_predictions_boxplot.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved plot to: {output_file}")
    
    # Also save as PDF for high quality
    output_pdf = 'yield_predictions_boxplot.pdf'
    plt.savefig(output_pdf, bbox_inches='tight')
    print(f"✓ Saved PDF to: {output_pdf}")
    
    plt.show()
    
    return fig, ax


def create_variety_comparison():
    """Create a box plot comparing varieties."""
    
    df = pd.read_csv('yield_predictions.csv')
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Prepare data by variety
    varieties = df['Variety'].unique()
    variety_data = []
    variety_labels = []
    variety_counts = []
    
    for variety in sorted(varieties):
        variety_df = df[df['Variety'] == variety]
        variety_data.append(variety_df['Grain Yield (ton/ha)'].values)
        variety_labels.append(variety)
        variety_counts.append(len(variety_df))
    
    # Create box plot
    bp = ax.boxplot(variety_data, labels=[f"{v}\n(n={c})" for v, c in zip(variety_labels, variety_counts)],
                    patch_artist=True, showmeans=True,
                    meanprops=dict(marker='D', markerfacecolor='red', markersize=8))
    
    # Color boxes
    variety_colors = {
        'ACA Fresno': '#e41a1c',
        'BG 620': '#377eb8',
        'BG 610': '#4daf4a',
        'DM Algarrobo': '#984ea3',
        'DM Pehuen': '#ff7f00',
        'DM Alerce': '#a65628',
        'DM Aromo': '#f781bf',
        'Baguette 620': '#999999'
    }
    
    for patch, variety in zip(bp['boxes'], variety_labels):
        patch.set_facecolor(variety_colors.get(variety, '#cccccc'))
        patch.set_alpha(0.6)
    
    # Add horizontal line for mean yield
    mean_yield = df['Grain Yield (ton/ha)'].mean()
    ax.axhline(y=mean_yield, color='red', linestyle='--', linewidth=2, 
               label=f'Overall Mean: {mean_yield:.2f} ton/ha', alpha=0.7)
    
    # Customize plot
    ax.set_xlabel('Variety (number of fields)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Grain Yield (ton/ha)', fontsize=12, fontweight='bold')
    ax.set_title('Wheat Grain Yield Distribution by Variety', 
                 fontsize=14, fontweight='bold', pad=20)
    
    # Add grid
    ax.grid(True, axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    # Legend
    ax.legend(loc='upper right', fontsize=10, framealpha=0.9)
    
    # Rotate x-axis labels if needed
    plt.xticks(rotation=45, ha='right')
    
    # Tight layout
    plt.tight_layout()
    
    # Save figure
    output_file = 'yield_by_variety_boxplot.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved variety comparison to: {output_file}")
    
    output_pdf = 'yield_by_variety_boxplot.pdf'
    plt.savefig(output_pdf, bbox_inches='tight')
    print(f"✓ Saved variety PDF to: {output_pdf}")
    
    plt.show()
    
    return fig, ax


def print_summary_stats():
    """Print summary statistics."""
    df = pd.read_csv('yield_predictions.csv')
    
    print("\n" + "=" * 80)
    print("YIELD PREDICTION STATISTICS")
    print("=" * 80)
    
    print(f"\nTotal Fields: {len(df)}")
    print(f"\nGrain Yield (ton/ha):")
    print(f"  Mean:   {df['Grain Yield (ton/ha)'].mean():.2f}")
    print(f"  Median: {df['Grain Yield (ton/ha)'].median():.2f}")
    print(f"  Std:    {df['Grain Yield (ton/ha)'].std():.2f}")
    print(f"  Min:    {df['Grain Yield (ton/ha)'].min():.2f} ({df.loc[df['Grain Yield (ton/ha)'].idxmin(), 'Field Name']})")
    print(f"  Max:    {df['Grain Yield (ton/ha)'].max():.2f} ({df.loc[df['Grain Yield (ton/ha)'].idxmax(), 'Field Name']})")
    
    print("\nYield by Variety:")
    variety_stats = df.groupby('Variety')['Grain Yield (ton/ha)'].agg(['mean', 'std', 'count'])
    variety_stats = variety_stats.sort_values('mean', ascending=False)
    print(variety_stats.to_string())
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("CREATING YIELD PREDICTION VISUALIZATIONS")
    print("=" * 80)
    
    try:
        # Print statistics
        print_summary_stats()
        
        print("\n" + "─" * 80)
        print("Creating visualizations...")
        print("─" * 80)
        
        # Create main yield plot
        print("\n1. Creating field-by-field yield plot...")
        create_yield_boxplot()
        
        # Create variety comparison
        print("\n2. Creating variety comparison plot...")
        create_variety_comparison()
        
        print("\n" + "=" * 80)
        print("✓ VISUALIZATIONS COMPLETE")
        print("=" * 80)
        print("\nCreated files:")
        print("  - yield_predictions_boxplot.png")
        print("  - yield_predictions_boxplot.pdf")
        print("  - yield_by_variety_boxplot.png")
        print("  - yield_by_variety_boxplot.pdf")
        
    except FileNotFoundError:
        print("\n✗ Error: Could not find yield_predictions.csv")
        print("Please run predict_yield.py first")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

