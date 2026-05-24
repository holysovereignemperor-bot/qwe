import os
import json
import time
import gc
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

try:
    import Cocoa
    import Quartz
    import ApplicationServices
    from AppKit import NSScreen, NSWorkspace
    # GPU Acceleration via CoreImage
    from Quartz import CIContext, CIImage, CIFilter
except ImportError:
    Cocoa = Quartz = ApplicationServices = NSScreen = NSWorkspace = CIContext = CIImage = CIFilter = None

def get_window_metadata():
    if not NSWorkspace: return {}
    workspace = NSWorkspace.sharedWorkspace()
    active_app = workspace.frontmostApplication()
    if not active_app: return {}
    return {
        "active_app_name": active_app.localizedName(),
        "bundle_id": active_app.bundleIdentifier(),
        "pid": active_app.processIdentifier(),
    }

def get_ui_tree():
    if not ApplicationServices or not ApplicationServices.AXIsProcessTrusted():
        return {"error": "Accessibility not granted"}
    system_wide = ApplicationServices.AXUIElementCreateSystemWide()
    error, frontmost_app_ptr = ApplicationServices.AXUIElementCopyAttributeValue(system_wide, "AXFocusedApplication", None)
    if error != 0 or not frontmost_app_ptr: return {"error": "No frontmost app"}

    def parse_element(element, depth=0, max_depth=5):
        if depth > max_depth: return None
        attrs = ["AXTitle", "AXRole", "AXDescription", "AXValue", "AXFrame"]
        node = {}
        for attr in attrs:
            err, val = ApplicationServices.AXUIElementCopyAttributeValue(element, attr, None)
            if err == 0:
                if attr == "AXFrame":
                    try: node["rect"] = {"x": val.origin.x, "y": val.origin.y, "w": val.size.width, "h": val.size.height}
                    except AttributeError: node["rect"] = str(val)
                else: node[attr[2:].lower()] = str(val)
        err, children = ApplicationServices.AXUIElementCopyAttributeValue(element, "AXChildren", None)
        if err == 0 and children:
            node["children"] = []
            for child in children:
                child_node = parse_element(child, depth + 1, max_depth)
                if child_node: node["children"].append(child_node)
        return node
    return parse_element(frontmost_app_ptr)

def capture_screen_raw():
    if not Quartz: return None
    display_id = Quartz.CGMainDisplayID()
    image_ref = Quartz.CGDisplayCreateImage(display_id)
    if not image_ref: return None
    width, height = Quartz.CGImageGetWidth(image_ref), Quartz.CGImageGetHeight(image_ref)
    provider = Quartz.CGImageGetDataProvider(image_ref)
    data = Quartz.CGDataProviderCopyData(provider)
    img = Image.frombuffer("RGBA", (width, height), data, "raw", "RGBA", 0, 1)
    return img.convert("RGB")

def get_marked_screenshot(quality=50, max_width=1024):
    img = capture_screen_raw()
    if not img: return None, []
    ui_tree = get_ui_tree()
    if "error" in ui_tree: return capture_screen(quality, max_width), []
    elements = []
    def collect_elements(node):
        if "rect" in node and isinstance(node["rect"], dict):
            if node["rect"]["w"] > 5 and node["rect"]["h"] > 5: elements.append(node)
        if "children" in node:
            for child in node["children"]: collect_elements(child)
    collect_elements(ui_tree)
    native_w, native_h = img.size
    draw = ImageDraw.Draw(img)
    try: font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except: font = ImageFont.load_default()
    marks = []
    for i, el in enumerate(elements[:100]):
        rect = el["rect"]
        x, y, w, h = rect["x"], rect["y"], rect["w"], rect["h"]
        draw.rectangle([x, y, x + w, y + h], outline="cyan", width=2)
        draw.rectangle([x, y, x + 25, y + 25], fill="cyan")
        draw.text((x + 5, y + 2), str(i), fill="black", font=font)
        marks.append({"id": i, "role": el.get("role"), "title": el.get("title"), "rect": rect})

    # GPU Acceleration: Grayscale filter (Simulated via CoreImage concept)
    # In pure PyObjC this requires CIContext conversion,
    # for stability on all M1s we use optimized PIL filters if CI is tricky.
    img = img.convert("L").convert("RGB") # Fast Grayscale

    if native_w > max_width:
        ratio = max_width / float(native_w)
        new_height = int(float(native_h) * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=quality)
    gc.collect()
    return buffer.getvalue(), marks

def capture_screen(quality=50, max_width=1024):
    img = capture_screen_raw()
    if not img: return None
    native_w, native_h = img.size
    if native_w > max_width:
        ratio = max_width / float(native_w)
        new_height = int(float(native_h) * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()

import tkinter as tk
class GhostOverlay:
    def __init__(self, master=None):
        self.master = master
        self.window = None
    def show_target(self, x, y, duration=1000):
        if not self.master: return
        def _show():
            self.window = tk.Toplevel(self.master)
            self.window.overrideredirect(True); self.window.attributes("-topmost", True); self.window.attributes("-alpha", 0.7)
            self.window.geometry(f"50x50+{int(x-25)}+{int(y-25)}")
            canvas = tk.Canvas(self.window, width=50, height=50, bg="cyan", highlightthickness=0)
            canvas.pack(); canvas.create_oval(5, 5, 45, 45, outline="white", width=2)
            self.window.after(duration, self.window.destroy)
        self.master.after(0, _show)

def get_screen_dimensions():
    if not NSScreen: return 1920, 1080
    screen = NSScreen.mainScreen()
    if not screen: return 1920, 1080
    frame = screen.frame()
    return frame.size.width, frame.size.height

def scale_coordinate(x, y, from_width, from_height):
    screen_w, screen_h = get_screen_dimensions()
    return x * (screen_w / from_width), y * (screen_h / from_height)

def simulate_click(x, y):
    import pyautogui; pyautogui.click(x, y)
def simulate_type(text):
    import pyautogui; pyautogui.write(text, interval=0.05)
