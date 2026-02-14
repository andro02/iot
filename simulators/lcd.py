import time

def run_lcd_simulator(delay, callback, stop_event, publish_event, settings):
    print(f"Starting {settings['name']} simulator")
    # LCD simulator ne generise podatke, on je pasivan (ceka komande),
    # ali cemo ostaviti petlju da drzi thread zivim.
    while not stop_event.is_set():
        time.sleep(1)

# funkcija koju cemo zvati iz main-a kada zelimo nesto da ispisemo
def display_simulated_text(settings, text):
    print(f"[{settings['name']} DISPLAY]: {text}")