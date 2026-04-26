import customtkinter as ctk
from datetime import datetime

class LaundryApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Laundry Dashboard")
        self.geometry("800x480")
        
        # Kleuren Palette
        self.bg_dark = "#1a1c2c"
        self.bg_light = "#f0f8ff"
        self.accent_green = "#00d056"
        self.accent_orange = "#ff9f00"
        self.accent_red = "#ff3b3b"
        self.text_blue = "#1e3a5f"

        self.configure(fg_color=self.bg_light)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar_visible = True
        self.current_timer = None
        self.sidebar_buttons = {}

        # Data: Droogtijden
        self.drying_times = {
            "Licht": [5400, 14400, 2700],      
            "Gemiddeld": [8100, 19800, 4500], 
            "Zwaar": [12600, 25200, 7200]
        }

        # Frames initialiseren
        self.home_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.selection_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.drying_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.confirm_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.timer_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.compare_frame = ctk.CTkFrame(self, fg_color="transparent")

        self.setup_sidebar()
        self.setup_home_screen()
        self.setup_selection_screen()
        self.show_home()

    # --- SIDEBAR & NAVIGATIE ---
    def setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=80, corner_radius=0, fg_color=self.bg_dark)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        self.ham_btn = ctk.CTkButton(self.sidebar, text="≡", width=80, height=80, 
                                     fg_color="white", text_color="black", corner_radius=0,
                                     font=("Arial", 32), command=self.toggle_sidebar)
        self.ham_btn.pack(pady=(0, 20))

        menu_items = [
            ("✧", "home", self.show_home), 
            ("⚡", "energy", None),
            ("⚖", "balance", self.show_comparison),
            ("⌛", "timer", None),
            ("⚙", "settings", None)
        ]

        for icon, name, actie in menu_items:
            btn = ctk.CTkButton(self.sidebar, text=icon, width=80, height=60, 
                                fg_color="transparent", text_color="white", 
                                font=("Arial", 28), command=actie)
            btn.pack(pady=10)
            self.sidebar_buttons[name] = btn

    def toggle_sidebar(self):
        if self.sidebar_visible:
            self.sidebar.grid_forget()
            self.sidebar_visible = False
        else:
            self.sidebar.grid(row=0, column=0, sticky="nsew")
            self.sidebar_visible = True

    def hide_all(self):
        if self.current_timer:
            self.after_cancel(self.current_timer)
            self.current_timer = None
        for f in [self.home_frame, self.selection_frame, self.drying_frame, 
                  self.confirm_frame, self.timer_frame, self.compare_frame]:
            f.grid_forget()

    # --- SCHERM 1: HOME ---
    def show_home(self):
        self.hide_all()
        self.home_frame.grid(row=0, column=1, sticky="nsew")

    def setup_home_screen(self):
        ctk.CTkLabel(self.home_frame, text="🌲", font=("Arial", 120), text_color=self.accent_green).pack(pady=(60,0))
        ctk.CTkLabel(self.home_frame, text="Hang de was buiten", font=("Arial Bold", 42), text_color="black").pack(pady=20)
        
        btn_cont = ctk.CTkFrame(self.home_frame, fg_color="transparent")
        btn_cont.pack(pady=40)

        ctk.CTkButton(btn_cont, text="TIMER INSTELLEN", fg_color=self.accent_green, hover_color="#00b34a",
                      width=280, height=70, corner_radius=15, font=("Arial Bold", 18),
                      command=self.show_selection).pack(side="left", padx=15)
        
        ctk.CTkButton(btn_cont, text="VERGELIJKING", fg_color="#4a5568", hover_color="#2d3748",
                      width=280, height=70, corner_radius=15, font=("Arial Bold", 18),
                      command=self.show_comparison).pack(side="left", padx=15)

    # --- SCHERM 2: WAS SELECTIE ---
    def show_selection(self):
        self.hide_all()
        self.selection_frame.grid(row=0, column=1, sticky="nsew")

    def setup_selection_screen(self):
        ctk.CTkLabel(self.selection_frame, text="Welk type was?", font=("Arial Bold", 32), text_color=self.text_blue).pack(pady=(60, 40))
        container = ctk.CTkFrame(self.selection_frame, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=40)
        container.grid_columnconfigure((0, 1, 2), weight=1)

        cards = [("Licht", "#cce0ff", "black", "🪶", "#bbd6ff"), 
                 ("Gemiddeld", "#66a3ff", "white", "👕", "#5594ff"), 
                 ("Zwaar", "#1a66ff", "white", "👖", "#0052cc")]
        
        for i, (label, color, t_col, icon, hover_c) in enumerate(cards):
            btn = ctk.CTkButton(container, fg_color=color, hover_color=hover_c, corner_radius=25, height=250, text="", 
                                 command=lambda l=label: self.show_drying_options(l))
            btn.grid(row=0, column=i, sticky="nsew", padx=15)
            btn.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(btn, text=icon, font=("Arial Bold", 80), text_color=t_col).grid(row=0, column=0, pady=(40, 0))
            ctk.CTkLabel(btn, text=label, font=("Arial Bold", 22), text_color=t_col).grid(row=1, column=0, pady=(10, 40))

    # --- SCHERM 3: DROOGOPTIES ---
    def show_drying_options(self, was_type):
        self.hide_all()
        for widget in self.drying_frame.winfo_children(): widget.destroy()
        
        tijden_sec = self.drying_times[was_type]
        opties = [("🌲", "Buiten", f"~{tijden_sec[0]//3600}u", self.accent_green, tijden_sec[0], "#00b34a"),
                  ("🏠", "Binnen", f"~{tijden_sec[1]//3600}u", self.accent_orange, tijden_sec[1], "#e68f00"),
                  ("🌀", "Droger", f"~{tijden_sec[2]//3600}u", self.accent_red, tijden_sec[2], "#e63535")]

        container = ctk.CTkFrame(self.drying_frame, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=40, pady=100)
        container.grid_columnconfigure((0, 1, 2), weight=1)

        for i, (icon, label, t_txt, kleur, t_sec, h_kleur) in enumerate(opties):
            btn = ctk.CTkButton(container, fg_color=kleur, hover_color=h_kleur, corner_radius=25, height=280, text="",
                                 command=lambda l=label, s=t_sec, k=kleur: self.show_confirmation(was_type, l, s, k))
            btn.grid(row=0, column=i, sticky="nsew", padx=15)
            ctk.CTkLabel(btn, text=icon, font=("Arial Bold", 75), text_color="white").pack(pady=(30,0))
            ctk.CTkLabel(btn, text=label, font=("Arial Bold", 24), text_color="white").pack()
            ctk.CTkLabel(btn, text=t_txt, font=("Arial Bold", 18), text_color="white").pack(pady=(5, 30))
        self.drying_frame.grid(row=0, column=1, sticky="nsew")

    # --- SCHERM 4: BEVESTIGING ---
    def show_confirmation(self, was_type, methode, seconden, kleur):
        self.hide_all()
        for widget in self.confirm_frame.winfo_children(): widget.destroy()
        
        icon = "🌲" if methode == "Buiten" else "🏠" if methode == "Binnen" else "🌀"
        ctk.CTkLabel(self.confirm_frame, text=icon, font=("Arial Bold", 120), text_color=kleur).pack(pady=(40, 10))
        ctk.CTkLabel(self.confirm_frame, text=f"{was_type} was {methode.lower()} drogen", font=("Arial Bold", 36), text_color="black").pack()
        
        ctk.CTkButton(self.confirm_frame, text="BEVESTIGEN", fg_color=kleur, height=70, width=400, 
                      corner_radius=20, font=("Arial Bold", 20),
                      command=lambda: self.start_timer(was_type, methode, seconden)).pack(pady=40)
        self.confirm_frame.grid(row=0, column=1, sticky="nsew")

    # --- SCHERM 5: TIMER ---
    def start_timer(self, was_type, methode, seconden):
        self.hide_all()
        for widget in self.timer_frame.winfo_children(): widget.destroy()

        self.time_label = ctk.CTkLabel(self.timer_frame, text="", font=("Arial Bold", 80), text_color=self.text_blue)
        self.time_label.pack(pady=40)

        f = ctk.CTkFrame(self.timer_frame, fg_color="white", corner_radius=15, height=70)
        f.pack(pady=10, padx=100, fill="x")
        ctk.CTkLabel(f, text=f"{methode} | {was_type} was", font=("Arial Bold", 20), text_color="black").pack(expand=True)

        self.remaining_sec = seconden
        self.update_timer_label()
        self.timer_frame.grid(row=0, column=1, sticky="nsew")

    def update_timer_label(self):
        if self.remaining_sec >= 0:
            h, m, s = self.remaining_sec // 3600, (self.remaining_sec % 3600) // 60, self.remaining_sec % 60
            self.time_label.configure(text=f"{h:02d}:{m:02d}:{s:02d}")
            self.remaining_sec -= 1
            self.current_timer = self.after(1000, self.update_timer_label)

    # --- SCHERM 6: VERGELIJKING (VOLLEDIG) ---
    def show_comparison(self):
        self.hide_all()
        for w in self.compare_frame.winfo_children(): w.destroy()
        
        inner = ctk.CTkFrame(self.compare_frame, fg_color="#ffffff", corner_radius=0)
        inner.pack(fill="both", expand=True)
        inner.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(inner, text="Vergelijking", font=("Arial Bold", 38), text_color="black").grid(row=0, column=0, columnspan=3, pady=30)

        data = [
            {"t": "Buiten drogen", "d": "droogtijd 4u", "k": "Gratis", "temp": "16°C", "v": "95%", "ex": "Morgen regen", "ex_c": "#f39c12", "h": False},
            {"t": "Binnen drogen", "d": "droogtijd 9u", "k": "Gratis", "temp": "20°C", "v": "45%", "ex": "Verluchten!", "ex_c": "transparent", "h": False},
            {"t": "Droogkast", "d": "droogtijd 1u", "k": "€0,81", "temp": "/", "v": "/", "ex": "Daluur: €0,52", "ex_c": "transparent", "h": True}
        ]

        for i, item in enumerate(data):
            kolom = ctk.CTkFrame(inner, fg_color="transparent")
            kolom.grid(row=1, column=i, sticky="nsew", padx=10)
            ctk.CTkLabel(kolom, text=item["t"], font=("Arial Bold", 22), text_color="black").pack()
            ctk.CTkFrame(kolom, height=2, width=100, fg_color="black").pack(pady=10)
            ctk.CTkLabel(kolom, text=item["d"], font=("Arial", 18), fg_color="#27ae60" if item["h"] else "transparent", text_color="black").pack(pady=5)
            ctk.CTkLabel(kolom, text=item["k"], font=("Arial Bold", 18), fg_color="#27ae60", text_color="white", corner_radius=6, width=140).pack(pady=15)
            ctk.CTkLabel(kolom, text=f"{item['temp']} | {item['v']}", font=("Arial", 18), text_color="black").pack()
            if item["ex"] != "transparent":
                box = ctk.CTkFrame(kolom, fg_color=item["ex_c"], corner_radius=8)
                box.pack(pady=20)
                ctk.CTkLabel(box, text=item["ex"], text_color="black" if item["ex_c"]=="transparent" else "white").pack(padx=10, pady=5)

        self.compare_frame.grid(row=0, column=1, sticky="nsew")

if __name__ == "__main__":
    app = LaundryApp()
    app.mainloop()