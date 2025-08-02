import cv2
import tkinter as tk
from PIL import Image, ImageTk
import datetime
import threading
import numpy as np
import os
import sys

# Project imports
from gui_view import AppGUI
from camera_manager import CameraManager
from video_recorder import VideoRecorder
from serial_manager import SerialManager
from plot_manager import PlotManager


# ============================================
# ----------- Get Base Path Method -----------
# ============================================
def get_base_path():
    """Get the base path of the application, which is useful for file operations."""
    if getattr(sys, 'frozen', False):
        # for frozen applications (PyInstaller), use the executable's directory
        base_path = os.path.dirname(sys.executable)
    else:
        # for development mode, use the script's directory
        base_path = os.path.dirname(os.path.abspath(__file__))
    return base_path


class AppController:
    """The main controller for the application."""

    def __init__(self, root):
        """Initializes the application controller."""
        self.root = root
        self.view = AppGUI(root, self)
        # set up traces for camera selection dropdowns after the view is created
        for panel in self.view.camera_panels:
            panel.selected_camera_var.trace_add("write", lambda *args, p=panel: self.on_camera_select(p.camera_id))
        # --- Multi-camera state variables ---
        self.caps = {}
        self.recorders = {}
        self.is_previewing = False
        self.is_recording = False
        self.available_cameras = {}
        self.resolution_cache = {}
        self.TARGET_FPS = 30.0
        # --- Serial communication state variables ---
        self.available_serial_ports = {}
        self.is_serial_connected = False
        self.serial_data_buffer = b''
        self.is_led_on = False
        self.is_serial_receiving = False
        self.log_files = {}
        self.selected_channels_for_log = []
        self.marker_pending = False
        self.start_receiving_time = None
        self.last_receive_time = None
        self.is_record_receive = False
         # --- Base path for use ---
        self.base_path = get_base_path()
        # --- Service components ---
        self.camera_manager = CameraManager()
        self.serial_manager = SerialManager(data_received_callback=self.on_serial_data_received)
        self.plot_manager = PlotManager(self.view.serial_plot_frame)
        # --- Final setup ---
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.refresh_cameras()
        self.refresh_serial_ports()
        self.view.set_serial_controls_state("disabled")


    # ============================================
    # ---------- Camera Control Methods ----------
    # ============================================
    def refresh_cameras(self):
        """Refresh the list of available cameras and reset the UI."""
        if self.is_previewing:
            return
        self.view.update_camera_state("State: Refreshing camera lists...")
        for panel in self.view.camera_panels:
            panel.selected_camera_var.set("Scanning...")
            panel.camera_menu.config(state="disabled")
            panel.selected_resolution_var.set("Choose camera first")
            panel.resolution_menu.config(state="disabled")
        self.view.camera_preview_button.config(state="disabled")
        self.available_cameras = {}
        self.resolution_cache = {}
        # start a thread to scan for cameras
        threading.Thread(target=self._scan_and_update_cameras, daemon=True).start()

    def _scan_and_update_cameras(self):
        """Scan for available cameras in a background thread and update the UI."""
        self.available_cameras = self.camera_manager.find_available_cameras()
        camera_names = list(self.available_cameras.keys())
        # update the UI when the scan is complete
        def update_ui():
            self.view.update_camera_menu(0, camera_names)
            self.view.update_camera_menu(1, camera_names)
            if camera_names:
                self.view.update_camera_state("State: Cameras refreshed.")
            else:
                self.view.update_camera_state("Error: No cameras found.", color="red")
        self.root.after(0, update_ui)

    def on_camera_select(self, camera_id):
        """Handle camera selection changes and trigger a resolution scan."""
        panel = self.view.get_camera_panel(camera_id)
        cam_name = panel.selected_camera_var.get()
        # if no camera is selected, disable resolution menu
        if cam_name == "--none--":
            panel.selected_resolution_var.set("--none--")
            panel.resolution_menu.config(state="disabled")
            return
        panel.resolution_menu.config(state="disabled")
        panel.selected_resolution_var.set("Scanning...")
        # scan for resolutions
        cam_index = self.available_cameras.get(cam_name)
        if cam_index is not None:
            if cam_index in self.resolution_cache:
                resolutions = self.resolution_cache[cam_index]
                self.view.update_camera_resolution_menu(camera_id, resolutions)
            else:
                threading.Thread(target=self._scan_camera_resolutions, args=(camera_id, cam_index), daemon=True).start()

    def _scan_camera_resolutions(self, camera_id, cam_index):
        """Scan for available resolutions for the chosen camera."""
        resolutions = self.camera_manager.find_available_resolutions(cam_index)
        self.resolution_cache[cam_index] = resolutions
        self.root.after(0, self.view.update_camera_resolution_menu, camera_id, resolutions)

    def toggle_preview(self):
        """Toggle the camera preview start or stop."""
        if self.is_previewing:
            self._stop_preview()
        else:
            self._start_preview()

    def _start_preview(self):
        """Validate selections and starts the camera preview streams."""
        selected_indices = set()
        cameras_to_open = []
        # 1. validate all selections and check for duplicates
        for cam_id in range(2):
            panel = self.view.get_camera_panel(cam_id)
            cam_name = panel.selected_camera_var.get()
            res_str = panel.selected_resolution_var.get()
            # if no camera is selected or resolution is invalid, skip this camera
            if cam_name == "--none--" or 'x' not in res_str:
                continue
            cam_index = self.available_cameras.get(cam_name)
            # if camera has already been selected, show error and skip
            if cam_index in selected_indices:
                self.view.update_camera_state(f"Error: Camera '{cam_name}' is selected more than once.", color="red")
                return 
            # add to the list of cameras to open
            selected_indices.add(cam_index)
            width, height = map(int, res_str.split('x'))
            cameras_to_open.append({
                'id': cam_id, 'index': cam_index, 'name': cam_name,
                'width': width, 'height': height
            })
        # 2. open the validated cameras
        self.caps = {}
        for cam_info in cameras_to_open:
            cap = cv2.VideoCapture(cam_info['index'])
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_info['width'])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_info['height'])
            cap.set(cv2.CAP_PROP_FPS, self.TARGET_FPS)
            if cap.isOpened():
                self.caps[cam_info['id']] = cap
            else:
                self.view.update_camera_state(f"Error: Cannot open camera '{cam_info['name']}'.", color="red")
        if not self.caps: # if no cameras were opened, show error
            if not selected_indices:
                 self.view.update_camera_state("Error: No valid camera selected for preview.", color="red")
            return
        # 3. start the preview
        self.is_previewing = True
        self.view.set_camera_preview_state(True)
        self._update_camera_frames()
        if self.is_serial_connected:
            self.view.record_receive_button.config(state="normal")
    
    def _stop_preview(self):
        """Stop all active camera previews."""
        if self.is_recording:
            self.toggle_recording()
        self.is_previewing = False
        for cap in self.caps.values():
            cap.release()
        self.caps = {}
        self.view.set_camera_preview_state(False)
        self.view.record_receive_button.config(state="disabled")

    def _update_camera_frames(self):
        """The main preview loop for camera feeds."""
        if not self.is_previewing:
            return
        # 1. get the active camera IDs
        active_cam_ids = list(self.caps.keys())
        for cam_id in active_cam_ids:
            cap = self.caps.get(cam_id)
            if not cap:
                continue
            ret, frame = cap.read()
            if ret:
                # 2. if recording, put the frame into the corresponding recorder
                if self.is_recording and cam_id in self.recorders:
                    self.recorders[cam_id].put_frame(frame)
                # 3. prepare and display the frame on its dedicated canvas
                canvas_to_draw = self.view.get_camera_canvas(cam_id) 
                canvas_width = canvas_to_draw.winfo_width()
                canvas_height = canvas_to_draw.winfo_height()
                if canvas_width > 1 and canvas_height > 1:
                    # resize the frame to fit the canvas
                    resized_frame = cv2.resize(frame, (canvas_width, canvas_height))
                    cv_image = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
                    photo = ImageTk.PhotoImage(image=Image.fromarray(cv_image))
                    # display the image on the canvas
                    self.view.display_camera_image(cam_id, photo)
        # if only one camera is active, clear the other canvas
        if len(active_cam_ids) == 1:
            other_canvas_index = 1 - active_cam_ids[0]
            other_canvas = self.view.get_camera_canvas(other_canvas_index)
            if other_canvas.find_all():
                other_canvas.delete("all")
        # 4. schedule the next frame update
        self.root.after(int(1000/60), self._update_camera_frames)

    def toggle_recording(self):
        """Toggle the video record start or stop."""
        if self.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        """Start a separate VideoRecorder for each active camera stream."""
        if not self.is_previewing or self.is_recording:
            return
        # create the output folder if it does not exist
        output_folder = os.path.join(self.base_path, "data", "video")
        try:
            os.makedirs(output_folder, exist_ok=True)
        except OSError as e:
            self.view.update_camera_state(f"Error: Cannot creating directory: {e}", color="red")
            return
        self.is_recording = True
        self.recorders = {}
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        for cam_id, cap in self.caps.items():
            filename = f"CAM{cam_id+1}_{timestamp}.avi"
            full_filepath = os.path.join(output_folder, filename)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            # create the VideoRecorder instance
            recorder = VideoRecorder(full_filepath, (width, height), self.TARGET_FPS)
            recorder.start()
            self.recorders[cam_id] = recorder
        # if no cameras are effectively opened, stop the recording and show an error
        if not self.recorders:
            self.is_recording = False
            self.view.update_camera_state("Error: No active streams to record.", color="red")
            return
        self.view.set_camera_recording_state(True, self.is_previewing)
        self.view.record_receive_button.config(state="disabled")

    def _stop_recording(self):
        """Stop all active recorders and wait for them to finish writing files."""
        if not self.is_recording:
            return
        for recorder in self.recorders.values():
            recorder.stop()
        # clear the recorders and reset the state
        self.recorders = {}
        self.is_recording = False
        self.view.set_camera_recording_state(False, self.is_previewing)
        if self.is_serial_connected and not self.is_serial_receiving:
            self.view.record_receive_button.config(state="normal")


    # ============================================
    # ---------- Serial Control Methods ----------
    # ============================================
    def refresh_serial_ports(self):
        """Refresh the list of available serial ports and reset the UI."""
        if self.is_serial_connected:
            return
        self.view.update_serial_state("State: Refreshing serial ports...")
        self.view.serial_port_var.set("Scanning...")
        self.view.serial_port_menu.config(state="disabled")
        self.view.serial_connect_button.config(state="disabled")
        self.available_serial_ports = {}
        # start a thread to scan for serial ports
        threading.Thread(target=self._scan_and_update_serial_ports, daemon=True).start()

    def _scan_and_update_serial_ports(self):
        """Scan for available serial ports in a background thread and update the UI."""
        self.available_serial_ports = self.serial_manager.find_serial_ports()
        ports = list(self.available_serial_ports)
        # update the UI when the scan is complete
        def update_serial_ui():
            self.view.update_serial_port_menu(ports)
            if ports:
                self.view.update_serial_state("State: Serial ports refreshed.")
            else:
                self.view.update_serial_state("Error: No serial ports found.", color="red")
        self.root.after(0, update_serial_ui)

    def toggle_serial_connection(self):
        """Toggle the serial connect or disconnect."""
        if self.is_serial_connected:
            self._disconnect_serial()
        else:
            self._connect_serial()

    def _connect_serial(self):
        """Connect to the selected serial port with the specified baudrate."""
        selected_port = self.view.serial_port_var.get()
        if not selected_port or "--none--" in selected_port or "No Ports" in selected_port:
            self.view.update_serial_state("Error: No valid port selected for connect.", color="red")
            return
        try:
            selected_baudrate = int(self.view.serial_baudrate_var.get())
        except (ValueError, tk.TclError):
            selected_baudrate = 115200  # Fallback to a common default
        # Attempt to connect using the SerialManager.
        if self.serial_manager.connect(selected_port, baudrate=selected_baudrate):
            self.is_serial_connected = True
            self.view.set_serial_connected_state(True, selected_port)
            if not self.is_previewing:
                self.view.record_receive_button.config(state="disabled")
        else:
            self.view.update_serial_state(f"Error: Failed to connect to {selected_port}", color="red")

    def _disconnect_serial(self):
        """Disconnect the serial connection if it is active."""
        if not self.is_serial_connected:
            return
        self.serial_manager.disconnect()
        self.is_serial_connected = False
        self.view.set_serial_connected_state(False)

    def _get_selected_led_channels(self):
        """Returns a list of selected led channel numbers (1 or 2)."""
        channels = []
        if self.view.led_channel1_var.get():
            channels.append(1)
        if self.view.led_channel2_var.get():
            channels.append(2)
        return channels
    
    def _get_selected_receive_channels(self):
        """Returns a list of selected receive channel numbers (1 or 2)."""
        channels = []
        if self.view.receive_channel1_var.get():
            channels.append(1)
        if self.view.receive_channel2_var.get():
            channels.append(2)
        return channels

    def toggle_led(self):
        """Toggle the led on or off."""
        if not self.is_serial_connected:
            return
        if self.is_led_on:
            self._led_off()
        else:
            self._led_on()

    def _led_on(self):
        """Turn the LED on for the selected serial channels."""
        channels_for_led = self._get_selected_led_channels()
        if not channels_for_led:
            self.view.update_led_control_state("No channel selected.", color="red")
            return
        self.is_led_on = True
        self.view.serial_connect_button.config(state="disabled")
        self.view.led_ch1_check.config(state="disabled")
        self.view.led_ch2_check.config(state="disabled")
        self.view.led_update_button.config(state="normal")
        self.view.update_led_control_state("LED on.")
        self.view.serial_led_button.config(text="LED Off")
        command_char = 'H'
        for ch in self._get_selected_led_channels():
            command = f"0{ch}00000000CC{command_char}\r\n"
            self.serial_manager.send_data(command)

    def _led_off(self):
        """Turn the LED off for the selected serial channels."""
        self.is_led_on = False
        if not self.is_serial_receiving:
            self.view.serial_connect_button.config(state="normal")
        self.view.led_ch1_check.config(state="normal")
        self.view.led_ch2_check.config(state="normal")
        self.view.led_update_button.config(state="disabled")
        self.view.update_led_control_state("LED off.")
        self.view.serial_led_button.config(text="LED On")
        command_char = 'I'
        for ch in self._get_selected_led_channels():
            command = f"0{ch}00000000CC{command_char}\r\n"
            self.serial_manager.send_data(command)
    
    def update_led(self):
        """Update the LED state based on the current selection."""
        if not self.is_led_on:
            return
        channels_for_led = self._get_selected_led_channels()
        if not channels_for_led:
            self.view.update_led_control_state("No channel selected.", color="red")
            return
        selected_mode = str(self.view.led_mode_var.get())
        target_modes = ["10Hz/40%", "10Hz/const", "50Hz/40%", "50Hz/const", "100Hz/40%", "100Hz/const"]
        command_char_list = ['A', 'B', 'C', 'D', 'E', 'F']
        try:
            index = target_modes.index(selected_mode)
        except ValueError:
            self.view.update_led_control_state("LED update failed.", color="red")
            return
        # turn on the selected channels with the new mode
        command_char = command_char_list[index]
        for ch in self._get_selected_led_channels():
            command = f"0{ch}00000000CCG{command_char}\r\n"
            self.serial_manager.send_data(command)
        self.view.update_led_control_state("LED updated.")

    def toggle_serial_receive(self):
        """Toggle the serial receive start or stop."""
        if not self.is_serial_connected:
            return
        if self.is_serial_receiving:
            self._stop_serial_receive()
        else:
            self._start_serial_receive()

    def _start_serial_receive(self):
        """Start receiving data from the selected serial port."""
        # 1. Check and store channels.
        channels_to_receive = self._get_selected_receive_channels()
        if not channels_to_receive:
            self.view.update_receive_data_state("No channel selected.", color="red")
            return
        self.selected_channels_for_log = channels_to_receive
        # 2. Create the output folder and file for logging.
        output_folder = os.path.join(self.base_path, "data", "signal")
        try:
            os.makedirs(output_folder, exist_ok=True)
        except OSError as e:
            self.view.update_receive_data_state(f"Cannot creating directory.", color="red")
            return
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self.log_files = {}
        try:
            for ch in self.selected_channels_for_log:
                filename = f"CH{ch}_{timestamp}.csv"
                full_filepath = os.path.join(output_folder, filename)
                file_handle = open(full_filepath, "w", newline='') # Use newline='' for proper CSV handling
                self.log_files[ch] = file_handle
                header = f"Time(s),CH{ch}_Data(V),Marker\n"
                file_handle.write(header)
            self.start_receiving_time = datetime.datetime.now()
            self.last_receive_time = None
        except IOError as e:
            self.view.update_receive_data_state(f"Create log file failed.", color="red")
            self._close_all_log_files()
            return
        # 3. Update UI and send "start" command to the hardware.
        self.is_serial_receiving = True
        self.view.serial_connect_button.config(state="disabled")
        self.view.receive_ch1_check.config(state="disabled")
        self.view.receive_ch2_check.config(state="disabled")
        self.view.add_marker_button.config(state="normal")
        self.view.serial_receive_button.config(text="Stop Receive")
        command_char = 'J'
        for ch in self._get_selected_receive_channels():
            command = f"0{ch}00000000CC{command_char}\r\n"
            self.serial_manager.send_data(command)
        self.plot_manager.clear_plot()  # Clear the plot before starting to receive data
        self.view.update_receive_data_state("Receiving...")
        self.view.record_receive_button.config(state="disabled")

    def _stop_serial_receive(self):
        """Stop receiving data from the selected serial port."""
        self.is_serial_receiving = False
        self._close_all_log_files()
        # update the UI and send "stop" command to the hardware.
        if not self.is_led_on:
            self.view.serial_connect_button.config(state="normal")
        self.view.receive_ch1_check.config(state="normal")
        self.view.receive_ch2_check.config(state="normal")
        self.view.add_marker_button.config(state="disabled")
        self.view.serial_receive_button.config(text="Start Receive")
        command_char = 'K'
        for ch in self._get_selected_receive_channels():
            command = f"0{ch}00000000CC{command_char}\r\n"
            self.serial_manager.send_data(command)
        self.view.update_receive_data_state("Receiving stopped.")
        if self.is_previewing and not self.is_recording:
            self.view.record_receive_button.config(state="normal")

    def toggle_record_receive(self):
        """Toggle the record and receive start or stop."""
        if not self.is_previewing or not self.is_serial_connected:
            return
        if self.is_record_receive:
            self._stop_record_receive()
        else:
            self._start_record_receive()

    def _start_record_receive(self):
        """Start camera recording and serial receiving at the same time."""
        self._start_recording()
        self._start_serial_receive()
        self.view.record_receive_button.config(state="normal")
        self.view.record_receive_button.config(text="Stop Record & Receive")
        self.view.camera_record_button.config(state="disabled")
        self.view.serial_receive_button.config(state="disabled")
        self.is_record_receive = True

    def _stop_record_receive(self):
        """Stop camera recording and serial receiving at the same time."""
        self.view.camera_record_button.config(state="normal")
        self.view.serial_receive_button.config(state="normal")
        self._stop_recording()
        self._stop_serial_receive()
        self.view.record_receive_button.config(state="normal")
        self.view.record_receive_button.config(text="Start Record & Receive")
        self.is_record_receive = False

    def on_serial_data_received(self, data_bytes):
        """Callback for processing raw bytes from serial, updating plot, and logging data."""
        # 1. Prepare the buffer and check if receiving is active.
        if not self.is_serial_receiving:
            return
        current_time = datetime.datetime.now()
        self.serial_data_buffer += data_bytes
        all_points_from_batch = []
        # 2. Process the serial data buffer to extract valid packets.
        while True:
            # find the start of a packet
            start_pos, channel = -1, 0
            h_pos = self.serial_data_buffer.find(b'H')
            i_pos = self.serial_data_buffer.find(b'I')
            if h_pos != -1 and (i_pos == -1 or h_pos < i_pos):
                start_pos, channel = h_pos, 1
            elif i_pos != -1:
                start_pos, channel = i_pos, 2
            if start_pos == -1:
                break
            next_h_pos = self.serial_data_buffer.find(b'H', start_pos + 1)
            next_i_pos = self.serial_data_buffer.find(b'I', start_pos + 1)
            # find the end of a packet
            end_pos = -1
            if next_h_pos != -1 and (next_i_pos == -1 or next_h_pos < next_i_pos):
                end_pos = next_h_pos
            elif next_i_pos != -1:
                end_pos = next_i_pos
            
            if end_pos == -1:
                break
            # extract the packet payload
            packet_payload_bytes = self.serial_data_buffer[start_pos + 1 : end_pos]
            try:
                packet_payload_str = packet_payload_bytes.decode('ascii')
            except UnicodeDecodeError:
                self.serial_data_buffer = self.serial_data_buffer[end_pos:]
                continue
            self.serial_data_buffer = self.serial_data_buffer[end_pos:]
            parts = packet_payload_str.rstrip('-').split('-') # split by '-'
            if not parts or (len(parts) == 1 and parts[0] == ''): # check if parts is empty
                continue
            if len(parts) % 2 != 0: # if parts length is odd, skip this packet
                continue
            # decode the hex values and calculate the processed value
            for i in range(0, len(parts), 2):
                hex_str = parts[i] + parts[i+1]
                try:
                    value_raw = int(hex_str, 16)
                    value_processed = (value_raw - 32767) * 3.6 / 1024
                    all_points_from_batch.append((channel, value_processed))
                except (ValueError, IndexError):
                    continue
        if not all_points_from_batch:
            return
        # 3. Calculate the time step.
        num_points = len(all_points_from_batch)
        start_time = self.last_receive_time or self.start_receiving_time
        time_diff = current_time - start_time
        time_step = time_diff / num_points if num_points > 0 else datetime.timedelta(0)
        # 4. Update the plot and log files.
        apply_marker_to_first = self.marker_pending # if True, apply marker to the first point
        if self.marker_pending:
            self.marker_pending = False
        for i, (ch, value) in enumerate(all_points_from_batch):
            if ch not in self.selected_channels_for_log:
                continue
            interpolated_time = start_time + (i + 1) * time_step
            relative_time = (interpolated_time - self.start_receiving_time).total_seconds()
            self.plot_manager.add_data_point(ch, relative_time, value)
            # write to the log file
            log_file = self.log_files.get(ch)
            if log_file:
                marker = '1' if i == 0 and apply_marker_to_first else '0'
                row = [f"{relative_time:.4f}", f"{value:.6f}", marker]
                line_to_write = ",".join(row) + "\n"
                log_file.write(line_to_write)
        self.last_receive_time = current_time
        self.root.after(100, self.plot_manager.update_plot) # update the plot after processing data

    def _close_all_log_files(self):
        """Safely close all open log files."""
        for file_handle in self.log_files.values():
            if file_handle and not file_handle.closed:
                file_handle.close()
                print(f"The data is saved in {file_handle.name}")
        self.log_files = {}
            
    def add_marker(self):
        """Set a flag to add a marker to the next logged data point."""
        if not self.is_serial_receiving:
            return
        # set the flag for write to the file
        self.marker_pending = True
        # use plotmanager to add a marker to the plot
        if self.start_receiving_time:
            current_relative_time = (datetime.datetime.now() - self.start_receiving_time).total_seconds()
            self.plot_manager.add_marker(current_relative_time)

    # ============================================
    # -------- General Application Method --------
    # ============================================
    def on_closing(self):
        """Handle the window close event, ensuring a clean shutdown."""
        if self.is_previewing:
            self._stop_preview()
        if self.is_serial_connected:
            self.serial_manager.disconnect()
        if self.is_serial_receiving:
            self._close_all_log_files()
        self.root.destroy()
