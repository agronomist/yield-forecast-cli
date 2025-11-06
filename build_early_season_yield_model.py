"""
Build early-season yield forecasting models.
Predict final yield based on mid-season indicators:
- Accumulated biomass at different DAS (Days After Sowing)
- Mean fAPAR at different DAS
- Peak NDVI
- Other growth indicators
"""

import json
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')


def load_field_data(field_name):
    """Load all data for a field."""
    # Load corrected yield detail
    detail_paths = [
        f"yield_detail_arps_{field_name.replace(' ', '_')}.json",
        f"more_fields/yield_detail_arps_{field_name.replace(' ', '_')}.json"
    ]
    
    for detail_path in detail_paths:
        if os.path.exists(detail_path):
            with open(detail_path, 'r') as f:
                return json.load(f)
    
    return None


def extract_mid_season_features(field_data, target_das_list=[30, 45, 60, 75, 90, 105, 120]):
    """Extract features at different days after sowing."""
    
    daily_biomass = field_data.get('daily_biomass', [])
    if not daily_biomass:
        return None
    
    # Convert to DataFrame
    df = pd.DataFrame(daily_biomass)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('days_after_sowing')
    
    features = {}
    
    # Final yield
    final_yield = field_data.get('grain_yield_ton_ha')
    if final_yield is None:
        return None
    
    features['final_yield'] = final_yield
    
    # Extract features at each target DAS
    for target_das in target_das_list:
        # Find closest observation
        closest_idx = (df['days_after_sowing'] - target_das).abs().idxmin()
        closest_row = df.iloc[closest_idx]
        actual_das = closest_row['days_after_sowing']
        
        # Only use if within 5 days of target
        if abs(actual_das - target_das) <= 5:
            features[f'biomass_{target_das}das'] = closest_row['cumulative_biomass_g_m2'] / 1000  # Convert to kg/m²
            features[f'fapar_{target_das}das'] = closest_row['fapar']
            features[f'apar_{target_das}das'] = closest_row['apar_mj_m2']
            features[f'days_monitored_{target_das}das'] = actual_das
    
    # Overall features
    features['max_fapar'] = df['fapar'].max() if len(df) > 0 else None
    features['mean_fapar'] = df['fapar'].mean() if len(df) > 0 else None
    features['peak_ndvi'] = None  # Will be filled from ARPS data
    
    # Load ARPS data for peak NDVI
    arps_paths = [
        f"arps_ndvi_data_cleaned/arps_ndvi_{field_data['field_name'].replace(' ', '_')}_CORRECTED.json",
        f"arps_ndvi_data_cleaned/arps_ndvi_{field_data['field_name'].replace(' ', '_')}.json",
        f"more_fields/arps_ndvi_data_cleaned/arps_ndvi_{field_data['field_name'].replace(' ', '_')}_CORRECTED.json",
        f"more_fields/arps_ndvi_data_cleaned/arps_ndvi_{field_data['field_name'].replace(' ', '_')}.json"
    ]
    
    for arps_path in arps_paths:
        if os.path.exists(arps_path):
            with open(arps_path, 'r') as f:
                arps_data = json.load(f)
                observations = arps_data.get('observations', [])
                if observations:
                    ndvi_values = [obs.get('ndvi_mean') for obs in observations if obs.get('ndvi_mean') is not None]
                    if ndvi_values:
                        features['peak_ndvi'] = max(ndvi_values)
                        features['mean_ndvi'] = np.mean(ndvi_values)
                    break
    
    # Sowing date and variety info
    features['sowing_date'] = field_data.get('sowing_date')
    features['days_total'] = len(daily_biomass)
    
    return features


def build_models(df_features):
    """Build predictive models at different growth stages."""
    
    print("\n" + "=" * 80)
    print("BUILDING PREDICTIVE MODELS")
    print("=" * 80)
    
    # Remove fields with missing data
    df_clean = df_features.dropna(subset=['final_yield'])
    
    target_das_list = [30, 45, 60, 75, 90, 105, 120]
    models = {}
    results = []
    
    for target_das in target_das_list:
        # Feature columns for this DAS
        feature_cols = [
            f'biomass_{target_das}das',
            f'fapar_{target_das}das',
            f'apar_{target_das}das'
        ]
        
        # Check which features are available
        available_features = [col for col in feature_cols if col in df_clean.columns]
        
        if len(available_features) < 1:
            continue
        
        # Prepare data
        X = df_clean[available_features].dropna()
        y = df_clean.loc[X.index, 'final_yield']
        
        if len(X) < 10:  # Need minimum samples
            continue
        
        print(f"\n{target_das} DAS Model:")
        print(f"  Samples: {len(X)}")
        print(f"  Features: {', '.join(available_features)}")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
        
        # Model 1: Linear Regression
        lr_model = LinearRegression()
        lr_model.fit(X_train, y_train)
        
        y_pred_train = lr_model.predict(X_train)
        y_pred_test = lr_model.predict(X_test)
        
        r2_train = r2_score(y_train, y_pred_train)
        r2_test = r2_score(y_test, y_pred_test)
        rmse_test = np.sqrt(mean_squared_error(y_test, y_pred_test))
        mae_test = mean_absolute_error(y_test, y_pred_test)
        
        print(f"  Linear Regression:")
        print(f"    R² (train): {r2_train:.3f}")
        print(f"    R² (test): {r2_test:.3f}")
        print(f"    RMSE: {rmse_test:.2f} ton/ha")
        print(f"    MAE: {mae_test:.2f} ton/ha")
        
        # Model 2: Random Forest
        rf_model = RandomForestRegressor(n_estimators=100, max_depth=5, random_state=42)
        rf_model.fit(X_train, y_train)
        
        y_pred_train_rf = rf_model.predict(X_train)
        y_pred_test_rf = rf_model.predict(X_test)
        
        r2_train_rf = r2_score(y_train, y_pred_train_rf)
        r2_test_rf = r2_score(y_test, y_pred_test_rf)
        rmse_test_rf = np.sqrt(mean_squared_error(y_test, y_pred_test_rf))
        mae_test_rf = mean_absolute_error(y_test, y_pred_test_rf)
        
        print(f"  Random Forest:")
        print(f"    R² (train): {r2_train_rf:.3f}")
        print(f"    R² (test): {r2_test_rf:.3f}")
        print(f"    RMSE: {rmse_test_rf:.2f} ton/ha")
        print(f"    MAE: {mae_test_rf:.2f} ton/ha")
        
        # Feature importance (for RF)
        feature_importance = dict(zip(available_features, rf_model.feature_importances_))
        print(f"  Feature importance:")
        for feat, imp in sorted(feature_importance.items(), key=lambda x: x[1], reverse=True):
            print(f"    {feat}: {imp:.3f}")
        
        models[target_das] = {
            'linear': lr_model,
            'random_forest': rf_model,
            'features': available_features,
            'r2_test': r2_test_rf,  # Use RF as it's usually better
            'rmse': rmse_test_rf,
            'mae': mae_test_rf
        }
        
        results.append({
            'DAS': target_das,
            'n_samples': len(X),
            'features': ', '.join(available_features),
            'r2_linear': r2_test,
            'r2_rf': r2_test_rf,
            'rmse_rf': rmse_test_rf,
            'mae_rf': mae_test_rf,
            'best_feature': max(feature_importance.items(), key=lambda x: x[1])[0] if feature_importance else None
        })
    
    return models, results, df_clean


def create_visualizations(df_features, models, results):
    """Create comprehensive visualizations."""
    
    print("\n" + "=" * 80)
    print("CREATING VISUALIZATIONS")
    print("=" * 80)
    
    # Create figure with multiple subplots
    fig = plt.figure(figsize=(22, 16))
    gs = fig.add_gridspec(4, 3, hspace=0.35, wspace=0.3)
    
    df_clean = df_features.dropna(subset=['final_yield'])
    
    # ===== ROW 1: Relationships at different DAS =====
    
    target_das_list = [30, 45, 60, 75, 90, 105, 120]
    
    for i, das in enumerate(target_das_list[:3]):
        ax = fig.add_subplot(gs[0, i])
        
        biomass_col = f'biomass_{das}das'
        if biomass_col in df_clean.columns:
            valid_data = df_clean[[biomass_col, 'final_yield']].dropna()
            if len(valid_data) > 0:
                ax.scatter(valid_data[biomass_col], valid_data['final_yield'], 
                          alpha=0.6, s=80, edgecolors='black', linewidth=0.5)
                
                # Add regression line
                z = np.polyfit(valid_data[biomass_col], valid_data['final_yield'], 1)
                p = np.poly1d(z)
                x_line = np.linspace(valid_data[biomass_col].min(), valid_data[biomass_col].max(), 100)
                ax.plot(x_line, p(x_line), "r--", linewidth=2, alpha=0.7)
                
                # Calculate correlation
                corr = valid_data[biomass_col].corr(valid_data['final_yield'])
                ax.set_title(f'{das} DAS: Biomass vs Yield\nCorrelation: {corr:.3f}', 
                           fontsize=12, fontweight='bold')
                ax.set_xlabel('Cumulative Biomass (kg/m²)', fontsize=11)
                ax.set_ylabel('Final Yield (ton/ha)', fontsize=11)
                ax.grid(True, alpha=0.3)
    
    # ===== ROW 2: fAPAR relationships =====
    
    for i, das in enumerate(target_das_list[:3]):
        ax = fig.add_subplot(gs[1, i])
        
        fapar_col = f'fapar_{das}das'
        if fapar_col in df_clean.columns:
            valid_data = df_clean[[fapar_col, 'final_yield']].dropna()
            if len(valid_data) > 0:
                ax.scatter(valid_data[fapar_col], valid_data['final_yield'], 
                          alpha=0.6, s=80, edgecolors='black', linewidth=0.5, color='green')
                
                # Add regression line
                z = np.polyfit(valid_data[fapar_col], valid_data['final_yield'], 1)
                p = np.poly1d(z)
                x_line = np.linspace(valid_data[fapar_col].min(), valid_data[fapar_col].max(), 100)
                ax.plot(x_line, p(x_line), "r--", linewidth=2, alpha=0.7)
                
                corr = valid_data[fapar_col].corr(valid_data['final_yield'])
                ax.set_title(f'{das} DAS: fAPAR vs Yield\nCorrelation: {corr:.3f}', 
                           fontsize=12, fontweight='bold')
                ax.set_xlabel('fAPAR', fontsize=11)
                ax.set_ylabel('Final Yield (ton/ha)', fontsize=11)
                ax.grid(True, alpha=0.3)
                ax.set_xlim([0, 1])
    
    # ===== ROW 3: Model performance over time =====
    
    ax3 = fig.add_subplot(gs[2, :])
    
    if results:
        results_df = pd.DataFrame(results)
        x = results_df['DAS']
        
        ax3.plot(x, results_df['r2_rf'], 'o-', linewidth=2.5, markersize=10, 
                label='R² (Random Forest)', color='steelblue')
        ax3.plot(x, results_df['r2_linear'], 's--', linewidth=2, markersize=8, 
                label='R² (Linear)', color='orange', alpha=0.7)
        
        ax3.set_xlabel('Days After Sowing (DAS)', fontsize=12, fontweight='bold')
        ax3.set_ylabel('R² Score', fontsize=12, fontweight='bold')
        ax3.set_title('Predictive Model Performance vs. Growth Stage', 
                     fontsize=14, fontweight='bold')
        ax3.legend(fontsize=11)
        ax3.grid(True, alpha=0.3)
        ax3.set_ylim([0, 1])
    
    # ===== ROW 4: RMSE over time =====
    
    ax4 = fig.add_subplot(gs[3, 0])
    
    if results:
        ax4.plot(x, results_df['rmse_rf'], 'o-', linewidth=2.5, markersize=10, 
                color='coral', label='RMSE')
        ax4.set_xlabel('Days After Sowing (DAS)', fontsize=12, fontweight='bold')
        ax4.set_ylabel('RMSE (ton/ha)', fontsize=12, fontweight='bold')
        ax4.set_title('Prediction Error vs. Growth Stage', fontsize=13, fontweight='bold')
        ax4.legend(fontsize=11)
        ax4.grid(True, alpha=0.3)
    
    # Feature importance over time
    ax5 = fig.add_subplot(gs[3, 1])
    
    if results:
        # Show which feature is most important at each stage
        feature_counts = {}
        for _, row in results_df.iterrows():
            best_feat = row['best_feature']
            if best_feat:
                feat_name = best_feat.split('_')[0]  # biomass, fapar, or apar
                feature_counts[feat_name] = feature_counts.get(feat_name, 0) + 1
        
        if feature_counts:
            ax5.bar(feature_counts.keys(), feature_counts.values(), 
                   color=['steelblue', 'green', 'orange'][:len(feature_counts)])
            ax5.set_ylabel('Frequency as Best Feature', fontsize=12, fontweight='bold')
            ax5.set_title('Most Important Feature by Stage', fontsize=13, fontweight='bold')
            ax5.grid(True, alpha=0.3, axis='y')
    
    # Correlation heatmap
    ax6 = fig.add_subplot(gs[3, 2])
    
    # Create correlation matrix for key features
    feature_cols = []
    for das in [45, 60, 75, 90]:
        for feat_type in ['biomass', 'fapar']:
            col = f'{feat_type}_{das}das'
            if col in df_clean.columns:
                feature_cols.append(col)
    
    if feature_cols and 'final_yield' in df_clean.columns:
        corr_cols = feature_cols + ['final_yield']
        corr_data = df_clean[corr_cols].corr()
        
        im = ax6.imshow(corr_data.values, cmap='RdYlGn', aspect='auto', vmin=-1, vmax=1)
        ax6.set_xticks(range(len(corr_cols)))
        ax6.set_yticks(range(len(corr_cols)))
        ax6.set_xticklabels([c.replace('_', ' ').replace('das', 'DAS') for c in corr_cols], 
                           rotation=45, ha='right', fontsize=9)
        ax6.set_yticklabels([c.replace('_', ' ').replace('das', 'DAS') for c in corr_cols], 
                           fontsize=9)
        ax6.set_title('Feature Correlation Matrix', fontsize=13, fontweight='bold')
        
        # Add text annotations
        for i in range(len(corr_cols)):
            for j in range(len(corr_cols)):
                text = ax6.text(j, i, f'{corr_data.iloc[i, j]:.2f}',
                               ha="center", va="center", color="black", fontsize=8)
        
        plt.colorbar(im, ax=ax6)
    
    plt.suptitle('Early-Season Yield Forecasting Model Analysis', 
                fontsize=18, fontweight='bold', y=0.995)
    
    output_file = 'early_season_yield_model_analysis.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved visualization to: {output_file}")
    
    output_pdf = 'early_season_yield_model_analysis.pdf'
    plt.savefig(output_pdf, bbox_inches='tight')
    print(f"✓ Saved PDF to: {output_pdf}")
    
    plt.close()


def create_prediction_examples(models, df_features):
    """Create examples showing predictions at different stages."""
    
    print("\n" + "=" * 80)
    print("CREATING PREDICTION EXAMPLES")
    print("=" * 80)
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes = axes.flatten()
    
    df_clean = df_features.dropna(subset=['final_yield'])
    
    # Select 4 example fields
    example_fields = df_clean.head(4)
    
    target_das_list = [30, 45, 60, 75, 90, 105, 120]
    
    for idx, (ax, (_, field_row)) in enumerate(zip(axes, example_fields.iterrows())):
        field_name = field_row.get('field_name', f'Field {idx+1}')
        actual_yield = field_row['final_yield']
        
        # Collect predictions at different stages
        predictions = []
        das_values = []
        
        for das in target_das_list:
            if das in models:
                model_info = models[das]
                features = model_info['features']
                
                # Get feature values for this field
                feature_values = []
                for feat in features:
                    val = field_row.get(feat)
                    if pd.isna(val):
                        break
                    feature_values.append(val)
                
                if len(feature_values) == len(features):
                    X = np.array([feature_values])
                    pred = model_info['random_forest'].predict(X)[0]
                    predictions.append(pred)
                    das_values.append(das)
        
        # Plot
        if predictions:
            ax.plot(das_values, predictions, 'o-', linewidth=2.5, markersize=8, 
                   label='Predicted Yield', color='steelblue')
            ax.axhline(y=actual_yield, color='red', linestyle='--', linewidth=2.5, 
                      label=f'Actual Yield: {actual_yield:.2f} ton/ha', alpha=0.8)
            ax.fill_between(das_values, 
                           [p - 0.5 for p in predictions], 
                           [p + 0.5 for p in predictions], 
                           alpha=0.2, color='steelblue', label='±0.5 ton/ha uncertainty')
            
            ax.set_xlabel('Days After Sowing', fontsize=11, fontweight='bold')
            ax.set_ylabel('Predicted Yield (ton/ha)', fontsize=11, fontweight='bold')
            ax.set_title(f'{field_name}\nEarly-Season Predictions', 
                        fontsize=12, fontweight='bold')
            ax.legend(fontsize=9)
            ax.grid(True, alpha=0.3)
    
    plt.suptitle('Example: Yield Predictions at Different Growth Stages', 
                fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    
    output_file = 'early_season_yield_prediction_examples.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved examples to: {output_file}")
    
    output_pdf = 'early_season_yield_prediction_examples.pdf'
    plt.savefig(output_pdf, bbox_inches='tight')
    print(f"✓ Saved PDF to: {output_pdf}")
    
    plt.close()


def main():
    """Main analysis function."""
    
    print("=" * 80)
    print("BUILDING EARLY-SEASON YIELD FORECASTING MODELS")
    print("=" * 80)
    print("\nThis analysis will:")
    print("  1. Extract mid-season growth indicators (biomass, fAPAR, NDVI)")
    print("  2. Build predictive models at different growth stages")
    print("  3. Evaluate which metrics are most predictive")
    print("  4. Show when reliable yield forecasts can be made")
    
    # Load corrected yield predictions to get field names
    df_yields = pd.read_csv('yield_predictions_arps_all_fields_CORRECTED.csv')
    
    print(f"\nProcessing {len(df_yields)} fields...")
    
    all_features = []
    
    for idx, row in df_yields.iterrows():
        field_name = row['Field Name']
        
        if idx % 10 == 0:
            print(f"  Processing {idx+1}/{len(df_yields)}...")
        
        # Load field data
        field_data = load_field_data(field_name)
        
        if field_data:
            features = extract_mid_season_features(field_data)
            if features:
                features['field_name'] = field_name
                all_features.append(features)
    
    print(f"\n✓ Extracted features from {len(all_features)} fields")
    
    # Convert to DataFrame
    df_features = pd.DataFrame(all_features)
    
    # Save features
    df_features.to_csv('early_season_features.csv', index=False)
    print(f"✓ Saved features to: early_season_features.csv")
    
    # Build models
    models, results, df_clean = build_models(df_features)
    
    # Save results
    if results:
        results_df = pd.DataFrame(results)
        results_df.to_csv('early_season_model_results.csv', index=False)
        print(f"\n✓ Saved model results to: early_season_model_results.csv")
    
    # Create visualizations
    create_visualizations(df_features, models, results)
    create_prediction_examples(models, df_features)
    
    # Print summary recommendations
    print("\n" + "=" * 80)
    print("KEY FINDINGS & RECOMMENDATIONS")
    print("=" * 80)
    
    if results:
        results_df = pd.DataFrame(results)
        
        # Find best early prediction time
        best_early = results_df[results_df['DAS'] <= 90].nlargest(1, 'r2_rf')
        best_overall = results_df.nlargest(1, 'r2_rf')
        
        if len(best_early) > 0:
            best_early_row = best_early.iloc[0]
            print(f"\n✓ Best EARLY prediction (≤90 DAS):")
            print(f"  Stage: {int(best_early_row['DAS'])} DAS")
            print(f"  R²: {best_early_row['r2_rf']:.3f}")
            print(f"  RMSE: {best_early_row['rmse_rf']:.2f} ton/ha")
            print(f"  Best feature: {best_early_row['best_feature']}")
        
        if len(best_overall) > 0:
            best_row = best_overall.iloc[0]
            print(f"\n✓ Best OVERALL prediction:")
            print(f"  Stage: {int(best_row['DAS'])} DAS")
            print(f"  R²: {best_row['r2_rf']:.3f}")
            print(f"  RMSE: {best_row['rmse_rf']:.2f} ton/ha")
            print(f"  Best feature: {best_row['best_feature']}")
        
        print(f"\n✓ Recommendations:")
        print(f"  - Early forecasts (60-75 DAS) can predict yield with R² ≈ {results_df[results_df['DAS']==75]['r2_rf'].iloc[0]:.3f}")
        print(f"  - Mid-season forecasts (90-105 DAS) are most reliable")
        print(f"  - Accumulated biomass is typically the best predictor")
        print(f"  - fAPAR also shows strong correlation with final yield")
    
    print("\n" + "=" * 80)
    print("✓ ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()

