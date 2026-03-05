import math

def ease_in_out_sine(t):
    """Ease-in-out sine function for smooth transitions."""
    return -(math.cos(math.pi * t) - 1) / 2