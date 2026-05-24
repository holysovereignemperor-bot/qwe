import customtkinter as ctk
import asyncio
import psutil
import threading
from blackboard import Blackboard
from mac_utils import GhostOverlay

class OmniAgentGUI(ctk.CTk):
    def __init__(self, orchestrator, blackboard):
        super().__init__()
        self.orchestrator = orchestrator
        self.blackboard = blackboard
        self.overlay = GhostOverlay(self)

        self.orchestrator.status_callback = self.handle_agent_event

        self.title("OmniAgent OS")
        self.geometry("900x600")
        ctk.set_appearance_mode("dark")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        self.header = ctk.CTkFrame(self, height=100, fg_color="#0b0c10")
        self.header.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        self.goal_entry = ctk.CTkEntry(self.header, placeholder_text="Enter global goal...", width=600, fg_color="#1f2833", text_color="#fff", border_color="#00e5ff")
        self.goal_entry.pack(side="left", padx=20, pady=20)

        self.run_btn = ctk.CTkButton(self.header, text="RUN", fg_color="#00e5ff", text_color="#0b0c10", hover_color="#00ffa3", command=self.start_task)
        self.run_btn.pack(side="left", padx=10)

        self.resource_label = ctk.CTkLabel(self.header, text="CPU: 0% | RAM: 0MB", text_color="#8b949e")
        self.resource_label.pack(side="right", padx=20)

        # Middle: Agent Cards
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_columnconfigure((0,1,2), weight=1)

        self.pm_card = self.create_card("Product Manager", 0)
        self.exec_card = self.create_card("Executor", 1)
        self.qa_card = self.create_card("QA Auditor", 2)

        # Bottom: Logs
        self.log_box = ctk.CTkTextbox(self, height=150, fg_color="#1a1a1a", text_color="#00ffa3", font=("Courier", 12))
        self.log_box.grid(row=2, column=0, sticky="ew", padx=10, pady=10)

        self.update_loop()

    def create_card(self, title, col):
        card = ctk.CTkFrame(self.main_frame, fg_color="#1f2833", border_width=1, border_color="rgba(255,255,255,0.08)")
        card.grid(row=0, column=col, sticky="nsew", padx=10, pady=10)

        lbl = ctk.CTkLabel(card, text=title, font=("SF Pro Display", 16, "bold"), text_color="#00e5ff")
        lbl.pack(pady=10)

        status = ctk.CTkLabel(card, text="Idle", text_color="#8b949e")
        status.pack(pady=10)

        return {"frame": card, "status": status}

    def handle_agent_event(self, event_type, data):
        if event_type == "visual_feedback":
            x, y = data.get('x', 0), data.get('y', 0)
            self.overlay.show_target(x, y)
        elif event_type == "log":
            self.log_box.insert("end", f"{data}\n")
            self.log_box.see("end")

    def start_task(self):
        goal = self.goal_entry.get()
        if goal:
            self.blackboard.goal = goal
            self.blackboard.is_running = True
            threading.Thread(target=self.run_orchestrator_sync).start()

    def run_orchestrator_sync(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.orchestrator.run(self.blackboard))

    def update_loop(self):
        cpu = psutil.cpu_percent()
        ram = psutil.Process().memory_info().rss / (1024 * 1024)
        self.resource_label.configure(text=f"CPU: {cpu}% | RAM: {ram:.1f}MB")

        if self.blackboard.is_running:
            self.pm_card["status"].configure(text=self.blackboard.status)

        self.after(1000, self.update_loop)
