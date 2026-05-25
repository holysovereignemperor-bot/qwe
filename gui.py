import customtkinter as ctk
import asyncio
import psutil
import threading
import os
from PIL import Image
from blackboard import Blackboard
from mac_utils import GhostOverlay

class OmniAgentGUI(ctk.CTk):
    def __init__(self, orchestrator, blackboard):
        super().__init__()
        self.orchestrator = orchestrator; self.blackboard = blackboard
        self.overlay = GhostOverlay(self); self.initial_context = ""
        self.orchestrator.status_callback = self.handle_agent_event

        self.title("Singularity Absolute"); self.geometry("1450x950")
        ctk.set_appearance_mode("dark"); self.configure(fg_color="#000000")

        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(1, weight=1)

        # Absolute Command Bar
        self.header = ctk.CTkFrame(self, height=80, fg_color="#050505", corner_radius=25, border_width=1, border_color="#1a1a1a")
        self.header.grid(row=0, column=0, sticky="ew", padx=20, pady=15)

        self.goal_entry = ctk.CTkEntry(self.header, placeholder_text="Absolute Command Input...", width=500, fg_color="#000", border_color="#00ffa3", corner_radius=15)
        self.goal_entry.pack(side="left", padx=30, pady=20)

        self.run_btn = ctk.CTkButton(self.header, text="ABSOLUTE", fg_color="#00ffa3", text_color="#000", font=("SF Pro Display", 14, "bold"), corner_radius=15, command=self.start_task)
        self.run_btn.pack(side="left", padx=10)

        self.reload_btn = ctk.CTkButton(self.header, text="Hot-Reload", width=120, fg_color="#1a1a1a", corner_radius=15, command=self.hot_reload)
        self.reload_btn.pack(side="left", padx=10)

        self.telemetry = ctk.CTkLabel(self.header, text="SINGULARITY: ABSOLUTE", text_color="#00ffa3", font=("SF Mono", 12))
        self.telemetry.pack(side="right", padx=40)

        # Tabview
        self.tabs = ctk.CTkTabview(self, fg_color="#000", segmented_button_selected_color="#00ffa3", corner_radius=25)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)

        self.tab_stream = self.tabs.add("Consciousness Stream")
        self.tab_visual = self.tabs.add("Visual Stream")
        self.tab_lab = self.tabs.add("Evolution Lab")

        # Consciousness Stream (Monologue as primary)
        self.stream_box = ctk.CTkTextbox(self.tab_stream, fg_color="#000", text_color="#00ffa3", font=("SF Mono", 13), border_width=0)
        self.stream_box.pack(fill="both", expand=True, padx=20, pady=20)
        self.stream_box.insert("end", ">> Singularity Absolute System Online.\n>> Waiting for initialization...\n")

        self.update_loop()

    def hot_reload(self):
        # Trigger orchestrator to reload plugins
        import plugin_system
        self.orchestrator.status_callback("log", "System: Triggering skill hot-reload...")
        # (Real trigger would call PluginLoader.load_plugins)

    def handle_agent_event(self, event_type, data):
        self.after(0, lambda: self._handle_event_main_thread(event_type, data))

    def _handle_event_main_thread(self, event_type, data):
        if event_type == "visual_feedback": self.overlay.show_target(data.get('x', 0), data.get('y', 0))
        elif event_type == "log":
             self.stream_box.insert("end", f"∞ {data}\n"); self.stream_box.see("end")
             self.overlay.show_status(data) # Mirror to native HUD
        elif event_type == "agent_active":
             pass # In Absolute, focus is on the Stream

    def start_task(self):
        if self.goal_entry.get():
            self.blackboard.goal = self.goal_entry.get(); self.blackboard.is_running = True
            threading.Thread(target=self.run_orchestrator_sync).start()

    def run_orchestrator_sync(self):
        loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        loop.run_until_complete(self.orchestrator.run(self.blackboard, self.initial_context))

    def update_loop(self):
        ram = psutil.virtual_memory().percent; cpu = psutil.cpu_percent()
        self.telemetry.configure(text=f"RAM: {ram}% | CPU: {cpu}% | ABS")
        # Periodic hot-reload check
        # self.orchestrator.plugin_loader.load_plugins()
        self.after(1000, self.update_loop)
