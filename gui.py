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
        self.project_manager = None

        self.orchestrator.status_callback = self.handle_agent_event
        self.title("OmniAgent OS: Transcendence"); self.geometry("1400x950")
        ctk.set_appearance_mode("dark"); self.configure(fg_color="#050505")

        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(1, weight=1)

        # Transcendence Header
        self.header = ctk.CTkFrame(self, height=70, fg_color="#0b0c10", corner_radius=15)
        self.header.grid(row=0, column=0, sticky="ew", padx=15, pady=10)

        self.goal_entry = ctk.CTkEntry(self.header, placeholder_text="Direct the Singularity...", width=500, fg_color="#000", border_color="#00ffa3")
        self.goal_entry.pack(side="left", padx=20, pady=15)

        self.run_btn = ctk.CTkButton(self.header, text="TRANSCEND", fg_color="#00ffa3", text_color="#000", font=("SF Pro Display", 13, "bold"), command=self.start_task)
        self.run_btn.pack(side="left", padx=5)

        self.telemetry = ctk.CTkLabel(self.header, text="RAM: 0% | CPU: 0%", text_color="#00ffa3", font=("SF Mono", 11))
        self.telemetry.pack(side="right", padx=25)

        # Tabview
        self.tabs = ctk.CTkTabview(self, fg_color="#050505", segmented_button_selected_color="#00ffa3")
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=15, pady=5)

        self.tab_core = self.tabs.add("Aura Core")
        self.tab_lessons = self.tabs.add("Neural Lessons")
        self.tab_chat = self.tabs.add("Interactive Chat")
        self.tab_visual = self.tabs.add("Visual Echo")

        # Core Tab
        self.tab_core.grid_columnconfigure((0,1,2), weight=1); self.tab_core.grid_rowconfigure(0, weight=1)
        self.pm_card = self.create_card(self.tab_core, "Architect (ToT)", 0)
        self.exec_card = self.create_card(self.tab_core, "Executor (VLA)", 1)
        self.qa_card = self.create_card(self.tab_core, "Auditor (Recursive)", 2)

        # Lessons Tab
        self.lessons_box = ctk.CTkTextbox(self.tab_lessons, fg_color="#1a1a1a", text_color="#00ffa3", font=("SF Mono", 12))
        self.lessons_box.pack(fill="both", expand=True, padx=10, pady=10)
        self.lessons_box.insert("end", "Neural Lesson Vault Active...\n")

        # Thought Stream (Monologue)
        self.monologue = ctk.CTkTextbox(self, height=130, fg_color="#000", text_color="#00ffa3", font=("SF Mono", 11), border_width=1, border_color="#1f2833")
        self.monologue.grid(row=2, column=0, sticky="ew", padx=15, pady=15)

        self.update_loop()

    def create_card(self, parent, title, col):
        card = ctk.CTkFrame(parent, fg_color="#0b0c10", border_width=2, border_color="#1f2833", corner_radius=15)
        card.grid(row=0, column=col, sticky="nsew", padx=10, pady=15)
        lbl = ctk.CTkLabel(card, text=title, font=("SF Pro Display", 18, "bold"), text_color="#00e5ff"); lbl.pack(pady=15)
        status = ctk.CTkLabel(card, text="Waiting...", text_color="#8b949e", wraplength=250); status.pack(pady=10)
        return {"frame": card, "status": status}

    def handle_agent_event(self, event_type, data):
        self.after(0, lambda: self._handle_event_main_thread(event_type, data))

    def _handle_event_main_thread(self, event_type, data):
        if event_type == "visual_feedback": self.overlay.show_target(data.get('x', 0), data.get('y', 0))
        elif event_type == "log":
             self.monologue.insert("end", f"⚡ {data}\n"); self.monologue.see("end")
        elif event_type == "lesson_learned":
             self.lessons_box.insert("end", f"\n[NEW LESSON] {data}\n")
        elif event_type == "agent_active":
             for name, card in [("PM", self.pm_card), ("Executor", self.exec_card), ("Auditor", self.qa_card)]:
                 card["frame"].configure(border_color="#00ffa3" if name == data else "#1f2833")

    def start_task(self):
        if self.goal_entry.get():
            self.blackboard.goal = self.goal_entry.get(); self.blackboard.is_running = True
            threading.Thread(target=self.run_orchestrator_sync).start()

    def run_orchestrator_sync(self):
        loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        loop.run_until_complete(self.orchestrator.run(self.blackboard, self.initial_context))

    def update_loop(self):
        ram = psutil.virtual_memory().percent; cpu = psutil.cpu_percent()
        self.telemetry.configure(text=f"RAM: {ram}% | CPU: {cpu}% | Cost: ${self.blackboard.total_cost:.4f}")
        self.after(1000, self.update_loop)
