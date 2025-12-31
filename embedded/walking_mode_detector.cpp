#include "classifiers.h"
#include <vector>

namespace NeuroGait {
    namespace WalkingModel {
        const float LDA_INTERCEPTS[4] = { 11.27914795, -6.67376791, -37.32819742, -9.55152424 };
        const float LDA_WEIGHTS[24] = { 222.55794735, -180.84421412, -0.53869367, -1317.71100468, -617.47667040, 2.92799155, -333.73277434, 19.74225361, 0.70823106, -480.47154707, 680.00517888, -0.55189923, 563.19728883, -70.55635035, -0.20774741, 1919.10033500, 769.05897865, -4.42325901, 54.94411848, 324.48528652, -0.71053907, 2217.86222408, -1201.75132386, -0.63538710 };
        const int LDA_CLASSES[4] = { 0, 1, 2, 3 };

        int predict_walking_mode(float* input_data) {
            int best_idx = 0;
            float max_score = -1e9;

            for (int c = 0; c < 4; ++c) {
                float current_score = LDA_INTERCEPTS[c];
                for (int i = 0; i < 6; ++i) {
                    current_score += input_data[i] * LDA_WEIGHTS[c * 6 + i];
                }
                if (current_score > max_score) {
                    max_score = current_score;
                    best_idx = c;
                }
            }
            return LDA_CLASSES[best_idx];
        }
    }
}