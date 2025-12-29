#include <cstdio>  // printf, fopen (Lighter than iostream)
#include <cstdlib> // strtof, atoi
#include <cstring> // strtok
#include <vector>
#include <cmath>
#include <unistd.h> // usleep
#include <time.h>   // clock_gettime
#include <sys/resource.h>

#include "signal_conditioner.h"
#include "feature_extraction.h"
#include "classifiers.h"
#include "state_machine.h"

// --- CONFIGURATION ---
const char* CSV_PATH = "../data/AB156/Raw/AB156_Circuit_001_raw.csv";
const int DECIMATION = 4;    // 1000Hz -> 250Hz

// --- HELPER: C-Style CSV Parsing (Zero-Copy) ---
// Finds the index of a column name in the header line
int get_col_index(char* header_line, const char* target) {
    int index = 0;
    // Duplicate line because strtok destroys it
    char* line_copy = strdup(header_line);
    char* token = strtok(line_copy, ",");
    int result = -1;

    while (token != NULL) {
        // Remove newlines/carriage returns
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

    // 1. Open CSV (C-Style)
    FILE* file = fopen(CSV_PATH, "r");
    if (!file) {
        perror("Error opening file");
        return 1;
    }

    // 2. Parse Header
    char line[1024];
    if (!fgets(line, sizeof(line), file)) return 1;

    int idx_ta = get_col_index(line, "Right_TA");
    int idx_mg = get_col_index(line, "Right_MG");
    int idx_rf = get_col_index(line, "Right_RF");
    int idx_mode = get_col_index(line, "Mode");

    if (idx_ta == -1 || idx_mg == -1 || idx_rf == -1) {
        fprintf(stderr, "Error: Missing columns.\n");
        return 1;
    }

    // 3. Initialize System
    SignalConditioner filters[3];
    for(int i=0; i<3; i++) filters[i].init();
    StimulationController fsm;
    
    // Static Buffers
    static float buffers[3][WINDOW_SIZE] = {0}; 
    int buffer_head = 0;

    printf("--- STARTING LIGHTWEIGHT SIMULATION (250Hz) ---\n");
    printf("Time(s) | GT_Mode | Pred_Mode | Pred_Phase | Stim | TA_RMS\n");

    int sample_count = 0;
    long t_ms = 0;
    int current_gt_mode = 0;

    // Timing Variables
    struct timespec next_tick;
    clock_gettime(CLOCK_MONOTONIC, &next_tick);

    // 4. Processing Loop
    while (fgets(line, sizeof(line), file)) {
        
        // Decimation: Process 1, Skip 3
        // We already read 1 line in the 'while'. We need to skip 3 more if needed.
        // BUT simpler logic: Read every line, only process if (line_count % 4 == 0)
        
        static int raw_line_count = 0;
        if (raw_line_count % DECIMATION != 0) {
            raw_line_count++;
            continue;
        }
        raw_line_count++;

        // Parse Line
        float ta=0, mg=0, rf=0;
        int col_idx = 0;
        char* token = strtok(line, ",");
        
        while (token != NULL) {
            if (col_idx == idx_ta) ta = strtof(token, NULL);
            else if (col_idx == idx_mg) mg = strtof(token, NULL);
            else if (col_idx == idx_rf) rf = strtof(token, NULL);
            else if (col_idx == idx_mode) current_gt_mode = atoi(token);
            
            token = strtok(NULL, ",");
            col_idx++;
        }

        // B. Filter & Add to Buffer
        buffers[0][buffer_head] = filters[0].filter(ta);
        buffers[1][buffer_head] = filters[1].filter(mg);
        buffers[2][buffer_head] = filters[2].filter(rf);

        // C. Inference (Every 100ms / 25 samples)
        if (sample_count % 25 == 0 && sample_count >= WINDOW_SIZE) {
            
            NeuroFeatures feats = FeatureExtractor::compute(buffers);
            int pred_mode = WalkingModel::predict_walking_mode(feats.values);
            
            int pred_phase = 0;
            if (pred_mode != 0) {
                 pred_phase = GaitPhaseModel::predict_lda(feats.values);
            }

            fsm.update(pred_mode, pred_phase, feats.values[1], t_ms);

            // Output (printf is lighter than cout)
            printf("%6.2fs | %d       | %-4s      | %-3s        | %-3s  | %.4f\n",
                   sample_count * 0.004, 
                   current_gt_mode,
                   (pred_mode == 0 ? "SIT " : "WALK"),
                   (pred_phase == 1 ? "SWG " : "STC "),
                   (fsm.getStimulationStatus() ? "ON " : "OFF"),
                   feats.values[1]);
        }

        // D. Advance Pointers
        buffer_head = (buffer_head + 1) % WINDOW_SIZE;
        sample_count++;
        t_ms += 4;

        // E. Precise Delay (4ms)
        next_tick.tv_nsec += 4000000; // +4ms
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