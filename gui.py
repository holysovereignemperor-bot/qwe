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
        self.title("OmniAgent OS - Sovereign Edition"); self.geometry("1400x950")
        ctk.set_appearance_mode("dark")

        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(1, weight=1)

        # Header
        self.header = ctk.CTkFrame(self, height=80, fg_color="#0b0c10")
        self.header.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        self.goal_entry = ctk.CTkEntry(self.header, placeholder_text="Command the Sovereign Singularity...", width=400, fg_color="#1f2833", text_color="#fff", border_color="#00ffa3")
        self.goal_entry.pack(side="left", padx=20, pady=15)

        self.run_btn = ctk.CTkButton(self.header, text="INITIATE", fg_color="#00ffa3", text_color="#0b0c10", hover_color="#00e5ff", font=("SF Pro Display", 14, "bold"), command=self.start_task)
        self.run_btn.pack(side="left", padx=10)

        self.resource_label = ctk.CTkLabel(self.header, text="CPU: 0% | RAM: 0MB | Cost: $0.00", text_color="#8b949e")
        self.resource_label.pack(side="right", padx=20)

        # Tabview
        self.tabview = ctk.CTkTabview(self, fg_color="#0b0c10", segmented_button_selected_color="#00ffa3", segmented_button_unselected_color="#1f2833")
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        self.tab_aura = self.tabview.add("Aura Workspace")
        self.tab_scheduler = self.tabview.add("Sovereign Scheduler")
        self.tab_vault = self.tabview.add("Secure Vault")
        self.tab_chat = self.tabview.add("Interactive Chat")
        self.tab_visual = self.tabview.add("Visual Replay")

        # Aura Tab
        self.tab_aura.grid_columnconfigure((0,1,2), weight=1); self.tab_aura.grid_rowconfigure(0, weight=1)
        self.pm_card = self.create_card(self.tab_aura, "Product Manager", 0)
        self.exec_card = self.create_card(self.tab_aura, "Executor", 1)
        self.qa_card = self.create_card(self.tab_aura, "QA Auditor", 2)

        # Scheduler Tab
        self.sched_box = ctk.CTkTextbox(self.tab_scheduler, fg_color="#1a1a1a", text_color="#00ffa3")
        self.sched_box.pack(fill="both", expand=True, padx=10, pady=10)
        self.sched_box.insert("end", "System Schedule:\n- No pending tasks.")

        # Vault Tab
        self.vault_label = ctk.CTkLabel(self.tab_vault, text="Encrypted Storage Active", font=("SF Pro Display", 18), text_color="#ff0055")
        self.vault_label.pack(pady=50)
        self.key_entry = ctk.CTkEntry(self.tab_vault, placeholder_text="Enter Key Name", width=200); self.key_entry.pack(pady=5)
        self.val_entry = ctk.CTkEntry(self.tab_vault, placeholder_text="Enter Secret Value", width=200, show="*"); self.val_entry.pack(pady=5)
        self.save_key_btn = ctk.CTkButton(self.tab_vault, text="Store in Vault", fg_color="#ff0055", command=self.save_to_vault); self.save_key_btn.pack(pady=10)

        # Other Tabs...
        self.chat_box = ctk.CTkTextbox(self.tab_chat, fg_color="#1a1a1a", text_color="#fff"); self.chat_box.pack(fill="both", expand=True, padx=10, pady=10)
        self.visual_label = ctk.CTkLabel(self.tab_visual, text="No visual data", text_color="#8b949e"); self.visual_label.pack(pady=20, fill="both", expand=True)

        # Monologue
        self.log_box = ctk.CTkTextbox(self, height=120, fg_color="#1a1a1a", text_color="#00ffa3", font=("SF Mono", 11))
        self.log_box.grid(row=2, column=0, sticky="ew", padx=10, pady=10)

        self.update_loop()

    def create_card(self, parent, title, col):
        card = ctk.CTkFrame(parent, fg_color="#1f2833", border_width=2, border_color="rgba(255,255,255,0.05)")
        card.grid(row=0, column=col, sticky="nsew", padx=10, pady=10)
        lbl = ctk.CTkLabel(card, text=title, font=("SF Pro Display", 16, "bold"), text_color="#00e5ff"); lbl.pack(pady=10)
        status = ctk.CTkLabel(card, text="Ready", text_color="#8b949e", wraplength=200); status.pack(pady=10)
        return {"frame": card, "status": status}

    def save_to_vault(self):
        if self.vault:
            self.vault.set_key(self.key_entry.get(), self.val_entry.get())
            self.log_box.insert("end", f"🔒 Vault: Key '{self.key_entry.get()}' secured.\n")

    def handle_agent_event(self, event_type, data):
        self.after(0, lambda: self._handle_event_main_thread(event_type, data))

    def _handle_event_main_thread(self, event_type, data):
        if event_type == "visual_feedback": self.overlay.show_target(data.get('x', 0), data.get('y', 0))
        elif event_type == "log": self.log_box.insert("end", f"⚡ {data}\n"); self.log_box.see("end")
        elif event_type == "clarification_required": self.chat_box.insert("end", f"Agent: {data}\n"); self.tabview.set("Interactive Chat")
        elif event_type == "visual_history": self._update_visual_replay(data)
        elif event_type == "agent_active":
             for name, card in [("PM", self.pm_card), ("Executor", self.exec_card), ("Auditor", self.qa_card)]:
                 card["frame"].configure(border_color="#00ffa3" if name == data else "rgba(255,255,255,0.05)")

    def _update_visual_replay(self, path):
        if os.path.exists(path):
            try:
                img = Image.open(path); img.thumbnail((800, 600))
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
        cpu = psutil.cpu_percent()
        ram = psutil.Process().memory_info().rss / (1024 * 1024)
        self.resource_label.configure(text=f"CPU: {cpu}% | RAM: {ram:.1f}MB | Cost: ${self.blackboard.total_cost:.4f}")

        if self.project_manager:
            new_p = self.project_manager.auto_switch_context()
            if new_p: self.log_box.insert("end", f"🔄 Sovereign Switch: {new_p}\n")

        self.after(1000, self.update_loop)
