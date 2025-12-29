#ifndef SIGNAL_CONDITIONER_H
#define SIGNAL_CONDITIONER_H

namespace NeuroGait {

// A standard Biquad filter class (Direct Form II Transposed)
class Biquad {
private:
    float b0, b1, b2, a1, a2;
    float s1, s2; // Internal state variables

public:
    Biquad(float _b0, float _b1, float _b2, float _a1, float _a2);
    void reset();
    float process(float x);
};

// Manages the filter chain (Bandpass + Notch)
class SignalConditioner {
private:
    Biquad bandpass;
    Biquad notch;

public:
    SignalConditioner();
    void init();
    
    // Process a single sample through the chain
    float filter(float sample);
};

}

#endif