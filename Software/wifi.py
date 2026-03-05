import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
import os
import threading
import time

class ControlWindow:
    def __init__(self, root, serial_manager, sequence_manager):
        self.root = root
        self.serial_manager = serial_manager
        self.sequence_manager = sequence_manager
        self.servo_controls = None
        self.wifi_connected = False
        self.wifi_ip = ''
        self.storage_info_label = None

    def open_control_window(self):
        """Open a new window to execute sequences over Wi-Fi or Serial."""
        exec_window = tk.Toplevel(self.root)
        exec_window.title("Control")
        exec_window.geometry("600x400")
        exec_window.columnconfigure(0, weight=1)
        exec_window.columnconfigure(1, weight=1)
        exec_window.rowconfigure(0, weight=1)

        # Serial Frame
        serial_frame = ttk.LabelFrame(exec_window, text="Serial Connection")
        serial_frame.grid(row=0, column=0, padx=10, pady=10, sticky=(tk.N, tk.S, tk.E, tk.W))
        serial_frame.columnconfigure(0, weight=1)
        serial_frame.columnconfigure(1, weight=1)
        serial_frame.rowconfigure(2, weight=1)

        serial_status = ttk.Label(serial_frame, text="Not Connected", foreground="red")
        serial_status.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        serial_button = ttk.Button(serial_frame, text="Connect", command=lambda: self.connect_serial_control(serial_status, serial_button, serial_seq_listbox, serial_ip_label))
        serial_button.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        serial_ip_label = ttk.Label(serial_frame, text="ESP32 IP: N/A")
        serial_ip_label.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)

        serial_seq_frame = ttk.Frame(serial_frame)
        serial_seq_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=(tk.N, tk.S, tk.E, tk.W))
        serial_seq_listbox = tk.Listbox(serial_seq_frame, height=15, width=40, selectmode=tk.SINGLE)
        serial_seq_listbox.pack(side='left', fill='both', expand=True)
        serial_scrollbar_y = ttk.Scrollbar(serial_seq_frame, orient='vertical', command=serial_seq_listbox.yview)
        serial_scrollbar_y.pack(side='right', fill='y')
        serial_seq_listbox.config(yscrollcommand=serial_scrollbar_y.set)

        serial_buttons_frame = ttk.Frame(serial_frame)
        serial_buttons_frame.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)
        ttk.Button(serial_buttons_frame, text="Upload Sequence", command=lambda: self.upload_sequence_serial(serial_seq_listbox)).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Button(serial_buttons_frame, text="Remove Sequence", command=lambda: self.remove_sequence_serial(serial_seq_listbox)).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        # Wi-Fi Frame
        wifi_frame = ttk.LabelFrame(exec_window, text="Wi-Fi Connection")
        wifi_frame.grid(row=0, column=1, padx=10, pady=10, sticky=(tk.N, tk.S, tk.E, tk.W))
        wifi_frame.columnconfigure(0, weight=1)
        wifi_frame.columnconfigure(1, weight=1)
        wifi_frame.rowconfigure(2, weight=1)

        ttk.Label(wifi_frame, text="ESP32 IP:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        wifi_ip_entry = ttk.Entry(wifi_frame)
        wifi_ip_entry.insert(0, '192.168.1.21')
        wifi_ip_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Button(wifi_frame, text="Connect", command=lambda: self.connect_wifi_control(wifi_ip_entry.get(), wifi_seq_listbox)).grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)

        wifi_seq_frame = ttk.Frame(wifi_frame)
        wifi_seq_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=(tk.N, tk.S, tk.E, tk.W))
        wifi_seq_listbox = tk.Listbox(wifi_seq_frame, height=15, width=40, selectmode=tk.SINGLE)
        wifi_seq_listbox.pack(side='left', fill='both', expand=True)
        wifi_scrollbar_y = ttk.Scrollbar(wifi_seq_frame, orient='vertical', command=wifi_seq_listbox.yview)
        wifi_scrollbar_y.pack(side='right', fill='y')
        wifi_seq_listbox.config(yscrollcommand=wifi_scrollbar_y.set)

        ttk.Button(wifi_frame, text="Execute Sequence", command=lambda: self.execute_selected_sequence_wifi(wifi_seq_listbox)).grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)
        ttk.Label(wifi_frame, text="Playback Speed:").grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        wifi_speed_slider = ttk.Scale(wifi_frame, from_=1, to=10, orient=tk.HORIZONTAL)
        wifi_speed_slider.set(5)
        wifi_speed_slider.grid(row=4, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        wifi_speed_value_label = ttk.Label(wifi_frame, text="5")
        wifi_speed_value_label.grid(row=4, column=2, padx=5, pady=5, sticky=tk.W)
        wifi_speed_slider.config(command=lambda val: wifi_speed_value_label.config(text=str(int(float(val)))))

        # Storage Info
        self.storage_info_label = ttk.Label(exec_window, text="Storage: N/A", anchor='w')
        self.storage_info_label.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky=(tk.W, tk.E))

    def connect_serial_control(self, status_label, button, serial_seq_listbox, ip_label):
        """Connect or disconnect the Serial connection and update the serial listbox."""
        if self.serial_manager.serial_connected:
            self.serial_manager.close_serial()
            status_label.config(text="Not Connected", foreground="red")
            button.config(text="Connect")
            serial_seq_listbox.delete(0, tk.END)
            ip_label.config(text="ESP32 IP: N/A")
            if self.servo_controls:
                self.servo_controls.disable_sliders()
            messagebox.showinfo("Disconnected", "Serial connection closed.")
            return

        def initialize_and_update():
            if self.serial_manager.initialize_serial():
                if self.servo_controls:
                    self.servo_controls.enable_sliders()
                status_label.config(text="Connected", foreground="green")
                button.config(text="Disconnect")
                self.serial_manager.ser.reset_input_buffer()
                self.serial_manager.ser.write("GET_IP\n".encode())
                start_time = time.time()
                ip_received = False
                while time.time() - start_time < 5:
                    if self.serial_manager.ser.in_waiting > 0:
                        raw_ip = self.serial_manager.ser.readline()
                        try:
                            esp32_ip = raw_ip.decode('utf-8', errors='ignore').strip()
                            if esp32_ip:
                                ip_label.config(text=f"ESP32 IP: {esp32_ip}")
                                ip_received = True
                                break
                        except UnicodeDecodeError:
                            continue
                if not ip_received:
                    ip_label.config(text="ESP32 IP: N/A")
                sequences = self.get_sequence_list_serial()
                serial_seq_listbox.delete(0, tk.END)
                for seq in sequences:
                    serial_seq_listbox.insert(tk.END, seq)
                messagebox.showinfo("Connected", "Serial connection established.")
                self.update_storage_info()
            else:
                messagebox.showerror("Connection Error", "Failed to establish Serial connection.")

        threading.Thread(target=initialize_and_update, daemon=True).start()

    def get_sequence_list_serial(self):
        """Retrieve the list of sequences from ESP32 via Serial."""
        if not self.serial_manager.is_serial_connected():
            return []
        try:
            self.serial_manager.ser.reset_input_buffer()
            self.serial_manager.ser.write("LIST_SEQUENCES\n".encode())
            sequences = []
            start_time = time.time()
            while time.time() - start_time < 5:
                if self.serial_manager.ser.in_waiting > 0:
                    line = self.serial_manager.ser.readline().decode('utf-8', errors='ignore').strip()
                    if line == "END_OF_LIST":
                        break
                    if line:
                        sequences.append(line)
            return sequences
        except Exception as e:
            print(f"Error retrieving sequence list over Serial: {e}")
            return []

    def upload_sequence_serial(self, serial_seq_listbox):
        """Upload a sequence to the ESP32 via Serial."""
        if self.sequence_manager and self.sequence_manager.is_playing:
            print("Playback in progress. Cannot upload sequences.")
            messagebox.showwarning("Playback in Progress", "Cannot upload sequences while playback is in progress.")
            return
        if not self.serial_manager.is_serial_connected():
            print("Serial connection required for uploading sequences.")
            messagebox.showerror("Serial Connection Required", "Please connect via Serial to upload sequences.")
            return

        file_path = filedialog.askopenfilename(defaultextension=".bin", filetypes=[("Binary Files", "*.bin")], title="Select Sequence File to Upload")
        if not file_path:
            print("Upload cancelled by the user.")
            return

        filename = os.path.basename(file_path)
        print(f"Attempting to upload sequence: {filename}")
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
            file_size = len(file_data)
            self.serial_manager.ser.reset_input_buffer()
            self.serial_manager.ser.reset_output_buffer()
            start_command = f"BEGIN_UPLOAD:{filename}:{file_size}\n"
            self.serial_manager.ser.write(start_command.encode())
            print(f"Upload command sent. Filename: {filename}, Size: {file_size} bytes")

            start_time = time.time()
            ack_received = False
            while time.time() - start_time < 10:
                if self.serial_manager.ser.in_waiting > 0:
                    ack = self.serial_manager.ser.readline()
                    try:
                        ack_str = ack.decode('utf-8', errors='ignore').strip()
                        if ack_str == "ACK":
                            ack_received = True
                            break
                        elif ack_str.startswith("ERROR") or ack_str == "STORAGE_FULL":
                            print(f"Upload failed. Error from ESP32: {ack_str}")
                            messagebox.showerror("Upload Failed", f"ESP32 responded with: {ack_str}")
                            return
                    except UnicodeDecodeError:
                        continue

            if not ack_received:
                print("No ACK received from ESP32. Upload failed.")
                messagebox.showerror("Upload Failed", "No ACK received from ESP32.")
                return

            chunk_size = 128
            for i in range(0, file_size, chunk_size):
                chunk = file_data[i:i+chunk_size]
                self.serial_manager.ser.write(chunk)
                self.serial_manager.ser.flush()
                time.sleep(0.1)

            end_command = "END_UPLOAD\n"
            self.serial_manager.ser.write(end_command.encode())
            print("Upload data sent. Waiting for confirmation from ESP32...")

            start_time = time.time()
            success_received = False
            while time.time() - start_time < 15:
                if self.serial_manager.ser.in_waiting > 0:
                    response = self.serial_manager.ser.readline()
                    try:
                        response_str = response.decode('utf-8', errors='ignore').strip()
                        if response_str == "UPLOAD_SUCCESS":
                            print(f"Sequence '{filename}' uploaded successfully.")
                            messagebox.showinfo("Upload Successful", f"Sequence '{filename}' uploaded successfully.")
                            success_received = True
                            break
                        elif response_str == "STORAGE_FULL":
                            print("ESP32 storage is full. Cannot upload the sequence.")
                            messagebox.showerror("Upload Failed", "ESP32 storage is full. Cannot upload the sequence.")
                            break
                        elif response_str.startswith("ERROR"):
                            print(f"Upload failed. Error from ESP32: {response_str}")
                            messagebox.showerror("Upload Failed", f"ESP32 responded with: {response_str}")
                            break
                    except UnicodeDecodeError:
                        continue

            if not success_received:
                print("No confirmation received from ESP32. Upload failed.")
                messagebox.showerror("Upload Failed", "No confirmation received from ESP32.")

            self.serial_manager.ser.reset_input_buffer()
            if self.serial_manager.serial_connected:
                sequences = self.get_sequence_list_serial()
                serial_seq_listbox.delete(0, tk.END)
                for seq in sequences:
                    serial_seq_listbox.insert(tk.END, seq)
        except Exception as e:
            print(f"Failed to upload sequence. Error: {e}")
            messagebox.showerror("Upload Failed", f"Failed to upload sequence: {e}")

    def remove_sequence_serial(self, serial_seq_listbox):
        """Remove a selected sequence from the ESP32 via Serial."""
        if not self.serial_manager.is_serial_connected():
            print("Serial connection required to remove sequences.")
            messagebox.showerror("Serial Connection Required", "Please connect via Serial to remove sequences.")
            return

        sequence_name = serial_seq_listbox.get(tk.ACTIVE)
        if not sequence_name:
            print("No sequence selected for removal.")
            messagebox.showwarning("No Selection", "Please select a sequence to remove.")
            return

        print(f"Attempting to remove sequence: {sequence_name}")
        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{sequence_name}'?")
        if not confirm:
            print("Sequence removal cancelled by the user.")
            return

        try:
            command = f"DELETE_SEQUENCE:{sequence_name}\n"
            self.serial_manager.ser.reset_input_buffer()
            self.serial_manager.ser.write(command.encode())
            start_time = time.time()
            response_received = False
            while time.time() - start_time < 10:
                if self.serial_manager.ser.in_waiting > 0:
                    response = self.serial_manager.ser.readline()
                    try:
                        response_str = response.decode('utf-8', errors='ignore').strip()
                        if response_str == "DELETE_SUCCESS":
                            print(f"Sequence '{sequence_name}' deleted successfully.")
                            messagebox.showinfo("Sequence Deleted", f"Sequence '{sequence_name}' deleted successfully.")
                            response_received = True
                            break
                        elif response_str.startswith("ERROR"):
                            print(f"Failed to delete sequence. ESP32 responded with: {response_str}")
                            messagebox.showerror("Delete Failed", f"ESP32 responded with: {response_str}")
                            response_received = True
                            break
                    except UnicodeDecodeError:
                        continue

            if not response_received:
                print("No response received from ESP32. Sequence removal failed.")
                messagebox.showerror("Delete Failed", "No response received from ESP32.")

            if self.serial_manager.serial_connected:
                sequences = self.get_sequence_list_serial()
                serial_seq_listbox.delete(0, tk.END)
                for seq in sequences:
                    serial_seq_listbox.insert(tk.END, seq)
        except Exception as e:
            print(f"Failed to delete sequence. Error: {e}")
            messagebox.showerror("Delete Failed", f"Failed to delete sequence: {e}")

    def connect_wifi_control(self, ip_address, wifi_seq_listbox):
        """Connect to the ESP32 via Wi-Fi and populate the Wi-Fi listbox."""
        self.wifi_ip = ip_address.strip()
        if not self.wifi_ip:
            messagebox.showwarning("Invalid IP", "Please enter a valid IP address.")
            return
        try:
            url = f"http://{self.wifi_ip}/list_sequences"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                sequences = response.json()
                wifi_seq_listbox.delete(0, tk.END)
                for seq in sequences:
                    wifi_seq_listbox.insert(tk.END, seq)
                self.wifi_connected = True
                messagebox.showinfo("Wi-Fi Connected", f"Connected to ESP32 at {self.wifi_ip}")
            else:
                messagebox.showerror("Connection Failed", f"Failed to connect to ESP32: {response.text}")
                self.wifi_connected = False
        except Exception as e:
            messagebox.showerror("Connection Failed", f"Failed to connect to ESP32: {e}")
            self.wifi_connected = False

    def execute_selected_sequence_wifi(self, wifi_seq_listbox):
        """Execute the selected sequence via Wi-Fi with retry logic and speed control."""
        sequence_name = wifi_seq_listbox.get(tk.ACTIVE)
        if not sequence_name:
            messagebox.showwarning("No Selection", "Please select a sequence to execute.")
            return
        playback_speed = int(wifi_seq_listbox.master.master.children['!scale'].get())

        print(f"Attempting to execute sequence: {sequence_name} via Wi-Fi at speed {playback_speed}")

        if self.wifi_connected:
            for attempt in range(3):
                try:
                    url = f"http://{self.wifi_ip}/execute_sequence"
                    response = requests.post(url, data={'sequence': sequence_name, 'speed': playback_speed}, timeout=10)
                    if response.status_code == 200:
                        print(f"Sequence '{sequence_name}' execution started successfully at speed {playback_speed}.")
                        messagebox.showinfo("Execution Started", f"Sequence '{sequence_name}' is being executed at speed {playback_speed}.")
                        return
                    else:
                        print(f"Attempt {attempt + 1}: Failed to execute sequence. Response: {response.text}")
                except Exception as e:
                    print(f"Attempt {attempt + 1}: Error executing sequence: {e}")
            print(f"Failed to execute sequence '{sequence_name}' via Wi-Fi after 3 attempts.")
            messagebox.showerror("Execution Failed", f"Failed to execute sequence via Wi-Fi after 3 attempts.")
        else:
            print("Wi-Fi connection required to execute sequences.")
            messagebox.showerror("No Connection", "Please connect via Wi-Fi to execute sequences.")

    def update_storage_info(self):
        """Request storage info from ESP32 and update the status bar."""
        if self.serial_manager.is_serial_connected():
            self.serial_manager.ser.write("GET_STORAGE_INFO\n".encode())
            start_time = time.time()
            while time.time() - start_time < 5:
                if self.serial_manager.ser.in_waiting > 0:
                    line = self.serial_manager.ser.readline().decode('utf-8', errors='ignore').strip()
                    if line.startswith("STORAGE_INFO"):
                        try:
                            _, used_bytes, total_bytes = line.split(':')
                            used_kb = int(used_bytes) / 1024
                            total_kb = int(total_bytes) / 1024
                            self.storage_info_label.config(text=f"Storage: {used_kb:.2f} KB / {total_kb:.2f} KB used")
                            print(f"Storage Info - Used: {used_kb:.2f} KB / Total: {total_kb:.2f} KB")
                        except ValueError:
                            print(f"Unexpected format in storage info: {line}")
                        return
            self.storage_info_label.config(text="Storage: N/A")
            print("Failed to retrieve storage info.")
