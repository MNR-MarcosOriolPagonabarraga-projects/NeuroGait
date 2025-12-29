#include "state_machine.h"
#include <iostream>

namespace NeuroGait {

StimulationController::StimulationController() 
    : currentPhase(0), currentMode(0), // Default Stance/Sitting 
      lastTransitionTime(0), currentPhaseDuration(0),
      avgSwingDuration(400.0f), avgStanceDuration(600.0f),
      swingCount(0), stanceCount(0), isStimulating(false) {}

void StimulationController::update(int mode, int predictedPhase, float ta_rms, long currentTimeMs) {
    currentMode = mode;
    currentPhaseDuration = currentTimeMs - lastTransitionTime;

    // --- 1. SAFETY GATE ---
    // Mode 0 = Sitting. Mode 6 (if used) = Standing.
    // We only enable for Mode 1 (Walking), 2 (Ascent), 3 (Descent).
    if (currentMode == 0) { 
        isStimulating = false;
        if (currentPhase != 0) { // Force reset to Stance if sitting
            currentPhase = 0; 
            lastTransitionTime = currentTimeMs;
        }
        return; 
    }

    // --- 2. TRANSITION LOGIC ---
    
    // Phase 0 = Stance, Phase 1 = Swing
    if (currentPhase == 0) { // In Stance, looking for Swing
        
        bool volitional_trigger = ta_rms > 0.02f; // Trigger Threshold
        bool model_says_swing = (predictedPhase == 1);
        bool min_time_passed = currentPhaseDuration > (avgStanceDuration * 0.2f);

        if (model_says_swing && volitional_trigger && min_time_passed) {
            // Enter Swing
            avgStanceDuration = (avgStanceDuration * 0.9f) + (currentPhaseDuration * 0.1f);
            
            currentPhase = 1; 
            lastTransitionTime = currentTimeMs;
            isStimulating = true;
            std::cout << "[FSM] >>> SWING ONSET (" << currentPhaseDuration << "ms Stance)" << std::endl;
        }

    } else if (currentPhase == 1) { // In Swing, looking for Stance
        
        bool model_says_stance = (predictedPhase == 0);
        bool timeout = currentPhaseDuration > 1200; // Safety timeout

        if (model_says_stance || timeout) {
            // Enter Stance
            avgSwingDuration = (avgSwingDuration * 0.9f) + (currentPhaseDuration * 0.1f);
            
            currentPhase = 0;
            lastTransitionTime = currentTimeMs;
            isStimulating = false;
            std::cout << "[FSM] <<< HEEL STRIKE (" << currentPhaseDuration << "ms Swing)" << std::endl;
        }
    }
}

bool StimulationController::getStimulationStatus() const { 
    return isStimulating; 
}

void StimulationController::printDebugInfo() const {
    std::cout << "\n[FSM STATISTICS]" << std::endl;
    std::cout << "  Avg Swing Duration: " << (int)avgSwingDuration << " ms" << std::endl;
    std::cout << "  Avg Stance Duration: " << (int)avgStanceDuration << " ms" << std::endl;
}

}