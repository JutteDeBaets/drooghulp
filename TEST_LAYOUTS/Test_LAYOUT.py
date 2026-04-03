
import customtkinter as ctk
from PIL import Image
import os

# Basis instellingen
ctk.set_appearance_mode("light") 

temperatuur = 18

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        

        # Formaat voor 7-inch scherm (800x480)
        self.geometry("800x480")
        self.title("Was-App Dashboard")

        # Achtergrondkleur (Lichtgroen)
        self.configure(fg_color="#90EE90") 

        # --- PAD NAAR AFBEELDING ---
        current_path = os.path.dirname(os.path.realpath(__file__))
        image_path = os.path.join(current_path, "tree.png")

        # --- BOOM ICOON AANMAKEN ---
        try:
            self.boom_icoon = ctk.CTkImage(
                light_image=Image.open(image_path),
                dark_image=Image.open(image_path),
                size=(100, 100)
            )
        except Exception as e:
            print(f"Fout: {e}")
            self.boom_icoon = None

        # --- GRID CONFIGURATIE ---
        # Kolom 0 (Links) en Kolom 1 (Rechts)
        self.grid_columnconfigure((0, 1), weight=1)
        # Rij 0 (Bovenste deel voor boom & hoofdtekst) krijgt de meeste ruimte
        self.grid_rowconfigure(0, weight=8)
        # Rij 1 (Onderste deel voor de kleine tekst) krijgt een klein beetje ruimte
        self.grid_rowconfigure(1, weight=2)
        self.grid_rowconfigure(2,weight= 2)

        # --- BOOM (Rij 0, Kolom 0) ---
        if self.boom_icoon:
            self.boom_label = ctk.CTkLabel(self, text="", image=self.boom_icoon)
            self.boom_label.grid(row=0, column=0, padx=(40, 20), sticky="e")

        # --- HOOFDTEKST (Rij 0, Kolom 1) ---
        self.hoofd_tekst = ctk.CTkLabel(
            self, 
            text="De zon schijnt.\nHang de was buiten!", 
            font=("Arial", 34, "bold"),
            text_color="#000000",
            justify="left"
        )
        self.hoofd_tekst.grid(row=0, column=1, padx=(20, 40), sticky="w")

        # --- DE ONDERTEKST (Rij 1, gecentreerd over beide kolommen) ---
        self.kleine_tekst = ctk.CTkLabel(
            self, 
            text="Klik verder", 
            font=("Arial", 18, "italic"), # Iets groter en cursief voor de look
            text_color="#FFFFFF"
        )
        # columnspan=2 zorgt dat de tekst over de hele breedte mag staan
        # sticky="n" zorgt dat hij aan de bovenkant van de onderste rij plakt (dicht bij de rest)
        self.kleine_tekst.grid(row=1, column=0, columnspan=2, sticky="n", pady=(0, 20))



if __name__ == "__main__":
    app = App()
    app.mainloop()