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

        self.title("OmniAgent OS: Eternity"); self.geometry("1450x950")
        ctk.set_appearance_mode("dark"); self.configure(fg_color="#000")

        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(1, weight=1)

        # Eternity Command Header
        self.header = ctk.CTkFrame(self, height=80, fg_color="#050505", corner_radius=20, border_width=1, border_color="#1a1a1a")
        self.header.grid(row=0, column=0, sticky="ew", padx=20, pady=15)

        self.goal_entry = ctk.CTkEntry(self.header, placeholder_text="Enter Eternal Command...", width=500, fg_color="#000", border_color="#00ffa3")
        self.goal_entry.pack(side="left", padx=25, pady=20)

        self.run_btn = ctk.CTkButton(self.header, text="ETERNITY", fg_color="#00ffa3", text_color="#000", font=("SF Pro Display", 14, "bold"), command=self.start_task)
        self.run_btn.pack(side="left", padx=10)

        self.telemetry = ctk.CTkLabel(self.header, text="CONSCIOUSNESS: ACTIVE", text_color="#00ffa3", font=("SF Mono", 12))
        self.telemetry.pack(side="right", padx=30)

        # Main Tabview
        self.tabs = ctk.CTkTabview(self, fg_color="#000", segmented_button_selected_color="#00ffa3", corner_radius=20)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)

        self.tab_core = self.tabs.add("Neural Core")
        self.tab_graph = self.tabs.add("Neural Graph")
        self.tab_visual = self.tabs.add("Visual Stream")

        # Core Tab
        self.tab_core.grid_columnconfigure((0,1,2), weight=1); self.tab_core.grid_rowconfigure(0, weight=1)
        self.pm_card = self.create_card(self.tab_core, "Architect", 0)
        self.exec_card = self.create_card(self.tab_core, "Executor", 1)
        self.qa_card = self.create_card(self.tab_core, "Auditor", 2)

        # Neural Graph Tab (Animated Canvas)
        self.graph_canvas = ctk.CTkCanvas(self.tab_graph, bg="#000", highlightthickness=0)
        self.graph_canvas.pack(fill="both", expand=True, padx=10, pady=10)
        self.graph_canvas.create_text(400, 300, text="Neural Node Map Initializing...", fill="#00ffa3", font=("SF Mono", 16))

        # Monologue
        self.monologue = ctk.CTkTextbox(self, height=130, fg_color="#000", text_color="#00ffa3", font=("SF Mono", 11), border_width=1, border_color="#1a1a1a")
        self.monologue.grid(row=2, column=0, sticky="ew", padx=20, pady=20)

        self.update_loop()

    def create_card(self, parent, title, col):
        card = ctk.CTkFrame(parent, fg_color="#050505", border_width=2, border_color="#111", corner_radius=20)
        card.grid(row=0, column=col, sticky="nsew", padx=15, pady=20)
        lbl = ctk.CTkLabel(card, text=title, font=("SF Pro Display", 20, "bold"), text_color="#00e5ff"); lbl.pack(pady=20)
        status = ctk.CTkLabel(card, text="Idle", text_color="#444", wraplength=250); status.pack(pady=15)
        return {"frame": card, "status": status}

    def handle_agent_event(self, event_type, data):
        self.after(0, lambda: self._handle_event_main_thread(event_type, data))

    def _handle_event_main_thread(self, event_type, data):
        if event_type == "visual_feedback": self.overlay.show_target(data.get('x', 0), data.get('y', 0))
        elif event_type == "log":
             self.monologue.insert("end", f"⚡ {data}\n"); self.monologue.see("end")
             # Simple Node update
             self.graph_canvas.create_oval(100, 100, 120, 120, fill="#00ffa3")
        elif event_type == "agent_active":
             for name, card in [("PM", self.pm_card), ("Executor", self.exec_card), ("Auditor", self.qa_card)]:
                 card["frame"].configure(border_color="#00ffa3" if name == data else "#111")

    def start_task(self):
        if self.goal_entry.get():
            self.blackboard.goal = self.goal_entry.get(); self.blackboard.is_running = True
            threading.Thread(target=self.run_orchestrator_sync).start()

    def run_orchestrator_sync(self):
        loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        loop.run_until_complete(self.orchestrator.run(self.blackboard, self.initial_context))

    def update_loop(self):
        ram = psutil.virtual_memory().percent; cpu = psutil.cpu_percent()
        self.telemetry.configure(text=f"RAM: {ram}% | CPU: {cpu}% | ETERNITY")
        self.after(1000, self.update_loop)
