# Specification: Hierarchical EMG Intent Recognition & Personalization

## 1. Project Pivot: From Binary to Hierarchical
**Context:**
The previous approach (direct binary classification of Swing vs. Stance) achieved a "Zero-R" baseline accuracy (~81%) because it failed to distinguish between static states (Sitting/Standing) and active gait. The signal baseline drift caused fixed thresholds to fail.

**New Objective:**
Implement a **Hierarchical Control Strategy** that first identifies the user's high-level state, and then—only when walking—infers the specific gait phase using personalized, calibrated thresholds.

---

## 2. System Architecture

### Layer 1: Global State Classifier (The "Gatekeeper")
* **Input:** EMG Features (MAV, WL).
* **Logic:** Multi-class classification based on the recording modes found in `data/AB156/AB156_Metadata.csv` (and in other subjects' metadata files).
* **Target Classes:**
    * `ID 0`: Sitting (Rest)
    * `ID 6`: Standing (Isometric stability)
    * `ID 1`: Level Walking (Dynamic cyclic)
    * `ID 2-5`: Ramps/Stairs (High-power transitions)
* **Output:** Activates specific sub-controllers.

### Layer 2: Gait Phase Estimator (The "Pacer")
* **Active Condition:** Only runs when `Layer 1 Output == ID 1 (Level Walking)`.
* **Input:** EMG Features + History.
* **Target Classes:**
    * `0`: Stance (Weight-bearing)
    * `1`: Swing (Limb advancement)
* **Ground Truth Source:** `Right_Heel_Contact` and `Right_Toe_Off` sensors (Gold Standard), falling back to **Calibrated Kinematics** if sensors are missing.

---

## 3. Data Engineering & Personalization Strategy

We will leverage `AB156_Metadata.csv` to replace hard-coded constants with patient-specific calibration.

### A. Dynamic Normalization (Drift Removal)
Instead of a fixed threshold (e.g., >20°), we will normalize the angle for **each specific circuit trial** using the metadata limits.
* **Formula:** $Angle_{norm} = \frac{Angle_{raw} - Knee_{Min}}{Knee_{Max} - Knee_{Min}}$
* **Source:** Columns `R Knee Min`, `R Knee Max` from `AB156_Metadata.csv`.
* **Benefit:** This handles the baseline drift seen in the plots, ensuring "80% flexion" always means the same physical event.

### B. Signal Quality Weighting
* **Mechanism:** During training, weigh the importance of input channels based on their Signal-to-Noise Ratio (SNR).
* **Source:** Columns `RTA SNR`, `RMG SNR`, etc.
* **Logic:** If `RTA SNR < 10.0`, the model should trust `RMG` or `RSOL` more for that specific patient/trial.


---

## 4. Implementation Directives (Python)

### Step 1: Update `Enabl3sDataLoader`
Modify `load_circuit` to accept the metadata dataframe and return normalized labels.

```python
def load_calibrated_circuit(self, circuit_id, metadata_df):
    # 1. Load Raw Data
    df = self.load_circuit(circuit_id)
    
    # 2. Get Calibration Params
    file_id = f"{self.subject_id}_Circuit_{circuit_id:03d}"
    meta = metadata_df[metadata_df['Filename'] == file_id].iloc[0]
    
    # 3. Check Quality
    if pd.notna(meta['Notes']) and "trip" in str(meta['Notes']).lower():
        return None # Skip bad data
        
    # 4. Normalize Kinematics (Example for Knee)
    k_min, k_max = meta['R Knee Min'], meta['R Knee Max']
    df['Knee_Norm'] = (df['Right_Knee'] - k_min) / (k_max - k_min)
    
    return df
```

### Step 2: Refine Labeling Logic

Use the normalized signal to create robust labels for the Phase Detector.

```python
def add_robust_labels(self, df):
    # Priority 1: Hardware Switches (If available)
    if 'Right_Toe_Off' in df.columns:
        df['Label_Phase'] = df['Right_Toe_Off'] # 1 = Swing
    
    # Priority 2: Calibrated Kinematics
    else:
        # Swing is typically the top 20-30% of the normalized ROM
        df['Label_Phase'] = np.where(df['Knee_Norm'] > 0.75, 1, 0)
        
    return df
```

### Step 3: Hierarchical Training Loop

Filter Data: Create df_walking = df[df['Mode'] == 1].

Train Classifier A: Train State_Model on all data to predict Mode.

Train Classifier B: Train Phase_Model only on df_walking to predict Label_Phase.

    
### Step 4: Success Metrics

State Accuracy: > 95% (Easy to distinguish Walking vs. Sitting).

Phase Accuracy: Precision/Recall on "Swing" class > 90% (Must escape the 81% "Stance-only" trap).

Stability: No rapid flickering between states during transitions.