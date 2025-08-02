## Advanced-Controller-APP

<p align="center">
  <img src="assets/appicon.png" alt="app icon" width="300" />
</p>

`Advanced Controller APP` is a desktop application built with Python and Tkinter, designed for scenarios that require simultaneous control and data acquisition from multiple cameras and serial devices. It features a GUI for real-time video previewing, video recording, sending control commands, and live-plotting/logging of signal data from external hardware.

<p align="center">
  <img src="assets/appview.png" alt="app view" width="300" />
</p>

## Core Features

- **Dual Camera Control**:
  - Automatically scans and lists available cameras.
  - Allows independent selection of resolutions for each camera.
  - Provides a real-time preview of up to 2 video streams.

- **Video Recording**:
  - Records video streams into local `.avi` files.
  - The recording process runs in a separate thread to ensure a smooth, non-blocking GUI experience.

- **Serial Communication**:
  - Automatically scans and lists available serial ports.
  - Supports connection with a custom baud rate.
  - Sends predefined control commands to hardware via the GUI.

- **Real-time Data Plotting & Logging**:
  - Receives data from serial and plots waveforms in real-time using Matplotlib.
  - The plot features dynamic axis scaling to always display the most recent data window.
  - Allows inserting "Marker" into the data stream for easier post-analysis.
  - Saves the received signal data, along with timestamps and markers, into `.csv` files.

- **Synchronized Recording**:
  - A one-click "Record-Receive" feature starts (or stops) both video recording and serial data logging simultaneously, ensuring temporal alignment of the data.

## Project Structure

The project is organized into several modules, each responsible for a specific function:

- `main.py`: The application's entry point.
- `app_controller.py`: The core controller, containing all business logic and state management.
- `gui_view.py`: Defines all Tkinter GUI components and their layout.
- `camera_manager.py`: Handles scanning and managing cameras and their resolutions.
- `video_recorder.py`: A standalone class for efficiently recording video in a background thread.
- `serial_manager.py`: Manages serial port connections, data reading, and writing.
- `plot_manager.py`: Manages the Matplotlib real-time plot embedded in the GUI.

## Dependencies

To run this project, you will need to install the following Python libraries:

- **opencv-python**: For camera operations.
- **pyserial**: For serial communication.
- **matplotlib**: For data plotting.
- **numpy**: A dependency for Matplotlib, also used for data handling.

You can install them via pip:
```bash
pip install opencv-python pyserial matplotlib numpy
```

## How to Run

1. Ensure all dependencies are installed.
2. Place all project code files in the same directory.
3. Run the main script from your terminal:

```bash
python main.py
```

## Functionality Guide

- **Camera Module**:
  - **Refresh** Cameras: Click the "Refresh Cameras" button to scan for cameras connected to the system.
  - **Select & Preview**: Choose different cameras and resolutions from the dropdown menus for "Camera 1" and "Camera 2". Click "Start Preview" to display the live feed on the canvases.
  - **Record**: While previewing, click "Start Record" to begin recording video. Click it again to stop. Recorded videos will be saved in the data/video/ directory.

- **Serial Communication Module**:



- **Synchronization Module**:
