import time

def run_four_sd_simulator(delay, callback, stop_event, publish_event, settings):
    print(f"Starting {settings['name']} simulator")
    last_time = ""
    while not stop_event.is_set():
        # Simulira prikaz vremena (samo ispisuje u konzolu kad se promeni minut/sekunda)
        current_time = time.strftime("%H:%M")
        
        if current_time != last_time:
            # Ovde callback nije nuzan za MQTT ako samo prikazuje vreme lokalno,
            # ali mozemo slati status da je aktivan
            print(f"[{settings['name']}] DISPLAY: {current_time}")
            last_time = current_time
            
        time.sleep(1) # Azuriranje svake sekunde