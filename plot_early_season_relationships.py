"""
Create comprehensive plots showing relationships between mid-season indicators
and final yield predictions.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

def create_relationship_plots():
    """Create plots showing relationships between indicators and yield."""
    
    print("=" * 80)
    print("CREATING EARLY-SEASON RELATIONSHIP PLOTS")
    print("=" * 80)
    
    # Load features
    df = pd.read_csv('early_season_features.csv')
    
    print(f"\nLoaded data for {len(df)} fields")
    
    # Remove missing values
    df_clean = df.dropna(subset=['final_yield'])
    
    # Create comprehensive figure
    fig = plt.figure(figsize=(20, 14))
    gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3)
    
    target_das_list = [60, 75, 90, 105, 120]
    
    # ===== ROW 1: Biomass vs Yield at different stages =====
    
    for i, das in enumerate(target_das_list):
        ax = fig.add_subplot(gs[0, i] if i < 3 else gs[1, i-3])
        
        biomass_col = f'biomass_{das}das'
        
        if biomass_col in df_clean.columns:
            valid_data = df_clean[[biomass_col, 'final_yield']].dropna()
            
            if len(valid_data) > 5:
                # Scatter plot
                ax.scatter(valid_data[biomass_col], valid_data['final_yield'], 
                          alpha=0.6, s=100, edgecolors='black', linewidth=0.8,
                          color='steelblue', zorder=3)
                
                # Add regression line
                X = valid_data[[biomass_col]]
                y = valid_data['final_yield']
                model = LinearRegression()
                model.fit(X, y)
                y_pred = model.predict(X)
                
                # Sort for plotting
                sorted_idx = np.argsort(valid_data[biomass_col])
                x_sorted = valid_data[biomass_col].iloc[sorted_idx]
                y_pred_sorted = y_pred[sorted_idx]
                
                ax.plot(x_sorted, y_pred_sorted, "r-", linewidth=2.5, 
                       alpha=0.8, label='Linear fit', zorder=2)
                
                # Calculate statistics
                r2 = r2_score(y, y_pred)
                corr = valid_data[biomass_col].corr(valid_data['final_yield'])
                slope = model.coef_[0]
                intercept = model.intercept_
                
                # Add statistics text
                stats_text = f'R² = {r2:.3f}\nCorr = {corr:.3f}\nSlope = {slope:.2f}'
                ax.text(0.05, 0.95, stats_text, transform=ax.transAxes,
                       fontsize=10, verticalalignment='top',
                       bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
                
                ax.set_xlabel('Cumulative Biomass (kg/m²)', fontsize=11, fontweight='bold')
                ax.set_ylabel('Final Yield (ton/ha)', fontsize=11, fontweight='bold')
                ax.set_title(f'{das} DAS: Biomass vs Yield', fontsize=12, fontweight='bold')
                ax.grid(True, alpha=0.3, zorder=1)
                ax.legend(fontsize=9, loc='lower right')
    
    # ===== ROW 2: fAPAR vs Yield at different stages =====
    
    for i, das in enumerate(target_das_list):
        row = 1 if i < 3 else 2
        col = i if i < 3 else i - 3
        
        ax = fig.add_subplot(gs[row, col])
        
        fapar_col = f'fapar_{das}das'
        
        if fapar_col in df_clean.columns:
            valid_data = df_clean[[fapar_col, 'final_yield']].dropna()
            
            if len(valid_data) > 5:
                # Scatter plot
                ax.scatter(valid_data[fapar_col], valid_data['final_yield'], 
                          alpha=0.6, s=100, edgecolors='black', linewidth=0.8,
                          color='#2ecc71', zorder=3)
                
                # Add regression line
                X = valid_data[[fapar_col]]
                y = valid_data['final_yield']
                model = LinearRegression()
                model.fit(X, y)
                y_pred = model.predict(X)
                
                sorted_idx = np.argsort(valid_data[fapar_col])
                x_sorted = valid_data[fapar_col].iloc[sorted_idx]
                y_pred_sorted = y_pred[sorted_idx]
                
                ax.plot(x_sorted, y_pred_sorted, "r-", linewidth=2.5, 
                       alpha=0.8, label='Linear fit', zorder=2)
                
                # Calculate statistics
                r2 = r2_score(y, y_pred)
                corr = valid_data[fapar_col].corr(valid_data['final_yield'])
                slope = model.coef_[0]
                
                # Add statistics text
                stats_text = f'R² = {r2:.3f}\nCorr = {corr:.3f}\nSlope = {slope:.2f}'
                ax.text(0.05, 0.95, stats_text, transform=ax.transAxes,
                       fontsize=10, verticalalignment='top',
                       bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
                
                ax.set_xlabel('fAPAR', fontsize=11, fontweight='bold')
                ax.set_ylabel('Final Yield (ton/ha)', fontsize=11, fontweight='bold')
                ax.set_title(f'{das} DAS: fAPAR vs Yield', fontsize=12, fontweight='bold')
                ax.grid(True, alpha=0.3, zorder=1)
                ax.set_xlim([0, 1])
                ax.legend(fontsize=9, loc='lower right')
    
    plt.suptitle('Mid-Season Indicators vs Final Yield - All Growth Stages', 
                fontsize=18, fontweight='bold', y=0.995)
    
    output_file = 'early_season_relationships_all_stages.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Saved plot to: {output_file}")
    
    output_pdf = 'early_season_relationships_all_stages.pdf'
    plt.savefig(output_pdf, bbox_inches='tight')
    print(f"✓ Saved PDF to: {output_pdf}")
    
    plt.close()
    
    # Create a second figure focusing on best predictors
    create_best_predictors_plot(df_clean)
    
    # Create prediction accuracy over time plot
    create_prediction_accuracy_plot()


def create_best_predictors_plot(df_clean):
    """Create focused plot on best predictors."""
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Biomass at 105 DAS (best overall)
    ax1 = axes[0, 0]
    biomass_col = 'biomass_105das'
    if biomass_col in df_clean.columns:
        valid_data = df_clean[[biomass_col, 'final_yield']].dropna()
        if len(valid_data) > 5:
            ax1.scatter(valid_data[biomass_col], valid_data['final_yield'], 
                       alpha=0.7, s=120, edgecolors='black', linewidth=0.8,
                       color='steelblue', zorder=3)
            
            # Regression
            X = valid_data[[biomass_col]]
            y = valid_data['final_yield']
            model = LinearRegression()
            model.fit(X, y)
            y_pred = model.predict(X)
            
            sorted_idx = np.argsort(valid_data[biomass_col])
            x_line = valid_data[biomass_col].iloc[sorted_idx]
            y_line = y_pred[sorted_idx]
            
            ax1.plot(x_line, y_line, "r-", linewidth=3, alpha=0.8, zorder=2)
            
            r2 = r2_score(y, y_pred)
            corr = valid_data[biomass_col].corr(valid_data['final_yield'])
            
            ax1.set_xlabel('Cumulative Biomass at 105 DAS (kg/m²)', fontsize=12, fontweight='bold')
            ax1.set_ylabel('Final Yield (ton/ha)', fontsize=12, fontweight='bold')
            ax1.set_title(f'Best Predictor: Biomass at 105 DAS\nR² = {r2:.3f}, Correlation = {corr:.3f}', 
                         fontsize=13, fontweight='bold')
            ax1.grid(True, alpha=0.3)
            
            # Add prediction zones
            x_min, x_max = ax1.get_xlim()
            y_min, y_max = ax1.get_ylim()
            
            # Low yield zone
            ax1.axhspan(y_min, 4.5, alpha=0.1, color='red', label='Low yield zone')
            # Medium yield zone
            ax1.axhspan(4.5, 6.0, alpha=0.1, color='yellow', label='Medium yield zone')
            # High yield zone
            ax1.axhspan(6.0, y_max, alpha=0.1, color='green', label='High yield zone')
            
            ax1.legend(fontsize=9, loc='lower right')
    
    # 2. fAPAR at 75 DAS (best early predictor)
    ax2 = axes[0, 1]
    fapar_col = 'fapar_75das'
    if fapar_col in df_clean.columns:
        valid_data = df_clean[[fapar_col, 'final_yield']].dropna()
        if len(valid_data) > 5:
            ax2.scatter(valid_data[fapar_col], valid_data['final_yield'], 
                       alpha=0.7, s=120, edgecolors='black', linewidth=0.8,
                       color='#2ecc71', zorder=3)
            
            X = valid_data[[fapar_col]]
            y = valid_data['final_yield']
            model = LinearRegression()
            model.fit(X, y)
            y_pred = model.predict(X)
            
            sorted_idx = np.argsort(valid_data[fapar_col])
            x_line = valid_data[fapar_col].iloc[sorted_idx]
            y_line = y_pred[sorted_idx]
            
            ax2.plot(x_line, y_line, "r-", linewidth=3, alpha=0.8, zorder=2)
            
            r2 = r2_score(y, y_pred)
            corr = valid_data[fapar_col].corr(valid_data['final_yield'])
            
            ax2.set_xlabel('fAPAR at 75 DAS', fontsize=12, fontweight='bold')
            ax2.set_ylabel('Final Yield (ton/ha)', fontsize=12, fontweight='bold')
            ax2.set_title(f'Best Early Predictor: fAPAR at 75 DAS\nR² = {r2:.3f}, Correlation = {corr:.3f}', 
                         fontsize=13, fontweight='bold')
            ax2.grid(True, alpha=0.3)
            ax2.set_xlim([0, 1])
            
            # Add prediction zones
            y_min, y_max = ax2.get_ylim()
            ax2.axhspan(y_min, 4.5, alpha=0.1, color='red')
            ax2.axhspan(4.5, 6.0, alpha=0.1, color='yellow')
            ax2.axhspan(6.0, y_max, alpha=0.1, color='green')
    
    # 3. Combined view: Biomass progression
    ax3 = axes[1, 0]
    
    # Show biomass at multiple stages
    das_list = [60, 75, 90, 105, 120]
    colors = plt.cm.viridis(np.linspace(0, 1, len(das_list)))
    
    for das, color in zip(das_list, colors):
        biomass_col = f'biomass_{das}das'
        if biomass_col in df_clean.columns:
            valid_data = df_clean[[biomass_col, 'final_yield']].dropna()
            if len(valid_data) > 5:
                # Calculate correlation
                corr = valid_data[biomass_col].corr(valid_data['final_yield'])
                ax3.scatter([das], [corr], s=200, color=color, 
                          edgecolors='black', linewidth=1.5, zorder=3,
                          label=f'{das} DAS (r={corr:.3f})')
    
    ax3.plot([60, 75, 90, 105, 120], 
             [df_clean[f'biomass_{d}das'].corr(df_clean['final_yield']) 
              for d in [60, 75, 90, 105, 120] 
              if f'biomass_{d}das' in df_clean.columns],
             'o-', linewidth=2.5, markersize=10, color='steelblue', zorder=2)
    
    ax3.set_xlabel('Days After Sowing', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Correlation with Final Yield', fontsize=12, fontweight='bold')
    ax3.set_title('Biomass Correlation vs Growth Stage', fontsize=13, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.set_ylim([0, 1])
    ax3.legend(fontsize=9, loc='lower right')
    
    # 4. Combined view: fAPAR progression
    ax4 = axes[1, 1]
    
    ax4.plot([60, 75, 90, 105, 120], 
             [df_clean[f'fapar_{d}das'].corr(df_clean['final_yield']) 
              for d in [60, 75, 90, 105, 120] 
              if f'fapar_{d}das' in df_clean.columns],
             'o-', linewidth=2.5, markersize=10, color='#2ecc71', zorder=2)
    
    for das, color in zip(das_list, colors):
        fapar_col = f'fapar_{das}das'
        if fapar_col in df_clean.columns:
            valid_data = df_clean[[fapar_col, 'final_yield']].dropna()
            if len(valid_data) > 5:
                corr = valid_data[fapar_col].corr(valid_data['final_yield'])
                ax4.scatter([das], [corr], s=200, color=color, 
                          edgecolors='black', linewidth=1.5, zorder=3)
    
    ax4.set_xlabel('Days After Sowing', fontsize=12, fontweight='bold')
    ax4.set_ylabel('Correlation with Final Yield', fontsize=12, fontweight='bold')
    ax4.set_title('fAPAR Correlation vs Growth Stage', fontsize=13, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    ax4.set_ylim([0, 1])
    
    plt.suptitle('Best Predictors: Biomass & fAPAR Relationships', 
                fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    
    output_file = 'early_season_best_predictors.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved plot to: {output_file}")
    
    output_pdf = 'early_season_best_predictors.pdf'
    plt.savefig(output_pdf, bbox_inches='tight')
    print(f"✓ Saved PDF to: {output_pdf}")
    
    plt.close()


def create_prediction_accuracy_plot():
    """Create plot showing prediction accuracy over time."""
    
    # Load model results
    results_df = pd.read_csv('early_season_model_results.csv')
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. R² over time
    ax1 = axes[0, 0]
    ax1.plot(results_df['DAS'], results_df['r2_rf'], 'o-', linewidth=3, 
            markersize=12, color='steelblue', label='Random Forest', zorder=3)
    ax1.plot(results_df['DAS'], results_df['r2_linear'], 's--', linewidth=2.5, 
            markersize=10, color='orange', label='Linear Regression', alpha=0.8, zorder=2)
    
    ax1.axhline(y=0.7, color='green', linestyle=':', linewidth=2, 
               label='Good (R²=0.7)', alpha=0.7)
    ax1.axhline(y=0.5, color='yellow', linestyle=':', linewidth=2, 
               label='Moderate (R²=0.5)', alpha=0.7)
    
    ax1.set_xlabel('Days After Sowing', fontsize=12, fontweight='bold')
    ax1.set_ylabel('R² Score', fontsize=12, fontweight='bold')
    ax1.set_title('Model Predictive Power vs Growth Stage', fontsize=13, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim([0, 1])
    
    # 2. RMSE over time
    ax2 = axes[0, 1]
    ax2.plot(results_df['DAS'], results_df['rmse_rf'], 'o-', linewidth=3, 
            markersize=12, color='coral', label='Random Forest', zorder=3)
    ax2.plot(results_df['DAS'], results_df['mae_rf'], 's--', linewidth=2.5, 
            markersize=10, color='purple', label='Mean Absolute Error', alpha=0.8, zorder=2)
    
    ax2.set_xlabel('Days After Sowing', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Error (ton/ha)', fontsize=12, fontweight='bold')
    ax2.set_title('Prediction Error vs Growth Stage', fontsize=13, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    # 3. Feature importance over time
    ax3 = axes[1, 0]
    
    # Extract feature importance
    feature_importance_data = []
    for _, row in results_df.iterrows():
        das = row['DAS']
        features_str = row['features']
        best_feat = row['best_feature']
        
        if features_str:
            features = [f.strip() for f in features_str.split(',')]
            for feat in features:
                feat_type = feat.split('_')[0]  # biomass, fapar, or apar
                is_best = (feat == best_feat)
                feature_importance_data.append({
                    'DAS': das,
                    'feature_type': feat_type,
                    'is_best': is_best
                })
    
    if feature_importance_data:
        feat_df = pd.DataFrame(feature_importance_data)
        
        # Count best features by type
        best_by_type = feat_df[feat_df['is_best']].groupby(['DAS', 'feature_type']).size().unstack(fill_value=0)
        
        if 'biomass' in best_by_type.columns:
            ax3.plot(best_by_type.index, best_by_type['biomass'], 'o-', 
                    linewidth=2.5, markersize=10, color='steelblue', label='Biomass')
        if 'fapar' in best_by_type.columns:
            ax3.plot(best_by_type.index, best_by_type['fapar'], 's-', 
                    linewidth=2.5, markersize=10, color='#2ecc71', label='fAPAR')
        if 'apar' in best_by_type.columns:
            ax3.plot(best_by_type.index, best_by_type['apar'], '^-', 
                    linewidth=2.5, markersize=10, color='orange', label='A PAR')
        
        ax3.set_xlabel('Days After Sowing', fontsize=12, fontweight='bold')
        ax3.set_ylabel('Times Selected as Best Feature', fontsize=12, fontweight='bold')
        ax3.set_title('Most Important Feature by Growth Stage', fontsize=13, fontweight='bold')
        ax3.legend(fontsize=10)
        ax3.grid(True, alpha=0.3)
    
    # 4. Combined performance metric
    ax4 = axes[1, 1]
    
    # Calculate a combined score (R² / RMSE normalized)
    results_df['combined_score'] = results_df['r2_rf'] / (results_df['rmse_rf'] / results_df['rmse_rf'].max())
    
    ax4.plot(results_df['DAS'], results_df['combined_score'], 'o-', 
            linewidth=3, markersize=12, color='purple', zorder=3)
    
    # Highlight best stage
    best_idx = results_df['combined_score'].idxmax()
    best_das = results_df.loc[best_idx, 'DAS']
    best_score = results_df.loc[best_idx, 'combined_score']
    
    ax4.scatter([best_das], [best_score], s=300, color='red', 
               marker='*', zorder=4, edgecolors='black', linewidth=2,
               label=f'Best: {int(best_das)} DAS')
    
    ax4.set_xlabel('Days After Sowing', fontsize=12, fontweight='bold')
    ax4.set_ylabel('Combined Performance Score', fontsize=12, fontweight='bold')
    ax4.set_title('Overall Model Performance vs Growth Stage', fontsize=13, fontweight='bold')
    ax4.legend(fontsize=10)
    ax4.grid(True, alpha=0.3)
    
    plt.suptitle('Early-Season Yield Forecasting: Model Performance Analysis', 
                fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    
    output_file = 'early_season_prediction_accuracy.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved plot to: {output_file}")
    
    output_pdf = 'early_season_prediction_accuracy.pdf'
    plt.savefig(output_pdf, bbox_inches='tight')
    print(f"✓ Saved PDF to: {output_pdf}")
    
    plt.close()


def main():
    """Main function."""
    try:
        create_relationship_plots()
        
        print("\n" + "=" * 80)
        print("✓ ALL RELATIONSHIP PLOTS CREATED")
        print("=" * 80)
        print("\nGenerated files:")
        print("  1. early_season_relationships_all_stages.png - All growth stages")
        print("  2. early_season_best_predictors.png - Focused on best predictors")
        print("  3. early_season_prediction_accuracy.png - Model performance over time")
        print("\nAll plots also saved as high-quality PDFs")
        
    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        print("Please ensure early_season_features.csv exists")
        print("Run build_early_season_yield_model.py first")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

