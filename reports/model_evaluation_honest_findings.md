# Honest ML Evaluation & Data Auditing

This report documents the rigorous, scientifically defensible evaluation of the predictive machine learning models in the eRTMAC platform. Through deep diagnostics and out-of-fold cross-validation, we identified catastrophic data leakages in initial approaches and established the true, empirically supported operational boundaries of predictive ML on these open-source datasets.

---

## 1. Predicting Rate of Penetration (USROP Dataset)

### Headline Finding
When forced to generalize across geographically diverse drilling operations, **LightGBM achieves a baseline global R² of 0.20, but critically returns a negative R² on 5 out of 7 held-out wells.** 

This establishes that pure surface telemetry (Torque, WOB, RPM) lacks the physical mapping required to predict ROP across entirely different geological formations without explicit rock-hardness or lithology data.

### The 0.97 R² Illusion & Leakage Audit
Initial evaluations reported an R² of 0.97. However, our diagnostic audit identified catastrophic spatial leakage caused by:
1. **Random Row Splitting:** Allowing adjacent rows from the same well to appear in both training and testing sets.
2. **Absolute Depth Leakage:** The inclusion of `Measured Depth` and `Hole Depth (TVD)`.

When we shifted to a strict **GroupKFold split on Well ID** (evaluating on entirely unseen wells) and dropped the depth columns, the R² collapsed from 0.97 to 0.20.

### Per-Fold Performance (GroupKFold on LightGBM)
The global average R² of 0.20 heavily masks the variance caused by missing lithology data. The model generalized excellently on one specific shallow well, but completely failed on the majority of the dataset:

| Fold / Held-Out Well | Well MD Range (m) | Mean ROP (m/h) | Out-of-Well R² |
| :--- | :--- | :--- | :--- |
| **Fold 7 (15/9-F-7)** | 301.2 - 633.5 | 55.27 | **+0.8504** |
| **Fold 4 (15/9-F-5)** | 2828.2 - 3792.2 | 26.48 | **+0.0219** |
| **Fold 6 (15/9-F-9)** | 225.2 - 633.5 | 47.90 | **-0.2014** |
| **Fold 3 (15/9-F-14)** | 987.9 - 3466.0 | 24.57 | **-0.2445** |
| **Fold 1 (15/9-F-15)** | 1306.5 - 4065.3 | 21.58 | **-0.5887** |
| **Fold 2 (15/9-F-15S)**| 1400.5 - 4090.0 | 17.33 | **-0.5349** |
| **Fold 5 (15/9-F-9 A)**| 491.0 - 1206.0 | 39.10 | **-0.5440** |

*Note: A diagnostic experiment engineering purely depth-independent relative features (e.g., rolling deltas and Torque/WOB ratios) decreased the global R² to 0.155 and worsened the negative fold count to 6 of 7. This confirms the ceiling is an immovable data limitation (missing rock mechanics), not a feature engineering gap.*

### SHAP Analysis
Without the "cheat code" of depth, SHAP (`shap.TreeExplainer`) confirms the model heavily relies on mechanically logical but geographically rigid features:
1. Average Hookload (5.50)
2. Mud Flow In (3.45)
3. Average Surface Torque (3.21)

`USROP Gamma gAPI`, our only rock-type proxy, ranked 8th out of 9 (0.56 importance). Gamma-ray is sufficient to distinguish sand from shale, but insufficient to proxy Unconfined Compressive Strength (UCS), sealing the generalization ceiling.

---

## 2. Predicting Mud-Loss Events (Volve Dataset)

### Headline Finding
By reframing the problem from Supervised Classification to Unsupervised Anomaly Detection, **our Isolation Forest model (fixed at a 2% false-alarm threshold) successfully detects 1 out of the 3 true catastrophic mud-loss events across all 5 random-seed CV validation splits**, while traditional supervised baselines caught 0/3.

### The Class-Imbalance Wall
The Volve Mud-Loss dataset contains an extreme class imbalance: ~1,305 "normal" rows against only 3 verified mud-loss event rows.
When evaluated rigorously using Stratified 5-Fold Cross Validation on held-out events, tree-based supervised classifiers (XGBoost/LightGBM) hit a mathematical wall. Lacking enough positive examples to carve a generalizable boundary, they defaulted to predicting the majority class ("Normal") across the board, catching **0 out of 3 events** (Recall = 0%).

### The Anomaly Detection Solution
We pivoted to an `IsolationForest` pipeline that completely bypassed the lack of event data by training purely on the envelope of "normal" operational telemetry. We locked the anomaly threshold (`contamination`) a-priori at exactly 2.0%. 

**Seed Robustness Check:**
To ensure the catch rate was not a statistical fluke of a lucky 5-Fold split, we executed the Out-Of-Fold CV across 5 distinct random seeds (`0, 1, 42, 123, 2024`). The outcome was completely deterministic:
* **Median Catch Rate:** 1 out of 3 events caught.
* **Range:** 1-1 out of 3 events caught across all 5 seeds.

### Honest Event-by-Event Breakdown (Out-of-Fold)
Evaluating the 3 true events against the 1,308 total records:

1. **Event at MD 2649.0m:** **FLAGGED**
   * Rank: **22 out of 1308** (Top 1.6% — securely breaching the 2% alarm threshold)
2. **Event at MD 3660.0m:** **MISSED** (Elevated Risk)
   * Rank: **55 out of 1308** (Top 4.2% — elevated signature, but below the strict 2% cutoff)
3. **Event at MD 2883.0m:** **MISSED** (Moderate Risk)
   * Rank: **105 out of 1308** (Top 8.0%)

### Summary
While standard supervised ML failed entirely, the robust anomaly detection pipeline empirically demonstrates that operational deviations preceding mud loss are severe enough to trigger an unsupervised alarm in at least 33% of catastrophic cases, while strictly maintaining a ~1.9% False Positive Rate.
