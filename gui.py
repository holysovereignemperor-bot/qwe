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
        self.project_manager = None; self.scheduler = None; self.vault = None

        self.orchestrator.status_callback = self.handle_agent_event
        self.title("OmniAgent OS - Aether Edition"); self.geometry("1400x950")
        ctk.set_appearance_mode("dark")

        # Focus Mode state
        self.is_focus_mode = False

        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(1, weight=1)

        # Header
        self.header = ctk.CTkFrame(self, height=60, fg_color="#0b0c10")
        self.header.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        self.goal_entry = ctk.CTkEntry(self.header, placeholder_text="Aether Command...", width=400, fg_color="#1a1a1a", border_color="#00ffa3")
        self.goal_entry.pack(side="left", padx=20, pady=10)

        self.run_btn = ctk.CTkButton(self.header, text="INITIATE", fg_color="#00ffa3", text_color="#0b0c10", command=self.start_task)
        self.run_btn.pack(side="left", padx=5)

        self.focus_btn = ctk.CTkButton(self.header, text="Focus Mode", width=100, fg_color="#1f2833", command=self.toggle_focus)
        self.focus_btn.pack(side="left", padx=10)

        self.telemetry_label = ctk.CTkLabel(self.header, text="RAM: 0% | CPU: 0%", text_color="#8b949e", font=("SF Mono", 11))
        self.telemetry_label.pack(side="right", padx=20)

        # Tabview
        self.tabview = ctk.CTkTabview(self, fg_color="#0b0c10", segmented_button_selected_color="#00ffa3")
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        self.tab_aura = self.tabview.add("Aether Workspace")
        self.tab_chat = self.tabview.add("Human Bridge")
        self.tab_visual = self.tabview.add("Visual Echo")
        self.tab_lab = self.tabview.add("Neural Lab")

        # Workspace Tab
        self.tab_aura.grid_columnconfigure((0,1,2), weight=1); self.tab_aura.grid_rowconfigure(0, weight=1)
        self.pm_card = self.create_card(self.tab_aura, "Architect", 0)
        self.exec_card = self.create_card(self.tab_aura, "Executor", 1)
        self.qa_card = self.create_card(self.tab_aura, "Auditor", 2)

        # Other Tabs...
        self.chat_box = ctk.CTkTextbox(self.tab_chat, fg_color="#1a1a1a", text_color="#fff"); self.chat_box.pack(fill="both", expand=True, padx=10, pady=10)
        self.visual_label = ctk.CTkLabel(self.tab_visual, text="Echo Chamber Idle", text_color="#8b949e"); self.visual_label.pack(pady=20, fill="both", expand=True)

        # Monologue
        self.log_box = ctk.CTkTextbox(self, height=100, fg_color="#000", text_color="#00ffa3", font=("SF Mono", 10))
        self.log_box.grid(row=2, column=0, sticky="ew", padx=10, pady=10)

        self.update_loop()

    def create_card(self, parent, title, col):
        card = ctk.CTkFrame(parent, fg_color="#1f2833", border_width=2, border_color="rgba(255,255,255,0.05)")
        card.grid(row=0, column=col, sticky="nsew", padx=10, pady=10)
        lbl = ctk.CTkLabel(card, text=title, font=("SF Pro Display", 16, "bold"), text_color="#00e5ff"); lbl.pack(pady=10)
        status = ctk.CTkLabel(card, text="Waiting", text_color="#8b949e", wraplength=200); status.pack(pady=10)
        return {"frame": card, "status": status}

    def toggle_focus(self):
        self.is_focus_mode = not self.is_focus_mode
        if self.is_focus_mode:
            self.geometry("500x150"); self.tabview.grid_remove(); self.log_box.grid_remove()
            self.focus_btn.configure(text="Exit Focus")
        else:
            self.geometry("1400x950"); self.tabview.grid(); self.log_box.grid()
            self.focus_btn.configure(text="Focus Mode")

    def handle_agent_event(self, event_type, data):
        self.after(0, lambda: self._handle_event_main_thread(event_type, data))

    def _handle_event_main_thread(self, event_type, data):
        if event_type == "visual_feedback": self.overlay.show_target(data.get('x', 0), data.get('y', 0))
        elif event_type == "log":
             # Typewriter effect concept: just insert for now
             self.log_box.insert("end", f"> {data}\n"); self.log_box.see("end")
        elif event_type == "clarification_required":
            self.chat_box.insert("end", f"Agent: {data}\n"); self.tabview.set("Human Bridge")
        elif event_type == "visual_history":
            self._update_visual_replay(data)
        elif event_type == "agent_active":
             for name, card in [("PM", self.pm_card), ("Executor", self.exec_card), ("Auditor", self.qa_card)]:
                 card["frame"].configure(border_color="#00ffa3" if name == data else "rgba(255,255,255,0.05)")

    def _update_visual_replay(self, path):
        if os.path.exists(path):
            try:
                img = Image.open(path); img.thumbnail((600, 450))
                p = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                self.visual_label.configure(image=p, text="")
            except Exception: pass

    def start_task(self):
        if self.goal_entry.get():
            self.blackboard.goal = self.goal_entry.get(); self.blackboard.is_running = True
            threading.Thread(target=self.run_orchestrator_sync).start()

    def run_orchestrator_sync(self):
        loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        loop.run_until_complete(self.orchestrator.run(self.blackboard, self.initial_context))

    def update_loop(self):
        ram = psutil.virtual_memory().percent; cpu = psutil.cpu_percent()
        self.telemetry_label.configure(text=f"RAM: {ram}% | CPU: {cpu}% | Cost: ${self.blackboard.total_cost:.4f}")
        self.after(1000, self.update_loop)
