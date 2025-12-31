#ifndef FEATURE_EXTRACTION_H
#define FEATURE_EXTRACTION_H

#include <cmath>

namespace NeuroGait {
    
    const int WINDOW_SIZE = 500;
    const int NUM_CHANNELS = 2; // TA, MG

    struct NeuroFeatures {
        // 2 channels * 3 features (MAV, RMS, WL) = 6 values
        float values[NUM_CHANNELS * 3]; 
    };

    class FeatureExtractor {
    public:
        static NeuroFeatures compute(const float buffers[NUM_CHANNELS][WINDOW_SIZE], 
                                     int head_index, 
                                     int len);
    };
}
#endif