#include "classifiers.h"
#include <vector>

namespace NeuroGait {
    namespace GaitPhaseModel {
        const int LDA_N_FEATURES = 6;
        const float LDA_INTERCEPT = 1.20588160;
        const float LDA_WEIGHTS[6] = { -94.47038980, 37.35439958, 1.16667454, 42.87301493, -119.60787531, 0.91495351 };

        int predict_gait_phase(float* input_data) {
            float score = LDA_INTERCEPT;
            for (int i = 0; i < LDA_N_FEATURES; ++i) {
                score += input_data[i] * LDA_WEIGHTS[i];
            }
            return (score > 0) ? 1.0 : 0.0;
        }
    }
}