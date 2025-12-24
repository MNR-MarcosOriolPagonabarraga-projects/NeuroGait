#ifndef SIGNAL_CONDITIONER_H
#define SIGNAL_CONDITIONER_H

namespace NeuroGait {

class Biquad {
private:
    float b0, b1, b2, a1, a2;
    float s1, s2; // State variables for Direct Form II Transposed

public:
    Biquad(float _b0, float _b1, float _b2, float _a1, float _a2);
    void reset();
    float process(float x);
};

class SignalConditioner {
private:
    Biquad bandpass;
    Biquad notch;

public:
    SignalConditioner();
    void init();
    float filter(float sample);
};

}

#endif // SIGNAL_CONDITIONER_H
