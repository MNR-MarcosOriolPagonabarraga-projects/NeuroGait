#ifndef HIERARCHICAL_CLASSIFIER_H
#define HIERARCHICAL_CLASSIFIER_H

#include <cmath>

// PHASE Model (LDA)
const int PHASE_N_FEATURES = 6;
const double PHASE_WEIGHTS[PHASE_N_FEATURES] = {-35.643553, 0.128592, 22.706944, 1.000791, 111.635731, -7.027729};
const double PHASE_BIAS = -0.448819;

int predict_phase(const double* features) {
    double score = PHASE_BIAS;
    for(int i=0; i<PHASE_N_FEATURES; i++) score += features[i] * PHASE_WEIGHTS[i];
    return (score > 0) ? 1 : 0;
}

// Hierarchical Control Logic
// State Modes: 0=Sitting, 1=Level Walking, 3=Ramp, 4=Terrain, 6=Standing
int predict_hierarchical(const double* features) {
    // Layer 1: Identify Global State
    int state = predict_state(features);

    // Layer 2: Dispatch to Phase Estimator (only for Walking)
    if (state == 1) {  // Level Walking
        // Return gait phase: 0=Stance, 1=Swing
        return predict_phase(features);
    } else {
        // For static states (Sitting/Standing) or non-level terrain,
        // return Stance (0) as default safe state
        return 0;
    }
}

// Helper function: Get current state name
const char* get_state_name(int state) {
    switch(state) {
        case 0: return "Sitting";
        case 1: return "Walking";
        case 3: return "Ramp";
        case 4: return "Terrain";
        case 6: return "Standing";
        default: return "Unknown";
    }
}
#endif // HIERARCHICAL_CLASSIFIER_H
