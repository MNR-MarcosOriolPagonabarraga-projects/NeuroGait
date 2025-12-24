#include <iostream>

// Finite State Machine (FSM)
// Enforces logical transitions between Stance and Swing

namespace NeuroGait {

enum State {
    STANCE = 0,
    SWING = 1
};

class StateMachine {
private:
    State currentState;
    int refractoryTimer;
    const int REFRACTORY_PERIOD_MS = 200;
    int msPerTick;

public:
    StateMachine(int tickMs = 10) : currentState(STANCE), refractoryTimer(0), msPerTick(tickMs) {}

    State update(bool classifierPrediction) {
        // Decrease timer
        if (refractoryTimer > 0) {
            refractoryTimer -= msPerTick;
        }

        // Logic
        switch (currentState) {
            case STANCE:
                // Classifier says SWING (1) and we are not in refractory period
                if (classifierPrediction && refractoryTimer <= 0) {
                    currentState = SWING;
                    // Trigger Stimulation potentially here
                    // triggerStimulation();
                }
                break;

            case SWING:
                // Classifier says STANCE (0)
                if (!classifierPrediction) {
                    currentState = STANCE;
                    // Reset refractory timer to prevent bouncing back immediately?
                    // Or set it? Usually refractory is after Stimulation event (Onset of Swing).
                    // Let's set it on TRANSITION to Swing ideally.
                }
                break;
        }

        // Correction: Refractory should usually start upon entering a stimulation state (Swing)
        // to prevent double-triggering. 
        // My logic above checks timer before entering Swing.
        // I should Set timer when Entering Swing.
        
        return currentState;
    }
    
    void transitionToSwing() {
         currentState = SWING;
         refractoryTimer = REFRACTORY_PERIOD_MS;
    }
    
    // Better Update Logic for production:
    State process(bool prediction) {
         if (refractoryTimer > 0) {
            refractoryTimer -= msPerTick;
            return currentState; // Locked
        }
        
        if (currentState == STANCE && prediction == true) {
            currentState = SWING;
            refractoryTimer = REFRACTORY_PERIOD_MS; // Lock logic to prevent oscillation
        } else if (currentState == SWING && prediction == false) {
             currentState = STANCE;
             // Minimal refractory for landing?
             refractoryTimer = 50; 
        }
        
        return currentState;
    }
};

}
