import customtkinter as ctk
from datetime import datetime

class LaundryApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Laundry Dashboard")
        self.geometry("800x480")
        
        # Kleuren configuratie
        self.bg_dark = "#1a1c2c"
        self.bg_light = "#f0f8ff"
        self.accent_green = "#00d056"
        self.accent_orange = "#ff9f00"
        self.accent_red = "#ff3b3b"
        self.text_blue = "#1e3a5f"
        self.active_blue = "#00daff"

        self.configure(fg_color=self.bg_light)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Data: Droogtijden [Buiten, Binnen, Droger]
        self.drying_times = {
            "Licht": [5400, 14400, 2700],      
            "Gemiddeld": [8100, 19800, 4500], 
            "Zwaar": [12600, 25200, 7200]
        }
        
        self.current_timer = None
        self.sidebar_buttons = {}
        self.setup_sidebar()

        # Frames initialiseren
        self.home_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.selection_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.drying_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.confirm_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.timer_frame = ctk.CTkFrame(self, fg_color="transparent")

        self.setup_home_screen()
        self.setup_selection_screen()
        self.setup_bovenhoek()
        
        self.show_home()

    def setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=80, corner_radius=0, fg_color=self.bg_dark)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        menu_items = [
            ("≡", "menu", None),
            ("✧", "home", self.show_home), 
            ("⚡", "energy", None),
            ("⚖", "balance", None),
            ("⌛", "timer", None),
            ("⚙", "settings", None)
        ]

        for icon, name, actie in menu_items:
            btn = ctk.CTkButton(self.sidebar, text=icon, width=40, height=40, 
                                fg_color="transparent", hover_color="#2d2f3f",
                                text_color="white", font=("Arial", 24),
                                command=actie)
            btn.pack(pady=15, padx=10)
            self.sidebar_buttons[name] = btn

    def update_sidebar_selection(self, active_name):
        for name, btn in self.sidebar_buttons.items():
            if name == active_name:
                btn.configure(text_color=self.active_blue)
            else:
                btn.configure(text_color="white")

    def setup_bovenhoek(self):
        nu = datetime.now()
        datum_tijd = nu.strftime("%a %d/%m, %H:%M")
        self.weather_info = ctk.CTkFrame(self, fg_color="white", corner_radius=15, height=60)
        self.weather_info.place(relx=0.97, rely=0.05, anchor="ne")
        ctk.CTkLabel(self.weather_info, text="☀️", font=("Arial", 25), text_color="orange").pack(side="left", padx=(15, 5))
        ctk.CTkLabel(self.weather_info, text=f"Kortrijk\n{datum_tijd}", 
                     font=("Arial Bold", 12), text_color="gray", justify="left").pack(side="left", padx=(5, 15), pady=10)

    def hide_all(self):
        if self.current_timer:
            self.after_cancel(self.current_timer)
            self.current_timer = None
        for f in [self.home_frame, self.selection_frame, self.drying_frame, self.confirm_frame, self.timer_frame]:
            f.grid_forget()

    def show_home(self):
        self.hide_all()
        self.home_frame.grid(row=0, column=1, sticky="nsew")
        self.update_sidebar_selection("home")

    def show_selection(self):
        self.hide_all()
        self.selection_frame.grid(row=0, column=1, sticky="nsew")
        self.update_sidebar_selection(None)

    # --- SCHERM 1: HOME ---
    def setup_home_screen(self):
        ctk.CTkLabel(self.home_frame, text="🌲", font=("Arial", 120), text_color=self.accent_green).pack(expand=True, pady=(60,0))
        ctk.CTkLabel(self.home_frame, text="Hang de was buiten", font=("Arial Bold", 42), text_color="black").pack(expand=True)
        ctk.CTkButton(self.home_frame, text="KLIK VOOR DROOGTYPE", fg_color=self.accent_green, hover_color="#00b34a",text_color="white",
                      height=60, width=400, corner_radius=15, font=("Arial Bold", 18), command=self.show_selection).pack(expand=True, pady=(0, 60))

    # --- SCHERM 2: SELECTIE WAS-SOORT ---
    def setup_selection_screen(self):
        ctk.CTkButton(self.selection_frame, text="←", width=40, height=40, fg_color="white", text_color="black", 
                      command=self.show_home).place(relx=0.05, rely=0.05)
        
        ctk.CTkLabel(self.selection_frame, text="Welk type was?", font=("Arial Bold", 32), text_color="white").pack(pady=(60, 40))
        
        container = ctk.CTkFrame(self.selection_frame, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=40)
        container.grid_columnconfigure((0, 1, 2), weight=1)

        # Naam, Kleur, Tekstkleur, Icoon, Hover-tint
        cards = [
            ("Licht", "#cce0ff", "black", "🪶", "#bbd6ff"), 
            ("Gemiddeld", "#66a3ff", "white", "👕", "#5594ff"), 
            ("Zwaar", "#1a66ff", "white", "👖", "#0052cc")
        ]
        
        for i, (label, color, t_col, icon, hover_c) in enumerate(cards):
            btn = ctk.CTkButton(container, fg_color=color, hover_color=hover_c, corner_radius=25, height=250, text="", 
                                 command=lambda l=label: self.show_drying_options(l))
            btn.grid(row=0, column=i, sticky="nsew", padx=15)
            btn.grid_columnconfigure(0, weight=1)

            # DIKKE EN WITTE TEKST HIER:
            l1 = ctk.CTkLabel(btn, text=icon, font=("Arial Bold", 80), text_color=t_col)
            l1.grid(row=0, column=0, pady=(40, 0))
            l2 = ctk.CTkLabel(btn, text=label, font=("Arial Bold", 22), text_color=t_col)
            l2.grid(row=1, column=0, pady=(10, 40))

            l1.bind("<Button-1>", lambda e, b=btn: b.invoke())
            l2.bind("<Button-1>", lambda e, b=btn: b.invoke())

    # --- SCHERM 3: DROOGOPTIES ---
    def show_drying_options(self, was_type):
        self.hide_all()
        for widget in self.drying_frame.winfo_children(): widget.destroy()
        ctk.CTkButton(self.drying_frame, text="←", width=40, height=40, fg_color="white", text_color="black", 
                      command=self.show_selection).place(relx=0.05, rely=0.05)

        tijden_sec = self.drying_times[was_type]
        tijden_text = [f"~{s//3600}u {(s%3600)//60}m" for s in tijden_sec]
        
        # Icoon, Naam, Tijd, Kleur, Seconden, Hover-tint
        opties = [("🌲", "Buiten", tijden_text[0], self.accent_green, tijden_sec[0], "#00b34a"),
                  ("🏠", "Binnen", tijden_text[1], self.accent_orange, tijden_sec[1], "#e68f00"),
                  ("🌀", "Droger", tijden_text[2], self.accent_red, tijden_sec[2], "#e63535")]

        container = ctk.CTkFrame(self.drying_frame, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=40, pady=100)
        container.grid_columnconfigure((0, 1, 2), weight=1)

        for i, (icon, label, t_txt, kleur, t_sec, h_kleur) in enumerate(opties):
            btn = ctk.CTkButton(container, fg_color=kleur, hover_color=h_kleur, corner_radius=25, height=280, text="",
                                 command=lambda l=label, s=t_sec, k=kleur: self.show_confirmation(was_type, l, s, k))
            btn.grid(row=0, column=i, sticky="nsew", padx=15)
            btn.grid_columnconfigure(0, weight=1)

            # DIKKE EN WITTE TEKST HIER:
            l1 = ctk.CTkLabel(btn, text=icon, font=("Arial Bold", 75), text_color="white")
            l1.grid(row=0, column=0, pady=(30,0))
            l2 = ctk.CTkLabel(btn, text=label, font=("Arial Bold", 24), text_color="white")
            l2.grid(row=1, column=0)
            l3 = ctk.CTkLabel(btn, text=t_txt, font=("Arial Bold", 18), text_color="white")
            l3.grid(row=2, column=0, pady=(5, 30))

            for lbl in [l1, l2, l3]: lbl.bind("<Button-1>", lambda e, b=btn: b.invoke())

        self.drying_frame.grid(row=0, column=1, sticky="nsew")

    # --- SCHERM 4: BEVESTIGING (HERSTELD) ---
    def show_confirmation(self, was_type, methode, seconden, kleur):
        self.hide_all()
        for widget in self.confirm_frame.winfo_children(): widget.destroy()
        
        ctk.CTkButton(self.confirm_frame, text="←", width=40, height=40, fg_color="white", text_color="black", 
                      command=lambda: self.show_drying_options(was_type)).place(relx=0.05, rely=0.05)

        icon = "🌲" if methode == "Buiten" else "🏠" if methode == "Binnen" else "🌀"
        # Hover kleur bepalen op basis van de methode
        h_col = "#00b34a" if methode == "Buiten" else "#e68f00" if methode == "Binnen" else "#e63535"

        ctk.CTkLabel(self.confirm_frame, text=icon, font=("Arial Bold", 120), text_color=kleur).pack(pady=(40, 10))
        ctk.CTkLabel(self.confirm_frame, text=f"{was_type} was {methode.lower()} drogen", 
                     font=("Arial Bold", 36), text_color=self.text_blue).pack()
        
        t_txt = f"~{seconden//3600}u {(seconden%3600)//60}m"
        ctk.CTkLabel(self.confirm_frame, text=f"Verwachte droogtijd: {t_txt}", font=("Arial Bold", 22), text_color="black").pack(pady=20)

        ctk.CTkButton(self.confirm_frame, text="BEVESTIGEN", fg_color=kleur, hover_color=h_col, height=70, width=500, 
                      corner_radius=20, font=("Arial Bold", 20),text_color="white",
                      command=lambda: self.start_timer(was_type, methode, seconden)).pack(pady=40)
        
        self.confirm_frame.grid(row=0, column=1, sticky="nsew")

    # --- SCHERM 5: TIMER ---
    def start_timer(self, was_type, methode, seconden):
        self.hide_all()
        # Maak het scherm leeg voor we beginnen
        for widget in self.timer_frame.winfo_children(): widget.destroy()

        # 1. De grote tikkende timer bovenin
        self.time_label = ctk.CTkLabel(self.timer_frame, text="", font=("Arial Bold", 80), text_color=self.text_blue)
        self.time_label.pack(pady=(40, 20))

        # Container voor de informatiekaarten
        info_container = ctk.CTkFrame(self.timer_frame, fg_color="transparent")
        info_container.pack(fill="x", padx=100)
        info_container.grid_columnconfigure((0, 1), weight=1)
        
        # Helper functie voor mooie kaarten met dikke tekst
        def make_card(master, icon, txt, col, row, col_idx, width_val=1):
            f = ctk.CTkFrame(master, fg_color="white", corner_radius=15, height=70)
            f.grid(row=row, column=col_idx, columnspan=width_val, sticky="nsew", padx=10, pady=10)
            # Hier zorgen we voor de dikke tekst
            ctk.CTkLabel(f, text=f"{icon}  {txt}", font=("Arial Bold", 20), text_color=col).pack(expand=True)

        # RIJ 1: Methode (Binnen/Buiten) en Wastype (Licht/Middel/Zwaar)
        icon_m = "🌲" if methode == "Buiten" else "🏠" if methode == "Binnen" else "🌀"
        color_m = self.accent_green if methode == "Buiten" else self.accent_orange
        make_card(info_container, icon_m, methode, color_m, 0, 0)
        
        icon_w = "🪶" if was_type == "Licht" else "👕" if was_type == "Gemiddeld" else "👖"
        make_card(info_container, icon_w, was_type, "blue", 0, 1)

        # RIJ 2 & 3: EXTRA INFO OP BASIS VAN METHODE
        if methode == "Buiten":
            # Weer info voor buiten
            make_card(info_container, "☀️", "20°C", "orange", 1, 0, width_val=2)
            make_card(info_container, "🌧️", "GEEN regen verwacht", "#3498db", 2, 0, width_val=2)
        
        elif methode == "Binnen":
            # Klimaat info voor binnen
            make_card(info_container, "🌡️", "21°C", "#e67e22", 1, 0, width_val=2)
            make_card(info_container, "💧", "45%", "#2980b9", 2, 0, width_val=2)

        # 2. De grote ANNULEREN knop onderaan
        ctk.CTkButton(self.timer_frame, text="ANNULEREN", fg_color="#4a5568", hover_color="#2d3748", 
                      height=60, width=500, corner_radius=15, font=("Arial Bold", 18),text_color="white",
                      command=lambda: self.confirm_cancel(was_type, methode)).pack(pady=30)

        # Timer starten
        self.remaining_sec = seconden
        self.update_timer_label()
        self.timer_frame.grid(row=0, column=1, sticky="nsew")

    def update_timer_label(self):
        if self.remaining_sec >= 0:
            h, m, s = self.remaining_sec // 3600, (self.remaining_sec % 3600) // 60, self.remaining_sec % 60
            tijd_str = f"{h:02d}:{m:02d}:{s:02d}"
            self.time_label.configure(text=tijd_str)
            if hasattr(self, 'popup_time_label') and self.popup_time_label and self.popup_time_label.winfo_exists():
                self.popup_time_label.configure(text=tijd_str)
            self.remaining_sec -= 1
            self.current_timer = self.after(1000, self.update_timer_label)

    def confirm_cancel(self, was_type, methode):
        self.overlay = ctk.CTkFrame(self, fg_color="#2b2b2b") 
        self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        popup = ctk.CTkFrame(self.overlay, fg_color="White", corner_radius=25, width=500, height=380)
        popup.place(relx=0.5, rely=0.5, anchor="center")
        popup.pack_propagate(False)

        ctk.CTkLabel(popup, text="Timer annuleren?", font=("Arial Bold", 20), text_color="Black").pack(pady=(30, 5))
        self.popup_time_label = ctk.CTkLabel(popup, text="", font=("Arial Bold", 32), text_color="Black")
        self.popup_time_label.pack(pady=10)

        ctk.CTkButton(popup, text="STOP TIMER", fg_color=self.accent_red, height=60, width=400,text_color="white", 
                      corner_radius=15, command=self.final_cancel).pack(pady=10)
        ctk.CTkButton(popup, text="GA TERUG", fg_color="#4a5568", height=60, width=400,text_color="white",
                      corner_radius=15, command=self.close_popup).pack(pady=10)

    def close_popup(self):
        self.popup_time_label = None
        self.overlay.destroy()

    def final_cancel(self):
        self.close_popup()
        self.show_home()

if __name__ == "__main__":
    app = LaundryApp()
    app.mainloop()