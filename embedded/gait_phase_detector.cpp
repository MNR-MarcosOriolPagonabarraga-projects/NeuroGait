#include "classifiers.h"
#include <vector>

namespace NeuroGait {
    namespace GaitPhaseModel {
        const float LDA_INTERCEPTS[3] = { -1.52854339, -0.50257199, -2.21347691 };
        const float LDA_WEIGHTS[27] = { -258.36090807, 44.46604704, 0.36068772, -480.05169126, 272.62456008, 0.23823900, -155.64048827, -101.55005795, 0.76708792, -345.26989900, 69.47061147, 0.42051518, -315.46287164, 217.50289439, 0.09830825, -6.70024954, -174.23456172, 0.36653707, 309.23509119, -58.09730508, -0.40186587, 416.34737213, -255.05618434, -0.17835762, 88.60566848, 140.24109691, -0.59854456 };
        const int LDA_CLASSES[3] = { 0, 1, 2 };

        int predict_lda(float* input_data) {
            int best_idx = 0;
            float max_score = -1e9;

            for (int c = 0; c < 3; ++c) {
                float current_score = LDA_INTERCEPTS[c];
                for (int i = 0; i < 9; ++i) {
                    current_score += input_data[i] * LDA_WEIGHTS[c * 9 + i];
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