import threading
import time
from simulators.four_sd import run_four_sd_simulator

def run_four_sd(settings, threads, stop_event, callback):
    if settings['simulated']:
        t = threading.Thread(target=run_four_sd_simulator, args=(1, callback, stop_event, None, settings))
        t.start()
        threads.append(t)
    else:
        from actuators.four_sd import FourSD
        fsd = FourSD(settings)
        # 4SD radi u pozadini cim se inicijalizuje, nema loop-a ovde
        return fsd