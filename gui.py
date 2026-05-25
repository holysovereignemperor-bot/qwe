import customtkinter as ctk
import asyncio
import psutil
import threading
import os
from PIL import Image
from blackboard import Blackboard
from mac_utils import GhostOverlay
from watcher_service import WatcherService

class OmniAgentGUI(ctk.CTk):
    def __init__(self, orchestrator, blackboard):
        super().__init__()
        self.orchestrator = orchestrator; self.blackboard = blackboard
        self.overlay = GhostOverlay(self); self.initial_context = ""

        self.orchestrator.status_callback = self.handle_agent_event
        self.title("OmniAgent OS: Infinity"); self.geometry("1450x950")
        ctk.set_appearance_mode("dark"); self.configure(fg_color="#000")

        # Proactive Watcher Initialization
        self.watcher = WatcherService(os.path.expanduser("~/Downloads"), self.handle_watcher_event)

        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(1, weight=1)

        # Infinity Command Header
        self.header = ctk.CTkFrame(self, height=80, fg_color="#0a0a0a", corner_radius=25, border_width=1, border_color="#1a1a1a")
        self.header.grid(row=0, column=0, sticky="ew", padx=20, pady=15)

        self.orb = ctk.CTkLabel(self.header, text="∞", font=("SF Pro Display", 36), text_color="#00ffa3")
        self.orb.pack(side="left", padx=30)

        self.goal_entry = ctk.CTkEntry(self.header, placeholder_text="Infinity Input...", width=400, fg_color="#050505", border_color="#111", corner_radius=15)
        self.goal_entry.pack(side="left", padx=10, pady=20)

        self.run_btn = ctk.CTkButton(self.header, text="INITIATE", fg_color="#00ffa3", text_color="#000", corner_radius=15, command=self.start_task)
        self.run_btn.pack(side="left", padx=5)

        self.watch_var = ctk.BooleanVar(value=False)
        self.watch_toggle = ctk.CTkSwitch(self.header, text="Watcher", variable=self.watch_var, command=self.toggle_watcher, progress_color="#00ffa3")
        self.watch_toggle.pack(side="left", padx=20)

        self.telemetry = ctk.CTkLabel(self.header, text="INFINITY CORE: ONLINE", text_color="#00ffa3", font=("SF Mono", 12))
        self.telemetry.pack(side="right", padx=40)

        # Tabs
        self.tabs = ctk.CTkTabview(self, fg_color="#000", segmented_button_selected_color="#00ffa3", corner_radius=25)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)

        self.tab_core = self.tabs.add("Core"); self.tab_swarm = self.tabs.add("Swarm View")
        self.tab_visual = self.tabs.add("Visual Stream"); self.tab_secure = self.tabs.add("Sovereign")

        # Core Workspace
        self.tab_core.grid_columnconfigure((0,1,2), weight=1); self.tab_core.grid_rowconfigure(0, weight=1)
        self.pm_card = self.create_card(self.tab_core, "Architect", 0)
        self.exec_card = self.create_card(self.tab_core, "Executor", 1)
        self.qa_card = self.create_card(self.tab_core, "Auditor", 2)

        # Monologue
        self.monologue = ctk.CTkTextbox(self, height=150, fg_color="#000", text_color="#00ffa3", font=("SF Mono", 11), border_width=1, border_color="#1a1a1a")
        self.monologue.grid(row=2, column=0, sticky="ew", padx=30, pady=25)

        self.update_loop()

    def create_card(self, parent, title, col):
        card = ctk.CTkFrame(parent, fg_color="#0a0a0a", border_width=2, border_color="#111", corner_radius=25)
        card.grid(row=0, column=col, sticky="nsew", padx=15, pady=20)
        lbl = ctk.CTkLabel(card, text=title, font=("SF Pro Display", 22, "bold"), text_color="#00e5ff"); lbl.pack(pady=25)
        status = ctk.CTkLabel(card, text="Ready", text_color="#444", wraplength=250); status.pack(pady=20)
        return {"frame": card, "status": status}

    def toggle_watcher(self):
        if self.watch_var.get(): self.watcher.start(); self.log_box_insert("System: Proactive Watcher Started.")
        else: self.watcher.stop(); self.log_box_insert("System: Watcher Suspended.")

    def handle_watcher_event(self, goal):
        self.goal_entry.delete(0, "end"); self.goal_entry.insert(0, goal); self.start_task()

    def handle_agent_event(self, event_type, data):
        self.after(0, lambda: self._handle_event_main_thread(event_type, data))

    def _handle_event_main_thread(self, event_type, data):
        if event_type == "visual_feedback": self.overlay.show_target(data.get('x', 0), data.get('y', 0))
        elif event_type == "log":
             self.monologue.insert("end", f"∞ {data}\n"); self.monologue.see("end")
             self.orb.configure(text_color="#00e5ff"); self.after(500, lambda: self.orb.configure(text_color="#00ffa3"))
        elif event_type == "agent_active":
             for name, card in [("PM", self.pm_card), ("Executor", self.exec_card), ("Auditor", self.qa_card)]:
                 card["frame"].configure(border_color="#00ffa3" if name == data else "#111")

    def log_box_insert(self, text):
        self.monologue.insert("end", f"∞ {text}\n"); self.monologue.see("end")

    def start_task(self):
        if self.goal_entry.get():
            self.blackboard.goal = self.goal_entry.get(); self.blackboard.is_running = True
            threading.Thread(target=self.run_orchestrator_sync).start()

    def run_orchestrator_sync(self):
        loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        loop.run_until_complete(self.orchestrator.run(self.blackboard, self.initial_context))

    def update_loop(self):
        ram = psutil.virtual_memory().percent; cpu = psutil.cpu_percent()
        self.telemetry.configure(text=f"RAM: {ram}% | CPU: {cpu}% | INF")
        self.after(1000, self.update_loop)
