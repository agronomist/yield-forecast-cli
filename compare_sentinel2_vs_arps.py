"""
Compare yield predictions from Sentinel-2 vs ARPS data.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns


def main():
    """Compare Sentinel-2 and ARPS yield predictions."""
    
    print("=" * 80)
    print("COMPARING SENTINEL-2 VS ARPS YIELD PREDICTIONS")
    print("=" * 80)
    
    # Load Sentinel-2 predictions
    s2_df = pd.read_csv('yield_predictions_all_80_fields_cleaned_final.csv')
    s2_df = s2_df.rename(columns={'Grain Yield (ton/ha)': 'Yield_S2'})
    
    # Load ARPS predictions
    arps_df = pd.read_csv('yield_predictions_arps_all_fields.csv')
    arps_df = arps_df.rename(columns={'Grain Yield (ton/ha)': 'Yield_ARPS'})
    
    # Merge on field name
    comparison_df = pd.merge(
        s2_df[['Field Name', 'Yield_S2']],
        arps_df[['Field Name', 'Yield_ARPS', 'Observations']],
        on='Field Name',
        how='inner'
    )
    
    print(f"\nFields with both predictions: {len(comparison_df)}")
    
    # Calculate differences
    comparison_df['Difference'] = comparison_df['Yield_ARPS'] - comparison_df['Yield_S2']
    comparison_df['Percent_Diff'] = (comparison_df['Difference'] / comparison_df['Yield_S2']) * 100
    
    # Statistics
    print("\n" + "=" * 80)
    print("COMPARISON STATISTICS")
    print("=" * 80)
    
    print(f"\nSentinel-2 (10m, ~5-day):")
    print(f"  Mean yield: {comparison_df['Yield_S2'].mean():.2f} ton/ha")
    print(f"  Std dev: {comparison_df['Yield_S2'].std():.2f} ton/ha")
    print(f"  Range: {comparison_df['Yield_S2'].min():.2f} - {comparison_df['Yield_S2'].max():.2f} ton/ha")
    
    print(f"\nARPS (3m, daily):")
    print(f"  Mean yield: {comparison_df['Yield_ARPS'].mean():.2f} ton/ha")
    print(f"  Std dev: {comparison_df['Yield_ARPS'].std():.2f} ton/ha")
    print(f"  Range: {comparison_df['Yield_ARPS'].min():.2f} - {comparison_df['Yield_ARPS'].max():.2f} ton/ha")
    print(f"  Avg observations: {comparison_df['Observations'].mean():.0f}")
    
    print(f"\nDifferences (ARPS - Sentinel-2):")
    print(f"  Mean difference: {comparison_df['Difference'].mean():.2f} ton/ha")
    print(f"  Std dev: {comparison_df['Difference'].std():.2f} ton/ha")
    print(f"  Mean % difference: {comparison_df['Percent_Diff'].mean():.1f}%")
    
    # Correlation
    correlation = comparison_df['Yield_S2'].corr(comparison_df['Yield_ARPS'])
    print(f"\nCorrelation: {correlation:.3f}")
    
    # RMSE
    rmse = np.sqrt(((comparison_df['Yield_ARPS'] - comparison_df['Yield_S2'])**2).mean())
    print(f"RMSE: {rmse:.2f} ton/ha")
    
    # Save comparison
    comparison_df = comparison_df.sort_values('Yield_S2')
    comparison_df.to_csv('yield_comparison_sentinel2_vs_arps.csv', index=False)
    print(f"\n✓ Saved detailed comparison to yield_comparison_sentinel2_vs_arps.csv")
    
    # Create comprehensive visualization
    fig = plt.figure(figsize=(20, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
    
    # 1. Scatter plot with 1:1 line
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.scatter(comparison_df['Yield_S2'], comparison_df['Yield_ARPS'], 
               alpha=0.6, s=80, c='steelblue', edgecolors='black', linewidth=0.5)
    
    # Add 1:1 line
    min_val = min(comparison_df['Yield_S2'].min(), comparison_df['Yield_ARPS'].min())
    max_val = max(comparison_df['Yield_S2'].max(), comparison_df['Yield_ARPS'].max())
    ax1.plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=2, label='1:1 line', alpha=0.7)
    
    # Add regression line
    z = np.polyfit(comparison_df['Yield_S2'], comparison_df['Yield_ARPS'], 1)
    p = np.poly1d(z)
    ax1.plot(comparison_df['Yield_S2'].sort_values(), p(comparison_df['Yield_S2'].sort_values()), 
            "g-", alpha=0.7, linewidth=2, label=f'Fit: y={z[0]:.2f}x+{z[1]:.2f}')
    
    ax1.set_xlabel('Sentinel-2 Yield (ton/ha)', fontsize=11, fontweight='bold')
    ax1.set_ylabel('ARPS Yield (ton/ha)', fontsize=11, fontweight='bold')
    ax1.set_title(f'Yield Predictions Comparison\nCorrelation: {correlation:.3f}, RMSE: {rmse:.2f}', 
                 fontsize=12, fontweight='bold')
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)
    
    # 2. Bland-Altman plot
    ax2 = fig.add_subplot(gs[0, 1])
    mean_yields = (comparison_df['Yield_S2'] + comparison_df['Yield_ARPS']) / 2
    diff_yields = comparison_df['Difference']
    
    ax2.scatter(mean_yields, diff_yields, alpha=0.6, s=80, c='purple', edgecolors='black', linewidth=0.5)
    ax2.axhline(y=0, color='r', linestyle='--', linewidth=2, alpha=0.7)
    ax2.axhline(y=diff_yields.mean(), color='g', linestyle='-', linewidth=2, alpha=0.7, 
               label=f'Mean: {diff_yields.mean():.2f}')
    ax2.axhline(y=diff_yields.mean() + 1.96*diff_yields.std(), color='orange', linestyle=':', linewidth=2, 
               label=f'+1.96 SD: {diff_yields.mean() + 1.96*diff_yields.std():.2f}')
    ax2.axhline(y=diff_yields.mean() - 1.96*diff_yields.std(), color='orange', linestyle=':', linewidth=2,
               label=f'-1.96 SD: {diff_yields.mean() - 1.96*diff_yields.std():.2f}')
    
    ax2.set_xlabel('Mean Yield (ton/ha)', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Difference (ARPS - S2)', fontsize=11, fontweight='bold')
    ax2.set_title('Bland-Altman Plot', fontsize=12, fontweight='bold')
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)
    
    # 3. Distribution comparison
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.hist(comparison_df['Yield_S2'], bins=20, alpha=0.6, label='Sentinel-2', 
            color='steelblue', edgecolor='black')
    ax3.hist(comparison_df['Yield_ARPS'], bins=20, alpha=0.6, label='ARPS', 
            color='#2ecc71', edgecolor='black')
    ax3.axvline(comparison_df['Yield_S2'].mean(), color='steelblue', linestyle='--', linewidth=2)
    ax3.axvline(comparison_df['Yield_ARPS'].mean(), color='#2ecc71', linestyle='--', linewidth=2)
    ax3.set_xlabel('Yield (ton/ha)', fontsize=11, fontweight='bold')
    ax3.set_ylabel('Frequency', fontsize=11, fontweight='bold')
    ax3.set_title('Yield Distribution', fontsize=12, fontweight='bold')
    ax3.legend(fontsize=10)
    ax3.grid(True, alpha=0.3, axis='y')
    
    # 4. Box plot comparison
    ax4 = fig.add_subplot(gs[1, 0])
    bp_data = [comparison_df['Yield_S2'], comparison_df['Yield_ARPS']]
    bp = ax4.boxplot(bp_data, labels=['Sentinel-2', 'ARPS'], patch_artist=True,
                     medianprops=dict(color='red', linewidth=2),
                     boxprops=dict(facecolor='lightblue', alpha=0.7))
    ax4.set_ylabel('Yield (ton/ha)', fontsize=11, fontweight='bold')
    ax4.set_title('Yield Distribution Comparison', fontsize=12, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='y')
    
    # 5. Difference histogram
    ax5 = fig.add_subplot(gs[1, 1])
    ax5.hist(comparison_df['Difference'], bins=25, alpha=0.7, color='coral', edgecolor='black')
    ax5.axvline(0, color='red', linestyle='--', linewidth=2, label='Zero difference')
    ax5.axvline(comparison_df['Difference'].mean(), color='green', linestyle='-', linewidth=2,
               label=f'Mean: {comparison_df["Difference"].mean():.2f}')
    ax5.set_xlabel('Difference (ARPS - S2) ton/ha', fontsize=11, fontweight='bold')
    ax5.set_ylabel('Frequency', fontsize=11, fontweight='bold')
    ax5.set_title('Yield Difference Distribution', fontsize=12, fontweight='bold')
    ax5.legend(fontsize=9)
    ax5.grid(True, alpha=0.3, axis='y')
    
    # 6. Percent difference histogram
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.hist(comparison_df['Percent_Diff'], bins=25, alpha=0.7, color='lightcoral', edgecolor='black')
    ax6.axvline(0, color='red', linestyle='--', linewidth=2, label='Zero %')
    ax6.axvline(comparison_df['Percent_Diff'].mean(), color='green', linestyle='-', linewidth=2,
               label=f'Mean: {comparison_df["Percent_Diff"].mean():.1f}%')
    ax6.set_xlabel('Percent Difference (%)', fontsize=11, fontweight='bold')
    ax6.set_ylabel('Frequency', fontsize=11, fontweight='bold')
    ax6.set_title('Percent Difference Distribution', fontsize=12, fontweight='bold')
    ax6.legend(fontsize=9)
    ax6.grid(True, alpha=0.3, axis='y')
    
    # 7. Ranked comparison plot
    ax7 = fig.add_subplot(gs[2, :])
    x = np.arange(len(comparison_df))
    width = 0.35
    
    ax7.bar(x - width/2, comparison_df['Yield_S2'], width, label='Sentinel-2', 
           alpha=0.8, color='steelblue', edgecolor='black', linewidth=0.5)
    ax7.bar(x + width/2, comparison_df['Yield_ARPS'], width, label='ARPS', 
           alpha=0.8, color='#2ecc71', edgecolor='black', linewidth=0.5)
    
    ax7.set_xlabel('Field (ordered by Sentinel-2 yield)', fontsize=11, fontweight='bold')
    ax7.set_ylabel('Yield (ton/ha)', fontsize=11, fontweight='bold')
    ax7.set_title(f'Field-by-Field Comparison - All {len(comparison_df)} Fields', 
                 fontsize=13, fontweight='bold')
    ax7.legend(fontsize=11)
    ax7.grid(True, alpha=0.3, axis='y')
    
    # Don't show x-tick labels (too many fields)
    ax7.set_xticks([])
    
    plt.suptitle('Sentinel-2 vs ARPS Yield Prediction Comparison',
                fontsize=16, fontweight='bold', y=0.995)
    
    plt.savefig('sentinel2_vs_arps_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"\n✓ Saved visualization to sentinel2_vs_arps_comparison.png")
    
    # Print top 10 largest differences
    print("\n" + "=" * 80)
    print("TOP 10 LARGEST DIFFERENCES (ARPS - Sentinel-2)")
    print("=" * 80)
    top_diff = comparison_df.nlargest(10, 'Difference')[['Field Name', 'Yield_S2', 'Yield_ARPS', 'Difference', 'Percent_Diff']]
    print(top_diff.to_string(index=False))
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()

