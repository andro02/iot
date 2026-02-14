import threading
from simulators.brgb import run_brgb_simulator

def run_brgb(settings, threads, stop_event, callback):
    if settings['simulated']:
        t = threading.Thread(target=run_brgb_simulator, args=(1, callback, stop_event, None, settings))
        t.start()
        threads.append(t)
    else:
        from actuators.brgb import BRGB
        rgb = BRGB(settings)
        return rgb