import os
import json
import time
import gc
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageChops

try:
    import Cocoa
    import Quartz
    import ApplicationServices
    from AppKit import NSScreen, NSWorkspace, NSPanel, NSColor, NSWindowAbove, NSView, NSBezierPath, NSTextField, NSTextAlignmentCenter
    from Foundation import NSRect, NSPoint, NSSize
except ImportError:
    Cocoa = Quartz = ApplicationServices = NSScreen = NSWorkspace = NSPanel = NSColor = NSView = NSBezierPath = NSTextField = None

def get_window_metadata():
    if not NSWorkspace: return {}
    workspace = NSWorkspace.sharedWorkspace()
    active_app = workspace.frontmostApplication()
    if not active_app: return {}
    return {"name": active_app.localizedName(), "bundle_id": active_app.bundleIdentifier(), "pid": active_app.processIdentifier()}

def get_ui_tree():
    if not ApplicationServices or not ApplicationServices.AXIsProcessTrusted(): return {"error": "Accessibility not granted"}
    system_wide = ApplicationServices.AXUIElementCreateSystemWide()
    error, frontmost_app_ptr = ApplicationServices.AXUIElementCopyAttributeValue(system_wide, "AXFocusedApplication", None)
    if error != 0 or not frontmost_app_ptr: return {"error": "No frontmost app"}
    def parse_element(element, depth=0, max_depth=7):
        if depth > max_depth: return None
        attrs = ["AXTitle", "AXRole", "AXDescription", "AXValue", "AXFrame"]
        node = {}
        for attr in attrs:
            err, val = ApplicationServices.AXUIElementCopyAttributeValue(element, attr, None)
            if err == 0:
                if attr == "AXFrame":
                    try: node["rect"] = {"x": val.origin.x, "y": val.origin.y, "w": val.size.width, "h": val.size.height}
                    except AttributeError: node["rect"] = str(val)
                else:
                    v = str(val).strip()
                    if v: node[attr[2:].lower()] = v
        if not node: return None
        err, children = ApplicationServices.AXUIElementCopyAttributeValue(element, "AXChildren", None)
        if err == 0 and children:
            node["children"] = []
            for child in children:
                child_node = parse_element(child, depth + 1, max_depth)
                if child_node: node["children"].append(child_node)
        return node
    return parse_element(frontmost_app_ptr)

def capture_screen_raw(display_id=None):
    if not Quartz: return None
    if display_id is None: display_id = Quartz.CGMainDisplayID()
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
    draw = ImageDraw.Draw(img)
    try: font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except: font = ImageFont.load_default()

    marks = []
    for i, el in enumerate(elements[:100]):
        rect = el["rect"]; x, y, w, h = rect["x"], rect["y"], rect["w"], rect["h"]

        # Privacy Shield: Redact Password fields or sensitive roles
        if el.get("role") == "AXSecureTextField" or "password" in el.get("description", "").lower():
            draw.rectangle([x, y, x + w, y + h], fill="black")
            continue

        draw.rectangle([x, y, x + w, y + h], outline="cyan", width=2)
        draw.rectangle([x, y, x + 25, y + 25], fill="cyan")
        draw.text((x + 5, y + 2), str(i), fill="black", font=font)
        marks.append({"id": i, "role": el.get("role"), "title": el.get("title"), "rect": rect})

    img = img.convert("L").convert("RGB")
    native_w, native_h = img.size
    if native_w > max_width:
        ratio = max_width / float(native_w); new_height = int(float(native_h) * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
    buffer = BytesIO(); img.save(buffer, format="JPEG", quality=quality)
    gc.collect()
    return buffer.getvalue(), marks

def compute_visual_diff(img_bytes1, img_bytes2):
    if not img_bytes1 or not img_bytes2: return 0.0
    img1 = Image.open(BytesIO(img_bytes1)).convert("L")
    img2 = Image.open(BytesIO(img_bytes2)).convert("L")
    diff = ImageChops.difference(img1, img2)
    return 1.0 if diff.getbbox() else 0.0

def capture_screen(quality=50, max_width=1024):
    img = capture_screen_raw()
    if not img: return None
    native_w, native_h = img.size
    if native_w > max_width:
        ratio = max_width / float(native_w); new_height = int(float(native_h) * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
    buffer = BytesIO(); img.save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()

if NSView:
    class HUDView(NSView):
        def drawRect_(self, rect):
            path = NSBezierPath.bezierPathWithOvalInRect_(self.bounds())
            NSColor.cyanColor().set(); path.stroke()
            NSColor.colorWithCalibratedCyan_magenta_yellow_black_alpha_(1, 0, 0, 0, 0.3).set(); path.fill()
else: HUDView = object

class GenesisHUD:
    def __init__(self): self.panel = None
    def show_target(self, x, y, duration=1.0):
        if not NSPanel or not NSView: return
        import threading
        def _create_panel():
            screen_h = NSScreen.mainScreen().frame().size.height
            flipped_y = screen_h - y - 25
            frame = NSRect(NSPoint(x - 25, flipped_y), NSSize(50, 50))
            self.panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(frame, 0, 2, False)
            self.panel.setFloatingPanel_(True); self.panel.setLevel_(NSWindowAbove)
            self.panel.setHasShadow_(False); self.panel.setOpaque_(False); self.panel.setBackgroundColor_(NSColor.clearColor())
            view = HUDView.alloc().initWithFrame_(self.panel.contentView().bounds())
            self.panel.setContentView_(view); self.panel.makeKeyAndOrderFront_(None); self.panel.display()
            time.sleep(duration); self.panel.close()
        threading.Thread(target=_create_panel).start()

    def spawn_status_hud(self, text, x=100, y=100, duration=3.0):
        if not NSPanel or not NSTextField: return
        import threading
        def _create_status():
            frame = NSRect(NSPoint(x, y), NSSize(300, 40))
            panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(frame, 0, 2, False)
            panel.setFloatingPanel_(True); panel.setLevel_(NSWindowAbove)
            panel.setBackgroundColor_(NSColor.blackColor().colorWithAlphaComponent_(0.8))
            label = NSTextField.alloc().initWithFrame_(panel.contentView().bounds())
            label.setStringValue_(text); label.setTextColor_(NSColor.cyanColor())
            label.setBezeled_(False); label.setDrawsBackground_(False); label.setEditable_(False)
            label.setAlignment_(NSTextAlignmentCenter)
            panel.setContentView_(label); panel.makeKeyAndOrderFront_(None); panel.display()
            time.sleep(duration); panel.close()
        threading.Thread(target=_create_status).start()

class GhostOverlay:
    def __init__(self, master=None): self.master = master; self.hud = GenesisHUD()
    def show_target(self, x, y, duration=1000):
        if NSPanel and NSView != object: self.hud.show_target(x, y, duration/1000.0)
    def show_status(self, text):
        if NSPanel: self.hud.spawn_status_hud(text)

def get_screen_dimensions():
    if not NSScreen: return 1920, 1080
    f = NSScreen.mainScreen().frame()
    return f.size.width, f.size.height

def scale_coordinate(x, y, from_width, from_height):
    sw, sh = get_screen_dimensions()
    return x * (sw / from_width), y * (sh / from_height)

def simulate_click(x, y):
    import pyautogui; pyautogui.click(x, y)
def simulate_type(text):
    import pyautogui; pyautogui.write(text, interval=0.05)
