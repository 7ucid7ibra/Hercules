import tkinter as tk
from tkinter import messagebox
from ttkbootstrap import Style
from connect import SerialManager
from controls import ServoControls
from sequence import SequenceManager
from wifi import ControlWindow

# Main window setup
style = Style('darkly')
root = style.master
root.title("Robot Arm Programming Interface")

def on_closing():
    """Handle the window close event."""
    if messagebox.askokcancel("Quit", "Do you want to quit?"):
        serial_manager.close_serial()
        root.destroy()

if __name__ == "__main__":
    # Initialize modules
    serial_manager = SerialManager()
    servo_controls = ServoControls(root, serial_manager)
    control_window = ControlWindow(root, serial_manager, None)  # Temporary None for SequenceManager
    sequence_manager = SequenceManager(root, serial_manager, servo_controls, control_window)  # Pass control_window
    control_window.sequence_manager = sequence_manager  # Update reference after SequenceManager is created
    control_window.servo_controls = servo_controls
    servo_controls.sequence_manager = sequence_manager

    # Configure root
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.after(1000, lambda: servo_controls.gradual_reset())
    root.after(100, serial_manager.process_gui_queue)

    # Run the GUI
    root.mainloop()

    # Ensure serial is closed on exit
    serial_manager.close_serial()
