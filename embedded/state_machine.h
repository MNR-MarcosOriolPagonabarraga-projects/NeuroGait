#ifndef STATE_MACHINE_H
#define STATE_MACHINE_H

#include "classifiers.h"

namespace NeuroGait {

class StimulationController {
private:
    int currentPhase; // 0=Stance, 1=Swing
    int currentMode;  // 0=Sitting, 1=Walking...
    
    // Timing Variables (in ms)
    long lastTransitionTime;
    long currentPhaseDuration;
    
    // Adaptive Logic
    float avgSwingDuration;
    float avgStanceDuration;
    int swingCount;
    int stanceCount;

    // Safety
    bool isStimulating;

public:
    StimulationController();

    /**
     * Main logic loop. 
     * @param mode: Context from LDA 1
     * @param predictedPhase: Phase from LDA 2
     * @param ta_rms: Raw RMS for volitional trigger check
     * @param currentTimeMs: System clock
     */
    void update(int mode, int predictedPhase, float ta_rms, long currentTimeMs);

    bool getStimulationStatus() const;
    void printDebugInfo() const;
};

}

#endif