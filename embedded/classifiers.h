#ifndef CLASSIFIERS_H
#define CLASSIFIERS_H

#include "feature_extraction.h"

namespace NeuroGait {

    // --- Walking Mode Model (Context Layer) ---
    namespace WalkingModel {
        // Returns: 0=Sitting, 1=Walking, 2=Ascent, 3=Descent
        int predict_walking_mode(float* input_data);
    }

    // --- Gait Phase Model (Action Layer) ---
    namespace GaitPhaseModel {
        // Returns: 0=Stance, 1=Swing, 2=None
        int predict_gait_phase(float* input_data);
    }
}

#endif