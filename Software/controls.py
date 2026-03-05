import tkinter as tk
from tkinter import ttk, messagebox
from functools import partial
import threading
import time

SERVO_PINS = [13, 12, 14, 27, 26, 25]
SERVO_NAMES = ["Base", "Shoulder", "Upper Arm", "Elbow", "Wrist", "Hand"]

class ServoControls:
    def __init__(self, root, serial_manager):
        self.root = root
        self.serial_manager = serial_manager
        self.sequence_manager = None
        self.sliders = []
        self.angle_labels = []
        self.buttons_plus = []
        self.buttons_minus = []
        self._setup_controls()

    def _is_playing(self):
        return bool(self.sequence_manager and self.sequence_manager.is_playing)

    def _setup_controls(self):
        """Set up servo controls in the main frame."""
        frame = ttk.Frame(self.root, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        frame.columnconfigure(2, weight=1)

        for i in range(6):
            servo_label = ttk.Label(frame, text=SERVO_NAMES[i])
            servo_label.grid(row=i, column=0, pady=5, sticky=tk.W)
            btn_decrement = ttk.Button(frame, text='-', width=3, command=partial(self.decrement_angle, i))
            btn_decrement.grid(row=i, column=1, padx=5)
            self.buttons_minus.append(btn_decrement)
            slider = ttk.Scale(frame, from_=0, to=180, orient=tk.HORIZONTAL, command=partial(self.on_slider_change, i))
            slider.set(90)
            slider.grid(row=i, column=2, pady=5, padx=5, sticky=(tk.W, tk.E))
            self.sliders.append(slider)
            btn_increment = ttk.Button(frame, text='+', width=3, command=partial(self.increment_angle, i))
            btn_increment.grid(row=i, column=3, padx=5)
            self.buttons_plus.append(btn_increment)
            angle_label = ttk.Label(frame, text="90°")
            angle_label.grid(row=i, column=4, pady=5, sticky=tk.W)
            self.angle_labels.append(angle_label)

        self.disable_sliders()

    def on_slider_change(self, servo_id, val):
        """Callback for slider movement."""
        angle = int(float(val))
        if servo_id < len(self.angle_labels):
            self.angle_labels[servo_id].config(text=f"{angle}°")
        self.serial_manager.send_servo_angle(servo_id, angle)

    def increment_angle(self, servo_id):
        """Increment servo angle by 5 degrees."""
        if not self.serial_manager.serial_connected:
            messagebox.showwarning("Serial Disconnected", "Please connect via Serial to control the servos.")
            return
        try:
            self.buttons_plus[servo_id].config(state='disabled')
            current_val = self.sliders[servo_id].get()
            new_val = min(current_val + 5, 180)
            self.sliders[servo_id].set(new_val)
            self.serial_manager.send_servo_angle(servo_id, int(new_val))
            self.angle_labels[servo_id].config(text=f"{int(new_val)}°")
            self.root.after(100, lambda: self.buttons_plus[servo_id].config(state='normal'))
        except Exception as e:
            print(f"Error incrementing angle: {e}")

    def decrement_angle(self, servo_id):
        """Decrement servo angle by 5 degrees."""
        if not self.serial_manager.serial_connected:
            messagebox.showwarning("Serial Disconnected", "Please connect via Serial to control the servos.")
            return
        try:
            self.buttons_minus[servo_id].config(state='disabled')
            current_val = self.sliders[servo_id].get()
            new_val = max(current_val - 5, 0)
            self.sliders[servo_id].set(new_val)
            self.serial_manager.send_servo_angle(servo_id, int(new_val))
            self.angle_labels[servo_id].config(text=f"{int(new_val)}°")
            self.root.after(100, lambda: self.buttons_minus[servo_id].config(state='normal'))
        except Exception as e:
            print(f"Error decrementing angle: {e}")

    def home_position(self):
        """Move servos to default position at selected speed."""
        if not self.serial_manager.is_serial_connected():
            messagebox.showwarning("Serial Disconnected", "Please connect via Serial to use the Home function.")
            return
        speed = self.speed_slider.get()
        try:
            command = f"HOME:{int(speed)}\n"
            self.serial_manager.command_queue.put(command)
            for i in range(6):
                threading.Thread(target=self.move_servo_smoothly, args=(i, 90), daemon=True).start()
            for i in range(6):
                self.serial_manager.gui_queue.put((self.sliders[i].set, (90,)))
                self.serial_manager.gui_queue.put((self.angle_labels[i].config, ({"text": f"90°"})))
            messagebox.showinfo("Home Command", "Moving to home position.")
        except Exception as e:
            messagebox.showerror("Home Error", f"Failed to send Home command: {e}")

    def move_servo_smoothly(self, servo_id, target_angle, step=5, delay=20):
        """Smoothly move a servo to the target angle."""
        try:
            current_val = self.sliders[servo_id].get()
            while current_val != target_angle and not self._is_playing():
                if current_val < target_angle:
                    new_val = min(current_val + step, target_angle)
                elif current_val > target_angle:
                    new_val = max(current_val - step, target_angle)
                else:
                    new_val = target_angle
                if new_val != current_val:
                    self.serial_manager.gui_queue.put((self.sliders[servo_id].set, (new_val,)))
                    self.serial_manager.gui_queue.put((self.angle_labels[servo_id].config, ({"text": f"{int(new_val)}°"})))
                    self.serial_manager.send_servo_angle(servo_id, int(new_val))
                    current_val = new_val
                    time.sleep(delay / 1000.0)
        except Exception as e:
            print(f"Error during smooth servo movement: {e}")

    def enable_sliders(self):
        """Enable sliders and buttons."""
        if not self.sliders:
            return
        for slider in self.sliders:
            slider.config(state='normal')
        for btn in self.buttons_plus + self.buttons_minus:
            btn.config(state='normal')

    def disable_sliders(self):
        """Disable sliders and buttons."""
        if not self.sliders:
            return
        for slider in self.sliders:
            if str(slider):
                slider.config(state='disabled')
        for btn in self.buttons_plus + self.buttons_minus:
            if str(btn):
                btn.config(state='disabled')

    def gradual_reset(self, servo_id=0, step=5):
        """Gradually move servos to 90° on startup."""
        if servo_id >= len(self.sliders):
            return
        try:
            current_val = self.sliders[servo_id].get()
            target_val = 90
            if current_val < target_val:
                new_val = min(current_val + step, target_val)
            elif current_val > target_val:
                new_val = max(current_val - step, target_val)
            else:
                new_val = target_val
            if new_val != current_val:
                self.sliders[servo_id].set(new_val)
                self.serial_manager.send_servo_angle(servo_id, int(new_val))
                self.angle_labels[servo_id].config(text=f"{int(new_val)}°")
            self.root.after(50, partial(self.gradual_reset, servo_id + 1, step))
        except Exception as e:
            print(f"Error during gradual reset: {e}")

    # Properties for sequence manager
    @property
    def speed_slider(self):
        return self._speed_slider

    @speed_slider.setter
    def speed_slider(self, value):
        self._speed_slider = value
