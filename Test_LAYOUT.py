import customtkinter as ctk
from PIL import Image
import os

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.geometry("800x480")
        self.title("Icoon Dashboard")
        self.licht_staat_aan = False

        # --- PAD NAAR AFBEELDING ---
        # Dit zorgt dat Python het plaatje altijd vindt in de huidige map
        current_path = os.path.dirname(os.path.realpath(__file__))
        image_path = os.path.join(current_path, "lamp.png")

        # --- ICOON AANMAKEN ---
        self.lamp_icoon = ctk.CTkImage(
            light_image=Image.open(image_path),
            dark_image=Image.open(image_path),
            size=(100, 100) # Maak het lekker groot voor het 7-inch scherm
        )

        # --- GRID CONFIGURATIE ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure((0, 1), weight=1)

        # Het licht-vlak (boven)
        self.licht_frame = ctk.CTkFrame(self, width=200, height=200, fg_color="#000000", corner_radius=20)
        self.licht_frame.grid(row=0, column=0, pady=20)

        # --- DE ICOON-KNOP (onder) ---
        self.knop = ctk.CTkButton(
            self, 
            text="",                # Geen tekst = icoon in het midden
            image=self.lamp_icoon,   # Het plaatje
            width=150,              # Breedte van de knop zelf
            height=150,             # Hoogte van de knop zelf
            fg_color="#3B3B3B",      # Een neutrale kleur voor de knop
            hover_color="#59D3B6",
            command=self.toggle_licht
        )
        self.knop.grid(row=1, column=0, pady=20)

    def toggle_licht(self):
        if self.licht_staat_aan:
            self.licht_frame.configure(fg_color="#000000")
            self.licht_staat_aan = False
        else:
            self.licht_frame.configure(fg_color="#FFFF00")
            self.licht_staat_aan = True

if __name__ == "__main__":
    app = App()
    app.mainloop()