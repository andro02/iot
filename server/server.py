from flask import Flask, jsonify, request
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import paho.mqtt.client as mqtt
import json
import threading
import time

app = Flask(__name__)

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
    "people_count": 0,
    "door_open_timers": {},
    "dms_pin_buffer": "",
    
    # pracenje vremena poslednjeg okidanja senzora za Vrata 1 i 2
    "door_1_last_dus": 0,
    "door_1_last_dpir": 0,
    "door_2_last_dus": 0,
    "door_2_last_dpir": 0,
    
    # "hladjenje" da ne prebrojimo istu osobu vise puta u 5 sekundi
    "cooldowns": {
        "door_1": 0,
        "door_2": 0
    }
}

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

    # LOGIKA ZA VRATA 1 (DUS1 i DPIR1)
    if topic == "Sensors/DUS1" and measurement == "Distance":
        if value < DISTANCE_THRESHOLD:
            SYSTEM_STATE["door_1_last_dus"] = current_time
            
            # Da li je u poslednjih 5s bio pokret unutra? (Znaci osoba izlazi)
            if (current_time - SYSTEM_STATE["door_1_last_dpir"] < TIME_WINDOW) and \
               (current_time - SYSTEM_STATE["cooldowns"]["door_1"] > TIME_WINDOW):
                
                SYSTEM_STATE["people_count"] = max(0, SYSTEM_STATE["people_count"] - 1) # broj ljudi ne id eu minus
                SYSTEM_STATE["cooldowns"]["door_1"] = current_time
                print(f"[LOGIC] Osoba IZAsLA kroz Vrata 1! Trenutno ljudi u kuci: {SYSTEM_STATE['people_count']}")

    if topic == "Sensors/DPIR1" and measurement == "Motion" and value == 1:
        SYSTEM_STATE["door_1_last_dpir"] = current_time
        turn_on_dl_for_10s() # staro pravilo za svetlo
        
        # Da li je u poslednjih 5s ocitana blizina spolja? (Znaci osoba ulazi)
        if (current_time - SYSTEM_STATE["door_1_last_dus"] < TIME_WINDOW) and \
           (current_time - SYSTEM_STATE["cooldowns"]["door_1"] > TIME_WINDOW):
            
            SYSTEM_STATE["people_count"] += 1
            SYSTEM_STATE["cooldowns"]["door_1"] = current_time
            print(f"[LOGIC] Osoba UsLA kroz Vrata 1! Trenutno ljudi u kuci: {SYSTEM_STATE['people_count']}")

    # LOGIKA ZA VRATA 2 (DUS2 i DPIR2)
    if topic == "Sensors/DUS2" and measurement == "Distance":
        if value < DISTANCE_THRESHOLD:
            SYSTEM_STATE["door_2_last_dus"] = current_time
            
            # Izlazak
            if (current_time - SYSTEM_STATE["door_2_last_dpir"] < TIME_WINDOW) and \
               (current_time - SYSTEM_STATE["cooldowns"]["door_2"] > TIME_WINDOW):
                SYSTEM_STATE["people_count"] = max(0, SYSTEM_STATE["people_count"] - 1)
                SYSTEM_STATE["cooldowns"]["door_2"] = current_time
                print(f"[LOGIC] Osoba IZAsLA kroz Vrata 2! Trenutno ljudi u kuci: {SYSTEM_STATE['people_count']}")

    if topic == "Sensors/DPIR2" and measurement == "Motion" and value == 1:
        SYSTEM_STATE["door_2_last_dpir"] = current_time
        
        # ulazak
        if (current_time - SYSTEM_STATE["door_2_last_dus"] < TIME_WINDOW) and \
           (current_time - SYSTEM_STATE["cooldowns"]["door_2"] > TIME_WINDOW):
            SYSTEM_STATE["people_count"] += 1
            SYSTEM_STATE["cooldowns"]["door_2"] = current_time
            print(f"[LOGIC] Osoba UsLA kroz Vrata 2! Trenutno ljudi u kuci: {SYSTEM_STATE['people_count']}")

    # LOGIKA ZA VRATA (DS1 i DS2) - ALARM 5 SEKUNDI
    if measurement == "Door_Status":
        door_name = topic.split("/")[-1] # DS1 ili DS2
        
        if value == 1: # vrata OTVORENA -> pokrecemo tajmer
            print(f"[LOGIC] {door_name} otvorena. Cekam 5 sekundi...")
            
            def alarm_door_open():
                trigger_alarm(f"{door_name} su ostala otvorena duze od 5 sekundi!")
            
            # pravimo tajmer i cuvamo ga zbog ponistavanaj
            timer = threading.Timer(5.0, alarm_door_open)
            SYSTEM_STATE["door_open_timers"][door_name] = timer
            timer.start()
            
        elif value == 0:
            print(f"[LOGIC] {door_name} zatvorena.")
            
            # ponistavamo tajmer ako je kucao
            if door_name in SYSTEM_STATE["door_open_timers"]:
                SYSTEM_STATE["door_open_timers"][door_name].cancel()
                del SYSTEM_STATE["door_open_timers"][door_name]
            
            # gasimo alarm ako je bio aktivan("dok se stanje DS-a ne promeni")
            if SYSTEM_STATE["alarm_active"]:
                deactivate_alarm()

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


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
