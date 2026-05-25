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

        self.title("Singularity Zero"); self.geometry("1450x950")
        ctk.set_appearance_mode("dark"); self.configure(fg_color="#000")

        # Zero Aesthetic (Orb Trigger)
        self.is_minimized = False
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(1, weight=1)

        # Singularity Orb (Header)
        self.header = ctk.CTkFrame(self, height=80, fg_color="#000", corner_radius=40, border_width=1, border_color="#111")
        self.header.grid(row=0, column=0, sticky="ew", padx=20, pady=15)

        self.orb = ctk.CTkLabel(self.header, text="○", font=("SF Pro Display", 32), text_color="#00ffa3")
        self.orb.pack(side="left", padx=30)

        self.goal_entry = ctk.CTkEntry(self.header, placeholder_text="Command Zero...", width=500, fg_color="#050505", border_color="#111", corner_radius=20)
        self.goal_entry.pack(side="left", padx=10, pady=20)

        self.run_btn = ctk.CTkButton(self.header, text="ZERO", fg_color="#00ffa3", text_color="#000", corner_radius=20, font=("SF Pro Display", 14, "bold"), command=self.start_task)
        self.run_btn.pack(side="left", padx=10)

        self.telemetry = ctk.CTkLabel(self.header, text="SINGULARITY: ZERO", text_color="#333", font=("SF Mono", 12))
        self.telemetry.pack(side="right", padx=40)

        # Infinity Tabs
        self.tabs = ctk.CTkTabview(self, fg_color="#000", segmented_button_selected_color="#00ffa3", corner_radius=30)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)

        self.tab_core = self.tabs.add("Intelligence"); self.tab_visual = self.tabs.add("Perception")
        self.tab_lab = self.tabs.add("Evolution"); self.tab_sovereign = self.tabs.add("Sovereignty")

        # Monologue
        self.monologue = ctk.CTkTextbox(self, height=130, fg_color="#000", text_color="#00ffa3", font=("SF Mono", 11), border_width=1, border_color="#111")
        self.monologue.grid(row=2, column=0, sticky="ew", padx=30, pady=25)

        self.update_loop()

    def create_card(self, parent, title, col):
        card = ctk.CTkFrame(parent, fg_color="#050505", border_width=2, border_color="#111", corner_radius=30)
        card.grid(row=0, column=col, sticky="nsew", padx=15, pady=25)
        lbl = ctk.CTkLabel(card, text=title, font=("SF Pro Display", 22, "bold"), text_color="#00e5ff"); lbl.pack(pady=25)
        status = ctk.CTkLabel(card, text="Waiting...", text_color="#222", wraplength=250); status.pack(pady=20)
        return {"frame": card, "status": status}

    def handle_agent_event(self, event_type, data):
        self.after(0, lambda: self._handle_event_main_thread(event_type, data))

    def _handle_event_main_thread(self, event_type, data):
        if event_type == "visual_feedback": self.overlay.show_target(data.get('x', 0), data.get('y', 0))
        elif event_type == "log":
             self.monologue.insert("end", f"0: {data}\n"); self.monologue.see("end")
             # Pulsing Orb effect concept
             self.orb.configure(text_color="#00e5ff")
             self.after(500, lambda: self.orb.configure(text_color="#00ffa3"))

    def start_task(self):
        if self.goal_entry.get():
            self.blackboard.goal = self.goal_entry.get(); self.blackboard.is_running = True
            threading.Thread(target=self.run_orchestrator_sync).start()

    def run_orchestrator_sync(self):
        loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        loop.run_until_complete(self.orchestrator.run(self.blackboard, self.initial_context))

    def update_loop(self):
        ram = psutil.virtual_memory().percent; cpu = psutil.cpu_percent()
        self.telemetry.configure(text=f"RAM: {ram}% | CPU: {cpu}% | ZERO")
        self.after(1000, self.update_loop)
