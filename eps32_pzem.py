"""
ESP32 LCD Display + PZEM - Complete Final Version
- LCD turns ON for 20 seconds after each webhook send
- LCD loop resumes automatically after 20 seconds
- LCD loop active by default on boot
- PZEM auto-restart on 3 consecutive failures
"""

import network
import time
from machine import Pin, I2C, RTC, UART, WDT
from micropython import const
import gc

print("\n" + "="*50)
print("ESP32 PZEM Monitor - Final")
print("="*50 + "\n")

gc.enable()
gc.collect()

# Global variables
connections = set()
tx_handle = None
rx_handle = None
i2c = None
lcd_addr = None
rtc = None
lcd_backlight = True
lcd_timer_active = False
lcd_timer_start = 0
lcd_counter = 0

# LCD loop control
lcd_loop_active = False
lcd_loop_state = False
lcd_loop_timer = 0

# PZEM variables
uart_pzem = None
pzem_enabled = False
pzem_voltage = None
pzem_current = None
pzem_power = None
pzem_energy = None
pzem_frequency = None
pzem_power_factor = None
pzem_last_read = 0
pzem_read_interval = 10000
pzem_device_id = 0x01

# Default WiFi credentials
DEFAULT_SSID = "TP-Link_5B9A"
DEFAULT_PASSWORD = "97180937"

wifi_ssid = ""
wifi_password = ""

def save_lcd_backlight_state():
    try:
        with open('lcd_config.txt', 'w') as f:
            f.write('1\n' if lcd_backlight else '0\n')
        return True
    except:
        return False

def load_lcd_backlight_state():
    global lcd_backlight
    try:
        with open('lcd_config.txt', 'r') as f:
            state = f.read().strip()
            lcd_backlight = (state == '1')
            return True
    except:
        lcd_backlight = True
        return False


# PZEM Functions
def pzem_init():
    global uart_pzem, pzem_enabled
    try:
        uart_pzem = UART(2, baudrate=9600, bits=8, parity=None, stop=1, 
                        tx=17, rx=16, timeout=1000)
        pzem_enabled = True
        print("PZEM initialized (UART2)")
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
        if response[0] != pzem_device_id:
            return None
        if response[1] == 0x84:
            return None
        if response[1] != 0x04:
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
            pzem_energy = (result[5] + (result[6] << 16)) / 100.0
            pzem_frequency = result[7] / 10.0
            pzem_power_factor = result[8] / 100.0
            
            print("PZEM: {:.1f}V {:.3f}A {:.1f}W {:.1f}Wh {:.1f}Hz PF:{:.2f}".format(
                pzem_voltage, pzem_current, pzem_power, pzem_energy, 
                pzem_frequency, pzem_power_factor))
            return True
        else:
            print("PZEM read failed - no data")
            pzem_voltage = None
            pzem_current = None
            pzem_power = None
            pzem_energy = None
            pzem_frequency = None
            pzem_power_factor = None
            return False
    except Exception as e:
        print("PZEM read error:", str(e))
        pzem_voltage = None
        pzem_current = None
        pzem_power = None
        pzem_energy = None
        pzem_frequency = None
        pzem_power_factor = None
        return False

def pzem_reset_energy():
    if not pzem_enabled or not uart_pzem:
        return False
    try:
        request = bytearray([pzem_device_id, 0x42])
        crc = pzem_calculate_crc(request)
        request.append(crc & 0xFF)
        request.append((crc >> 8) & 0xFF)
        
        uart_pzem.read()
        uart_pzem.write(request)
        uart_pzem.flush()
        time.sleep_ms(100)
        response = uart_pzem.read()
        
        if response and len(response) >= 4:
            print("PZEM energy reset successful")
            return True
        return False
    except Exception as e:
        print("PZEM reset error:", str(e))
        return False

# LCD Functions
def lcd_write(data):
    if i2c and lcd_addr:
        try:
            if lcd_backlight:
                data = data | 0x08
            else:
                data = data & 0xF7
            i2c.writeto(lcd_addr, bytearray([data]))
        except:
            pass

def lcd_pulse(data):
    bl = 0x08 if lcd_backlight else 0x00
    lcd_write(data | 0x04 | bl)
    time.sleep_us(1)
    lcd_write(data | bl)
    time.sleep_us(50)

def lcd_write_nibble(data):
    bl = 0x08 if lcd_backlight else 0x00
    lcd_write(data | bl)
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
            i2c = None
            return False
        for addr in [0x27, 0x3F]:
            if addr in devices:
                lcd_addr = addr
                break
        if not lcd_addr:
            i2c = None
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
        print("LCD init error:", str(e))
        i2c = None
        lcd_addr = None
        return False

def lcd_clear():
    if i2c and lcd_addr:
        lcd_cmd(0x01)
        time.sleep_ms(2)

def lcd_set_pos(row, col):
    if i2c and lcd_addr:
        offsets = [0x00, 0x40, 0x14, 0x54]
        if row < 4 and col < 20:
            lcd_cmd(0x80 | (offsets[row] + col))

def lcd_text(text, row=0, col=0):
    if i2c and lcd_addr:
        lcd_set_pos(row, col)
        for c in text[:20]:
            lcd_char(ord(c))

def lcd_set_backlight(state):
    global lcd_backlight
    if not i2c or not lcd_addr:
        return False
    lcd_backlight = state
    try:
        if lcd_backlight:
            lcd_write(0x08)
        else:
            lcd_write(0x00)
        time.sleep_ms(10)
        return True
    except:
        return False

def lcd_timer_on():
    global lcd_timer_active, lcd_timer_start
    if not i2c or not lcd_addr:
        return False
    if lcd_set_backlight(True):
        lcd_timer_active = True
        lcd_timer_start = time.ticks_ms()
        return True
    return False

def check_lcd_timer():
    global lcd_timer_active, lcd_loop_active, lcd_loop_state, lcd_loop_timer
    if not lcd_timer_active:
        return
    if time.ticks_diff(time.ticks_ms(), lcd_timer_start) >= 20000:
        print("LCD timer expired - resuming LCD loop")
        lcd_set_backlight(False)
        lcd_timer_active = False
        save_lcd_backlight_state()
        
        # Resume LCD loop after timer expires
        lcd_loop_active = True
        lcd_loop_state = False
        lcd_loop_timer = time.ticks_ms()

def check_lcd_loop():
    global lcd_loop_active, lcd_loop_state, lcd_loop_timer
    if not lcd_loop_active:
        return
    now = time.ticks_ms()
    elapsed = time.ticks_diff(now, lcd_loop_timer)
    if lcd_loop_state:
        if elapsed >= 20000:
            lcd_set_backlight(False)
            lcd_loop_state = False
            lcd_loop_timer = now
    else:
        if elapsed >= 45000:
            lcd_set_backlight(True)
            lcd_loop_state = True
            lcd_loop_timer = now

def lcd_display(line1="", line2="", line3="", line4=""):
    if not i2c or not lcd_addr:
        return
    try:
        lcd_clear()
        if line1:
            lcd_text(line1, 0, 0)
        if line2:
            lcd_text(line2, 1, 0)
        if line3:
            lcd_text(line3, 2, 0)
        if line4:
            lcd_text(line4, 3, 0)
    except:
        pass

def get_signal_quality(rssi):
    if rssi >= -50:
        return 100
    elif rssi <= -100:
        return 0
    return 2 * (rssi + 100)

def update_lcd_status():
    global pzem_last_webhook, pzem_webhook_interval
    
    if not i2c or not lcd_addr:
        return
    try:
        now = time.ticks_ms()
        line3 = line4 =" "
        # Line 2: Amp, Volt
        if pzem_voltage is not None and pzem_current is not None:
            line1 = "{:.2f}A  {:.1f}V".format(pzem_current, pzem_voltage)
        else:
            line1 = "---A  ---V"
        
        # Line 3: Power Factor, Signal Quality
        line2 = ""
        if pzem_power_factor is not None:
            line2 = "PF:{:.2f}".format(pzem_power_factor)
        else:
            line2 = "PF:---"
        
        lcd_display(line1, line2, line3, line4)
    except Exception as e:
        print("LCD update error:", str(e))


def main():
    global lcd_loop_active, lcd_loop_state, lcd_loop_timer
    global pzem_enabled, uart_pzem, lcd_timer_active, lcd_timer_start
    
    print("\n" + "="*50)
    print("Starting System...")
    print("="*50)
    
    gc.collect()
    print("Initial memory:", gc.mem_free())
    
    # Initialize Watchdog Timer
    print("\nInitializing Watchdog (30s)...")
    try:
        wdt = WDT(timeout=30000)
        print("Watchdog initialized")
    except Exception as e:
        print("Watchdog failed:", str(e))
        wdt = None
    
    # Step 4: LCD
    print("\n4. LCD Display")
    lcd_ok = lcd_init()
    if lcd_ok:
        lcd_set_backlight(lcd_backlight)
        lcd_display("ESP32 Ready", "Initializing...", "", "")
        
        # Start LCD backlight loop by default
        print("   Starting LCD loop (20s ON, 45s OFF)")
        lcd_loop_active = True
        lcd_loop_state = True
        lcd_loop_timer = time.ticks_ms()
    gc.collect()
    
    # Step 5: PZEM
    print("\n5. PZEM Interface")
    pzem_ok = pzem_init()
    gc.collect()
    
    # Read PZEM immediately and send to webhook
    if pzem_ok:
        print("\n6. Initial PZEM Read")
        
        # Feed watchdog before long operations
        if wdt:
            wdt.feed()
        
        time.sleep(2)
        if pzem_read_all():
            print("   Initial PZEM read successful")
            
            # Feed watchdog
            if wdt:
                wdt.feed()
               # Turn on LCD for 20 seconds after webhook send
                if lcd_ok:
                    print("   LCD ON for 20 seconds")
                    lcd_set_backlight(True)
                    lcd_timer_active = True
                    lcd_timer_start = time.ticks_ms()
                    update_lcd_status()
        else:
            print("   Initial PZEM read failed")
    
  
    print("\n" + "="*50)
    print("System Ready!")
    print("="*50)
    print("LCD:", "Active" if lcd_ok else "Disabled")
    print("LCD Loop: Active (default)")
    print("PZEM:", "Active" if pzem_ok else "Disabled")
    print("Watchdog:", "Active" if wdt else "Disabled")
    print("Free memory:", gc.mem_free())
    print("="*50 + "\n")
    
    counter = 0
    last_update = 0
    last_lcd = 0
    last_gc = 0
    last_pzem_read = 0
    pzem_fail_count = 0
    max_pzem_failures = 3
    
    # Initialize webhook timer
    pzem_last_webhook = time.ticks_ms()
    
    try:
        while True:
            # Feed watchdog
            if wdt:
                wdt.feed()
            
            now = time.ticks_ms()
            
            check_lcd_timer()
            check_lcd_loop()
                      
            # PZEM reading every 10 seconds
            if pzem_enabled and time.ticks_diff(now, last_pzem_read) >= pzem_read_interval:
                print("time to read pzem..")
                read_success = pzem_read_all()
                last_pzem_read = now
                
                if read_success:
                    pzem_fail_count = 0
                else:
                    pzem_fail_count += 1
                    print("PZEM read failed ({}/{})".format(pzem_fail_count, max_pzem_failures))
                    
                    if pzem_fail_count >= max_pzem_failures:
                        print("PZEM restart triggered!")
                        print("Reinitializing PZEM...")
                        pzem_enabled = False
                        time.sleep_ms(500)
                        if pzem_init():
                            print("PZEM reinitialized successfully")
                            pzem_fail_count = 0
                        else:
                            print("PZEM reinit failed, will retry later")
                
                if lcd_ok:
                    update_lcd_status()
                       
            # GC every 60s
            if time.ticks_diff(now, last_gc) > 60000:
                gc.collect()
                last_gc = now
                    
            # LCD update every 5s
            if lcd_ok and time.ticks_diff(now, last_lcd) > 5000:
                update_lcd_status()
                last_lcd = now
    
    except KeyboardInterrupt:
        print("\nStopping...")
        if lcd_ok:
            lcd_display("Stopped", "Goodbye!", "", "")


if __name__ == "__main__":
    main()
