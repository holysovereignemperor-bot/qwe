import os
import json
import time
import gc
from io import BytesIO
from PIL import Image

try:
    import Cocoa
    import Quartz
    import ApplicationServices
    from AppKit import NSScreen
except ImportError:
    Cocoa = Quartz = ApplicationServices = NSScreen = None

def get_ui_tree():
    """Extracts the macOS Accessibility Tree and returns a summarized JSON."""
    if not ApplicationServices:
        return {"error": "ApplicationServices not available"}

    if not ApplicationServices.AXIsProcessTrusted():
        return {"error": "Accessibility permissions not granted"}

    system_wide = ApplicationServices.AXUIElementCreateSystemWide()
    error, frontmost_app_ptr = ApplicationServices.AXUIElementCopyAttributeValue(
        system_wide, "AXFocusedApplication", None
    )

    if error != 0 or not frontmost_app_ptr:
        return {"error": f"Could not find frontmost application (Error: {error})"}

    def parse_element(element, depth=0, max_depth=5):
        if depth > max_depth:
            return None

        attrs = ["AXTitle", "AXRole", "AXDescription", "AXValue", "AXFrame"]
        node = {}

        for attr in attrs:
            err, val = ApplicationServices.AXUIElementCopyAttributeValue(element, attr, None)
            if err == 0:
                if attr == "AXFrame":
                    try:
                        node["rect"] = {
                            "x": val.origin.x, "y": val.origin.y,
                            "w": val.size.width, "h": val.size.height
                        }
                    except AttributeError:
                        node["rect"] = str(val)
                else:
                    node[attr[2:].lower()] = str(val)

        err, children = ApplicationServices.AXUIElementCopyAttributeValue(element, "AXChildren", None)
        if err == 0 and children:
            node["children"] = []
            for child in children:
                child_node = parse_element(child, depth + 1, max_depth)
                if child_node:
                    node["children"].append(child_node)

        return node

    return parse_element(frontmost_app_ptr)

def capture_screen(quality=50, max_width=1024):
    """Captures the screen, downscales, and returns as a JPEG byte buffer."""
    if not Quartz:
        return None

    display_id = Quartz.CGMainDisplayID()
    image_ref = Quartz.CGDisplayCreateImage(display_id)

    if not image_ref:
        return None

    width = Quartz.CGImageGetWidth(image_ref)
    height = Quartz.CGImageGetHeight(image_ref)

    provider = Quartz.CGImageGetDataProvider(image_ref)
    data = Quartz.CGDataProviderCopyData(provider)

    img = Image.frombuffer("RGBA", (width, height), data, "raw", "RGBA", 0, 1)

    if width > max_width:
        ratio = max_width / float(width)
        new_height = int(float(height) * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

    img = img.convert("RGB")
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=quality)

    del data
    gc.collect()

    return buffer.getvalue()

def is_trusted():
    """Checks if the application has accessibility permissions."""
    if not ApplicationServices:
        return False
    return ApplicationServices.AXIsProcessTrusted()

import tkinter as tk

class GhostOverlay:
    """A transparent overlay to show visual feedback. Must be triggered on main thread if using Tkinter."""
    def __init__(self, master=None):
        self.master = master
        self.window = None

    def show_target(self, x, y, duration=1000):
        """Schedules showing a target. Duration in ms."""
        if not self.master:
            return

        # This part should be thread-safe if called via master.after
        def _show():
            self.window = tk.Toplevel(self.master)
            self.window.overrideredirect(True)
            self.window.attributes("-topmost", True)
            self.window.attributes("-alpha", 0.7)
            self.window.geometry(f"50x50+{int(x-25)}+{int(y-25)}")

            canvas = tk.Canvas(self.window, width=50, height=50, bg="cyan", highlightthickness=0)
            canvas.pack()
            canvas.create_oval(5, 5, 45, 45, outline="white", width=2)

            # Auto-destroy
            self.window.after(duration, self.window.destroy)

        self.master.after(0, _show)

def get_screen_dimensions():
    """Returns native screen width and height."""
    if not NSScreen:
        return 1920, 1080 # Default
    screen = NSScreen.mainScreen()
    if not screen:
        return 1920, 1080
    frame = screen.frame()
    return frame.size.width, frame.size.height

def scale_coordinate(x, y, from_width, from_height):
    """Scales coordinates from vision/screenshot space to native screen space."""
    screen_w, screen_h = get_screen_dimensions()

    scale_x = screen_w / from_width
    scale_y = screen_h / from_height

    return x * scale_x, y * scale_y

def simulate_click(x, y):
    """Simulates a mouse click at native coordinates."""
    import pyautogui
    pyautogui.click(x, y)

def simulate_type(text):
    """Simulates typing text."""
    import pyautogui
    pyautogui.write(text, interval=0.05)
