#include <cstdio>  // printf, fopen
#include <cstdlib> // strtof, atoi
#include <cstring> // strtok
#include <vector>
#include <cmath>
#include <unistd.h>
#include <time.h>
#include <sys/resource.h>

#include "signal_conditioner.h"
#include "feature_extraction.h"
#include "classifiers.h"
#include "state_machine.h"

// --- CONFIGURATION ---
const char* CSV_PATH = "../data/AB156/Raw/AB156_Circuit_001_raw.csv";
const int DECIMATION = 4;    // 1000Hz -> 250Hz

// --- MEMORY DIAGNOSTICS ---
void print_memory_report(size_t buffer_size) {
    // 1. Calculate Theoretical Embedded Usage
    size_t filter_size = sizeof(NeuroGait::SignalConditioner) * 2; // 2 Channels
    size_t fsm_size = sizeof(NeuroGait::StimulationController);
    size_t total_static = buffer_size + filter_size + fsm_size;

    printf("\n=== MEMORY DIAGNOSTICS (Target: Cortex-M0+) ===\n");
    printf("  [Data Buffers]   %zu bytes (2 channels x %d float samples)\n", buffer_size, NeuroGait::WINDOW_SIZE);
    printf("  [Filter States]  %zu bytes (Biquad coefficients)\n", filter_size);
    printf("  [State Machine]  %zu bytes\n", fsm_size);
    printf("  ------------------------------------------------\n");
    printf("  TOTAL SRAM USAGE: %zu bytes (%.2f KB)\n", total_static, total_static / 1024.0f);
    printf("==================================================\n\n");
}

void print_pc_process_usage() {
    struct rusage usage;
    getrusage(RUSAGE_SELF, &usage);
    // ru_maxrss is in KB on Linux
    printf("  [HOST DEBUG] PC Process RAM: %ld KB\n", usage.ru_maxrss);
}

// --- HELPER: CSV Parsing ---
int get_col_index(char* header_line, const char* target) {
    int index = 0;
    char* line_copy = strdup(header_line);
    char* token = strtok(line_copy, ",");
    int result = -1;

    while (token != NULL) {
        token[strcspn(token, "\r\n")] = 0;
        if (strcmp(token, target) == 0) {
            result = index;
            break;
        }
        token = strtok(NULL, ",");
        index++;
    }
    free(line_copy);
    return result;
}

int main() {
    using namespace NeuroGait;

    // Open CSV
    FILE* file = fopen(CSV_PATH, "r");
    if (!file) {
        perror("Error opening file");
        return 1;
    }

    // Parse Header
    char line[1024];
    if (!fgets(line, sizeof(line), file)) return 1;

    int idx_ta = get_col_index(line, "Right_TA");
    int idx_mg = get_col_index(line, "Right_MG");
    int idx_mode = get_col_index(line, "Mode");

    if (idx_ta == -1 || idx_mg == -1) {
        fprintf(stderr, "Error: Missing TA or MG columns.\n");
        return 1;
    }

    // Initialize System (2 Channels)
    SignalConditioner filters[2];
    for(int i=0; i<2; i++) filters[i].init();
    StimulationController fsm;
    
    // Static Buffers
    static float buffers[2][WINDOW_SIZE] = {0}; 
    int buffer_head = 0;

    // --- PRINT MEMORY STATS STARTUP ---
    print_memory_report(sizeof(buffers));

    printf("--- STARTING SIMULATION (250Hz) ---\n");
    printf(" Time(s)  |  GT  |  Mode  |  Phase  |  Stim  \n");

    int sample_count = 0;
    long t_ms = 0;
    int current_gt_mode = 0;

    struct timespec next_tick;
    clock_gettime(CLOCK_MONOTONIC, &next_tick);

    // 4. Processing Loop
    while (fgets(line, sizeof(line), file)) {
        
        static int raw_line_count = 0;
        if (raw_line_count % DECIMATION != 0) {
            raw_line_count++;
            continue;
        }
        raw_line_count++;

        float ta=0, mg=0;
        int col_idx = 0;
        char* token = strtok(line, ",");
        
        while (token != NULL) {
            if (col_idx == idx_ta) ta = strtof(token, NULL);
            else if (col_idx == idx_mg) mg = strtof(token, NULL);
            else if (col_idx == idx_mode) current_gt_mode = atoi(token);
            token = strtok(NULL, ",");
            col_idx++;
        }

        // B. Add to Buffer (Circular Write)
        buffers[0][buffer_head] = filters[0].filter(ta);
        buffers[1][buffer_head] = filters[1].filter(mg);

        // C. Inference (Every 100ms)
        if (sample_count % 25 == 0 && sample_count >= WINDOW_SIZE) {
    
            // Extract FULL Context features (500 samples / 2000ms) for Walking Mode
            NeuroFeatures context_feats = FeatureExtractor::compute(buffers, buffer_head, 500);
            int pred_mode = WalkingModel::predict_walking_mode(context_feats.values);
            
            int pred_phase = 0;
            if (pred_mode != 0 && pred_mode != 6) { // If Walking
                // Extract SHORT Phase features (50 samples / 200ms) for Gait Phase
                NeuroFeatures phase_feats = FeatureExtractor::compute(buffers, buffer_head, 50);
                pred_phase = GaitPhaseModel::predict_gait_phase(phase_feats.values);
            }

            fsm.update(pred_mode, pred_phase, context_feats.values[1], t_ms);
            
            const char* mode_str;
            switch (pred_mode) {
                case 0:  mode_str = "SIT"; break;
                case 1:  mode_str = "LEVEL WALK"; break;
                case 2:  mode_str = "Ramp ASCENT"; break;
                case 3:  mode_str = "Ramp DESCENT"; break;
                default: mode_str = "UNKNOWN"; break;
            }

            // Output with Buffer Monitor
            printf(" %6.2fs  |  %d   |  %-4s  |  %-3s  |  %-3s  \n",
                   sample_count * 0.004, 
                   current_gt_mode,
                   mode_str,
                   (pred_phase == 1 ? "SWG " : "STC "),
                   (fsm.getStimulationStatus() ? "ON " : "OFF")
            );
        }

        // Periodic PC Memory Check (Every 5 seconds of sim time)
        if (sample_count % 1250 == 0) {
            print_pc_process_usage();
        }

        buffer_head = (buffer_head + 1) % WINDOW_SIZE;
        sample_count++;
        t_ms += 4;

        next_tick.tv_nsec += 4000000; 
        if (next_tick.tv_nsec >= 1000000000) {
            next_tick.tv_nsec -= 1000000000;
            next_tick.tv_sec += 1;
        }
        clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &next_tick, NULL);
    }

    printf("--- END ---\n");
    fclose(file);
    return 0;
}