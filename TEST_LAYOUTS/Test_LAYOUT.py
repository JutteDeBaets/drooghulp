import customtkinter as ctk
from PIL import Image
import os

# Basis instellingen
ctk.set_appearance_mode("dark") 
temperatuur = 16

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Formaat voor 7-inch scherm (800x480)
        self.geometry("800x480")
        self.title("Was-App Dashboard")

        # Configureer het hoofdgrid van het venster (1 cel die het hele scherm vult)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- 1. HET HOOFDSCHERM (FRAME) ---
        self.home_frame = ctk.CTkFrame(self, fg_color="#90EE90", corner_radius=0)
        self.home_frame.grid(row=0, column=0, sticky="nsew")
        self.setup_home_scherm()

        # --- 2. HET DETAIL SCHERM (FRAME) ---
        # We maken hem aan, maar hij wordt pas zichtbaar na een klik
        self.detail_frame = ctk.CTkFrame(self, fg_color="black", corner_radius=0)
        self.setup_detail_scherm()

        # Verbind een klik op het hele venster aan de wissel-functie
        self.bind("<Button-1>", self.wissel_scherm)
        self.huidig_scherm = "home"

    def setup_home_scherm(self):
        # Grid voor het homescherm
        self.home_frame.grid_columnconfigure((0, 1), weight=1)
        self.home_frame.grid_rowconfigure(0, weight=8)
        self.home_frame.grid_rowconfigure((1, 2), weight=2)

        # Boom Icoon inladen
        current_path = os.path.dirname(os.path.realpath(__file__))
        image_path = os.path.join(current_path, "tree.png")
        try:
            self.boom_icoon = ctk.CTkImage(light_image=Image.open(image_path), 
                                           dark_image=Image.open(image_path), 
                                           size=(120, 120))
            self.boom_label = ctk.CTkLabel(self.home_frame, text="", image=self.boom_icoon)
            self.boom_label.grid(row=0, column=0, padx=(40, 20), sticky="e")
        except:
            print("Kon tree.png niet vinden")

        # Grote tekst
        self.hoofd_tekst = ctk.CTkLabel(self.home_frame, 
                                       text="De zon schijnt.\nHang de was buiten!", 
                                       font=("Arial", 34, "bold"), 
                                       text_color="#000000", 
                                       justify="left")
        self.hoofd_tekst.grid(row=0, column=1, padx=(20, 40), sticky="w")

        # Kleine instructie tekst
        self.kleine_tekst = ctk.CTkLabel(self.home_frame, 
                                        text="Tik voor details", 
                                        font=("Arial", 18, "italic"), 
                                        text_color="#000000")
        self.kleine_tekst.grid(row=1, column=0, columnspan=2, sticky="n")

        # Temperatuur tekst
        self.graden_label = ctk.CTkLabel(self.home_frame, 
                                         text=f"Temperatuur: {temperatuur}°C", 
                                         font=("Arial", 16), 
                                         text_color="#000000")
        self.graden_label.grid(row=2, column=0, columnspan=2, sticky="n")

    def setup_detail_scherm(self):
        # Grid voor detail scherm: 3 kolommen, 2 rijen
        self.detail_frame.grid_columnconfigure((0, 1, 2), weight=1)
        self.detail_frame.grid_rowconfigure(0, weight=1) # Rij voor titel
        self.detail_frame.grid_rowconfigure(1, weight=4) # Rij voor de 3 vakken

        # --- TITEL BOVENAAN ---
        self.titel_label = ctk.CTkLabel(self.detail_frame, 
                                       text="Welke stof?", 
                                       font=("Arial", 32, "bold"), 
                                       text_color="white")
        self.titel_label.grid(row=0, column=0, columnspan=3, pady=(20, 0))

        # --- DE DRIE VAKKEN ---
        kleuren = ["#90EE90", "#90EE90", "#90EE90"]
        teksten = ["Lichte stof", "Middel stof", "Zware stof"]

        for i in range(3):
            # Maak een frame per vakje
            v = ctk.CTkFrame(self.detail_frame, fg_color=kleuren[i], corner_radius=15)
            v.grid(row=1, column=i, sticky="nsew", padx=15, pady=30)
            
            # Zet de tekst in het midden van het vakje
            ctk.CTkLabel(v, 
                         text=teksten[i], 
                         font=("Arial", 22, "bold"), 
                         text_color="black").pack(expand=True)

    def wissel_scherm(self, event):
        # Simpele logica om tussen de twee frames te schakelen
        if self.huidig_scherm == "home":
            self.home_frame.grid_forget()
            self.detail_frame.grid(row=0, column=0, sticky="nsew")
            self.huidig_scherm = "detail"
        else:
            self.detail_frame.grid_forget()
            self.home_frame.grid(row=0, column=0, sticky="nsew")
            self.huidig_scherm = "home"

if __name__ == "__main__":
    app = App()
    app.mainloop()
