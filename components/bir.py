import threading
from simulators.bir import run_bir_simulator

def run_bir(settings, threads, stop_event, callback):
    if settings['simulated']:
        t = threading.Thread(target=run_bir_simulator, args=(1, callback, stop_event, None, settings))
        t.start()
        threads.append(t)
    else:
        from sensors.bir import BIR
        bir = BIR(settings['pin'], callback)
        t = threading.Thread(target=bir.loop)
        t.start()
        threads.append(t)