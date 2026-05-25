try:
    from Cocoa import NSStatusBar, NSVariableStatusItemLength, NSMenu, NSMenuItem
except ImportError:
    NSStatusBar = None

class MenuBarController:
    """Native macOS Status Bar control for Apex Edition."""
    def __init__(self, start_callback, stop_callback):
        self.start_cb = start_callback
        self.stop_cb = stop_callback
        self.status_item = None

    def setup_menu(self):
        if not NSStatusBar: return
        self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        self.status_item.button().setTitle_("Ω")

        menu = NSMenu.alloc().init()

        start_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Initiate Apex", "startAction:", "a")
        start_item.setTarget_(self)
        menu.addItem_(start_item)

        stop_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Terminate Loop", "stopAction:", "t")
        stop_item.setTarget_(self)
        menu.addItem_(stop_item)

        menu.addItem_(NSMenuItem.separatorItem())
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Quit OmniAgent", "terminate:", "q")
        menu.addItem_(quit_item)

        self.status_item.setMenu_(menu)

    def startAction_(self, sender):
        if self.start_cb: self.start_cb()

    def stopAction_(self, sender):
        if self.stop_cb: self.stop_cb()
