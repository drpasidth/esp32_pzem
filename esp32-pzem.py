"""
ESP32 PZEM to LCD 16x2 Display
Simple PZEM readout displayed on I2C LCD
"""

from machine import Pin, I2C, UART
import time
import gc

print("\n" + "="*40)
print("ESP32 PZEM -> LCD 16x2")
print("="*40 + "\n")

gc.enable()
gc.collect()

# Global variables
i2c = None
lcd_addr = None

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
pzem_read_interval = 5000  # Read every 5 seconds

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
        
        uart_pzem.read()  # Clear buffer
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
            
            print("V:{:.1f} A:{:.3f} W:{:.1f} PF:{:.2f}".format(
                pzem_voltage, pzem_current, pzem_power, pzem_power_factor))
            return True
        else:
            print("PZEM: No data")
            return False
    except Exception as e:
        print("PZEM error:", str(e))
        return False

# ============== LCD 16x2 Functions ==============
def lcd_write(data):
    if i2c and lcd_addr:
        try:
            i2c.writeto(lcd_addr, bytearray([data | 0x08]))  # Backlight ON
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
            print("LCD: No I2C device found")
            return False
        
        for addr in [0x27, 0x3F]:
            if addr in devices:
                lcd_addr = addr
                break
        
        if not lcd_addr:
            print("LCD: No compatible address")
            return False
        
        time.sleep_ms(50)
        lcd_write_nibble(0x30)
        time.sleep_ms(5)
        lcd_write_nibble(0x30)
        time.sleep_ms(1)
        lcd_write_nibble(0x30)
        time.sleep_ms(1)
        lcd_write_nibble(0x20)
        lcd_cmd(0x28)  # 4-bit, 2-line
        lcd_cmd(0x0C)  # Display ON, cursor OFF
        lcd_cmd(0x01)  # Clear
        time.sleep_ms(2)
        lcd_cmd(0x06)  # Entry mode
        print("LCD initialized at 0x{:02X}".format(lcd_addr))
        return True
    except Exception as e:
        print("LCD init error:", str(e))
        return False

def lcd_clear():
    if i2c and lcd_addr:
        lcd_cmd(0x01)
        time.sleep_ms(2)

def lcd_set_pos(row, col):
    if i2c and lcd_addr:
        offsets = [0x00, 0x40]  # 16x2 LCD
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
    """Update LCD with PZEM readings"""
    if not i2c or not lcd_addr:
        return
    
    # Line 1: Voltage and Current
    if pzem_voltage is not None and pzem_current is not None:
        line1 = "{:.1f}V  {:.2f}A".format(pzem_voltage, pzem_current)
    else:
        line1 = "---V  ---A"
    
    # Line 2: Power and Power Factor
    if pzem_power is not None and pzem_power_factor is not None:
        line2 = "{:.0f}W  PF:{:.2f}".format(pzem_power, pzem_power_factor)
    else:
        line2 = "---W  PF:---"
    
    lcd_display(line1, line2)

# ============== Main ==============
def main():
    global pzem_enabled, uart_pzem
    
    print("\nStarting...")
    gc.collect()
    
    # Initialize LCD
    lcd_ok = lcd_init()
    if lcd_ok:
        lcd_display("PZEM Monitor", "Starting...")
    
    # Initialize PZEM
    pzem_ok = pzem_init()
    
    time.sleep(1)
    
    if lcd_ok:
        if pzem_ok:
            lcd_display("PZEM Ready", "Reading...")
        else:
            lcd_display("PZEM Error", "Check wiring")
    
    print("\nSystem Ready")
    print("LCD:", "OK" if lcd_ok else "Failed")
    print("PZEM:", "OK" if pzem_ok else "Failed")
    print("Free mem:", gc.mem_free())
    print("="*40 + "\n")
    
    last_read = 0
    last_gc = 0
    
    try:
        while True:
            now = time.ticks_ms()
            
            # Read PZEM at interval
            if pzem_enabled and time.ticks_diff(now, last_read) >= pzem_read_interval:
                pzem_read_all()
                last_read = now
                
                if lcd_ok:
                    update_lcd()
            
            # GC every 60s
            if time.ticks_diff(now, last_gc) > 60000:
                gc.collect()
                last_gc = now
            
            time.sleep_ms(100)
    
    except KeyboardInterrupt:
        print("\nStopped")
        if lcd_ok:
            lcd_display("Stopped", "Goodbye!")

if __name__ == "__main__":
    main()
