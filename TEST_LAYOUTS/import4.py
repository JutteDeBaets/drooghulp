import customtkinter as ctk
from datetime import datetime
import json
import threading
import time
import random  # Voor testwaarden
from urllib.request import urlopen
 
import requests
 
# ─────────────────────────────────────────────
#  PLATFORM DETECTIE
# ─────────────────────────────────────────────
try:
    import RPi.GPIO as GPIO
    ON_PI = True
except ImportError:
    GPIO = None
    ON_PI = False
    print("Systeem: Geen Raspberry Pi gedetecteerd. Test-modus geactiveerd.")
 
# ─────────────────────────────────────────────
#  PIN-MAPPING BOARD → BCM  (uit main.py)
# ─────────────────────────────────────────────
BOARD_TO_BCM = {
    3: 2, 5: 3, 7: 4, 8: 14, 10: 15, 11: 17, 12: 18, 13: 27,
    15: 22, 16: 23, 18: 24, 19: 10, 21: 9, 22: 25, 23: 11,
    24: 8, 26: 7, 27: 0, 28: 1, 29: 5, 31: 6, 32: 12, 33: 13,
    35: 19, 36: 16, 37: 26, 38: 20, 40: 21,
}
 
def resolve_bcm_pin(pin, numbering_mode):
    """Zet een BOARD-pin om naar BCM indien nodig."""
    mode = numbering_mode.upper()
    if mode == "BCM":
        return pin
    if mode == "BOARD":
        if pin not in BOARD_TO_BCM:
            raise ValueError(f"BOARD pin {pin} kan niet worden omgezet naar BCM.")
        return BOARD_TO_BCM[pin]
    raise ValueError("PIN_NUMBERING moet 'BOARD' of 'BCM' zijn.")
 
def _build_dht_reader(sensor_names, bcm_pin):
    """Bouw een DHT-lezer: CircuitPython met auto-fallback naar Adafruit_DHT (uit main.py)."""
    circuit_error = None
    try:
        import adafruit_dht
        import board
 
        board_pin_name = f"D{bcm_pin}"
        if not hasattr(board, board_pin_name):
            raise RuntimeError(f"board.{board_pin_name} is niet beschikbaar op dit apparaat.")
        board_pin = getattr(board, board_pin_name)
 
        sensor_types = list(sensor_names) or ["DHT22"]
        current_index = 0
        failures = 0
        max_failures = 3
 
        def _make_sensor(sensor_type):
            if sensor_type == "DHT11":
                return adafruit_dht.DHT11(board_pin, use_pulseio=False)
            return adafruit_dht.DHT22(board_pin, use_pulseio=False)
 
        sensor_obj = _make_sensor(sensor_types[current_index])
 
        def _circuit_read():
            nonlocal sensor_obj, current_index, failures
            try:
                humidity    = sensor_obj.humidity
                temperature = sensor_obj.temperature
                if humidity is None or temperature is None:
                    raise RuntimeError("DHT gaf None terug")
                failures = 0
                return humidity, temperature
            except RuntimeError:
                failures += 1
                if failures >= max_failures:
                    failures = 0
                    current_index = (current_index + 1) % len(sensor_types)
                    try:
                        sensor_obj.exit()
                    except Exception:
                        pass
                    sensor_obj = _make_sensor(sensor_types[current_index])
                return None, None
 
        label = "|".join(sensor_types)
        return _circuit_read, f"adafruit-circuitpython-dht({label})", sensor_obj
 
    except Exception as err:
        circuit_error = err
 
    try:
        import Adafruit_DHT
        sensor_obj = getattr(Adafruit_DHT, sensor_names[0])
 
        def _legacy_read():
            return Adafruit_DHT.read_retry(sensor_obj, bcm_pin, retries=3, delay_seconds=1)
 
        return _legacy_read, "Adafruit_DHT", None
    except Exception as adafruit_error:
        raise RuntimeError(
            "Geen ondersteunde DHT-backend beschikbaar. "
            "Installeer adafruit-circuitpython-dht of Adafruit_DHT. "
            f"CircuitPython fout: {circuit_error}; "
            f"Adafruit_DHT fout: {adafruit_error}"
        )
 
# ─────────────────────────────────────────────
#  CONSTANTEN  (één plek om te wijzigen)
# ─────────────────────────────────────────────
# SPI bit-bang instellingen (Grove Sound via PmodAD1)
SOUND_CLK_PIN          = 16        # BOARD pin
SOUND_CS_PIN           = 12        # BOARD pin
SOUND_D0_PIN           = 36        # BOARD pin
SOUND_PIN_MODE         = "BOARD"
HALF_CLOCK_DELAY       = 0.00001   # seconden
VREF                   = 3.3       # volt
ADC_SAMPLE_ON_FALLING  = True
 
# Bewegingssensor (BCM 14 = BOARD 8)
MOTION_BCM_PIN = 14
 
# DHT-sensor (BOARD 7 = BCM 4)
DHT_SENSOR_TYPES = ["DHT22", "DHT11"]
DHT_PIN          = 7
DHT_PIN_MODE     = "BOARD"
 
DEFAULT_CITY = "Kortrijk"
DEFAULT_LAT   = 50.828
DEFAULT_LON   = 3.265
DEFAULT_WIND_BUITEN  = 10   # km/h
DEFAULT_VOCHT_BUITEN = 60   # % (fallback als API geen vocht geeft)
MAX_DROOGTIJD_UREN   = 24
MIN_DROOGTIJD_UREN   = 0.5
 
 
class LaundryApp(ctk.CTk):
 
    # ─────────────────────────────────────────
    #  KLASSE-CONSTANTEN
    # ─────────────────────────────────────────
    STOF_FACTOREN = {"Licht": 0.6, "Gemiddeld": 1.0, "Zwaar": 1.5}
 
    # Droogkast-basistijden in seconden (buiten/binnen worden live berekend)
    KAST_SECONDEN = {"Licht": 2700, "Gemiddeld": 4500, "Zwaar": 7200}
 
    KLEUREN = {
        "bg_dark":      "#1a1c2c",
        "bg_light":     "#f0f8ff",
        "accent_green": "#00d056",
        "accent_orange":"#ff9f00",
        "accent_red":   "#ff3b3b",
        "text_blue":    "#1e3a5f",
        "active_blue":  "#00daff",
    }
   
    # ─────────────────────────────────────────
    #  INIT
    # ─────────────────────────────────────────
    def __init__(self):
        super().__init__()
 
        self.title("Laundry Dashboard")
        self.geometry("800x480")
 
        self.actieve_timers = []
        self.current_screen = None  # Cruciaal: dit voorkomt de AttributeError
        self.current_timer = None
        self.huidig_stoftype = "Gemiddeld"
        self.sidebar_buttons = {}
        self.sidebar_visible = True
        self.popup_time_label = None
 
        # Snelkoppelingen naar kleuren
        for k, v in self.KLEUREN.items():
            setattr(self, k, v)
 
        self.configure(fg_color=self.bg_light)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.actieve_timers = []  # Lijst met dictionaries: {'naam': ..., 'resterend': ..., 'totaal': ..., 'type': ...}
        self.update_timers_loop() # Start het tikken van de klok
 
        # ── State ──────────────────────────────
        self.huidig_stoftype = "Gemiddeld"
        self.current_timer   = None
        self.sidebar_buttons = {}
        self.sidebar_visible = True
        self.popup_time_label = None
 
        # ── GPIO + sensoren initialiseren (uit main.py) ────────────────
        self._gpio_clk  = None
        self._gpio_cs   = None
        self._gpio_d0   = None
        self._dht_read  = None      # callable: () -> (humidity, temperature)
        self._dht_obj   = None      # sensor-object voor exit() bij afsluiten
        self._last_temp = None
        self._last_hum  = None
        self._dht_error_reported = False
        self._next_dht_time = 0.0
 
        if ON_PI:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
 
                self._gpio_clk = resolve_bcm_pin(SOUND_CLK_PIN, SOUND_PIN_MODE)
                self._gpio_cs  = resolve_bcm_pin(SOUND_CS_PIN,  SOUND_PIN_MODE)
                self._gpio_d0  = resolve_bcm_pin(SOUND_D0_PIN,  SOUND_PIN_MODE)
 
                GPIO.setup(self._gpio_clk, GPIO.OUT, initial=GPIO.LOW)
                GPIO.setup(self._gpio_cs,  GPIO.OUT, initial=GPIO.HIGH)
                GPIO.setup(self._gpio_d0,  GPIO.IN,  pull_up_down=GPIO.PUD_DOWN)
                GPIO.setup(MOTION_BCM_PIN, GPIO.IN,  pull_up_down=GPIO.PUD_DOWN)
 
                self.gpio_available = True
                print(
                    f"GPIO: CLK=BCM{self._gpio_clk}, CS=BCM{self._gpio_cs}, "
                    f"D0=BCM{self._gpio_d0}, Motion=BCM{MOTION_BCM_PIN}"
                )
            except Exception as e:
                self.gpio_available = False
                print(f"GPIO niet beschikbaar: {e}")
 
            try:
                bcm_dht = resolve_bcm_pin(DHT_PIN, DHT_PIN_MODE)
                self._dht_read, backend, self._dht_obj = _build_dht_reader(
                    DHT_SENSOR_TYPES, bcm_dht
                )
                print(f"Sensor: DHT geïnitialiseerd via {backend} op BCM{bcm_dht}.")
            except Exception as e:
                self._dht_read = None
                print(f"DHT sensor niet beschikbaar: {e}")
        else:
            self.gpio_available = False
            print("Systeem: Geen Raspberry Pi – test-modus actief.")
 
        # Gecachte weerdata
        self.locatie = {"city": DEFAULT_CITY, "lat": DEFAULT_LAT, "lon": DEFAULT_LON}
        
        self.huidige_temp = "--°C"
        self.weer_code    = 0
 
        self.live_energieprijs = 0.28
        self.fetch_energy_prices()
 
        # ── Ham-knop aanmaken VÓÓR sidebar (fix crash) ──
        self.ham_btn = ctk.CTkButton(
            self, text="≡", width=40, height=40,
            fg_color=self.bg_dark, text_color="white",
            font=("Arial", 30), corner_radius=10, border_width=0,
            command=self.toggle_sidebar
        )
        
        self.METHODE_STYLING = {
            "Buiten": {"icoon": "🌲", "kleur": "#27ae60"},
            "Binnen": {"icoon": "🏠", "kleur": "#f39c12"},
            "Droger": {"icoon": "🌀", "kleur": "#e74c3c"}
        }
 
        # ── UI opbouwen ────────────────────────
        self.setup_sidebar()
        self._init_frames()
        self.setup_home_screen()
        self.setup_selection_screen()
        self.setup_bovenhoek()
        self.show_home()
 
        # ── Sluit-handler ──────────────────────
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
 
        # ── Weerdata laden op achtergrond ───────
        threading.Thread(target=self._load_weather_async, daemon=True).start()
 
    def on_closing(self):
        """Veilig afsluiten: annuleer actieve timer en sluit sensoren."""
        if self.current_timer:
            self.after_cancel(self.current_timer)
        if self._dht_obj is not None:
            try:
                self._dht_obj.exit()
            except Exception:
                pass
        if ON_PI:
            try:
                pins = [p for p in [
                    self._gpio_clk, self._gpio_cs, self._gpio_d0, MOTION_BCM_PIN
                ] if p is not None]
                GPIO.cleanup(pins)
            except Exception:
                pass
        self.destroy()
 
    # ─────────────────────────────────────────
    #  WEER & LOCATIE  (gecentraliseerd)
    # ─────────────────────────────────────────
    def _load_weather_async(self):
        """Laad weer op achtergrond; update UI via after() zodat tkinter veilig blijft."""
        locatie   = self._fetch_location()
        weer_code = self._fetch_weather(locatie["lat"], locatie["lon"])
        # Terugkoppelen naar main thread
        self.after(0, lambda: self._apply_weather(locatie, weer_code))
 
    def _fetch_location(self) -> dict:
        try:
            with urlopen("http://ip-api.com/json/", timeout=5) as r:
                data = json.load(r)
                return {
                    "city": data.get("city", DEFAULT_CITY),
                    "lat":  data.get("lat",  DEFAULT_LAT),
                    "lon":  data.get("lon",  DEFAULT_LON),
                }
        except Exception as e:
            print(f"Locatie fout: {e}")
            return {"city": DEFAULT_CITY, "lat": DEFAULT_LAT, "lon": DEFAULT_LON}
 
    def _fetch_weather(self, lat: float, lon: float) -> int:
        try:
            url = (
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={lat}&longitude={lon}&current_weather=true"
            )
            with urlopen(url, timeout=5) as r:
                data = json.load(r)
                current = data["current_weather"]
                self.huidige_temp = f"{current['temperature']}°C"
                return int(current["weathercode"])
        except Exception as e:
            print(f"Weer fout: {e}")
            self.huidige_temp = "--°C"
            return 0
 
    def _apply_weather(self, locatie: dict, weer_code: int):
        """Pas gecachte waarden toe en update de UI-widget."""
        self.locatie   = locatie
        self.weer_code = weer_code
        icon = self._weer_icon(weer_code)
        tijd = datetime.now().strftime("%a %d/%m, %H:%M")
 
        # Update bestaande labels (aangemaakt in setup_bovenhoek)
        self.weer_icon.configure(text=icon)
        self.stad_label.configure(text=locatie["city"])
        self.tijd_label.configure(text=tijd)
 
    @staticmethod
    def _weer_icon(code: int) -> str:
        if code == 0:          return "☀️"
        if 1 <= code <= 3:     return "☁️"
        if code >= 51:         return "🌧️"
        return "⛅"
 
    # ─────────────────────────────────────────
    #  SENSOR (intern)
    # ─────────────────────────────────────────
    def read_pmodad1_bitbang(self) -> int:
        """Lees 12-bit sample van PmodAD1 (ADCS7476) via software SPI (uit main.py).
        16 bits worden uitgeschoven; bit-sampling op falling edge zoals in main.py.
        """
        value = 0
        GPIO.output(self._gpio_cs, GPIO.LOW)
        time.sleep(HALF_CLOCK_DELAY)
 
        for _ in range(16):
            GPIO.output(self._gpio_clk, GPIO.HIGH)
            time.sleep(HALF_CLOCK_DELAY)
            GPIO.output(self._gpio_clk, GPIO.LOW)
            time.sleep(HALF_CLOCK_DELAY)
            if ADC_SAMPLE_ON_FALLING:
                value = (value << 1) | int(GPIO.input(self._gpio_d0))
            else:
                GPIO.output(self._gpio_clk, GPIO.HIGH)
                time.sleep(HALF_CLOCK_DELAY)
                value = (value << 1) | int(GPIO.input(self._gpio_d0))
 
        GPIO.output(self._gpio_cs, GPIO.HIGH)
        return value & 0x0FFF
 
    def get_internal_sensor_data(self) -> dict:
        """Leest DHT temp/vocht (met caching) en PmodAD1 geluidssensor.
        DHT wordt max. eens per 2 seconden uitgelezen (timing uit main.py).
        Zonder Pi worden vaste testwaarden teruggegeven.
        """
        # --- Geluidssensor via PmodAD1 ---
        geluid = 0.0
        if self.gpio_available:
            try:
                raw_value = self.read_pmodad1_bitbang()
                geluid    = round((raw_value / 4095.0) * VREF, 3)
            except Exception as e:
                print(f"Fout bij uitlezen geluidssensor: {e}")
 
        # --- DHT temperatuur & vochtigheid (gecached, max 1x per 2s) ---
        now = time.monotonic()
        if self._dht_read is not None and now >= self._next_dht_time:
            self._next_dht_time = now + 2.0
            try:
                hum, temp = self._dht_read()
                if hum is not None and temp is not None:
                    self._last_hum  = hum
                    self._last_temp = temp
            except Exception as e:
                if not self._dht_error_reported:
                    print(f"DHT driver fout: {e}")
                    self._dht_error_reported = True
 
        # Gebruik gecachte waarden; valt terug op veilige standaardwaarden
        temp  = self._last_temp if self._last_temp is not None else 15.0
        vocht = self._last_hum  if self._last_hum  is not None else 80.0
 
        return {
            "temp":   round(temp,  1),
            "vocht":  round(vocht, 1),
            "geluid": geluid,
        }
    
    def fetch_energy_prices(self):
        try:
            # Voorbeeld URL (Enever API voor NL/BE prijzen)
            url = "https://enever.nl/api/stroomprijs_vandaag.php" 
            response = requests.get(url, timeout=5)
            data = response.json()
        
            # Zoek de prijs voor het huidige uur
            huidig_uur = datetime.now().hour
            # De data-structuur hangt af van de API die je kiest
            actuele_prijs = data['data'][huidig_uur]['prijs'] 
        
            # Update de UI veilig via after()
            self.live_energieprijs = actuele_prijs 
            print(f"Systeem: Live energieprijs bijgewerkt naar €{self.live_energieprijs}")
        except Exception as e:
            self.live_energieprijs = 0.28 # Veilige backup
 
    # ─────────────────────────────────────────
    #  DROOGTIJD BEREKENING
    # ─────────────────────────────────────────
    def bereken_droogtijd(
        self,
        temp: float,
        vocht: float,
        wind: float = 0,
        is_buiten: bool = True,
        stof_type: str = "Gemiddeld",
    ) -> float:
        basis_min   = 240
        stof_factor = self.STOF_FACTOREN.get(stof_type, 1.0)
        temp_factor = max(0.5, min(2.0, 1 - (temp - 20) * 0.05))  # Nu ook bovengeklemd
        vocht_factor = 1.0 if vocht < 60 else 1 + (vocht - 60) * 0.04
        wind_factor  = max(0.6, 1 - wind * 0.02) if is_buiten else 1.0
 
        uren = (basis_min * stof_factor * temp_factor * vocht_factor * wind_factor) / 60
        return round(max(MIN_DROOGTIJD_UREN, min(MAX_DROOGTIJD_UREN, uren)), 1)
 
    def _bereken_alle_tijden(self, was_type: str) -> tuple[int, int, int]:
        """Geeft (sec_buiten, sec_binnen, sec_kast) terug."""
        try:
            temp_buiten = float(self.huidige_temp.replace("°C", ""))
        except ValueError:
            temp_buiten = 15.0
 
        binnen = self.get_internal_sensor_data()
 
        sec_buiten = int(self.bereken_droogtijd(
            temp_buiten, DEFAULT_VOCHT_BUITEN,
            wind=DEFAULT_WIND_BUITEN, is_buiten=True, stof_type=was_type
        ) * 3600)
        sec_binnen = int(self.bereken_droogtijd(
            binnen["temp"], binnen["vocht"],
            wind=0, is_buiten=False, stof_type=was_type
        ) * 3600)
        sec_kast = self.KAST_SECONDEN[was_type]
 
        return sec_buiten, sec_binnen, sec_kast
    def add_timer(self, methode, was_type, seconden):
        # Voeg een nieuwe timer toe aan de lijst
        self.actieve_timers.append({
            "methode": methode,
            "was_type": was_type,
            "resterend": seconden,
            "totaal": seconden
        })
 
    def update_timers_loop(self):
        for timer in self.actieve_timers:
            if timer["resterend"] > 0:
                timer["resterend"] -= 1
        
        # Gebruik hasattr() als extra veiligheid[cite: 1]
        if getattr(self, "current_screen", None) == "timers":
            self.refresh_timer_display()
            
        self.after(1000, self.update_timers_loop)
 
    def refresh_timer_display(self):
        # Alleen uitvoeren als we op het timer-scherm zijn en de elementen bestaan
        if self.current_screen == "timers" and hasattr(self, 'timer_ui_elements'):
            for i, timer in enumerate(self.actieve_timers):
                if i in self.timer_ui_elements:
                    # Bereken voortgang
                    procent = (timer["totaal"] - timer["resterend"]) / timer["totaal"]
                    tijd_str = f"{timer['resterend']//3600:02d}:{(timer['resterend']%3600)//60:02d}:{timer['resterend']%60:02d}"
                    
                    # Update de bestaande widgets (GEEN destroy!)
                    self.timer_ui_elements[i]["pb"].set(procent)
                    self.timer_ui_elements[i]["tijd"].configure(text=tijd_str)
            
    # ─────────────────────────────────────────
    #  SIDEBAR
    # ─────────────────────────────────────────
    def setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=80, corner_radius=0, fg_color=self.bg_dark)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
 
        ctk.CTkButton(
            self.sidebar, text="≡", width=40, height=40,
            fg_color=self.bg_dark, hover_color="#2d2f3f",
            text_color="white", font=("Arial", 32),
            corner_radius=10, border_width=0, border_spacing=0,
            command=self.toggle_sidebar
        ).pack(side="top", anchor="n", pady=(20, 10))
 
        menu_items = [
            ("✧", "home",    self.show_home),
            ("⚡", "energy", None),
            ("⚖", "balance", self.show_comparison),
            ("⌛", "timer",  self.show_timers_screen),
            ("⚙", "settings", self.show_debug_info),
        ]
        for icon, name, actie in menu_items:
            btn = ctk.CTkButton(
                self.sidebar, text=icon, width=40, height=40,
                fg_color="transparent", hover_color="#2d2f3f",
                text_color="white", font=("Arial", 24),
                command=actie if actie else lambda: None
            )
            pady_val = (30, 15) if name == "home" else 15
            btn.pack(pady=pady_val, padx=10)
            self.sidebar_buttons[name] = btn
 
    def toggle_sidebar(self):
        if self.sidebar_visible:
            self.sidebar.grid_forget()
            self.sidebar_visible = False
            self.ham_btn.place(x=20, y=20)
            self.ham_btn.lift()
        else:
            self.ham_btn.place_forget()
            self.sidebar.grid(row=0, column=0, sticky="nsew")
            self.sidebar_visible = True
 
    def update_sidebar_selection(self, active_name):
        for name, btn in self.sidebar_buttons.items():
            color = self.active_blue if name == active_name else "white"
            btn.configure(text_color=color)
 
    # ─────────────────────────────────────────
    #  BOVENHOEK (weer-widget)
    # ─────────────────────────────────────────
    def setup_bovenhoek(self):
        """Bouw het widget; vult alvast met placeholders – _apply_weather update later."""
        self.weer_frame = ctk.CTkFrame(self, fg_color="white", corner_radius=15)
        self.weer_frame.place(relx=0.97, rely=0.05, anchor="ne")
 
        self.weer_icon = ctk.CTkLabel(
            self.weer_frame, text="⏳",
            font=("Arial", 28), text_color=self.bg_dark
        )
        self.weer_icon.pack(side="left", padx=(15, 2), pady=5)
 
        tekst_container = ctk.CTkFrame(self.weer_frame, fg_color="transparent")
        tekst_container.pack(side="left", padx=(0, 15), pady=5)
 
        self.stad_label = ctk.CTkLabel(
            tekst_container, text="Laden…",
            font=("Arial", 12), text_color="#666"
        )
        self.stad_label.pack(anchor="e")
 
        self.tijd_label = ctk.CTkLabel(
            tekst_container, text=datetime.now().strftime("%a %d/%m, %H:%M"),
            font=("Arial", 12), text_color="#666"
        )
        self.tijd_label.pack(anchor="e")
 
    # ─────────────────────────────────────────
    #  FRAMES INITIALISEREN
    # ─────────────────────────────────────────
    def _init_frames(self):
        self.home_frame     = ctk.CTkFrame(self, fg_color="transparent")
        self.selection_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.drying_frame   = ctk.CTkFrame(self, fg_color="transparent")
        self.confirm_frame  = ctk.CTkFrame(self, fg_color="transparent")
        self.timer_frame    = ctk.CTkFrame(self, fg_color="transparent")
        self.compare_frame  = ctk.CTkFrame(self, fg_color="transparent")
 
    # ─────────────────────────────────────────
    #  NAVIGATIE HELPERS
    # ─────────────────────────────────────────
    def hide_all(self):
        if self.current_timer:
            self.after_cancel(self.current_timer)
            self.current_timer = None
        for f in [
            self.home_frame, self.selection_frame, self.drying_frame,
            self.confirm_frame, self.timer_frame, self.compare_frame,
        ]:
            f.grid_forget()
 
    def show_home(self):
        self.hide_all()
        self.home_frame.grid(row=0, column=1, sticky="nsew")
        self.update_sidebar_selection("home")
 
    def show_selection(self):
        self.hide_all()
        self.selection_frame.grid(row=0, column=1, sticky="nsew")
        self.update_sidebar_selection(None)
 
    def show_comparison(self):
        self.hide_all()
        for w in self.compare_frame.winfo_children():
            w.destroy()
        self.build_comparison_ui()
        self.compare_frame.grid(row=0, column=1, sticky="nsew")
        self.update_sidebar_selection("balance")
 
    # ─────────────────────────────────────────
    #  SCHERM 1 – HOME
    # ─────────────────────────────────────────
    def setup_home_screen(self):
        ctk.CTkLabel(
            self.home_frame, text="🌲", font=("Arial", 120),
            text_color=self.accent_green
        ).pack(expand=True, pady=(60, 0))
 
        ctk.CTkLabel(
            self.home_frame, text="Hang de was buiten",
            font=("Arial Bold", 42), text_color="black"
        ).pack(expand=True)
 
        btn_row = ctk.CTkFrame(self.home_frame, fg_color="transparent")
        btn_row.pack(expand=True, pady=(0, 60))
 
        ctk.CTkButton(
            btn_row, text="TIMER INSTELLEN",
            fg_color=self.accent_green, hover_color="#00b34a", text_color="white",
            height=60, width=150, corner_radius=15, font=("Arial Bold", 18),
            command=self.show_selection
        ).pack(side="left", padx=10)
 
        ctk.CTkButton(
            btn_row, text="VERGELIJKING",
            fg_color="#4a5568", hover_color="#2d3748", text_color="white",
            height=60, width=150, corner_radius=15, font=("Arial Bold", 18),
            command=self.show_comparison
        ).pack(side="left", padx=10)
 
    # ─────────────────────────────────────────
    #  SCHERM 2 – SELECTIE WAS-SOORT
    # ─────────────────────────────────────────
    def setup_selection_screen(self):
        ctk.CTkButton(
            self.selection_frame, text="←", width=40, height=40,
            fg_color="white", text_color="black", command=self.show_home
        ).place(relx=0.05, rely=0.05)
 
        ctk.CTkLabel(
            self.selection_frame,
            text="Voor welk type was wil je een timer zetten?",
            font=("Arial Bold", 32), text_color="black"
        ).pack(pady=(60, 40))
 
        container = ctk.CTkFrame(self.selection_frame, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=40)
        container.grid_columnconfigure((0, 1, 2), weight=1)
 
        cards = [
            ("Licht",    "#cce0ff", "black", "🪶", "#bbd6ff"),
            ("Gemiddeld","#66a3ff", "white", "👕", "#5594ff"),
            ("Zwaar",    "#1a66ff", "white", "👖", "#0052cc"),
        ]
        for i, (label, color, t_col, icon, hover_c) in enumerate(cards):
            btn = ctk.CTkButton(
                container, fg_color=color, hover_color=hover_c,
                corner_radius=25, height=250, text="",
                command=lambda l=label: self.show_drying_options(l)
            )
            btn.grid(row=0, column=i, sticky="nsew", padx=15)
            btn.grid_columnconfigure(0, weight=1)
 
            l1 = ctk.CTkLabel(btn, text=icon, font=("Arial Bold", 80), text_color=t_col)
            l1.grid(row=0, column=0, pady=(40, 0))
            l2 = ctk.CTkLabel(btn, text=label, font=("Arial Bold", 22), text_color=t_col)
            l2.grid(row=1, column=0, pady=(10, 40))
 
            for lbl in [l1, l2]:
                lbl.bind("<Button-1>", lambda e, b=btn: b.invoke())
 
    # ─────────────────────────────────────────
    #  SCHERM 3 – DROOGOPTIES
    # ─────────────────────────────────────────
    def show_drying_options(self, was_type: str):
        self.hide_all()
        self.huidig_stoftype = was_type
        
        for w in self.drying_frame.winfo_children():
            w.destroy()
        
        # Terug-knop (exact zoals in je voorbeeld)
        ctk.CTkButton(
            self.drying_frame, text="←", width=40, height=40,
            fg_color="white", text_color="black", command=self.show_selection
        ).place(relx=0.05, rely=0.05)
 
        # Titel (Zelfde font en padding als je selectiescherm)
        ctk.CTkLabel(
            self.drying_frame,
            text=f"Kies een methode voor {was_type} was",
            font=("Arial Bold", 32), text_color="black"
        ).pack(pady=(60, 40))
 
        # --- DATA BEREKENEN ---
        sec_buiten, sec_binnen, sec_kast = self._bereken_alle_tijden(was_type)
        def fmt(s: int) -> str:
            return f"~{s // 3600}u {(s % 3600) // 60}m"
 
        opties = [
            ("🌲", "Buiten", fmt(sec_buiten), self.accent_green,  sec_buiten, "#00b34a"),
            ("🏠", "Binnen", fmt(sec_binnen), self.accent_orange, sec_binnen, "#e68f00"),
            ("🌀", "Droger", fmt(sec_kast),   self.accent_red,    sec_kast,   "#e63535"),
        ]
 
        # Container met exact dezelfde instellingen
        container = ctk.CTkFrame(self.drying_frame, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=40)
        container.grid_columnconfigure((0, 1, 2), weight=1)
 
        for i, (icon, label, t_txt, kleur, t_sec, h_kleur) in enumerate(opties):
            # Height=250 zoals in je voorbeeld
            btn = ctk.CTkButton(
                container, fg_color=kleur, hover_color=h_kleur,
                corner_radius=25, height=250, text="",
                command=lambda l=label, s=t_sec, k=kleur: self.show_confirmation(was_type, l, s, k)
            )
            btn.grid(row=0, column=i, sticky="nsew", padx=15)
            btn.grid_columnconfigure(0, weight=1)
 
            # Icon en Labels met verdeling voor de 250px hoogte
            l1 = ctk.CTkLabel(btn, text=icon, font=("Arial Bold", 70), text_color="white")
            l1.grid(row=0, column=0, pady=(30, 0))
            
            l2 = ctk.CTkLabel(btn, text=label, font=("Arial Bold", 22), text_color="white")
            l2.grid(row=1, column=0, pady=(5, 0))
            
            l3 = ctk.CTkLabel(btn, text=t_txt, font=("Arial Bold", 18), text_color="white")
            l3.grid(row=2, column=0, pady=(0, 30))
 
            for lbl in [l1, l2, l3]:
                lbl.bind("<Button-1>", lambda e, b=btn: b.invoke())
 
        self.drying_frame.grid(row=0, column=1, sticky="nsew")
 
    # ─────────────────────────────────────────
    #  SCHERM 4 – BEVESTIGING
    # ─────────────────────────────────────────
    def show_confirmation(self, was_type: str, methode: str, seconden: int, kleur: str):
        self.hide_all()
        for w in self.confirm_frame.winfo_children():
            w.destroy()
 
        ctk.CTkButton(
            self.confirm_frame, text="←", width=40, height=40,
            fg_color="white", text_color="black",
            command=lambda: self.show_drying_options(was_type)
        ).place(relx=0.05, rely=0.05)
 
        icon  = {"Buiten": "🌲", "Binnen": "🏠"}.get(methode, "🌀")
        h_col = {"Buiten": "#00b34a", "Binnen": "#e68f00"}.get(methode, "#e63535")
 
        ctk.CTkLabel(self.confirm_frame, text=icon,
                     font=("Arial Bold", 120), text_color=kleur).pack(pady=(40, 10))
        ctk.CTkLabel(self.confirm_frame,
                     text=f"{was_type} was {methode.lower()} drogen",
                     font=("Arial Bold", 36), text_color=self.text_blue).pack()
 
        t_txt = f"~{seconden // 3600}u {(seconden % 3600) // 60}m"
        ctk.CTkLabel(self.confirm_frame,
                     text=f"Verwachte droogtijd: {t_txt}",
                     font=("Arial Bold", 22), text_color="black").pack(pady=20)
 
        ctk.CTkButton(
            self.confirm_frame, text="BEVESTIGEN",
            fg_color=kleur, hover_color=h_col, height=70, width=500,
            corner_radius=20, font=("Arial Bold", 20), text_color="white",
            command=lambda: self.start_timer(was_type, methode, seconden)
        ).pack(pady=40)
 
        self.add_timer(methode, was_type, seconden)
        self.confirm_frame.grid(row=0, column=1, sticky="nsew")
        
 
    # ─────────────────────────────────────────
    #  SCHERM 5 – TIMER
    # ─────────────────────────────────────────
    def start_timer(self, was_type: str, methode: str, seconden: int):
        self.hide_all()
        for w in self.timer_frame.winfo_children():
            w.destroy()
 
        # Grote tikkende klok
        self.time_label = ctk.CTkLabel(
            self.timer_frame, text="",
            font=("Arial Bold", 80), text_color=self.text_blue
        )
        self.time_label.pack(pady=(40, 20))
 
        # Info-kaarten
        info = ctk.CTkFrame(self.timer_frame, fg_color="transparent")
        info.pack(fill="x", padx=100)
        info.grid_columnconfigure((0, 1), weight=1)
 
        def make_card(master, icon, txt, col, row, col_idx, colspan=1):
            f = ctk.CTkFrame(master, fg_color="white", corner_radius=15, height=70)
            f.grid(row=row, column=col_idx, columnspan=colspan,
                   sticky="nsew", padx=10, pady=10)
            ctk.CTkLabel(f, text=f"{icon}  {txt}",
                         font=("Arial Bold", 20), text_color=col).pack(expand=True)
 
        icon_m  = {"Buiten": "🌲", "Binnen": "🏠"}.get(methode, "🌀")
        color_m = self.accent_green if methode == "Buiten" else self.accent_orange
        make_card(info, icon_m, methode, color_m, 0, 0)
 
        icon_w = {"Licht": "🪶", "Gemiddeld": "👕"}.get(was_type, "👖")
        make_card(info, icon_w, was_type, "blue", 0, 1)
 
        if methode == "Buiten":
            make_card(info, "☀️",  self.huidige_temp,       "orange",   1, 0, colspan=2)
            make_card(info, "🌧️", "GEEN regen verwacht",   "#3498db",  2, 0, colspan=2)
        elif methode == "Binnen":
            binnen = self.get_internal_sensor_data()
            make_card(info, "🌡️", f"{binnen['temp']}°C",   "#e67e22",  1, 0, colspan=2)
            make_card(info, "💧", f"{binnen['vocht']}%",   "#2980b9",  2, 0, colspan=2)
 
        ctk.CTkButton(
            self.timer_frame, text="ANNULEREN",
            fg_color="#4a5568", hover_color="#2d3748",
            height=60, width=500, corner_radius=15,
            font=("Arial Bold", 18), text_color="white",
            command=lambda: self.confirm_cancel(was_type, methode)
        ).pack(pady=30)
 
        self.remaining_sec = seconden
        self._tick()
        self.timer_frame.grid(row=0, column=1, sticky="nsew")
 
    def _tick(self):
        """Eén tick per seconde; stopt netjes op 0."""
        if self.remaining_sec > 0:
            h = self.remaining_sec // 3600
            m = (self.remaining_sec % 3600) // 60
            s = self.remaining_sec % 60
            tijd_str = f"{h:02d}:{m:02d}:{s:02d}"
            self.time_label.configure(text=tijd_str)
            if (
                self.popup_time_label is not None
                and self.popup_time_label.winfo_exists()
            ):
                self.popup_time_label.configure(text=tijd_str)
            self.remaining_sec -= 1
            self.current_timer = self.after(1000, self._tick)
        else:
            self.time_label.configure(text="00:00:00")
            self._timer_klaar()
 
    def _timer_klaar(self):
        """Wordt aangeroepen wanneer de timer op 0 komt."""
        # Sluit eventuele popup
        if hasattr(self, "overlay") and self.overlay.winfo_exists():
            self.close_popup()
        self.show_home()
 
    # ─────────────────────────────────────────
    #  ANNULEER-POPUP
    # ─────────────────────────────────────────
    def confirm_cancel(self, was_type: str, methode: str):
        self.overlay = ctk.CTkFrame(self, fg_color="#2b2b2b")
        self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
 
        popup = ctk.CTkFrame(self.overlay, fg_color="white",
                             corner_radius=25, width=500, height=380)
        popup.place(relx=0.5, rely=0.5, anchor="center")
        popup.pack_propagate(False)
 
        ctk.CTkLabel(popup, text="Timer annuleren?",
                     font=("Arial Bold", 20), text_color="black").pack(pady=(30, 5))
        self.popup_time_label = ctk.CTkLabel(
            popup, text="", font=("Arial Bold", 32), text_color="black"
        )
        self.popup_time_label.pack(pady=10)
 
        ctk.CTkButton(popup, text="STOP TIMER",
                      fg_color=self.accent_red, height=60, width=400,
                      text_color="white", corner_radius=15,
                      command=self.final_cancel).pack(pady=10)
        ctk.CTkButton(popup, text="GA TERUG",
                      fg_color="#4a5568", height=60, width=400,
                      text_color="white", corner_radius=15,
                      command=self.close_popup).pack(pady=10)
 
    def close_popup(self):
        self.popup_time_label = None
        self.overlay.destroy()
 
    def final_cancel(self):
        self.close_popup()
        self.show_home()
 
    def show_timers_screen(self):
        self.hide_all()
        self.current_screen = "timers"
        self.timer_ui_elements = {}

        for w in self.timer_frame.winfo_children(): 
            w.destroy()

        # 1. Maak de scrollbox ÉÉN keer aan, BUITEN de loop
        scroll = ctk.CTkScrollableFrame(self.timer_frame, fg_color="transparent", width=700, height=400)
        scroll.pack(expand=True, fill="both", padx=50, pady=20)

        for i, timer in enumerate(self.actieve_timers):
            stijl = self.METHODE_STYLING.get(timer["methode"], {"icoon": "⏳", "kleur": "gray"})
            
            # 2. Voeg de kaart toe aan 'scroll'
            card = ctk.CTkFrame(scroll, fg_color="white", corner_radius=20, height=100)
            card.pack(fill="x", pady=10, padx=10)
            card.pack_propagate(False)

            ctk.CTkLabel(card, text=stijl["icoon"], font=("Arial", 40), text_color=stijl["kleur"]).pack(side="left", padx=20)
            ctk.CTkLabel(card, text=f"{timer['methode']} - {timer['was_type']}", 
                         font=("Arial Bold", 16), text_color="black").pack(side="left")

            pb = ctk.CTkProgressBar(card, width=200, progress_color=stijl["kleur"])
            pb.pack(side="left", padx=20)
            pb.set(0) # Startwaarde
            
            lbl_tijd = ctk.CTkLabel(card, text="00:00:00", font=("Consolas", 20, "bold"), text_color="black")
            lbl_tijd.pack(side="right", padx=20)

            self.timer_ui_elements[i] = {"pb": pb, "tijd": lbl_tijd}
            
        self.timer_frame.grid(row=0, column=1, sticky="nsew")
        self.refresh_timer_display()
 
    # ─────────────────────────────────────────
    #  SCHERM 6 – VERGELIJKING
    # ─────────────────────────────────────────
    def build_comparison_ui(self):
        inner = ctk.CTkFrame(self.compare_frame, fg_color="#f0f8ff", corner_radius=0)
        inner.pack(fill="both", expand=True)
        inner.grid_columnconfigure((0, 1, 2), weight=1)
 
        try:
            temp_buiten = float(self.huidige_temp.replace("°C", ""))
        except ValueError:
            temp_buiten = 15.0
 
        binnen = self.get_internal_sensor_data()
 
        tijd_buiten = self.bereken_droogtijd(
            temp_buiten, DEFAULT_VOCHT_BUITEN,
            wind=DEFAULT_WIND_BUITEN, is_buiten=True, stof_type=self.huidig_stoftype
        )
        tijd_binnen = self.bereken_droogtijd(
            binnen["temp"], binnen["vocht"],
            wind=0, is_buiten=False, stof_type=self.huidig_stoftype
        )
        tijd_droger = round(self.KAST_SECONDEN[self.huidig_stoftype] / 3600, 1)
 
        ctk.CTkLabel(
            inner,
            text=f"Vergelijking ({self.huidig_stoftype} was)",
            font=("Arial Bold", 32), text_color="black"
        ).grid(row=0, column=0, columnspan=3, pady=(30, 20))
 
        prijs_per_beurt = self.live_energieprijs * 2.5
 
        data_lijst = [
            {
                "t":    "Buiten drogen",
                "d":    f"droogtijd {tijd_buiten}u",
                "k":    "Gratis",
                "temp": f"{temp_buiten}°C",
                "v":    f"vocht {DEFAULT_VOCHT_BUITEN}%",
                "ex":   "Gebaseerd op\nweerbericht",
                "ex_c": "#f39c12" if self.weer_code > 0 else "transparent",
                "h":    tijd_buiten < tijd_binnen,
            },
            {
                "t":    "Binnen drogen",
                "d":    f"droogtijd {tijd_binnen}u",
                "k":    "Gratis",
                "temp": f"{binnen['temp']}°C",
                "v":    f"vocht {binnen['vocht']}%",
                "ex":   "Sensor data\nvan Pi",
                "ex_c": "transparent",
                "h":    tijd_binnen < tijd_buiten,
            },
            {
                "t": "Droogkast",
                "d": f"droogtijd {tijd_droger}u",
                "k": f"kost: €{prijs_per_beurt:.2f}", # <--- Hier wordt het dynamisch!
                "temp": "/",
                "v": "/",
                "ex": f"Nu: €{self.live_energieprijs}/kWh",
                "ex_c": "transparent",
                "h": False,
            },
        ]
 
        for i, item in enumerate(data_lijst):
            col = ctk.CTkFrame(inner, fg_color="transparent")
            col.grid(row=1, column=i, sticky="nsew", padx=10)
 
            ctk.CTkLabel(col, text=item["t"],
                         font=("Arial Bold", 22), text_color="black").pack()
            ctk.CTkFrame(col, height=2, width=140, fg_color="black").pack(pady=10)
 
            tijd_kleur    = "#27ae60" if item["h"] else "transparent"
            tijd_txt_kleur = "white"  if item["h"] else "black"
            ctk.CTkLabel(col, text=item["d"], font=("Arial", 18),
                         text_color=tijd_txt_kleur, fg_color=tijd_kleur,
                         corner_radius=6, width=160, height=32).pack(pady=5)
 
            ctk.CTkLabel(col, text=item["k"], font=("Arial Bold", 18),
                         text_color="white", fg_color="#27ae60",
                         corner_radius=6, width=180, height=35).pack(pady=15)
 
            ctk.CTkLabel(col, text=item["temp"],
                         font=("Arial", 18), text_color="black").pack()
            ctk.CTkLabel(col, text=item["v"],
                         font=("Arial", 18), text_color="black").pack(pady=5)
 
            if item["ex"]:
                ex_c = item["ex_c"] if item["ex_c"] != "transparent" else "transparent"
                box  = ctk.CTkFrame(col, fg_color=ex_c, corner_radius=8)
                box.pack(pady=20, padx=10)
                ctk.CTkLabel(box, text=item["ex"], font=("Arial", 15),
                             text_color="black", padx=10, pady=5).pack()
 
            if i < 2:
                ctk.CTkFrame(inner, width=2, fg_color="#444").grid(
                    row=1, column=i, sticky="nse", pady=(0, 40)
                )
    
    def show_debug_info(self):
    """Toon een popup met de rauwe sensorwaarden en fouten."""
    debug_win = ctk.CTkToplevel(self)
    debug_win.title("Sensor Debugger")
    debug_win.geometry("400x300")
    debug_win.attributes("-topmost", True)

    binnen = self.get_internal_sensor_data()
    
    info = f"DHT Temp: {self._last_temp}\n"
    info += f"DHT Vocht: {self._last_hum}\n"
    info += f"Sound ADC: {binnen['geluid']}V\n"
    info += f"On Pi: {ON_PI}\n"
    info += f"Next DHT Read: {round(self._next_dht_time - time.monotonic(), 1)}s"
    
    ctk.CTkLabel(debug_win, text=info, font=("Consolas", 14), justify="left").pack(pady=20)
    ctk.CTkButton(debug_win, text="Sluit", command=debug_win.destroy).pack(pady=10)
    
if __name__ == "__main__":
    app = LaundryApp()
    app.mainloop()