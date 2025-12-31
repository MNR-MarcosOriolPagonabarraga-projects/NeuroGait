#include "feature_extraction.h"

namespace NeuroGait {

    NeuroFeatures FeatureExtractor::compute(const float buffers[NUM_CHANNELS][WINDOW_SIZE], 
                                            int head_index, 
                                            int len) {
        NeuroFeatures features;
        int f_idx = 0;

        // Valid length check
        if (len > WINDOW_SIZE) len = WINDOW_SIZE;

        for (int ch = 0; ch < NUM_CHANNELS; ch++) {
            float sum_abs = 0.0f;
            float sum_sq = 0.0f;
            float sum_wl = 0.0f;
            
            int start_idx = (head_index - len + WINDOW_SIZE) % WINDOW_SIZE;
            
            float prev_rect_val = 0.0f;

            int pre_start_idx = (start_idx - 1 + WINDOW_SIZE) % WINDOW_SIZE;
            float pre_val = buffers[ch][pre_start_idx];
            prev_rect_val = (pre_val > 0) ? pre_val : -pre_val;

            for (int i = 0; i < len; i++) {
                int current_idx = (start_idx + i) % WINDOW_SIZE;
                float val = buffers[ch][current_idx];
                
                // Rectify (Match Python)
                float rect_val = (val > 0) ? val : -val;

                // MAV & RMS
                sum_abs += rect_val;
                sum_sq += rect_val * rect_val;

                // WL
                float diff = rect_val - prev_rect_val;
                sum_wl += (diff > 0) ? diff : -diff;
                
                prev_rect_val = rect_val;
            }

            features.values[f_idx++] = sum_abs / len;       // MAV (normalized)
            features.values[f_idx++] = std::sqrt(sum_sq / len); // RMS (normalized)
            features.values[f_idx++] = sum_wl;              // WL (Extensive - depends on len!)
        }

        return features;
    }
}