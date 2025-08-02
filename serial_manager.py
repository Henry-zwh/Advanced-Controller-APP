import serial
import serial.tools.list_ports
import threading
import time


class SerialManager:
    """Manages serial port communication."""
    """Including finding ports, connecting, and handling reading/writing in a separate thread."""

    def __init__(self, data_received_callback=None):
        """Initialize the SerialManager."""
        self.serial_port = None
        self.is_connected = False
        self.read_thread = None
        self.stop_thread_event = threading.Event()
        self.data_received_callback = data_received_callback

    @staticmethod
    def find_serial_ports():
        """Scan and return a list of available serial ports."""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    
    def connect(self, port, baudrate=9600):
        """Connect to the chosen serial port."""
        if self.is_connected:
            return True
        try:
            self.serial_port = serial.Serial(port, baudrate, timeout=1)
            self.is_connected = True
            # start the reading thread
            self.stop_thread_event.clear()
            self.read_thread = threading.Thread(target=self._read_from_port, daemon=True)
            self.read_thread.start()
            return True
        except serial.SerialException as e:
            self.serial_port = None
            return False
        
    def disconnect(self):
        """Disconnect from the current serial port."""
        if not self.is_connected:
            return
        self.stop_thread_event.set()
        if self.read_thread:
            self.read_thread.join() # wait for the thread to terminate
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.is_connected = False
        self.serial_port = None

    def _read_from_port(self):
        """Private method that runs in a thread to continuously read data from the serial port."""
        while not self.stop_thread_event.is_set():
            try:
                if self.serial_port and self.serial_port.in_waiting > 0:
                    # Read all available bytes in the buffer
                    data_bytes = self.serial_port.read(self.serial_port.in_waiting)
                    if data_bytes and self.data_received_callback:
                        # Pass raw bytes to the callback for processing
                        self.data_received_callback(data_bytes)
            except serial.SerialException:
                self.disconnect()
                break
            time.sleep(0.01)

    def send_data(self, data):
        """Send data to the connected serial port."""
        if self.is_connected and self.serial_port:
            self.serial_port.write(data.encode('utf-8'))

