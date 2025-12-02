"""
ESP32 PZEM Monitor with WiFi Manager & Web Server
- WiFi Manager with AP fallback
- Web server showing PZEM parameters
- LCD: Line1=IP, Line2=Amp & Volt
"""

from machine import Pin, I2C, UART
import network
import socket
import time
import gc

print("\n" + "="*40)
print("ESP32 PZEM + WiFi + WebServer")
print("="*40 + "\n")

gc.enable()
gc.collect()

# WiFi credentials
DEFAULT_SSID = "TP-Link_5B9A"
DEFAULT_PASSWORD = "97180937"
AP_SSID = "ESP32-PZEM-Setup"
AP_PASSWORD = "12345678"

# Global variables
i2c = None
lcd_addr = None
wlan = None
ap = None
server = None
ip_address = "0.0.0.0"

# PZEM variables
uart_pzem = None
pzem_enabled = False
pzem_voltage = None
pzem_current = None
pzem_power = None
pzem_energy = None
pzem_frequency = None
pzem_power_factor = None
pzem_device_id = 0x01
pzem_read_interval = 5000

# ============== WiFi Manager ==============
def save_wifi_config(ssid, password):
    try:
        with open('wifi_config.txt', 'w') as f:
            f.write(ssid + '\n')
            f.write(password + '\n')
        return True
    except:
        return False

def load_wifi_config():
    try:
        with open('wifi_config.txt', 'r') as f:
            ssid = f.readline().strip()
            password = f.readline().strip()
            if ssid:
                return ssid, password
    except:
        pass
    return DEFAULT_SSID, DEFAULT_PASSWORD

def connect_wifi():
    global wlan, ip_address
    
    ssid, password = load_wifi_config()
    print("Connecting to:", ssid)
    
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if wlan.isconnected():
        ip_address = wlan.ifconfig()[0]
        print("Already connected:", ip_address)
        return True
    
    wlan.connect(ssid, password)
    
    # Wait up to 15 seconds
    for i in range(15):
        if wlan.isconnected():
            ip_address = wlan.ifconfig()[0]
            print("Connected! IP:", ip_address)
            return True
        print("Waiting... ({}/15)".format(i+1))
        time.sleep(1)
    
    print("WiFi connection failed")
    return False

def start_ap_mode():
    global ap, ip_address
    
    print("Starting AP Mode:", AP_SSID)
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=AP_SSID, password=AP_PASSWORD, authmode=3)
    
    time.sleep(1)
    ip_address = ap.ifconfig()[0]
    print("AP IP:", ip_address)
    return True

def wifi_manager_page():
    """Generate WiFi config page HTML"""
    html = """<!DOCTYPE html>
<html>
<head>
    <title>ESP32 WiFi Setup</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body{font-family:Arial;margin:20px;background:#1a1a2e;color:#fff;}
        .card{background:#16213e;padding:20px;border-radius:10px;max-width:400px;margin:auto;}
        h1{color:#e94560;text-align:center;}
        input{width:100%;padding:12px;margin:8px 0;border:none;border-radius:5px;box-sizing:border-box;}
        button{width:100%;padding:12px;background:#e94560;color:#fff;border:none;border-radius:5px;cursor:pointer;font-size:16px;}
        button:hover{background:#ff6b6b;}
    </style>
</head>
<body>
    <div class="card">
        <h1>WiFi Setup</h1>
        <form action="/save" method="GET">
            <input type="text" name="ssid" placeholder="WiFi SSID" required>
            <input type="password" name="pass" placeholder="WiFi Password" required>
            <button type="submit">Connect</button>
        </form>
    </div>
</body>
</html>"""
    return html

# ============== Web Server ==============
def api_json():
    """Return PZEM data as JSON"""
    def fmt(val):
        return 'null' if val is None else str(val)
    
    json_str = '{"voltage":%s,"current":%s,"power":%s,"energy":%s,"frequency":%s,"pf":%s}' % (
        fmt(pzem_voltage),
        fmt(pzem_current),
        fmt(pzem_power),
        fmt(pzem_energy),
        fmt(pzem_frequency),
        fmt(pzem_power_factor)
    )
    return json_str

def pzem_web_page():
    """Generate PZEM data page with AJAX auto-refresh"""
    html = """<!DOCTYPE html>
<html>
<head>
    <title>PZEM Monitor</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body{font-family:Arial;margin:0;padding:20px;background:#0f0f23;color:#fff;}
        h1{text-align:center;color:#00d4ff;}
        .grid{display:grid;grid-template-columns:repeat(2,1fr);gap:15px;max-width:500px;margin:auto;}
        .card{background:linear-gradient(135deg,#1a1a3e,#2d2d5a);padding:20px;border-radius:15px;text-align:center;}
        .value{font-size:32px;font-weight:bold;color:#00ff88;}
        .label{font-size:14px;color:#888;margin-top:5px;}
        .volt{color:#ffcc00;}
        .amp{color:#ff6b6b;}
        .watt{color:#00d4ff;}
        .status{text-align:center;color:#666;margin-top:20px;font-size:12px;}
        .online{color:#00ff88;}
    </style>
</head>
<body>
    <h1>PZEM Monitor</h1>
    <div class="grid">
        <div class="card">
            <div class="value volt" id="volt">---</div>
            <div class="label">Voltage (V)</div>
        </div>
        <div class="card">
            <div class="value amp" id="amp">---</div>
            <div class="label">Current (A)</div>
        </div>
        <div class="card">
            <div class="value watt" id="watt">---</div>
            <div class="label">Power (W)</div>
        </div>
        <div class="card">
            <div class="value" id="energy">---</div>
            <div class="label">Energy (kWh)</div>
        </div>
        <div class="card">
            <div class="value" id="freq">---</div>
            <div class="label">Frequency (Hz)</div>
        </div>
        <div class="card">
            <div class="value" id="pf">---</div>
            <div class="label">Power Factor</div>
        </div>
    </div>
    <p class="status">IP: %s | <span class="online" id="status">Updating...</span></p>
    
    <script>
        function updateData() {
            fetch('/api')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('volt').textContent = (data.voltage !== null) ? data.voltage.toFixed(1) : '---';
                    document.getElementById('amp').textContent = (data.current !== null) ? data.current.toFixed(3) : '---';
                    document.getElementById('watt').textContent = (data.power !== null) ? data.power.toFixed(1) : '---';
                    document.getElementById('energy').textContent = (data.energy !== null) ? data.energy.toFixed(2) : '---';
                    document.getElementById('freq').textContent = (data.frequency !== null) ? data.frequency.toFixed(1) : '---';
                    document.getElementById('pf').textContent = (data.pf !== null) ? data.pf.toFixed(2) : '---';
                    document.getElementById('status').textContent = 'Live (5s refresh)';
                })
                .catch(err => {
                    document.getElementById('status').textContent = 'Connection error';
                });
        }
        updateData();
        setInterval(updateData, 5000);
    </script>
</body>
</html>""" % ip_address
    return html

def start_web_server():
    global server
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', 80))
        server.listen(5)
        server.setblocking(False)
        print("Web server started on port 80")
        return True
    except Exception as e:
        print("Web server error:", str(e))
        return False

def handle_web_client():
    global wlan, ip_address
    if not server:
        return
    
    try:
        client, addr = server.accept()
        client.settimeout(2)
        request = client.recv(1024).decode('utf-8')
        
        # Parse request
        if 'GET /api' in request:
            response = api_json()
            client.send('HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\n\r\n')
            client.send(response)
        
        elif 'GET /save?' in request:
            # Parse WiFi credentials
            try:
                params = request.split('GET /save?')[1].split(' ')[0]
                ssid = ""
                password = ""
                for param in params.split('&'):
                    if param.startswith('ssid='):
                        ssid = param[5:].replace('%20', ' ').replace('+', ' ')
                    elif param.startswith('pass='):
                        password = param[5:].replace('%20', ' ').replace('+', ' ')
                
                if ssid:
                    save_wifi_config(ssid, password)
                    client.send('HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n')
                    client.send('<html><body style="background:#1a1a2e;color:#fff;text-align:center;padding:50px;font-family:Arial;"><h1>Saved!</h1><p>Rebooting...</p></body></html>')
                    client.close()
                    time.sleep(2)
                    import machine
                    machine.reset()
            except Exception as e:
                print("Save error:", str(e))
                client.send('HTTP/1.1 400 Bad Request\r\n\r\n')
        
        elif 'GET /setup' in request:
            response = wifi_manager_page()
            client.send('HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n')
            client.send(response)
        
        else:
            # Default: PZEM data page
            response = pzem_web_page()
            client.send('HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n')
            client.send(response)
        
        client.close()
    except OSError:
        pass  # No client waiting
    except Exception as e:
        print("Client error:", str(e))

# ============== PZEM Functions ==============
def pzem_init():
    global uart_pzem, pzem_enabled
    try:
        uart_pzem = UART(2, baudrate=9600, bits=8, parity=None, stop=1, 
                        tx=17, rx=16, timeout=1000)
        pzem_enabled = True
        print("PZEM initialized (TX=17, RX=16)")
        return True
    except Exception as e:
        print("PZEM init error:", str(e))
        pzem_enabled = False
        return False

def pzem_calculate_crc(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc

def pzem_read_input_registers(address, count):
    global uart_pzem
    if not pzem_enabled or not uart_pzem:
        return None
    try:
        request = bytearray([
            pzem_device_id, 0x04,
            (address >> 8) & 0xFF, address & 0xFF,
            (count >> 8) & 0xFF, count & 0xFF
        ])
        crc = pzem_calculate_crc(request)
        request.append(crc & 0xFF)
        request.append((crc >> 8) & 0xFF)
        
        uart_pzem.read()
        uart_pzem.write(request)
        uart_pzem.flush()
        time.sleep_ms(100)
        
        response = uart_pzem.read()
        if not response or len(response) < 5:
            return None
        if response[0] != pzem_device_id or response[1] != 0x04:
            return None
        
        byte_count = response[2]
        expected_len = 3 + byte_count + 2
        if len(response) < expected_len:
            return None
        
        data = response[3:3+byte_count]
        received_crc = response[3+byte_count] | (response[3+byte_count+1] << 8)
        calculated_crc = pzem_calculate_crc(response[:3+byte_count])
        if received_crc != calculated_crc:
            return None
        
        registers = []
        for i in range(0, byte_count, 2):
            reg_value = (data[i] << 8) | data[i+1]
            registers.append(reg_value)
        return registers
    except Exception as e:
        print("PZEM read error:", str(e))
        return None

def pzem_read_all():
    global pzem_voltage, pzem_current, pzem_power, pzem_energy
    global pzem_frequency, pzem_power_factor
    
    if not pzem_enabled:
        return False
    try:
        result = pzem_read_input_registers(address=0x0000, count=10)
        if result and len(result) >= 10:
            pzem_voltage = result[0] / 10.0
            pzem_current = (result[1] + (result[2] << 16)) / 1000.0
            pzem_power = (result[3] + (result[4] << 16)) / 10.0
            pzem_energy = (result[5] + (result[6] << 16)) / 1000.0
            pzem_frequency = result[7] / 10.0
            pzem_power_factor = result[8] / 100.0
            return True
        return False
    except:
        return False

# ============== LCD 16x2 Functions ==============
def lcd_write(data):
    if i2c and lcd_addr:
        try:
            i2c.writeto(lcd_addr, bytearray([data | 0x08]))
        except:
            pass

def lcd_pulse(data):
    lcd_write(data | 0x04)
    time.sleep_us(1)
    lcd_write(data)
    time.sleep_us(50)

def lcd_write_nibble(data):
    lcd_write(data)
    lcd_pulse(data)

def lcd_cmd(cmd):
    lcd_write_nibble(cmd & 0xF0)
    lcd_write_nibble((cmd << 4) & 0xF0)

def lcd_char(data):
    lcd_write_nibble(0x01 | (data & 0xF0))
    lcd_write_nibble(0x01 | ((data << 4) & 0xF0))

def lcd_init():
    global i2c, lcd_addr
    try:
        i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=100000)
        time.sleep_ms(50)
        devices = i2c.scan()
        if not devices:
            return False
        
        for addr in [0x27, 0x3F]:
            if addr in devices:
                lcd_addr = addr
                break
        
        if not lcd_addr:
            return False
        
        time.sleep_ms(50)
        lcd_write_nibble(0x30)
        time.sleep_ms(5)
        lcd_write_nibble(0x30)
        time.sleep_ms(1)
        lcd_write_nibble(0x30)
        time.sleep_ms(1)
        lcd_write_nibble(0x20)
        lcd_cmd(0x28)
        lcd_cmd(0x0C)
        lcd_cmd(0x01)
        time.sleep_ms(2)
        lcd_cmd(0x06)
        print("LCD initialized")
        return True
    except Exception as e:
        print("LCD error:", str(e))
        return False

def lcd_clear():
    if i2c and lcd_addr:
        lcd_cmd(0x01)
        time.sleep_ms(2)

def lcd_set_pos(row, col):
    if i2c and lcd_addr:
        offsets = [0x00, 0x40]
        if row < 2 and col < 16:
            lcd_cmd(0x80 | (offsets[row] + col))

def lcd_text(text, row=0, col=0):
    if i2c and lcd_addr:
        lcd_set_pos(row, col)
        for c in text[:16]:
            lcd_char(ord(c))

def lcd_display(line1="", line2=""):
    if not i2c or not lcd_addr:
        return
    try:
        lcd_clear()
        if line1:
            lcd_text(line1, 0, 0)
        if line2:
            lcd_text(line2, 1, 0)
    except:
        pass

def update_lcd():
    """Update LCD: Line1=IP, Line2=Amp & Volt"""
    if not i2c or not lcd_addr:
        return
    
    # Line 1: IP Address
    line1 = ip_address
    
    # Line 2: Amp and Volt
    if pzem_current is not None and pzem_voltage is not None:
        line2 = "{:.2f}A {:.1f}V".format(pzem_current, pzem_voltage)
    else:
        line2 = "---A  ---V"
    
    lcd_display(line1, line2)

# ============== Main ==============
def main():
    global ip_address
    
    print("\nStarting System...")
    gc.collect()
    
    # Initialize LCD
    lcd_ok = lcd_init()
    if lcd_ok:
        lcd_display("PZEM Monitor", "Starting...")
    
    # Initialize PZEM
    pzem_ok = pzem_init()
    
    # Connect to WiFi
    if lcd_ok:
        lcd_display("Connecting WiFi", DEFAULT_SSID[:16])
    
    wifi_connected = connect_wifi()
    
    if not wifi_connected:
        # Start AP mode for configuration
        print("Starting AP mode for setup...")
        start_ap_mode()
        if lcd_ok:
            lcd_display("AP:" + AP_SSID[:10], ip_address)
    
    # Start web server
    web_ok = start_web_server()
    
    time.sleep(1)
    
    print("\n" + "="*40)
    print("System Ready!")
    print("="*40)
    print("IP:", ip_address)
    print("Web: http://" + ip_address)
    print("API: http://" + ip_address + "/api")
    print("Setup: http://" + ip_address + "/setup")
    print("LCD:", "OK" if lcd_ok else "Failed")
    print("PZEM:", "OK" if pzem_ok else "Failed")
    print("="*40 + "\n")
    
    if lcd_ok:
        update_lcd()
    
    last_read = 0
    last_gc = 0
    
    try:
        while True:
            now = time.ticks_ms()
            
            # Handle web clients
            handle_web_client()
            
            # Read PZEM every 5 seconds
            if pzem_enabled and time.ticks_diff(now, last_read) >= pzem_read_interval:
                if pzem_read_all():
                    print("V:{:.1f} A:{:.2f} W:{:.1f} PF:{:.2f}".format(
                        pzem_voltage, pzem_current, pzem_power, pzem_power_factor))
                last_read = now
                
                if lcd_ok:
                    update_lcd()
            
            # GC every 60s
            if time.ticks_diff(now, last_gc) > 60000:
                gc.collect()
                last_gc = now
            
            time.sleep_ms(50)
    
    except KeyboardInterrupt:
        print("\nStopped")
        if lcd_ok:
            lcd_display("Stopped", "Goodbye!")

if __name__ == "__main__":
    main()
