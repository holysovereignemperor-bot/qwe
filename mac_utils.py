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

# Global state for Temporal consistency
_UI_ELEMENT_CACHE = {}

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
    provider = Quartz.CGImageGetDataProvider(image_ref); data = Quartz.CGDataProviderCopyData(provider)
    img = Image.frombuffer("RGBA", (width, height), data, "raw", "RGBA", 0, 1)
    return img.convert("RGB")

def get_marked_screenshot(quality=50, max_width=1024, attention_regions=None):
    """Temporal UI Consistency: Elements retain IDs across frames."""
    global _UI_ELEMENT_CACHE
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

    draw = ImageDraw.Draw(img, "RGBA")
    try: font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except: font = ImageFont.load_default()

    new_cache = {}
    marks = []
    for i, el in enumerate(elements[:100]):
        rect = el["rect"]; x, y, w, h = rect["x"], rect["y"], rect["w"], rect["h"]

        # Stability check: match element to previous cache by title/role
        el_id = f"{el.get('role')}_{el.get('title')}"
        if el_id in _UI_ELEMENT_CACHE:
             display_id = _UI_ELEMENT_CACHE[el_id]
        else:
             display_id = i
        new_cache[el_id] = display_id

        if el.get("role") == "AXSecureTextField" or "password" in el.get("description", "").lower():
            draw.rectangle([x, y, x + w, y + h], fill="black"); continue

        draw.rectangle([x, y, x + w, y + h], outline=(0, 229, 255, 180), width=2)
        draw.rectangle([x, y, x + 25, y + 25], fill=(0, 229, 255, 255))
        draw.text((x + 5, y + 2), str(display_id), fill="black", font=font)
        marks.append({"id": display_id, "role": el.get("role"), "title": el.get("title"), "rect": rect})

    _UI_ELEMENT_CACHE = new_cache

    img = img.convert("L").convert("RGB")
    native_w, native_h = img.size
    if native_w > max_width:
        ratio = max_width / float(native_w); new_height = int(float(native_h) * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
    buffer = BytesIO(); img.save(buffer, format="JPEG", quality=quality); gc.collect()
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
    def __init__(self): self.panel = None; self.thought_panel = None
    def show_target(self, x, y, duration=1.0):
        if not NSPanel or not NSView: return
        import threading
        def _create():
            screen_h = NSScreen.mainScreen().frame().size.height
            frame = NSRect(NSPoint(x - 25, screen_h - y - 25), NSSize(50, 50))
            p = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(frame, 0, 2, False)
            p.setFloatingPanel_(True); p.setLevel_(NSWindowAbove); p.setBackgroundColor_(NSColor.clearColor())
            p.setContentView_(HUDView.alloc().initWithFrame_(p.contentView().bounds()))
            p.makeKeyAndOrderFront_(None); time.sleep(duration); p.close()
        threading.Thread(target=_create).start()

    def show_monologue(self, text, duration=4.0):
        if not NSPanel or not NSTextField: return
        import threading
        def _create():
            screen_w = NSScreen.mainScreen().frame().size.width
            frame = NSRect(NSPoint(screen_w / 2 - 200, 50), NSSize(400, 40))
            p = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(frame, 0, 2, False)
            p.setFloatingPanel_(True); p.setLevel_(NSWindowAbove)
            p.setBackgroundColor_(NSColor.blackColor().colorWithAlphaComponent_(0.8))
            label = NSTextField.alloc().initWithFrame_(p.contentView().bounds())
            label.setStringValue_(text); label.setTextColor_(NSColor.cyanColor())
            label.setBezeled_(False); label.setDrawsBackground_(False); label.setEditable_(False); label.setAlignment_(NSTextAlignmentCenter)
            p.setContentView_(label); p.makeKeyAndOrderFront_(None); p.display()
            time.sleep(duration); p.close()
        threading.Thread(target=_create).start()

class GhostOverlay:
    def __init__(self, master=None): self.master = master; self.hud = GenesisHUD()
    def show_target(self, x, y, duration=1000):
        if NSPanel and NSView != object: self.hud.show_target(x, y, duration/1000.0)
    def show_status(self, text):
        if NSPanel: self.hud.show_monologue(text)

def get_screen_dimensions():
    if not NSScreen: return 1920, 1080
    f = NSScreen.mainScreen().frame(); return f.size.width, f.size.height

def scale_coordinate(x, y, from_width, from_height):
    sw, sh = get_screen_dimensions(); return x * (sw / from_width), y * (sh / from_height)

def simulate_click(x, y):
    import pyautogui; pyautogui.click(x, y)
def simulate_type(text):
    import pyautogui; pyautogui.write(text, interval=0.05)
def simulate_gesture(action, x=None, y=None, dx=0, dy=0):
    import pyautogui
    if action == "scroll": pyautogui.scroll(dy)
    elif action == "drag": pyautogui.dragTo(x, y, duration=0.5)
    elif action == "swipe_left": pyautogui.hotkey('ctrl', 'left')
    elif action == "swipe_right": pyautogui.hotkey('ctrl', 'right')
