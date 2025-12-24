# NeuroGait: Closed-Loop EMG-FES for Gait Rehabilitation

> **Master's Thesis Project | Neuroengineering** > **Section:** Results & Implementation  
> **Focus:** Real-time, low-resource gait intention detection using Surface EMG.

---

## Project Overview
This project develops a **closed-loop control system** for Functional Electrical Stimulation (FES) to assist patients with gait impairments (e.g., Drop Foot). 

Unlike commercial systems that rely on tilt sensors or IMUs, this system uses **only Surface EMG** to detect motor intention and gait phase. It employs a **Cross-Modal Learning** strategy: high-fidelity kinematic data (Goniometers/IMUs) is used *only* during offline training to generate Ground Truth labels, while the final deployed model relies exclusively on lightweight EMG features.

## ⚙️ System Architecture

### 1. Hardware Constraints (Production Environment)
* **Target Platform:** Low-power Microcontroller (e.g., ESP32, ARM Cortex-M4).
* **Sensors:** 3 Surface EMG Channels (No IMU/Encoders in final device).
* **Actuator:** FES Unit (Voltage-controlled biphasic stimulation).
* **Requirement:** Real-time processing (<10ms latency) with minimal memory footprint.

### 2. Muscle Configuration (Input)
We utilize 3 specific EMG channels to robustly differentiate gait phases:
1.  **TA (Tibialis Anterior):** Primary indicator for **Swing Phase** (Dorsiflexion).
2.  **MG (Medial Gastrocnemius):** Primary indicator for **Push-off** (Plantarflexion).
3.  **RF (Rectus Femoris):** Primary indicator for **Heel Strike/Loading** (Stabilization).

---

## Machine Learning Pipeline

### Strategy: Cross-Modal Supervised Learning
We solve the "missing label" problem by using a rich dataset (ENABL3S) where kinematic ground truth exists, to train a model that sees only EMG.

#### Phase 1: Data Ingestion & Labeling (Python / Offline)
* **Dataset:** ENABL3S (Example Subject: `AB156`).
* **Ground Truth Generation:**
    * Load `Right_Ankle_Angle` (Kinematics).
    * **Rule:** If Angle > Threshold ($\approx 0^\circ$ relative to neutral) $\rightarrow$ Label as `SWING (1)`.
    * **Rule:** Else $\rightarrow$ Label as `STANCE (0)`.
* **Input Features ($X$):** Raw EMG from TA, MG, RF.

#### Phase 2: Signal Processing & Feature Engineering
Simulating the embedded firmware environment:
1.  **Pre-processing:**
    * Bandpass Filter: 20-450 Hz.
    * Notch Filter: 50/60 Hz.
    * Rectification: `abs(signal)`.
2.  **Feature Extraction:**
    * **Window Size:** 100ms (Sliding window).
    * **Features:**
        * **MAV** (Mean Absolute Value): Energy metric.
        * **WL** (Waveform Length): Complexity/Onset metric.
    * **Input Vector:** `[TA_MAV, TA_WL, MG_MAV, MG_WL, RF_MAV, RF_WL]` (6 floats).

#### Phase 3: Classification Model
* **Model Choice:** **Linear Discriminant Analysis (LDA)**.
* **Why?** $O(n)$ complexity, matrix multiplication is native to C++, highly stable.
* **Output:** Probability of Swing vs. Stance.

#### Phase 4: Control Logic (The "Safety Layer")
A **Finite State Machine (FSM)** filters the LDA output to prevent jitter or physiological impossibilities.
* **Illegal Transition:** `Swing` $\rightarrow$ `Push-off` (Must pass through `Heel Strike`).
* **Refractory Period:** Ignore triggers for 200ms after a stimulation event.

---

## Repository Structure

```text
NeuroGait/
├── data/
│   ├── raw/                # ENABL3S csv files (e.g., AB156_Circuit_001_raw.csv)
│   └── processed/          # Cached datasets (optional)
├── src/
│   ├── data_loader.py      # Enabl3sDataLoader class (Lazy loading, memory optimized)
│   ├── preprocessing.py    # Filters and Feature Extraction (Python implementation)
│   ├── train_model.py      # Scikit-learn LDA pipeline + Export to C++
│   └── validation.py       # Confusion Matrix & Latency Analysis
├── embedded/               # C++ Firmware Logic
│   ├── feature_extraction.cpp  # Embedded port of MAV/WL
│   ├── classifier.h            # Exported LDA Weights (W vector, Bias)
│   └── state_machine.cpp       # FSM Control Logic
└── notebooks/
    └── 01_Exploratory_Analysis.ipynb  # Visualization of EMG vs. Ankle Angle
```

## Workflow for Agents/Collaborators

1.  **Data Loading**: Use src/data_loader.py to inspect Right_Ankle (Ground Truth) vs Right_TA/MG/RF. Note: Ankle data is in Radians (~1.8 to 2.2 rad).

2.  **Training**: Run train_model.py to generate the decision boundary.

    - Metric: Accuracy > 90% and Recall on "Swing Onset" (Critical for drop foot).

3.  **Porting**: Save the LDA coefficients (W vector and bias b) to embedded/classifier.h.

4.  **Simulation**: Test the full pipeline on a "held-out" circuit file to simulate real-time performance.

## Scope & Goals

- Goal: Demonstrate that a low-resource microcontroller can robustly detect gait phases using only 3 muscle channels.

- Success Criteria:

    - Correct detection of Swing Phase onset within 100ms.

    - Rejection of standing/shifting weight (Static balance).

    - Successful simulation of FES trigger signals.