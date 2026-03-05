import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import struct
from utils import ease_in_out_sine

class SequenceManager:
    def __init__(self, root, serial_manager, servo_controls, control_window):
        self.root = root
        self.serial_manager = serial_manager
        self.servo_controls = servo_controls
        self.control_window = control_window  # Store the ControlWindow instance
        self.saved_positions = []
        self.is_playing = False
        self.playback_thread = None
        self.listbox = None
        self.speed_slider = None
        self._setup_sequence_controls()

    def _setup_sequence_controls(self):
        """Set up sequence management controls."""
        seq_frame = ttk.Frame(self.root, padding="10")
        seq_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        ttk.Separator(self.root, orient='horizontal').grid(row=1, column=0, sticky=(tk.W, tk.E), pady=10)

        buttons_frame = ttk.LabelFrame(seq_frame, text="Position Management")
        buttons_frame.grid(row=0, column=0, columnspan=5, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(buttons_frame, text="Save Position", command=self.save_position).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Button(buttons_frame, text="Remove Position", command=self.remove_position).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Button(buttons_frame, text="Move Up", command=self.move_up).grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        ttk.Button(buttons_frame, text="Move Down", command=self.move_down).grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)

        self.listbox = tk.Listbox(seq_frame, height=10, width=50, selectmode=tk.MULTIPLE)
        self.listbox.grid(row=1, column=0, columnspan=5, pady=5, sticky=(tk.W, tk.E))
        scrollbar = ttk.Scrollbar(seq_frame, orient='vertical', command=self.listbox.yview)
        scrollbar.grid(row=1, column=5, sticky=(tk.N, tk.S))
        self.listbox.configure(yscrollcommand=scrollbar.set)

        playback_frame = ttk.LabelFrame(seq_frame, text="Playback Controls")
        playback_frame.grid(row=2, column=0, columnspan=5, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(playback_frame, text="Play Sequence", command=self.play_sequence).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Button(playback_frame, text="Play Position", command=self.play_selected_position).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Button(playback_frame, text="Stop Playback", command=self.stop_playback).grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        ttk.Button(playback_frame, text="Save Sequence", command=self.export_sequence).grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)

        other_controls_frame = ttk.LabelFrame(seq_frame, text="Other Controls")
        other_controls_frame.grid(row=3, column=0, columnspan=5, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(other_controls_frame, text="Control", command=self.control_window.open_control_window).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)  # Use existing instance
        ttk.Button(other_controls_frame, text="Home", command=self.servo_controls.home_position).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Label(other_controls_frame, text="Playback Speed:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.servo_controls.speed_slider = ttk.Scale(other_controls_frame, from_=1, to=10, orient=tk.HORIZONTAL)
        self.servo_controls.speed_slider.set(5)
        self.servo_controls.speed_slider.grid(row=0, column=3, padx=5, pady=5, sticky=(tk.W, tk.E))
        speed_value_label = ttk.Label(other_controls_frame, text="5")
        speed_value_label.grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        self.servo_controls.speed_slider.config(command=lambda val: speed_value_label.config(text=str(int(float(val)))))

        for i in range(5):
            seq_frame.columnconfigure(i, weight=1)

    def save_position(self):
        """Save the current servo positions."""
        if self.is_playing:
            messagebox.showwarning("Playback in Progress", "Cannot save positions while playback is in progress.")
            return
        angles = [int(slider.get()) for slider in self.servo_controls.sliders]
        self.saved_positions.append(angles)
        position_str = ','.join(map(str, angles))
        self.listbox.insert(tk.END, position_str)

    def remove_position(self):
        """Remove selected saved positions."""
        if self.is_playing:
            messagebox.showwarning("Playback in Progress", "Cannot remove positions while playback is in progress.")
            return
        selected_indices = list(self.listbox.curselection())
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select positions to remove.")
            return
        for index in reversed(selected_indices):
            self.listbox.delete(index)
            self.saved_positions.pop(index)

    def move_up(self):
        """Move selected positions up."""
        selected_indices = list(self.listbox.curselection())
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select positions to move.")
            return
        for index in selected_indices:
            if index == 0:
                continue
            self.saved_positions[index - 1], self.saved_positions[index] = self.saved_positions[index], self.saved_positions[index - 1]
            temp = self.listbox.get(index - 1)
            self.listbox.delete(index - 1)
            self.listbox.insert(index, temp)
        self.listbox.selection_clear(0, tk.END)
        for index in [i - 1 for i in selected_indices if i > 0]:
            self.listbox.selection_set(index)

    def move_down(self):
        """Move selected positions down."""
        selected_indices = list(self.listbox.curselection())
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select positions to move.")
            return
        max_index = self.listbox.size() - 1
        for index in reversed(selected_indices):
            if index == max_index:
                continue
            self.saved_positions[index + 1], self.saved_positions[index] = self.saved_positions[index], self.saved_positions[index + 1]
            temp = self.listbox.get(index + 1)
            self.listbox.delete(index + 1)
            self.listbox.insert(index, temp)
        self.listbox.selection_clear(0, tk.END)
        for index in [i + 1 for i in selected_indices if i < max_index]:
            self.listbox.selection_set(index)

    def play_sequence(self):
        """Start playing the saved sequence."""
        if self.is_playing:
            messagebox.showwarning("Playback in Progress", "A playback is already in progress.")
            return
        if not self.saved_positions:
            messagebox.showwarning("No Sequences", "No saved positions to play.")
            return
        if not self.serial_manager.serial_connected:
            messagebox.showwarning("Serial Disconnected", "Please connect via Serial to play the sequence.")
            return
        self.is_playing = True
        self.playback_thread = threading.Thread(target=self.playback_worker, daemon=True)
        self.playback_thread.start()

    def playback_worker(self):
        """Worker thread for playing back the sequence."""
        try:
            speed = self.servo_controls.speed_slider.get()
            min_duration = 0.5
            max_duration = 5.0
            total_duration = max_duration - ((speed - 1) / 9) * (max_duration - min_duration)
            update_interval = 0.02
            steps = int(total_duration / update_interval)
            for idx, position in enumerate(self.saved_positions):
                if not self.is_playing:
                    break
                self.root.after(0, lambda step=idx: [self.listbox.selection_clear(0, tk.END), self.listbox.selection_set(step), self.listbox.activate(step)])
                current_angles = [int(slider.get()) for slider in self.servo_controls.sliders]
                target_angles = position
                for step_num in range(steps + 1):
                    if not self.is_playing:
                        break
                    t = step_num / steps
                    ease = ease_in_out_sine(t)
                    angles_step = []
                    for servo_id in range(6):
                        start = current_angles[servo_id]
                        end = target_angles[servo_id]
                        delta = end - start
                        angle = start + delta * ease
                        angle = int(angle)
                        angles_step.append(angle)
                        self.serial_manager.send_servo_angle(servo_id, angle)
                    self.root.after(0, lambda angles=angles_step: [self.serial_manager.gui_queue.put((self.servo_controls.sliders[sid].set, (angle,))) or self.serial_manager.gui_queue.put((self.servo_controls.angle_labels[sid].config, ({"text": f"{angle}°"}))) for sid, angle in enumerate(angles)])
                    time.sleep(update_interval)
                current_angles = target_angles.copy()
            if self.is_playing:
                self.serial_manager.gui_queue.put((messagebox.showinfo, ("Playback Complete", "Sequence playback has completed.")))
        except Exception as e:
            self.serial_manager.gui_queue.put((messagebox.showerror, ("Playback Error", f"An error occurred during playback: {e}")))
        finally:
            self.is_playing = False

    def stop_playback(self):
        """Stop the ongoing playback."""
        if self.is_playing:
            self.is_playing = False
            messagebox.showinfo("Playback Stopped", "Sequence playback has been stopped.")

    def play_selected_position(self):
        """Play a single selected position."""
        if self.is_playing:
            messagebox.showwarning("Playback in Progress", "Cannot play position while playback is in progress.")
            return
        selected = self.listbox.curselection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a position to play.")
            return
        if not self.serial_manager.serial_connected:
            messagebox.showwarning("Serial Disconnected", "Please connect via Serial to play the position.")
            return
        position_index = selected[0]
        position = self.saved_positions[position_index]
        threading.Thread(target=self.play_position_worker, args=(position, position_index), daemon=True).start()

    def play_position_worker(self, position, position_index):
        """Worker thread for playing a single position."""
        self.is_playing = True
        try:
            speed = self.servo_controls.speed_slider.get()
            min_duration = 0.5
            max_duration = 5.0
            total_duration = max_duration - ((speed - 1) / 9) * (max_duration - min_duration)
            update_interval = 0.02
            steps = int(total_duration / update_interval)
            self.root.after(0, lambda step=position_index: [self.listbox.selection_clear(0, tk.END), self.listbox.selection_set(step), self.listbox.activate(step)])
            current_angles = [int(slider.get()) for slider in self.servo_controls.sliders]
            target_angles = position
            for step_num in range(steps + 1):
                if not self.is_playing:
                    break
                t = step_num / steps
                ease = ease_in_out_sine(t)
                angles_step = []
                for servo_id in range(6):
                    start = current_angles[servo_id]
                    end = target_angles[servo_id]
                    delta = end - start
                    angle = start + delta * ease
                    angle = int(angle)
                    angles_step.append(angle)
                    self.serial_manager.send_servo_angle(servo_id, angle)
                self.root.after(0, lambda angles=angles_step: [self.serial_manager.gui_queue.put((self.servo_controls.sliders[sid].set, (angle,))) or self.serial_manager.gui_queue.put((self.servo_controls.angle_labels[sid].config, ({"text": f"{angle}°"}))) for sid, angle in enumerate(angles)])
                time.sleep(update_interval)
        except Exception as e:
            self.serial_manager.gui_queue.put((messagebox.showerror, ("Playback Error", f"An error occurred during position playback: {e}")))
        finally:
            self.is_playing = False

    def export_sequence(self):
        """Export the saved sequence to a binary file."""
        if self.is_playing:
            messagebox.showwarning("Playback in Progress", "Cannot save sequences while playback is in progress.")
            return
        if not self.saved_positions:
            messagebox.showwarning("No Sequences", "No saved positions to save.")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".bin", filetypes=[("Binary Files", "*.bin")], title="Save Sequence As")
        if not file_path:
            return
        try:
            with open(file_path, 'wb') as f:
                f.write(struct.pack('<H', len(self.saved_positions)))
                for position in self.saved_positions:
                    f.write(struct.pack('<6B', *position))
            messagebox.showinfo("Save Successful", f"Sequence saved to {file_path}")
        except Exception as e:
            messagebox.showerror("Save Failed", f"Failed to save sequence: {e}")
