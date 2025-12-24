#include <iostream>
#include <vector>
#include <cmath>
#include "signal_conditioner.h"
#include "feature_extraction.cpp"
#include "state_machine.cpp"

// Mock Main for Integration Testing
// Simulates the microcontroller loop

int main() {
    NeuroGait::SignalConditioner conditioner;
    conditioner.init();

    // NeuroGait::StateMachine fsm; // Not used in this simple test but part of system

    // Simulate raw data (e.g., 50Hz noise + signal)
    // 1000 samples (1 second)
    
    std::cout << "Time,Raw,Filtered" << std::endl;
    
    for (int i = 0; i < 100; i++) {
        float t = i * 0.001f; // 1ms
        float raw = sin(2 * M_PI * 50 * t) + 0.5f * sin(2 * M_PI * 100 * t); // 50Hz hum + 100Hz signal
        
        float filtered = conditioner.filter(raw);
        
        std::cout << t << "," << raw << "," << filtered << std::endl;
    }

    return 0;
}
