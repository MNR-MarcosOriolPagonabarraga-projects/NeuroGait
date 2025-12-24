#include "signal_conditioner.h"

namespace NeuroGait {

// Biquad Implementation
Biquad::Biquad(float _b0, float _b1, float _b2, float _a1, float _a2)
    : b0(_b0), b1(_b1), b2(_b2), a1(_a1), a2(_a2), s1(0.0f), s2(0.0f) {}

void Biquad::reset() {
    s1 = 0.0f;
    s2 = 0.0f;
}

// Direct Form II Transposed
float Biquad::process(float x) {
    float y = b0 * x + s1;
    s1 = s2 + b1 * x - a1 * y;
    s2 = b2 * x - a2 * y;
    return y;
}

// SignalConditioner Implementation
// Coefficients generated via Python for fs=200Hz:
// 1. Bandpass (20-90Hz):
// b = [0.66245985, 0.0, -0.66245985]
// a = [1.0, 0.23261682, -0.32491970]
//
// 2. Notch (50Hz, Q=30):
// b = [0.97448228, 0.0, 0.97448228]
// a = [1.0, 0.0, 0.94896457]

SignalConditioner::SignalConditioner() 
    : bandpass(0.66245985f, 0.0f, -0.66245985f, 0.23261682f, -0.32491970f),
      notch(0.97448228f, 0.0f, 0.97448228f, 0.0f, 0.94896457f) 
      // Note: Biquad class takes a1, a2 (the coefficients applied to y), usually these are positive in the difference equation subtraction or negative if addition. 
      // Standard: y[n] = b0*x[n] + ... - a1*y[n-1] ...
      // Scipy returns 'a' such that a[0]*y[n] + a[1]*y[n-1] ... = ...
      // So y[n] = ... - a[1]*y[n-1] ...
      // My Biquad::process uses: - a1 * y.
      // So I should pass the raw a[1] and a[2] from scipy.
      // Scipy a = [1.0, -0.15..., -0.63...]
      // So -a1*y means -(-0.15)*y = +0.15y.
      // Wait. The formula is y[n] = (b*x - a_rest*y) / a0.
      // Since a0=1, y[n] = b*x - (a1*y[n-1] + a2*y[n-2]).
      // My code: s1 = ... - a1 * y.
      // So if I pass a1 = -0.15, formula becomes - (-0.15)*y = +0.15y.
      // This matches y[n] = ... - a1*y[n-1] if a1 is the coefficient in the polynomial a[1].
      // Yes. I will pass the raw coefficients from Scipy.
{
}

void SignalConditioner::init() {
    bandpass.reset();
    notch.reset();
}

float SignalConditioner::filter(float sample) {
    // Pipeline: Bandpass -> Notch -> Output
    float bp_out = bandpass.process(sample);
    float notch_out = notch.process(bp_out);
    return notch_out;
}

}
