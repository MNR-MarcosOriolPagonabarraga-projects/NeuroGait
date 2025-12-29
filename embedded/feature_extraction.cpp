#include "feature_extraction.h"

namespace NeuroGait {
    NeuroFeatures FeatureExtractor::compute(const float buffers[NUM_CHANNELS][WINDOW_SIZE]) {
        NeuroFeatures features;
        int f_idx = 0;

        for (int ch = 0; ch < NUM_CHANNELS; ch++) {
            float sum_abs = 0.0f;
            float sum_sq = 0.0f;
            float sum_wl = 0.0f;

            for (int i = 0; i < WINDOW_SIZE; i++) {
                float val = buffers[ch][i];
                float abs_val = (val > 0) ? val : -val;
                
                sum_abs += abs_val;
                sum_sq += val * val;

                if (i > 0) {
                    float diff = val - buffers[ch][i-1];
                    sum_wl += (diff > 0) ? diff : -diff;
                }
            }

            features.values[f_idx++] = sum_abs / WINDOW_SIZE;      // MAV
            features.values[f_idx++] = std::sqrt(sum_sq / WINDOW_SIZE); // RMS
            features.values[f_idx++] = sum_wl;                     // WL
        }

        return features;
    }
}