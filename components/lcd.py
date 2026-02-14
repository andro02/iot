import threading
import time
from simulators.lcd import run_lcd_simulator

def run_lcd(settings, threads, stop_event, callback):
    if settings['simulated']:
        t = threading.Thread(target=run_lcd_simulator, args=(1, callback, stop_event, None, settings))
        t.start()
        threads.append(t)
        return None # Simulator ne vraca objekat, ispis ide u konzolu
    else:
        from actuators.lcd import LCD
        # Kreiramo objekat pravog LCD-a i vracamo ga main-u da moze da pise po njemu
        lcd_display = LCD(settings)
        return lcd_display