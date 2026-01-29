def run_dl_simulator(callback, stop_event):
    # Simulator samo čeka – nema input-a ovde
    while not stop_event.is_set():
        pass

# import time

# class DL(object):
#     def __init__(self, pin):
#         self.pin = pin
#         self.state = False
    
#     def turn_on(self):
#         if not self.state:
#             self.state = True
#             t = time.localtime()
#             print(f"[{time.strftime('%H:%M:%S', t)}] DL: LIGHT ON")
        
#     def turn_off(self):
#         if self.state:
#             self.state = False
#             t = time.localtime()
#             print(f"[{time.strftime('%H:%M:%S', t)}] DL: LIGHT OFF")