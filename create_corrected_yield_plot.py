"""
Create yield predictions plot using CORRECTED data.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def create_corrected_yield_plot():
    """Create yield predictions plot with corrected values."""
    
    print("=" * 80)
    print("CREATING CORRECTED YIELD PREDICTIONS PLOT - ALL 83 FIELDS")
    print("=" * 80)
    
    # Load corrected yield predictions
    df = pd.read_csv('yield_predictions_arps_all_fields_CORRECTED.csv')
    
    print(f"\nLoaded {len(df)} fields (CORRECTED)")
    
    # Sort by yield (ascending for horizontal bar plot)
    df = df.sort_values('Grain Yield (ton/ha)', ascending=True).reset_index(drop=True)
    
    # Calculate statistics
    mean_yield = df['Grain Yield (ton/ha)'].mean()
    median_yield = df['Grain Yield (ton/ha)'].median()
    q1_yield = df['Grain Yield (ton/ha)'].quantile(0.25)
    q3_yield = df['Grain Yield (ton/ha)'].quantile(0.75)
    min_yield = df['Grain Yield (ton/ha)'].min()
    max_yield = df['Grain Yield (ton/ha)'].max()
    
    print(f"\nStatistics (CORRECTED):")
    print(f"  Mean: {mean_yield:.2f} ton/ha")
    print(f"  Median: {median_yield:.2f} ton/ha")
    print(f"  Range: {min_yield:.2f} - {max_yield:.2f} ton/ha")
    
    # Create figure with appropriate height
    fig_height = max(20, len(df) * 0.25)
    fig, ax = plt.subplots(figsize=(14, fig_height))
    
    # Prepare data
    field_names = df['Field Name'].values
    yields = df['Grain Yield (ton/ha)'].values
    
    # Create y positions
    y_pos = np.arange(len(field_names))
    
    # Create color gradient: red (low) -> yellow -> green (high)
    norm = plt.Normalize(vmin=min_yield, vmax=max_yield)
    cmap = plt.cm.RdYlGn
    colors = cmap(norm(yields))
    
    # Plot horizontal bars
    bars = ax.barh(y_pos, yields, color=colors, edgecolor='black', linewidth=0.6, height=0.8)
    
    # Add vertical lines for statistics
    ax.axvline(x=mean_yield, color='black', linestyle='--', linewidth=2.5, 
               label=f'Mean: {mean_yield:.2f} ton/ha', alpha=0.9, zorder=10)
    ax.axvline(x=median_yield, color='black', linestyle='-', linewidth=2, 
               label=f'Median: {median_yield:.2f} ton/ha', alpha=0.8, zorder=10)
    ax.axvline(x=q1_yield, color='gray', linestyle=':', linewidth=1.5, 
               label=f'Q1: {q1_yield:.2f} ton/ha', alpha=0.7, zorder=9)
    ax.axvline(x=q3_yield, color='gray', linestyle=':', linewidth=1.5, 
               label=f'Q3: {q3_yield:.2f} ton/ha', alpha=0.7, zorder=9)
    
    # Add yield values at the end of each bar
    for i, (y, val) in enumerate(zip(y_pos, yields)):
        ax.text(val + 0.08, y, f'{val:.2f}', 
                va='center', ha='left', fontsize=6.5, fontweight='bold')
    
    # Customize axes
    ax.set_yticks(y_pos)
    ax.set_yticklabels(field_names, fontsize=7)
    ax.set_xlabel('Grain Yield (ton/ha)', fontsize=15, fontweight='bold')
    ax.set_ylabel('Field Name', fontsize=15, fontweight='bold')
    
    # Title with statistics
    title = (f'ARPS Yield Predictions (CORRECTED) - {len(df)} Fields Ranked by Yield\n'
             f'Data Source: PlanetScope 3m Daily | Mean: {mean_yield:.2f} ton/ha | '
             f'Range: {min_yield:.2f} - {max_yield:.2f} ton/ha')
    ax.set_title(title, fontsize=17, fontweight='bold', pad=20)
    
    # Add grid
    ax.grid(True, axis='x', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    # Set x-axis limits
    ax.set_xlim(0, max_yield * 1.15)
    
    # Legend
    ax.legend(loc='lower right', fontsize=11, framealpha=0.95, 
              title='Statistics', title_fontsize=12, ncol=2)
    
    # Tight layout
    plt.tight_layout()
    
    # Save figures
    output_png = 'yield_predictions_all_83_fields_CORRECTED.png'
    plt.savefig(output_png, dpi=300, bbox_inches='tight')
    print(f"\n✓ Saved plot to: {output_png}")
    
    output_pdf = 'yield_predictions_all_83_fields_CORRECTED.pdf'
    plt.savefig(output_pdf, bbox_inches='tight')
    print(f"✓ Saved PDF to: {output_pdf}")
    
    plt.close()
    
    # Also create boxplot version
    create_boxplot_version(df, mean_yield, median_yield, q1_yield, q3_yield, min_yield, max_yield)
    
    return fig, ax


def create_boxplot_version(df, mean_yield, median_yield, q1_yield, q3_yield, min_yield, max_yield):
    """Create compact boxplot version."""
    
    fig, ax = plt.subplots(figsize=(20, 12))
    
    # Sort by yield (descending)
    df = df.sort_values('Grain Yield (ton/ha)', ascending=False).reset_index(drop=True)
    
    field_names = df['Field Name'].values
    yields = df['Grain Yield (ton/ha)'].values
    
    # Create x positions
    x_pos = np.arange(len(field_names))
    
    # Color gradient
    norm = plt.Normalize(vmin=min_yield, vmax=max_yield)
    cmap = plt.cm.RdYlGn
    colors = cmap(norm(yields))
    
    # Plot bars
    bars = ax.bar(x_pos, yields, color=colors, edgecolor='black', linewidth=0.5)
    
    # Add horizontal lines
    ax.axhline(y=mean_yield, color='black', linestyle='--', linewidth=2.5, 
               label=f'Mean: {mean_yield:.2f} ton/ha', alpha=0.9, zorder=10)
    ax.axhline(y=median_yield, color='black', linestyle='-', linewidth=2, 
               label=f'Median: {median_yield:.2f} ton/ha', alpha=0.8, zorder=10)
    ax.axhline(y=q1_yield, color='gray', linestyle=':', linewidth=1.5, 
               label=f'Q1: {q1_yield:.2f} ton/ha', alpha=0.7, zorder=9)
    ax.axhline(y=q3_yield, color='gray', linestyle=':', linewidth=1.5, 
               label=f'Q3: {q3_yield:.2f} ton/ha', alpha=0.7, zorder=9)
    
    # Customize axes
    ax.set_xticks(x_pos)
    ax.set_xticklabels(field_names, rotation=90, ha='right', fontsize=7)
    ax.set_xlabel('Field Name', fontsize=15, fontweight='bold')
    ax.set_ylabel('Grain Yield (ton/ha)', fontsize=15, fontweight='bold')
    
    # Title
    title = (f'ARPS Yield Predictions (CORRECTED) - {len(df)} Fields Ranked by Yield\n'
             f'Data Source: PlanetScope 3m Daily | Mean: {mean_yield:.2f} ton/ha | '
             f'Range: {min_yield:.2f} - {max_yield:.2f} ton/ha')
    ax.set_title(title, fontsize=17, fontweight='bold', pad=20)
    
    # Add grid
    ax.grid(True, axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    # Set y-axis limits
    ax.set_ylim(0, max_yield * 1.1)
    
    # Legend
    ax.legend(loc='upper right', fontsize=11, framealpha=0.95, 
              title='Statistics', title_fontsize=12)
    
    # Tight layout
    plt.tight_layout()
    
    # Save
    output_png = 'yield_predictions_all_83_fields_CORRECTED_boxplot.png'
    plt.savefig(output_png, dpi=300, bbox_inches='tight')
    print(f"✓ Saved boxplot to: {output_png}")
    
    output_pdf = 'yield_predictions_all_83_fields_CORRECTED_boxplot.pdf'
    plt.savefig(output_pdf, bbox_inches='tight')
    print(f"✓ Saved PDF to: {output_pdf}")
    
    plt.close()


if __name__ == "__main__":
    try:
        create_corrected_yield_plot()
        
        print("\n" + "=" * 80)
        print("✓ CORRECTED YIELD PREDICTIONS PLOT CREATED")
        print("=" * 80)
        print("\nGenerated files:")
        print("  - yield_predictions_all_83_fields_CORRECTED.png")
        print("  - yield_predictions_all_83_fields_CORRECTED.pdf")
        print("  - yield_predictions_all_83_fields_CORRECTED_boxplot.png")
        print("  - yield_predictions_all_83_fields_CORRECTED_boxplot.pdf")
        
    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        print("Please ensure yield_predictions_arps_all_fields_CORRECTED.csv exists")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

