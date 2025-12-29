#include "signal_conditioner.h"

namespace NeuroGait {

// --- Biquad Implementation ---
// Initializes the filter coefficients and clears state variables
Biquad::Biquad(float _b0, float _b1, float _b2, float _a1, float _a2)
    : b0(_b0), b1(_b1), b2(_b2), a1(_a1), a2(_a2), s1(0.0f), s2(0.0f) {}

// Resets the internal state (useful when restarting therapy)
void Biquad::reset() {
    s1 = 0.0f;
    s2 = 0.0f;
}

// Processes one sample using Direct Form II Transposed difference equation
// y[n] = b0*x[n] + s1[n-1]
// s1[n] = s2[n-1] + b1*x[n] - a1*y[n]
// s2[n] = b2*x[n] - a2*y[n]
float Biquad::process(float x) {
    float y = b0 * x + s1;
    s1 = s2 + b1 * x - a1 * y;
    s2 = b2 * x - a2 * y;
    return y;
}

// --- SignalConditioner Implementation ---

SignalConditioner::SignalConditioner() 
    // Initialize Filters with Pre-Calculated Python Coefficients
    // 1. Bandpass (20-450Hz approx / optimized for fs=250Hz)
    : bandpass(0.66245985f, 0.0f, -0.66245985f, 0.23261682f, -0.32491970f),
    // 2. Notch (50Hz to remove power line hum)
      notch(0.97448228f, 0.0f, 0.97448228f, 0.0f, 0.94896457f) 
{
}

void SignalConditioner::init() {
    bandpass.reset();
    notch.reset();
}

float SignalConditioner::filter(float sample) {
    // Pipeline: Input -> Bandpass -> Notch -> Output
    float bp_out = bandpass.process(sample);
    float notch_out = notch.process(bp_out);
    return notch_out;
}

}