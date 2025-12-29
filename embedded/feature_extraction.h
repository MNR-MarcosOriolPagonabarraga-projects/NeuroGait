#ifndef FEATURE_EXTRACTION_H
#define FEATURE_EXTRACTION_H

#include <cmath>

namespace NeuroGait {

// Configuration matches Python: 2000ms window @ 250Hz = 500 samples
const int WINDOW_SIZE = 500; 
const int NUM_CHANNELS = 3;
const int NUM_FEATURES_PER_CH = 3; // MAV, RMS, WL

struct NeuroFeatures {
    float values[NUM_CHANNELS * NUM_FEATURES_PER_CH]; // [TA_MAV, TA_RMS, TA_WL, MG_..., RF_...]
};

class FeatureExtractor {
public:
    /**
     * Compute features for all 3 channels.
     * @param buffers: 2D array [Channel][Sample]
     */
    static NeuroFeatures compute(const float buffers[NUM_CHANNELS][WINDOW_SIZE]);
};

}

#endif