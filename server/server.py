from flask import Flask, jsonify, request
from flask import render_template # Opciono, ako ces servirati HTML direktno
from flask_cors import CORS # Ako HTML otvaras kao obican fajl, treba ti CORS. Dodaj CORS(app) gore ispod app = Flask(__name__)
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import paho.mqtt.client as mqtt
import json
import threading
import time
import ast

app = Flask(__name__)
CORS(app) #?????

# --- INFLUXDB SETUP ---
token = "B8HDBR5Sh9cCibUUGyUAM2rDL4ajESUs_UyUHpRp52OT3mL1IriRtRCD2cnnix-09BGs1_OU9xv9HMNXnWDSGg=="
org = "FTN"
url = "http://localhost:8086"
bucket = "iot_db"
influxdb_client = InfluxDBClient(url=url, token=token, org=org)

# --- GLOBALNO STANJE SISTEMA (STATE MACHINE) ---
# server pamti sve sto je bitno za donosenje odluka
SYSTEM_STATE = {
    "alarm_active": False,
    "security_armed": False,
    "alarm_reason": "",
    "people_count": 1, # vreati na 0
    "door_open_timers": {},
    "dms_pin_buffer": "",
    
    # pracenje vremena poslednjeg okidanja senzora za Vrata 1 i 2
    "door_1_last_dus": 0, "door_1_last_dpir": 0,
    "door_2_last_dus": 0, "door_2_last_dpir": 0,
    
    # "hladjenje" da ne prebrojimo istu osobu vise puta u 5 sekundi
    "cooldowns": {
        "door_1": 0,
        "door_2": 0
    },

    # tajmeri za bezbednost
    "pin_clear_timer": None,
    "intrusion_timer": None,

    # za LCD i stopericu
    "dht_readings": {},
    "stopwatch_time": 0,
    "stopwatch_running": False,
    "stopwatch_blinking": False,
    "btn_add_seconds": 10
}

SECRET_PIN = "1111"

dl_timer = None

# MQTT Configuration
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    print("Povezan na MQTT Broker. Slusam senzore...")
    # Pretplata na sve senzore da bismo dobijali podatke
    client.subscribe("Sensors/#")
    client.subscribe("Actuators/#")

def on_message(client, userdata, msg):
    try:
        payload_str = msg.payload.decode('utf-8')
        data = json.loads(payload_str)
        
        # sacuvamo u InfluxDB bazu
        save_to_db(data)
        
        # prosledjujemo glavnom delu da proveri pravila
        process_logic(msg.topic, data)
        
    except Exception as e:
        print(f"Error in on_message: {e}")

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

mqtt_client.connect("localhost", 1883, 60)
mqtt_client.loop_start()

# --- ALARM LOGIKA ---
def trigger_alarm(reason):
    if not SYSTEM_STATE["alarm_active"]:
        SYSTEM_STATE["alarm_active"] = True
        SYSTEM_STATE["alarm_reason"] = reason
        print(f"\n[ALARM UPOZORENJE] Ukljucen ALARM! Razlog: {reason}")
        
        # pali zujalicu na PI1
        mqtt_client.publish("Commands/PI1/DB", json.dumps({"command": "on"}))
        
        # zapisujemo dogadjaj u bazu
        save_alarm_state_to_db(True, reason)

def deactivate_alarm():
    if SYSTEM_STATE["alarm_active"]:
        SYSTEM_STATE["alarm_active"] = False
        print("\n[ALARM] Alarm je UGASEN.")
        
        # gasi zujalicu na PI1
        mqtt_client.publish("Commands/PI1/DB", json.dumps({"command": "off"}))
        
        # zapisujemo dogadjaj u bazu
        save_alarm_state_to_db(False, "Deactivated")

def save_alarm_state_to_db(is_active, reason):
    write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)
    point = Point("Alarm_State") \
        .field("active", int(is_active)) \
        .field("reason", reason)
    write_api.write(bucket=bucket, org=org, record=point)

# --- BEZBEDNOSNA LOGIKA (DMS) ---
def handle_dms_input(key):
    SYSTEM_STATE["dms_pin_buffer"] += str(key)
    
    # Ako korisnik kuca presporo (prodje 5 sekundi), brisemo ono sto je do sad ukucao
    if SYSTEM_STATE["pin_clear_timer"] is not None:
        SYSTEM_STATE["pin_clear_timer"].cancel()
        
    def clear_buffer():
        SYSTEM_STATE["dms_pin_buffer"] = ""
        
    SYSTEM_STATE["pin_clear_timer"] = threading.Timer(5.0, clear_buffer)
    SYSTEM_STATE["pin_clear_timer"].start()

    # Kada je ukucano 4 karaktera, proveravamo PIN
    if len(SYSTEM_STATE["dms_pin_buffer"]) == 4:
        entered_pin = SYSTEM_STATE["dms_pin_buffer"]
        SYSTEM_STATE["dms_pin_buffer"] = "" # Resetujemo bafer
        
        if entered_pin == SECRET_PIN:
            print("\n[SIGURNOST] Tacan PIN unet!")
            
            # 1. Ponisti tajmer za uljeza (ako smo usli u kucu i kucamo PIN da sprecimo alarm)
            if SYSTEM_STATE["intrusion_timer"] is not None:
                SYSTEM_STATE["intrusion_timer"].cancel()
                SYSTEM_STATE["intrusion_timer"] = None
                print("[SIGURNOST] Alarm za uljeza otkazan.")

            # 2. Gasi alarm i deaktiviraj sistem
            if SYSTEM_STATE["alarm_active"]:
                deactivate_alarm()
                SYSTEM_STATE["security_armed"] = False
                print("[SIGURNOST] Sistem deaktiviran.")
            
            # 3. Samo deaktiviraj sistem
            elif SYSTEM_STATE["security_armed"]:
                SYSTEM_STATE["security_armed"] = False
                print("[SIGURNOST] Sistem deaktiviran.")
                
            # 4. Naoruzaj sistem (nakon 10 sekundi)
            else:
                print("[SIGURNOST] Sistem se aktivira (naoruzava) za 10 sekundi! Napustite objekat.")
                def arm_system():
                    SYSTEM_STATE["security_armed"] = True
                    print("\n[SIGURNOST] SISTEM JE SADA AKTIVAN (NAORUZAN)!")
                threading.Timer(10.0, arm_system).start()
        else:
            print(f"\n[SIGURNOST] Pogresan PIN: {entered_pin}")

# --- AKCIJE ---
def turn_on_dl_for_10s():
    global dl_timer
    
    # ako tajmer vec postoji, samo ga prekidamo i krecemo ispocetka
    if dl_timer is not None:
        dl_timer.cancel()
        print("[LOGIC] DPIR1 ponovo detektovao pokret! Produzavam DL na jos 10s.")
    else:
        # ako tajmera nema (svetlo je ugaseno), saljemo MQTT komandu da se upali
        print("\n[LOGIC] DPIR1 detektovao prvi pokret! Palim DL na 10 sekundi.")
        cmd_on = json.dumps({"command": "on"})
        mqtt_client.publish("Commands/PI1/DL", cmd_on)
    
    # funkciju koja ce ga ugasiti
    def turn_off():
        global dl_timer
        print("[LOGIC] Nema pokreta vec 10s. Gasim DL.")
        cmd_off = json.dumps({"command": "off"})
        mqtt_client.publish("Commands/PI1/DL", cmd_off)
        dl_timer = None # resetujemo promenljivu kada se svetlo ugasi
        
    # ponovo NOVI Timer (brojimo 10 sekundi ispocetka)
    dl_timer = threading.Timer(10.0, turn_off)
    dl_timer.start()

# --- LCD ROTACIJA (Pozadinski zadatak) ---
def start_lcd_rotation():
    def rotation_loop():
        current_index = 0
        while True:
            time.sleep(5) # Smenjuje prikaz na svakih 5 sekundi
            keys = list(SYSTEM_STATE["dht_readings"].keys())
            if not keys:
                continue
            
            # Kruzimo kroz dostupne DHT senzore
            current_index = (current_index + 1) % len(keys)
            sensor_name = keys[current_index]
            data = SYSTEM_STATE["dht_readings"][sensor_name]
            
            # Formatiranje za 16x2 ekran
            text = f"{sensor_name[:16]}\nT:{data.get('temp', 0):.1f}C H:{data.get('hum', 0):.1f}%"
            mqtt_client.publish("Commands/PI3/LCD", json.dumps({"command": "write", "text": text}))

    threading.Thread(target=rotation_loop, daemon=True).start()

# --- STOPERICA LOGIKA ---
def run_stopwatch_tick():
    if SYSTEM_STATE["stopwatch_running"] and SYSTEM_STATE["stopwatch_time"] > 0:
        SYSTEM_STATE["stopwatch_time"] -= 1
        
        mins = SYSTEM_STATE["stopwatch_time"] // 60
        secs = SYSTEM_STATE["stopwatch_time"] % 60
        time_str = f"{mins:02d}:{secs:02d}"
        
        # Saljemo komandu na PI2 za 4SD
        mqtt_client.publish("Commands/PI2/4SD", json.dumps({"command": "show", "text": time_str}))
        
        if SYSTEM_STATE["stopwatch_time"] == 0:
            SYSTEM_STATE["stopwatch_running"] = False
            SYSTEM_STATE["stopwatch_blinking"] = True
            mqtt_client.publish("Commands/PI2/4SD", json.dumps({"command": "blink"}))
        else:
            threading.Timer(1.0, run_stopwatch_tick).start()

# Pokrecemo rotaciju LCD-a prilikom pokretanja servera
start_lcd_rotation()

# --- GLAVNA LOGIKA ---
def process_logic(topic, data):
    """
    Ova funkcija evaluira pravila iz specifikacije na osnovu pristiglih podataka.
    """
    measurement = data.get("measurement")
    value = data.get("value")
    current_time = time.time()
    
    # Udaljenost ispod koje smatramo da je covek ispred samih vrata
    DISTANCE_THRESHOLD = 50.0 
    TIME_WINDOW = 5.0 # Vremenski prozor od 5s izmedju DUS i DPIR

    # ////////////////////////////////////////////////////
    # LOGIKA ZA VRATA 1 (DUS1 i DPIR1)
    if topic == "Sensors/DUS1" and measurement == "Distance":
        if value < DISTANCE_THRESHOLD:
            SYSTEM_STATE["door_1_last_dus"] = current_time
            
            # Da li je u poslednjih 5s bio pokret unutra? (Znaci osoba izlazi)
            if (current_time - SYSTEM_STATE["door_1_last_dpir"] < TIME_WINDOW) and \
               (current_time - SYSTEM_STATE["cooldowns"]["door_1"] > TIME_WINDOW):
                
                SYSTEM_STATE["people_count"] = max(0, SYSTEM_STATE["people_count"] - 1) # broj ljudi ne id eu minus
                SYSTEM_STATE["cooldowns"]["door_1"] = current_time
                print(f"[LOGIC] Osoba IZASLA kroz Vrata 1! Trenutno ljudi u kuci: {SYSTEM_STATE['people_count']}")

    if topic == "Sensors/DPIR1" and measurement == "Motion" and value == 1:
        SYSTEM_STATE["door_1_last_dpir"] = current_time
        turn_on_dl_for_10s() # staro pravilo za svetlo
        
        # Da li je u poslednjih 5s ocitana blizina spolja? (Znaci osoba ulazi)
        if (current_time - SYSTEM_STATE["door_1_last_dus"] < TIME_WINDOW) and \
           (current_time - SYSTEM_STATE["cooldowns"]["door_1"] > TIME_WINDOW):
            
            SYSTEM_STATE["people_count"] += 1
            SYSTEM_STATE["cooldowns"]["door_1"] = current_time
            print(f"[LOGIC] Osoba USLA kroz Vrata 1! Trenutno ljudi u kuci: {SYSTEM_STATE['people_count']}")

    # ////////////////////////////////////////////////////
    # LOGIKA ZA VRATA 2 (DUS2 i DPIR2)
    if topic == "Sensors/DUS2" and measurement == "Distance":
        if value < DISTANCE_THRESHOLD:
            SYSTEM_STATE["door_2_last_dus"] = current_time
            
            # Izlazak
            if (current_time - SYSTEM_STATE["door_2_last_dpir"] < TIME_WINDOW) and \
               (current_time - SYSTEM_STATE["cooldowns"]["door_2"] > TIME_WINDOW):
                SYSTEM_STATE["people_count"] = max(0, SYSTEM_STATE["people_count"] - 1)
                SYSTEM_STATE["cooldowns"]["door_2"] = current_time
                print(f"[LOGIC] Osoba IZASLA kroz Vrata 2! Trenutno ljudi u kuci: {SYSTEM_STATE['people_count']}")

    if topic == "Sensors/DPIR2" and measurement == "Motion" and value == 1:
        SYSTEM_STATE["door_2_last_dpir"] = current_time
        
        # ulazak
        if (current_time - SYSTEM_STATE["door_2_last_dus"] < TIME_WINDOW) and \
           (current_time - SYSTEM_STATE["cooldowns"]["door_2"] > TIME_WINDOW):
            SYSTEM_STATE["people_count"] += 1
            SYSTEM_STATE["cooldowns"]["door_2"] = current_time
            print(f"[LOGIC] Osoba USLA kroz Vrata 2! Trenutno ljudi u kuci: {SYSTEM_STATE['people_count']}")

    # ////////////////////////////////////////////////////
    # ==========================================
    # LOGIKA ZA DMS
    # ==========================================
    if topic == "Sensors/DMS" and measurement == "Key_Pressed":
        handle_dms_input(value)
    
    # ////////////////////////////////////////////////////
    # LOGIKA ZA VRATA (DS1 i DS2) - ALARM 5 SEKUNDI            
    if measurement == "Door_Status":
        door_name = topic.split("/")[-1] # DS1 ili DS2
        
        if value == 1: # vrata OTVORENA -> pokrecemo tajmer
            # pokrecemo tajmer SAMO ako vec ne postoji za ova vrata
            if door_name not in SYSTEM_STATE["door_open_timers"]:
                print(f"[LOGIKA] {door_name} otvorena. Cekam 5 sekundi...")
                
                def alarm_door_open():
                    trigger_alarm(f"{door_name} su ostala otvorena duze od 5 sekundi!")
                    
                timer = threading.Timer(5.0, alarm_door_open)
                SYSTEM_STATE["door_open_timers"][door_name] = timer
                timer.start()
                
                # ako su vrata otvorena dok je SISTEM NAORUZAN, krece odbrojavanje od 10s za PIN
                if SYSTEM_STATE["security_armed"] and not SYSTEM_STATE["alarm_active"]:
                    print(f"\n[SIGURNOST] Ulazak detektovan na {door_name}! Imate 10 sekundi da unesete PIN.")
                    
                    def intrusion_alarm():
                        trigger_alarm(f"Nedozvoljen ulazak na {door_name} (PIN nije unet)")
                    
                    if SYSTEM_STATE["intrusion_timer"] is not None:
                        SYSTEM_STATE["intrusion_timer"].cancel()
                        
                    SYSTEM_STATE["intrusion_timer"] = threading.Timer(10.0, intrusion_alarm)
                    SYSTEM_STATE["intrusion_timer"].start()
            
        elif value == 0:
            print(f"[LOGIKA] {door_name} zatvorena.")
            
            # gasimo tajmer za 5s otvorenih vrata
            if door_name in SYSTEM_STATE["door_open_timers"]:
                SYSTEM_STATE["door_open_timers"][door_name].cancel()
                del SYSTEM_STATE["door_open_timers"][door_name] # brisemo tajmer iz recnika
            
            # gasimo alarm SAMO ako su ga OVA vrata i upalila 
            # (ako je naoruzan, alarm za uljeza se gasi samo PIN-om)
            if SYSTEM_STATE["alarm_active"] and not SYSTEM_STATE["security_armed"]:
                if f"{door_name} su ostala otvorena" in SYSTEM_STATE["alarm_reason"]:
                    deactivate_alarm()


    # ///////////////////////////////////////////////
    # ==========================================
    # LOGIKA ZA NULA LJUDI U KUCI (svi DPIR senzori pokreta)
    # ==========================================
    if topic in ["Sensors/DPIR1", "Sensors/DPIR2", "Sensors/DPIR3"] and measurement == "Motion" and value == 1:
        
        # Ako je broj ljudi 0, a detektovan je pokret -> ALARM
        if SYSTEM_STATE["people_count"] == 0:
            sensor_name = topic.split("/")[-1]
            trigger_alarm(f"Pokret detektovan na {sensor_name} dok je kuca prazna!")

    # ////////////////////////////////////////////////////
    # ==========================================
    # LOGIKA ZA SLAVSKU IKONU (GSG)
    # ==========================================
    if topic == "Sensors/Gyro":
        try:
            axes = ast.literal_eval(value)

            ACC_THRESHOLD = 0.85
            ROT_THRESHOLD = 35

            if measurement == "Acceleration":
                if abs(axes[0]) > ACC_THRESHOLD or abs(axes[1]) > ACC_THRESHOLD:
                    print(f"\n[SIGURNOST] UPOZORENJE! Slavska ikona je pomerena! X:{axes[0]:.2f}, Y:{axes[1]:.2f}")
                    trigger_alarm("Slavska ikona je pomerena!")

            elif measurement == "Rotation":
                if abs(axes[0]) > ROT_THRESHOLD or abs(axes[1]) > ROT_THRESHOLD:
                    print(f"\n[SIGURNOST] UPOZORENJE! Slavska ikona je pomerena! X:{axes[0]:.2f}, Y:{axes[1]:.2f}")
                    trigger_alarm("Slavska ikona se naginje!")

        except Exception as e:
            print(f"[GYRO ERROR] {e}")

    # ///////////////////////////////////////////////
    # ==========================================
    # LOGIKA ZA CUVANJE DHT PODATAKA (Za LCD)
    # ==========================================
    if measurement in ["Temperature", "Humidity"]:
        sensor_name = data.get("name", "Unknown DHT")
        if sensor_name not in SYSTEM_STATE["dht_readings"]:
            SYSTEM_STATE["dht_readings"][sensor_name] = {"temp": 0.0, "hum": 0.0}
            
        if measurement == "Temperature":
            SYSTEM_STATE["dht_readings"][sensor_name]["temp"] = value
        else:
            SYSTEM_STATE["dht_readings"][sensor_name]["hum"] = value

    # ////////////////////////////////////////////////////
    # ==========================================
    # LOGIKA ZA STOPERICU I DUGME (BTN)
    # ==========================================
    if topic == "Sensors/BTN" and measurement == "Button_Pressed" and value == 1:
        if SYSTEM_STATE["stopwatch_blinking"]:
            # zaustavi treperenje kada istekne vreme
            SYSTEM_STATE["stopwatch_blinking"] = False
            SYSTEM_STATE["stopwatch_time"] = 0
            mqtt_client.publish("Commands/PI2/4SD", json.dumps({"command": "clear"}))
            print("[STOPERICA] Treperenje zaustavljeno.")
        else:
            # Dodaj N sekundi i pokreni ako vec nije pokrenuto
            SYSTEM_STATE["stopwatch_time"] += SYSTEM_STATE["btn_add_seconds"]
            print(f"[STOPERICA] Dodato {SYSTEM_STATE['btn_add_seconds']}s. Ukupno: {SYSTEM_STATE['stopwatch_time']}s")
            
            if not SYSTEM_STATE["stopwatch_running"]:
                SYSTEM_STATE["stopwatch_running"] = True
                run_stopwatch_tick()

    # ////////////////////////////////////////////////////
    # ==========================================
    # LOGIKA ZA IR DALJINSKI I RGB SIJALICU 
    # ==========================================
    if topic == "Sensors/IR" and measurement == "IR_Remote":
        # mapiramo tastere sa daljinskog na bojel; salje brojeve (1, 2, 3...) kao stringove
        color_map = {
            "1": "red",
            "2": "green",
            "3": "blue",
            "4": "yellow",
            "5": "purple",
            "6": "light_blue",
            "7": "white",
            "0": "off"
        }

        button = str(value)
        if button in color_map:
            color = color_map[button]
            print(f"[LOGIKA] Daljinski pritisnut: {button}. Menjam RGB na: {color}")
            mqtt_client.publish("Commands/PI3/BRGB", json.dumps({"command": color}))

def save_to_db(data):
    write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)
    point = Point(data["measurement"]) \
        .tag("simulated", data["simulated"]) \
        .tag("runs_on", data["runs_on"]) \
        .tag("name", data["name"])
    
    measurement_name = data["measurement"]

    # LISTA MERENJA KOJA UVEK MORAJU BITI TEKST
    text_measurements = [
        "Key_Pressed",   # Tastatura (DMS)
        "IR_Remote",     # Daljinski (IR)
        "RGB_Color",     # Boja svetla (BRGB)
        "LCD_Text",      # Tekst ekrana (LCD)
        "Acceleration",  # Ziroskop [x, y, z]
        "Rotation"       # Ziroskop [x, y, z]
    ]

    if measurement_name in text_measurements: 
        point = point.field("value_str", str(data["value"]))
    else:
        # za ostale pokusaj da konvertujes u broj
        try:
            val = float(data["value"])
            point = point.field("value", val)
        except (ValueError, TypeError):
            point = point.field("value_str", str(data["value"]))

    write_api.write(bucket=bucket, org=org, record=point)


# Route to store dummy data
@app.route('/store_data', methods=['POST'])
def store_data():
    try:
        data = request.get_json()
        store_data(data)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# http://127.0.0.1:5000/force_pin za forsiranje DMS PIN-a
@app.route('/force_pin', methods=['GET'])
def force_pin():
    # Simuliramo da je neko na DMS-u brzo ukucao "1111" npr.
    for char in SECRET_PIN:
        handle_dms_input(char)
    return jsonify({"status": "success", "message": "PIN forced!"})

def handle_influx_query(query):
    try:
        query_api = influxdb_client.query_api()
        tables = query_api.query(query, org=org)

        container = []
        for table in tables:
            for record in table.records:
                container.append(record.values)

        return jsonify({"status": "success", "data": container})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/simple_query', methods=['GET'])
def retrieve_simple_data():
    query = f"""from(bucket: "{bucket}")
    |> range(start: -10m)
    |> filter(fn: (r) => r._measurement == "Humidity")"""
    return handle_influx_query(query)


@app.route('/aggregate_query', methods=['GET'])
def retrieve_aggregate_data():
    query = f"""from(bucket: "{bucket}")
    |> range(start: -10m)
    |> filter(fn: (r) => r._measurement == "Humidity")
    |> mean()"""
    return handle_influx_query(query)

# ////////////////////////////////////////////////////

# Rutiranje za gasenje alarma preko Web aplikacije
@app.route('/api/alarm/deactivate', methods=['POST'])
def api_alarm_deactivate():
    try:
        data = request.get_json()
        pin = data.get("pin", "")
        
        # Specifikacija kaze da se iz ALARM stanja izlazi unosom PIN-a na DMS-u ili Web app
        if pin == SECRET_PIN:
            if SYSTEM_STATE["alarm_active"]:
                deactivate_alarm()
            SYSTEM_STATE["security_armed"] = False
            
            # Ponistavamo tajmer za uljeza ako je aktivan
            if SYSTEM_STATE["intrusion_timer"]:
                SYSTEM_STATE["intrusion_timer"].cancel()
                SYSTEM_STATE["intrusion_timer"] = None
                
            return jsonify({"status": "success", "message": "Alarm and Security Deactivated"})
        else:
            return jsonify({"status": "error", "message": "Invalid PIN"}), 403
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# Ruta za povlacenje trenutnog stanja sistema (za iscrtavanje na Webu)
@app.route('/api/status', methods=['GET'])
def api_status():
    return jsonify({
        "alarm_active": SYSTEM_STATE["alarm_active"],
        "security_armed": SYSTEM_STATE["security_armed"],
        "people_count": SYSTEM_STATE["people_count"],
        "stopwatch_time": SYSTEM_STATE["stopwatch_time"],
        "btn_add_seconds": SYSTEM_STATE["btn_add_seconds"]
    })


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
