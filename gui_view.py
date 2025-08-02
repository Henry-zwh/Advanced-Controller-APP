import tkinter as tk
from tkinter import ttk


class CameraControlPanel:
    """A control panel for a single camera in the GUI."""

    def __init__(self, parent, controller, camera_id):
        self.frame = ttk.Frame(parent)
        self.camera_id = camera_id
        self.controller = controller
        self.selected_camera_var = tk.StringVar()
        self.selected_resolution_var = tk.StringVar()
        # create widgets for camera control
        ttk.Label(self.frame, text=f"Camera {camera_id+1}:").pack(side=tk.LEFT, padx=(0, 5))
        self.camera_menu = ttk.OptionMenu(self.frame, self.selected_camera_var, "Scanning...")
        self.camera_menu.pack(side=tk.LEFT, padx=5)
        self.camera_menu.config(state="disabled")
        ttk.Label(self.frame, text="Resolution:").pack(side=tk.LEFT, padx=(10, 5))
        self.resolution_menu = ttk.OptionMenu(self.frame, self.selected_resolution_var, "Choose Camera First")
        self.resolution_menu.pack(side=tk.LEFT, padx=5)
        self.resolution_menu.config(state="disabled")

    def grid(self, **kwargs):
        self.frame.grid(**kwargs)


class AppGUI:
    """Main GUI class for the application."""

    def __init__(self, root, controller):
        """Initialize the GUI"""
        self.root = root
        self.controller = controller
        self.root.title("Advanced Controller APP")
        self.camera_panels = []
        self.camera_canvases = []
        self._create_widgets()

    def _create_widgets(self):
        """Create and layout all GUI components."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # === Camera Panels ===
        panel1 = CameraControlPanel(main_frame, self.controller, 0)
        panel1.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.camera_panels.append(panel1)
        panel2 = CameraControlPanel(main_frame, self.controller, 1)
        panel2.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.camera_panels.append(panel2)

        # === Camera Canvases ===
        camera_canvas_frame = ttk.Frame(main_frame)
        camera_canvas_frame.grid(row=2, column=0, sticky="nsew")
        main_frame.rowconfigure(2, weight=1)
        camera_canvas_frame.columnconfigure(0, weight=1)
        camera_canvas_frame.columnconfigure(1, weight=1)
        camera_canvas_frame.rowconfigure(0, weight=1)
        canvas1 = tk.Canvas(camera_canvas_frame, bg="black")
        canvas1.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.camera_canvases.append(canvas1)
        canvas2 = tk.Canvas(camera_canvas_frame, bg="black")
        canvas2.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self.camera_canvases.append(canvas2)
        
        # === Global Camera Controls ===
        global_camera_control_frame = ttk.Frame(main_frame)
        global_camera_control_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        self.camera_refresh_button = ttk.Button(global_camera_control_frame, text="Refresh Cameras", command=self.controller.refresh_cameras)
        self.camera_refresh_button.pack(side=tk.LEFT, padx=(0, 5))
        self.camera_preview_button = ttk.Button(global_camera_control_frame, text="Start Preview", command=self.controller.toggle_preview, state="disabled")
        self.camera_preview_button.pack(side=tk.LEFT, padx=5)
        self.camera_record_button = ttk.Button(global_camera_control_frame, text="Start Record", command=self.controller.toggle_recording, state="disabled")
        self.camera_record_button.pack(side=tk.LEFT, padx=5)
        self.camera_state_label = ttk.Label(global_camera_control_frame, text="State: Initializing...")
        self.camera_state_label.pack(side=tk.RIGHT, padx=5)
        
        # === Port Connection Widgets ===
        ttk.Separator(main_frame, orient='horizontal').grid(row=4, column=0, sticky='ew', pady=15)
        serial_conn_frame = ttk.Frame(main_frame)
        serial_conn_frame.grid(row=5, column=0, sticky='ew', pady=(0, 5))
        ttk.Label(serial_conn_frame, text="Port:").pack(side=tk.LEFT)
        self.serial_port_var = tk.StringVar()
        self.serial_port_menu = ttk.OptionMenu(serial_conn_frame, self.serial_port_var, "No Ports")
        self.serial_port_menu.pack(side=tk.LEFT, padx=(5, 10))
        ttk.Label(serial_conn_frame, text="Baudrate:").pack(side=tk.LEFT)
        self.serial_baudrate_var = tk.StringVar()
        common_baudrates = ['9600', '19200', '38400', '57600', '115200']
        self.serial_baudrate_menu = ttk.OptionMenu(serial_conn_frame, self.serial_baudrate_var, common_baudrates[4], *common_baudrates)
        self.serial_baudrate_menu.pack(side=tk.LEFT, padx=5)
        self.serial_refresh_button = ttk.Button(serial_conn_frame, text="Refresh Ports", command=self.controller.refresh_serial_ports)
        self.serial_refresh_button.pack(side=tk.LEFT, padx=5)
        self.serial_connect_button = ttk.Button(serial_conn_frame, text="Connect", command=self.controller.toggle_serial_connection)
        self.serial_connect_button.pack(side=tk.LEFT, padx=5)
        self.serial_state_label = ttk.Label(serial_conn_frame, text="State: Disconnected.")
        self.serial_state_label.pack(side=tk.RIGHT, padx=5)

        # === LED Widgets ===
        led_control_frame = ttk.Frame(main_frame)
        led_control_frame.grid(row=6, column=0, sticky='ew', pady=(0, 5))
        self.led_channel1_var = tk.BooleanVar(value=True)
        self.led_channel2_var = tk.BooleanVar(value=True)
        self.led_ch1_check = ttk.Checkbutton(led_control_frame, text="CH 1", variable=self.led_channel1_var)
        self.led_ch1_check.pack(side=tk.LEFT)
        self.led_ch2_check = ttk.Checkbutton(led_control_frame, text="CH 2", variable=self.led_channel2_var)
        self.led_ch2_check.pack(side=tk.LEFT, padx=5)
        ttk.Label(led_control_frame, text="Mode:").pack(side=tk.LEFT)
        self.led_mode_var = tk.StringVar()
        modes = ["10Hz/40%", "10Hz/const", "50Hz/40%", "50Hz/const", "100Hz/40%", "100Hz/const"]
        self.led_mode_menu = ttk.OptionMenu(led_control_frame, self.led_mode_var, modes[0], *modes)
        self.led_mode_menu.pack(side=tk.LEFT, padx=5)
        self.serial_led_button = ttk.Button(led_control_frame, text="LED On", command=self.controller.toggle_led)
        self.serial_led_button.pack(side=tk.LEFT, padx=5)
        self.led_update_button = ttk.Button(led_control_frame, text="Update LED", command=self.controller.update_led)
        self.led_update_button.pack(side=tk.LEFT, padx=5)
        self.led_control_state_label = ttk.Label(led_control_frame, text="LED off.")
        self.led_control_state_label.pack(side=tk.RIGHT, padx=5)

        # === Receive Data Widgets ===
        receive_control_frame = ttk.Frame(main_frame)
        receive_control_frame.grid(row=7, column=0, sticky='ew', pady=(0, 5))
        self.receive_channel1_var = tk.BooleanVar(value=True)
        self.receive_channel2_var = tk.BooleanVar(value=True)
        self.receive_ch1_check = ttk.Checkbutton(receive_control_frame, text="CH 1", variable=self.receive_channel1_var)
        self.receive_ch1_check.pack(side=tk.LEFT)
        self.receive_ch2_check = ttk.Checkbutton(receive_control_frame, text="CH 2", variable=self.receive_channel2_var)
        self.receive_ch2_check.pack(side=tk.LEFT, padx=5)
        self.serial_receive_button = ttk.Button(receive_control_frame, text="Start Receive", command=self.controller.toggle_serial_receive)
        self.serial_receive_button.pack(side=tk.LEFT)
        self.record_receive_button = ttk.Button(receive_control_frame, text="Start Record & Receive", command=self.controller.toggle_record_receive)
        self.record_receive_button.pack(side=tk.LEFT)
        self.add_marker_button = ttk.Button(receive_control_frame, text="Add Marker", command=self.controller.add_marker)
        self.add_marker_button.pack(side=tk.LEFT, padx=5)
        self.receive_data_state_label = ttk.Label(receive_control_frame, text="Receiving stopped.")
        self.receive_data_state_label.pack(side=tk.RIGHT, padx=5)
        
        # === Serial Plot Frame ===
        self.serial_plot_frame = ttk.Frame(main_frame)
        self.serial_plot_frame.grid(row=8, column=0, sticky='nsew', pady=(5,0))
        main_frame.rowconfigure(8, weight=1)


    # ============================================
    # ---------- Generic Update Methods ----------
    # ============================================
    def get_camera_panel(self, camera_id):
        """Get the camera control panel."""
        return self.camera_panels[camera_id]

    def get_camera_canvas(self, camera_id):
        """Get the canvas for displaying camera images."""
        return self.camera_canvases[camera_id]

    def update_dropdown_menu(self, menu, var, options, default_value=None):
        """Update a dropdown menu with new options."""
        menu['menu'].delete(0, 'end')
        if options:
            menu['menu'].add_command(label="--none--", command=tk._setit(var, "--none--"))
            for option in options:
                menu['menu'].add_command(label=option, command=tk._setit(var, option))
            var.set(default_value if default_value else "--none--")
            menu.config(state="normal")
        else:
            var.set("no options")
            menu.config(state="disabled")
    
    def update_camera_state(self, text, color="black"):
        """Update the camera state label."""
        self.camera_state_label.config(text=text, foreground=color)

    def update_serial_state(self, text, color="black"):
        """Update the serial state label."""
        self.serial_state_label.config(text=text, foreground=color)

    def update_led_control_state(self, text, color="black"):
        """Update the led control state label."""
        self.led_control_state_label.config(text=text, foreground=color)

    def update_receive_data_state(self, text, color="black"):
        """Update the receive data state label."""
        self.receive_data_state_label.config(text=text, foreground=color)


    # ============================================
    # -------- Camera-Specific UI Methods --------
    # ============================================
    def update_camera_menu(self, camera_id, camera_list):
        """Update the camera selection menu."""
        panel = self.get_camera_panel(camera_id)
        self.update_dropdown_menu(panel.camera_menu, panel.selected_camera_var, camera_list)
        if not camera_list:
            panel.selected_camera_var.set("no cameras")
        else:
            self.camera_preview_button.config(state="normal")

    def update_camera_resolution_menu(self, camera_id, res_list):
        """Update the resolution selection menu for the chosen camera."""
        panel = self.get_camera_panel(camera_id)
        default_res = res_list[len(res_list) // 2] if res_list else None
        self.update_dropdown_menu(panel.resolution_menu, panel.selected_resolution_var, res_list, default_res)

    def display_camera_image(self, camera_id, image):
        """Display a camera image on the corresponding canvas."""
        canvas = self.get_camera_canvas(camera_id)
        canvas.create_image(0, 0, image=image, anchor=tk.NW)
        canvas.image = image

    def set_camera_preview_state(self, is_previewing):
        """Update the GUI based on the camera preview state."""
        if is_previewing:
            self.camera_preview_button.config(text="Stop Preview")
            self.camera_record_button.config(state="normal")
            self.camera_refresh_button.config(state="disabled")
            for panel in self.camera_panels:
                panel.camera_menu.config(state="disabled")
                panel.resolution_menu.config(state="disabled")
            self.update_camera_state(f"State: Previewing...")
        else:
            self.camera_preview_button.config(text="Start Preview")
            self.camera_record_button.config(state="disabled", text="Start Record")
            self.camera_refresh_button.config(state="normal")
            for panel in self.camera_panels:
                panel.camera_menu.config(state="normal")
                panel.resolution_menu.config(state="normal")
            self.update_camera_state("State: Preview Available.")
            for canvas in self.camera_canvases:
                canvas.delete("all")

    def set_camera_recording_state(self, is_recording, is_previewing):
        """Update the GUI based on the camera recording state."""
        if is_recording:
            self.camera_record_button.config(text="Stop Record")
            self.camera_preview_button.config(state="disabled")
            self.update_camera_state("State: Recording...")
        else:
            self.camera_record_button.config(text="Start Record")
            if is_previewing:
                 self.camera_preview_button.config(state="normal")
            
            if is_previewing:
                self.update_camera_state("State: Previewing...")
            else:
                self.update_camera_state("State: Preview Available.")


    # ============================================
    # -------- Serial-Specific UI Methods --------
    # ============================================
    def update_serial_port_menu(self, port_list):
        """Update the serial port selection menu."""
        self.update_dropdown_menu(self.serial_port_menu, self.serial_port_var, port_list)
        # enable connect button only if ports are found
        if not port_list:
            self.serial_port_var.set("no ports")
        else:
            self.serial_connect_button.config(state="normal")

    def set_serial_controls_state(self, state):
        """Set the state of serial control widgets."""
        # led control widgets
        self.led_ch1_check.config(state=state)
        self.led_ch2_check.config(state=state)
        self.led_mode_menu.config(state=state)
        self.serial_led_button.config(state=state)
        self.led_update_button.config(state=state)
        # receive data widgets
        self.receive_ch1_check.config(state=state)
        self.receive_ch2_check.config(state=state)
        self.serial_receive_button.config(state=state)
        self.add_marker_button.config(state=state)
        self.record_receive_button.config(state=state)

    def set_serial_connected_state(self, is_connected, port_name=""):
        """Update the GUI based on the serial connection state."""
        if is_connected:
            self.serial_connect_button.config(text="Disconnect")
            self.serial_port_menu.config(state="disabled")
            self.serial_baudrate_menu.config(state="disabled")
            self.serial_refresh_button.config(state="disabled")
            self.update_serial_state(f"State: Connected to {port_name}.")
            self.set_serial_controls_state("normal")
            self.led_update_button.config(state="disabled")
            self.add_marker_button.config(state="disabled")
        else:
            self.serial_connect_button.config(text="Connect")
            self.serial_port_menu.config(state="normal")
            self.serial_baudrate_menu.config(state="normal")
            self.serial_refresh_button.config(state="normal")
            self.update_serial_state("State: Disconnected.")
            self.set_serial_controls_state("disabled")
