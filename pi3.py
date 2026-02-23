import threading
import time
import json
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
from settings import load_settings

from components.dpir1 import run_dpir1
from components.dht import run_dht
from components.bir import run_bir
from components.brgb import run_brgb
from components.lcd import run_lcd

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
except:
    pass

HOSTNAME = "localhost" 
PORT = 1883
batch = []
counter_lock = threading.Lock()
publish_data_limit = 5
publish_data_counter = 0
publish_event = threading.Event()

rgb_device = None
lcd_device = None

def create_payload(cfg, measurement, value):
    return {"measurement": measurement, "value": value, "simulated": cfg['simulated'], "runs_on": cfg['runs_on'], "name": cfg['name']}

def add_to_batch(topic, payload):
    global publish_data_counter
    with counter_lock:
        batch.append((topic, json.dumps(payload), 0, False))
        publish_data_counter += 1
    if publish_data_counter >= publish_data_limit: publish_event.set()

def publisher_task(event, batch_data, stop_event):
    global publish_data_counter
    while not stop_event.is_set():
        event.wait(timeout=5)
        with counter_lock:
            if not batch_data: continue
            local_batch = batch_data.copy()
            batch_data.clear()
            publish_data_counter = 0
        try:
            publish.multiple(local_batch, hostname=HOSTNAME, port=PORT)
            print(f"[PI3 MQTT] Poslato {len(local_batch)} poruka.")
        except Exception as e:
            pass
        event.clear()

def dpir3_callback(): 
    add_to_batch("Sensors/DPIR3", 
                 create_payload(settings['DPIR3'], "Motion", 1))
    print(f"[DPIR3] Motion Detected")

def dht_callback(humidity, temperature, event, cfg):
    if humidity is None or temperature is None:
        return
    
    add_to_batch("Sensors/DHT", 
                 create_payload(cfg, "Humidity", humidity))
    add_to_batch("Sensors/DHT", 
                 create_payload(cfg, "Temperature", temperature))
    
    print(f"[{cfg['name']}] Temp: {temperature:.1f}C, Hum: {humidity:.1f}%")


def bir_callback(key, event, cfg):
    add_to_batch("Sensors/IR", 
                 create_payload(cfg, "IR_Remote", key))
    print(f"[IR] Button: {key}")

def brgb_callback(color):
    add_to_batch("Actuators/BRGB", 
                 create_payload(settings['BRGB'], "RGB_Color", color))
    print(f"[BRGB] Color set to: {color}")

def lcd_callback(text):
    add_to_batch("Actuators/LCD", 
                 create_payload(settings['LCD'], "LCD_Text", text))
    print(f"[LCD] Text displayed: {text}")

def on_connect(client, userdata, flags, rc):
    client.subscribe("Commands/PI3/#")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        command = payload.get("command")
        
        if msg.topic == "Commands/PI3/BRGB":
            if rgb_device: 
                rgb_device.turnOff() if command == "off" else rgb_device.set_color(command)
            brgb_callback(command)
            
        elif msg.topic == "Commands/PI3/LCD":
            text = payload.get("text", "")
            if lcd_device: lcd_device.print_text(text)
            lcd_callback(text)
            
    except Exception as e:
        print(f"Error handling MQTT command: {e}")

if __name__ == "__main__":
    print('Starting PI3...')
    settings = load_settings()
    threads = []
    stop_event = threading.Event()

    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(HOSTNAME, PORT, 60)
    mqtt_client.loop_start()

    # pblisher thread (Daemon)
    pub_thread = threading.Thread(target=publisher_task, args=(publish_event, batch, stop_event))
    pub_thread.daemon = True # Ovo znaci da ce se ugasiti kad se ugasi glavni program
    pub_thread.start()
    threads.append(pub_thread)
    print("Publisher thread started.")

    # inicijalizacija aktuatora (ako nisu simulirani, dobijamo objekte)
    rgb_device = run_brgb(settings['BRGB'], threads, stop_event, brgb_callback)
    lcd_device = run_lcd(settings['LCD'], threads, stop_event, lcd_callback)
    
    run_dht(settings['DHT1'], threads, stop_event, dht_callback)
    run_dht(settings['DHT2'], threads, stop_event, dht_callback)
    run_bir(settings['IR'], threads, stop_event, bir_callback)
    run_dpir1(settings['DPIR3'], threads, stop_event, dpir3_callback)

    try:
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        print('Stopping PI3...')
        stop_event.set()
    finally:
        for t in threads:
            t.join()

        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print("PI3 stopped.")