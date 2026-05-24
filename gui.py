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
        self.orchestrator = orchestrator
        self.blackboard = blackboard
        self.overlay = GhostOverlay(self)
        self.initial_context = ""

        self.orchestrator.status_callback = self.handle_agent_event

        self.title("OmniAgent OS - Singularity Pro Max")
        self.geometry("1400x900")
        ctk.set_appearance_mode("dark")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        self.header = ctk.CTkFrame(self, height=80, fg_color="#0b0c10")
        self.header.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        self.goal_entry = ctk.CTkEntry(self.header, placeholder_text="Command Pro Max...", width=500, fg_color="#1f2833", text_color="#fff", border_color="#00e5ff")
        self.goal_entry.pack(side="left", padx=20, pady=15)

        self.run_btn = ctk.CTkButton(self.header, text="EXECUTE", fg_color="#00e5ff", text_color="#0b0c10", hover_color="#00ffa3", font=("SF Pro Display", 14, "bold"), command=self.start_task)
        self.run_btn.pack(side="left", padx=10)

        self.voice_var = ctk.BooleanVar(value=False)
        self.voice_toggle = ctk.CTkSwitch(self.header, text="Voice", variable=self.voice_var, command=self.toggle_voice, progress_color="#00e5ff")
        self.voice_toggle.pack(side="left", padx=20)

        self.resource_label = ctk.CTkLabel(self.header, text="CPU: 0% | RAM: 0MB | Cost: $0.00", text_color="#8b949e")
        self.resource_label.pack(side="right", padx=20)

        # Tabview
        self.tabview = ctk.CTkTabview(self, fg_color="#0b0c10", segmented_button_selected_color="#00e5ff", segmented_button_selected_hover_color="#00ffa3")
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        self.tab_aura = self.tabview.add("Aura Workspace")
        self.tab_chat = self.tabview.add("Interactive Chat")
        self.tab_visual = self.tabview.add("Visual Replay")
        self.tab_memory = self.tabview.add("Neural Memory")
        self.tab_explorer = self.tabview.add("Project Explorer")

        # Aura Tab
        self.tab_aura.grid_columnconfigure((0,1,2), weight=1)
        self.tab_aura.grid_rowconfigure(0, weight=1)
        self.pm_card = self.create_card(self.tab_aura, "Product Manager", 0)
        self.exec_card = self.create_card(self.tab_aura, "Executor", 1)
        self.qa_card = self.create_card(self.tab_aura, "QA Auditor", 2)

        # Chat Tab
        self.chat_box = ctk.CTkTextbox(self.tab_chat, fg_color="#1a1a1a", text_color="#fff")
        self.chat_box.pack(fill="both", expand=True, padx=10, pady=10)
        self.chat_entry = ctk.CTkEntry(self.tab_chat, placeholder_text="Respond to agent...", fg_color="#1f2833")
        self.chat_entry.pack(fill="x", padx=10, pady=5)
        self.chat_entry.bind("<Return>", self.send_user_response)

        # Visual Replay Tab
        self.visual_frame = ctk.CTkFrame(self.tab_visual, fg_color="#1a1a1a")
        self.visual_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.visual_label = ctk.CTkLabel(self.visual_frame, text="Waiting for visual data...", text_color="#8b949e")
        self.visual_label.pack(pady=20)

        # Memory & Explorer Tabs...
        self.memory_list = ctk.CTkTextbox(self.tab_memory, fg_color="#1a1a1a", text_color="#00e5ff")
        self.memory_list.pack(fill="both", expand=True, padx=10, pady=10)
        self.explorer_list = ctk.CTkTextbox(self.tab_explorer, fg_color="#1a1a1a", text_color="#8b949e")
        self.explorer_list.pack(fill="both", expand=True, padx=10, pady=10)

        # Monologue
        self.log_box = ctk.CTkTextbox(self, height=120, fg_color="#1a1a1a", text_color="#00ffa3", font=("SF Mono", 11))
        self.log_box.grid(row=2, column=0, sticky="ew", padx=10, pady=10)

        self.update_loop()

    def create_card(self, parent, title, col):
        card = ctk.CTkFrame(parent, fg_color="#1f2833", border_width=2, border_color="rgba(255,255,255,0.05)")
        card.grid(row=0, column=col, sticky="nsew", padx=10, pady=10)
        lbl = ctk.CTkLabel(card, text=title, font=("SF Pro Display", 16, "bold"), text_color="#00e5ff")
        lbl.pack(pady=10)
        status = ctk.CTkLabel(card, text="Waiting...", text_color="#8b949e", wraplength=200)
        status.pack(pady=10)
        return {"frame": card, "status": status}

    def toggle_voice(self):
        self.orchestrator.voice.set_enabled(self.voice_var.get())

    def send_user_response(self, event):
        text = self.chat_entry.get()
        if text:
            self.blackboard.user_response = text
            self.blackboard.add_chat("user", text)
            self.chat_box.insert("end", f"User: {text}\n")
            self.chat_entry.delete(0, "end")
            self.blackboard.is_paused = False

    def handle_agent_event(self, event_type, data):
        self.after(0, lambda: self._handle_event_main_thread(event_type, data))

    def _handle_event_main_thread(self, event_type, data):
        if event_type == "visual_feedback":
            self.overlay.show_target(data.get('x', 0), data.get('y', 0))
        elif event_type == "log":
            self.log_box.insert("end", f"⚡ {data}\n"); self.log_box.see("end")
        elif event_type == "clarification_required":
            self.chat_box.insert("end", f"Agent: {data}\n")
            self.tabview.set("Interactive Chat")
        elif event_type == "visual_history":
            self._update_visual_replay(data)
        elif event_type == "agent_active":
             agent_name = data
             for name, card in [("PM", self.pm_card), ("Executor", self.exec_card), ("Auditor", self.qa_card)]:
                 card["frame"].configure(border_color="#00ffa3" if name == agent_name else "rgba(255,255,255,0.05)")

    def _update_visual_replay(self, image_path):
        if os.path.exists(image_path):
            try:
                img = Image.open(image_path)
                # Resize for preview
                img.thumbnail((800, 600))
                photo = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                self.visual_label.configure(image=photo, text="")
            except Exception:
                pass

    def start_task(self):
        goal = self.goal_entry.get()
        if goal:
            self.blackboard.goal = goal
            self.blackboard.is_running = True
            threading.Thread(target=self.run_orchestrator_sync).start()

    def run_orchestrator_sync(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.orchestrator.run(self.blackboard, self.initial_context))

    def update_loop(self):
        cpu = psutil.cpu_percent()
        ram = psutil.Process().memory_info().rss / (1024 * 1024)
        self.resource_label.configure(text=f"CPU: {cpu}% | RAM: {ram:.1f}MB | Cost: ${self.blackboard.total_cost:.4f}")
        if self.blackboard.is_running: self.pm_card["status"].configure(text=self.blackboard.status)
        self.after(1000, self.update_loop)
