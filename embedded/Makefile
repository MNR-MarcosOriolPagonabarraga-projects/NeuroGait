# Compiler settings
CXX = g++

# FLAGS EXPLAINED:
# -Os:              Optimize for Size (critical for 32KB chips)
# -s:               Strip debug symbols (reduces file size)
# -flto:            Link Time Optimization (removes unused code across files)
# -ffunction-sections: Put each function in its own section
# -fdata-sections:     Put each variable in its own section
# -Wl,--gc-sections:   Tell linker to "Garbage Collect" unused sections
CXXFLAGS = -I. -Wall -Os -s -flto -ffunction-sections -fdata-sections -Wl,--gc-sections -std=c++11

TARGET = neurogait_sim

SRCS = main.cpp \
       signal_conditioner.cpp \
       feature_extraction.cpp \
       state_machine.cpp \
       walking_mode_detector.cpp \
       gait_phase_detector.cpp

all: $(TARGET)

$(TARGET): $(SRCS)
	$(CXX) $(CXXFLAGS) -o $(TARGET) $(SRCS)
	@echo "Optimization complete. Check size with: ls -lh $(TARGET)"

clean:
	rm -f $(TARGET) *.o

run: $(TARGET)
	./$(TARGET)