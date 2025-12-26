import os
import numpy as np
from bokeh.plotting import figure, show
from bokeh.layouts import column
from bokeh.models import Title

from src.lib.data_loader import Enabl3sDataLoader

# Configuration constants
DATA_ROOT = "data"
SUBJECT_ID = "AB156"
CHANNELS = ['TA', 'MG', 'RF', 'Ankle_Angle', 'Knee_Angle', 'Mode']
LABELS = ['TA (mV)', 'MG (mV)', 'RF (mV)', 'Ankle Angle (deg)', 'Knee Angle (deg)', 'Mode']
SAMPLING_RATE = 250


def load_data(data_root, subject_id, channels, target_fs, circuit_range):
    """
    Load EMG data for specified circuits and channels.
    
    Args:
        data_root (str): Root directory containing data
        subject_id (str): Subject identifier
        channels (list): List of channel names to load
        target_fs (int): Target sampling frequency
        circuit_range (range): Range of circuit numbers to load
        
    Returns:
        tuple: (time_axis, raw_data) where time_axis is in seconds and 
               raw_data is a numpy array of shape (n_samples, n_channels)
    """
    loader = Enabl3sDataLoader(data_root, subject_id, target_fs=target_fs)
    df_raw = loader.load_dataset_batch(circuit_range, channels)
    
    time_axis = np.arange(len(df_raw)) / target_fs
    raw_data = df_raw.values
    
    return time_axis, raw_data


def create_channel_plots(time_axis, raw_data, channels, labels):
    """
    Create individual Bokeh plots for each channel with responsive sizing.
    
    Args:
        time_axis (np.array): Time values in seconds
        raw_data (np.array): Raw signal data (n_samples, n_channels)
        channels (list): List of channel names
        
    Returns:
        list: List of Bokeh figure objects
    """
    plots = []
    
    for i, channel_name in enumerate(channels):
        # Create figure with responsive sizing to fill window
        p = figure(
            title=channel_name,
            x_axis_label="Time (s)" if i == len(channels) - 1 else None,
            y_axis_label=labels[i],
            tools="pan,wheel_zoom,box_zoom,reset,save",
            sizing_mode="stretch_width",
            height=200
        )
        
        # Add line plot
        p.line(
            time_axis,
            raw_data[:, i],
            line_width=1.5,
            color="gray",
            alpha=0.7,
            legend_label=channel_name
        )
        
        # Configure legend
        p.legend.location = "top_right"
        p.legend.click_policy = "hide"
        
        # Link x-axes for all plots except the first one
        if i > 0 and len(plots) > 0:
            p.x_range = plots[0].x_range
        
        plots.append(p)
    
    return plots


def create_multi_channel_layout(plots, subject_id):
    """
    Create a vertical layout of channel plots with a title.
    
    Args:
        plots (list): List of Bokeh figure objects
        subject_id (str): Subject identifier for the title
        
    Returns:
        bokeh.layouts.Column: Layout object containing all plots
    """
    # Create layout with responsive sizing
    layout = column(*plots, sizing_mode="stretch_width")
    
    # Add overall title to the first plot
    if len(plots) > 0:
        plots[0].add_layout(
            Title(text=f"Raw EMG Signals - {subject_id}", text_font_size="14pt"),
            'above'
        )
    
    return layout


def main():
    """
    Main function to load and visualize EMG data using Bokeh.
    """
    # Define circuit range
    range_circuits = range(1, len(os.listdir(f"{DATA_ROOT}/{SUBJECT_ID}/Raw")) + 1)
    
    # Load data
    print(f"Loading data for subject {SUBJECT_ID}...")
    time_axis, raw_data = load_data(
        DATA_ROOT,
        SUBJECT_ID,
        CHANNELS,
        SAMPLING_RATE,
        range_circuits
    )
    
    print(f"Data loaded: {raw_data.shape[0]} samples, {raw_data.shape[1]} channels")
    
    # Create plots
    print("Creating plots...")
    plots = create_channel_plots(time_axis, raw_data, CHANNELS, LABELS)
    
    # Create layout
    layout = create_multi_channel_layout(plots, SUBJECT_ID)
    
    # Display
    print("Displaying plots...")
    show(layout)


if __name__ == "__main__":
    main()
