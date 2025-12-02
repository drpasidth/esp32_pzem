import machine
from machine import Pin
import network
import time

# WiFi credentials
WIFI_SSID = "TP-Link_5B9A"
WIFI_PASSWORD = "97180937"

# Relay setup
HAS_RELAY = False
relay = None

try:
    relay = Pin(12, Pin.OUT)
    relay.value(1)
    HAS_RELAY = True
except Exception as e:
    print("Relay init failed:", e)
    HAS_RELAY = False

# Create WLAN object
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        
        # Wait up to 10 seconds for connection
        for _ in range(10):
            if wlan.isconnected():
                print("Connected!")
                print("IP address:", wlan.ifconfig()[0])
                return True
            print("Waiting for connection...")
            time.sleep(1)
    
    return wlan.isconnected()

# Main execution
if connect_wifi():
    print("WiFi connected successfully")
    if HAS_RELAY and relay:
        for _ in range(3):
            relay.value(1)
            time.sleep(1)  # Fixed: use time.sleep(), seconds not ms
            relay.value(0)
            time.sleep(1)
    while True:
        print("Connected to WiFi")
        time.sleep(5)
else:
    print("Failed to connect to WiFi")
