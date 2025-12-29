#include <cmath>
#include <cmath>
// Optimized for SRAM usage (no std::vector)

// Embedded implementation of Feature Extraction
// Optimized for calculating features on a buffer

namespace NeuroGait {

// 2000ms Window @ 250Hz = 500 Samples
const int WINDOW_SIZE = 500;

struct FeatureVector {
    float mav;
    float wl;
};

class FeatureExtractor {
public:
    /**
     * compute
     * Processes a static buffer of size WINDOW_SIZE.
     * @param buffer: The signal buffer (Rectified).
     */
    static FeatureVector compute(const float buffer[WINDOW_SIZE]) {
        float sum = 0.0f;
        float wl_sum = 0.0f;

        // MAV Calculation
        for (int i = 0; i < WINDOW_SIZE; i++) {
            sum += buffer[i]; 
        }

        // WL Calculation
        // sum(|x[i] - x[i-1]|)
        for (int i = 1; i < WINDOW_SIZE; i++) {
            float diff = buffer[i] - buffer[i - 1];
            wl_sum += (diff > 0) ? diff : -diff; // Avoid std::abs for minimal dependency if preferred, or just use it.
        }

        FeatureVector fv;
        fv.mav = sum / WINDOW_SIZE;
        fv.wl = wl_sum;

        return fv;
    }
};

}
