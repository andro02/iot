from actuators.db import DB

def run_db(settings, threads, stop_event, callback):
    if settings['simulated']:
        pass
    else:
        print("Starting DB Real Loop (Hold 'B' to buzz)")
        
        db = DB(settings['pin'], callback)
        return db
    return None