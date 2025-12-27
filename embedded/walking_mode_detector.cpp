// Generated C++ code for Linear Discriminant Analysis
// Source Model: models/walking_mode/state_classifier.pkl
#include <vector>

const float LDA_INTERCEPTS[4] = { 13.10446319, -7.44296176, -40.84770439, -16.46275112 };
const float LDA_WEIGHTS[36] = { 638.19437057, -631.13753234, -0.28685308, -619.13201524, -865.03564917, 2.26307977, -3039.66504459, 1197.81464298, 2.90894424, -386.66960364, 143.39680338, 0.63924986, -350.91928869, 609.54985916, -0.45705485, -186.93733798, -147.67912595, 0.35039046, 88.81825739, 478.33713596, -0.42347478, 1601.26862165, 802.17113628, -3.60665150, 2691.69796533, -878.95298751, -4.74523483, -211.36279914, 416.14376368, -0.82877813, 857.78008985, -601.71936160, -0.27071623, 3988.50839786, -1131.94105238, -2.68964922 };
const int LDA_CLASSES[4] = { 0.0, 1.0, 2.0, 3.0 };

int predict_lda(float* input_data) {
    int best_idx = 0;
    float max_score = -1e9;

    for (int c = 0; c < 4; ++c) {
        float current_score = LDA_INTERCEPTS[c];
        for (int i = 0; i < 9; ++i) {
            current_score += input_data[i] * LDA_WEIGHTS[c * 9 + i];
        }
        if (current_score > max_score) {
            max_score = current_score;
            best_idx = c;
        }
    }
    return LDA_CLASSES[best_idx];
}