import serial
import serial.tools.list_ports
import threading
import queue
import time
import tkinter as tk

# Configure the serial port
SERIAL_PORT = 'COM5'
BAUD_RATE = 115200
TIMEOUT = 1

class SerialManager:
    def __init__(self):
        self.ser = None
        self.serial_connected = False
        self.command_queue = queue.Queue()
        self.gui_queue = queue.Queue()
        threading.Thread(target=self.command_sender, daemon=True).start()

    def process_gui_queue(self):
        """Process the GUI update queue."""
        while not self.gui_queue.empty():
            func, args = self.gui_queue.get()
            func(*args)
        tk._default_root.after(100, self.process_gui_queue)

    def initialize_serial(self):
        """Initialize serial connection."""
        try:
            self.ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT, write_timeout=5)
            time.sleep(2)
            print(f"Connected to {SERIAL_PORT}")
            self.serial_connected = True
            threading.Thread(target=self.read_serial_responses, daemon=True).start()
            return True
        except serial.SerialException as e:
            print(f"Error opening serial port {SERIAL_PORT}: {e}")
            self.ser = None
            self.serial_connected = False
            return False

    def close_serial(self):
        """Close serial connection."""
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
                print("Serial port closed")
            self.ser = None
            self.serial_connected = False
        except Exception as e:
            print(f"Error closing serial: {e}")

    def is_serial_connected(self):
        """Check if the serial connection is active."""
        if self.ser is None:
            return False
        if not self.ser.is_open:
            self.ser = None
            self.serial_connected = False
            return False
        return True

    def send_servo_angle(self, servo_id, angle):
        """Send a command to move a servo to a specific angle."""
        if self.serial_connected and self.is_serial_connected():
            command = f"{servo_id}:{angle}\n"
            if not self.command_queue.full():
                self.command_queue.put(command)
            else:
                print("Command queue is full, dropping command.")

    def command_sender(self):
        """Background thread to send commands from the queue."""
        while True:
            command = self.command_queue.get()
            if command is None:
                break
            if self.serial_connected and self.is_serial_connected():
                try:
                    self.ser.write(command.encode())
                except Exception as e:
                    print(f"Error sending command '{command.strip()}': {e}")
            self.command_queue.task_done()

    def read_serial_responses(self):
        """Background thread to read responses from the serial port."""
        while self.serial_connected and self.is_serial_connected():
            try:
                if self.ser.in_waiting > 0:
                    raw_data = self.ser.readline()
                    try:
                        response = raw_data.decode('utf-8', errors='ignore').strip()
                        if "Servo" in response or "Steps" in response:
                            print(response)
                    except UnicodeDecodeError:
                        continue
            except Exception as e:
                print(f"Error reading serial response: {e}")