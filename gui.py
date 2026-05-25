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

        self.title("Sovereign Origin"); self.geometry("1450x950")
        ctk.set_appearance_mode("dark"); self.configure(fg_color="#000")

        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(1, weight=1)

        # --- Origin Crystal (3D-Effect Header) ---
        self.header = ctk.CTkFrame(self, height=100, fg_color="#0a0a0a", corner_radius=30, border_width=2, border_color="#1a1a1a")
        self.header.grid(row=0, column=0, sticky="ew", padx=20, pady=15)

        self.origin_crystal = ctk.CTkLabel(self.header, text="◆", font=("SF Pro Display", 48), text_color="#00ffa3")
        self.origin_crystal.pack(side="left", padx=40)

        self.goal_entry = ctk.CTkEntry(self.header, placeholder_text="Command the Origin...", width=500, fg_color="#000", border_color="#00ffa3", corner_radius=20)
        self.goal_entry.pack(side="left", padx=10, pady=25)

        self.run_btn = ctk.CTkButton(self.header, text="ORIGIN", fg_color="#00ffa3", text_color="#000", font=("SF Pro Display", 14, "bold"), corner_radius=20, command=self.start_task)
        self.run_btn.pack(side="left", padx=10)

        self.telemetry = ctk.CTkLabel(self.header, text="ORIGIN ENGINE: OPTIMIZED", text_color="#333", font=("SF Mono", 12))
        self.telemetry.pack(side="right", padx=50)

        # Tabview
        self.tabs = ctk.CTkTabview(self, fg_color="#000", segmented_button_selected_color="#00ffa3", corner_radius=30)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)

        self.tab_eng = self.tabs.add("Engineering"); self.tab_core = self.tabs.add("Core Intelligence")
        self.tab_visual = self.tabs.add("Perception"); self.tab_sovereign = self.tabs.add("Sovereignty")

        # Engineering Pipeline Log
        self.eng_log = ctk.CTkTextbox(self.tab_eng, fg_color="#050505", text_color="#00ffa3", font=("SF Mono", 12))
        self.eng_log.pack(fill="both", expand=True, padx=10, pady=10)
        self.eng_log.insert("end", ">> Engineering Pipeline Idle.\n")

        # Monologue
        self.monologue = ctk.CTkTextbox(self, height=130, fg_color="#000", text_color="#00ffa3", font=("SF Mono", 11), border_width=1, border_color="#111")
        self.monologue.grid(row=2, column=0, sticky="ew", padx=30, pady=25)

        self.update_loop()

    def create_card(self, parent, title, col):
        card = ctk.CTkFrame(parent, fg_color="#050505", border_width=2, border_color="#111", corner_radius=30)
        card.grid(row=0, column=col, sticky="nsew", padx=15, pady=25)
        lbl = ctk.CTkLabel(card, text=title, font=("SF Pro Display", 22, "bold"), text_color="#00e5ff"); lbl.pack(pady=25)
        status = ctk.CTkLabel(card, text="Ready", text_color="#222", wraplength=250); status.pack(pady=20)
        return {"frame": card, "status": status}

    def handle_agent_event(self, event_type, data):
        self.after(0, lambda: self._handle_event_main_thread(event_type, data))

    def _handle_event_main_thread(self, event_type, data):
        if event_type == "visual_feedback": self.overlay.show_target(data.get('x', 0), data.get('y', 0))
        elif event_type == "log":
             self.monologue.insert("end", f"∞ {data}\n"); self.monologue.see("end")
             self.origin_crystal.configure(text_color="#00e5ff"); self.after(500, lambda: self.origin_crystal.configure(text_color="#00ffa3"))
        elif event_type == "agent_active":
             # Engineering specific coloring
             if data == "Executor": self.eng_log.insert("end", "[RUN] Step Execution...\n")

    def start_task(self):
        if self.goal_entry.get():
            self.blackboard.goal = self.goal_entry.get(); self.blackboard.is_running = True
            threading.Thread(target=self.run_orchestrator_sync).start()

    def run_orchestrator_sync(self):
        loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        loop.run_until_complete(self.orchestrator.run(self.blackboard, self.initial_context))

    def update_loop(self):
        ram = psutil.virtual_memory().percent; cpu = psutil.cpu_percent()
        self.telemetry.configure(text=f"RAM: {ram}% | CPU: {cpu}% | ORIGIN")
        self.after(1000, self.update_loop)
