from actuators.dl import DL

def run_dl(settings, threads, stop_event, callback):
    if settings['simulated']:
        pass
    else:
        print("Starting DL Real Loop (Press 'L' to toggle)")
        
        # Ovde prosledjujemo callback klasi/funkciji za pravi hardver
        dl = DL(settings['pin'], callback)
        return dl
    return None