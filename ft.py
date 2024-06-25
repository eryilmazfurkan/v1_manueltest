import smbus
import time
import subprocess
import RPi.GPIO as GPIO
import re
from datetime import datetime
import os
import sqlite3
from db import *

fore_white = "\033[37m"
fore_blue = "\033[34m"
fore_red = "\033[31m"
italic = "\033[3m"
back_yellow = "\033[43m"
fore_yellow = "\033[33m"
back_black = "\033[40m"
reset = "\033[0m"

def i2c_device_detected(address):
    result = subprocess.run(['i2cdetect', '-y', '1'], capture_output=True, text=True)
    return format(address, '02x') in result.stdout

def test_led():
    led_values = [0xFF, 0xFC, 0xDD, 0xBD, 0x7D, 0xF9, 0xF5, 0xED]
    dev_addr = 0x20  
    conf_addr = 0x03
    write_addr = 0x01
    output_data = 0xFD
    if i2c_device_detected(dev_addr):
        bus = smbus.SMBus(1)
        bus.write_byte_data(dev_addr, conf_addr, 0x00)

        for value in led_values:
            bus.write_byte_data(dev_addr, write_addr, value)
            time.sleep(2)
            bus.write_byte_data(dev_addr, write_addr, output_data)

        user_input = input(f"{fore_white}LED'leri Kontrol Edin. Tüm LED'ler yanıyorsa{fore_blue}{italic} E {reset}{fore_white}yanmıyorsa{fore_red}{italic} H {reset}{fore_white}giriniz: {reset}")

        if user_input.upper() == 'E':
            return True
        elif user_input.upper() == 'H':
            return False
        else:
            return False
    else:
        return False
"""    
def check_button_pressed(button_pin, timeout):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    button_pressed = False
#    print(f"{timeout} saniye içinde butona basınız")
    try:
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            if GPIO.input(button_pin) == GPIO.LOW:
                button_pressed = True
                break
            time.sleep(0.1)

        if button_pressed:
            return True
        else:
            return False

    except KeyboardInterrupt:
        GPIO.cleanup()
"""
def check_button_pressed(button_pin, timeout):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    button_pressed = False
    try:
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            if GPIO.input(button_pin) == GPIO.LOW:
                button_pressed = True
                break
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        GPIO.cleanup()
    
    return button_pressed


def rtc():
    i2cdetect_result = subprocess.run(['i2cdetect', '-y', '0'], stdout=subprocess.PIPE)
    i2cdetect_output = i2cdetect_result.stdout.decode('utf-8')
    
    if 'UU' in i2cdetect_output or '51' in i2cdetect_output:
        hwclock_result = subprocess.run(['sudo', 'hwclock', '--show', '--utc'], stdout=subprocess.PIPE)
        system_time_result = subprocess.run(['date'], stdout=subprocess.PIPE)

        hwclock_time_str = hwclock_result.stdout.decode('utf-8').strip().split('.')[0]
        hwclock_time = datetime.strptime(hwclock_time_str, '%Y-%m-%d %H:%M:%S')
        hwclock = hwclock_time.strftime('%H:%M')

        system_time_str = system_time_result.stdout.decode('utf-8').strip()
        pattern = r'\b(\d{2}:\d{2}):\d{2}\b'
        system = re.search(pattern, system_time_str).group(1)

        return hwclock == system
    else:
        return False
    
def tpm():
    activate_venv_command = "source venv/bin/activate"
    subprocess.call(activate_venv_command, shell=True)

    os.chdir("/home/pi/ws/tbm/eltt2")

    tpm_output = subprocess.run(['sudo', './eltt2', '-g'], stdout=subprocess.PIPE)
    tpm = tpm_output.stdout.decode('utf-8')
    check_tpm = "TPM_PT_FAMILY_INDICATOR:"
    if  check_tpm in  tpm:
        return True
    else:
        return False

def uspc_pd(address):
    return i2c_device_detected(address)

def currentsensor(address):
    return i2c_device_detected(address)

def adc(address):
    return i2c_device_detected(address)

def cellular_modem():
    cellular_output = subprocess.run(['lsusb'], stdout=subprocess.PIPE)
    cellular = cellular_output.stdout.decode('utf-8')
    check = "2c7c:0125"
    if check in cellular:
        return True
    else:
        return False

def get_iccid():
    if cellular_modem():
        for attempt in range(10):
            try:
                response = subprocess.check_output(["atcom","AT+ICCID"]).decode("utf8")
                match = re.search(r'\+ICCID: (\d+)',response)
                iccid =  match.group(1)
                if iccid.startswith("8") and len(iccid) == 20:
                    return iccid
                else:
                    return False
            except subprocess.CalledProcessError as e:
                return False
    else:
        return False 
    
def get_imei():
    if cellular_modem():
        for attempt in range(10):
            try:
                response = subprocess.check_output(["atcom","AT+GSN"]).decode("utf8")
                match = re.search(r'\r\r\n(\d+)\r\n', response)
                imei =  match.group(1)
                if imei.startswith("8") and len(imei) == 15:
                    return imei
                else:
                    return False
            except subprocess.CalledProcessError as e:
                return False         
    else:
        return False
    
def get_firmware():
    if cellular_modem():
        for attempt in range(10):
            try:
                response = subprocess.check_output(["atcom", "AT+QGMR"]).decode("utf8")
                pattern = r'\b([\w\d_\.]+)\b'
                match = re.findall(pattern, response)
                firmware = match[2]
                if "EG25G" in firmware:
                    return firmware
                else:
                    return False
            except subprocess.CalledProcessError as e:
                return False
    else:
        return False           
    
def main():
    connection = sqlite3.connect('results.db')
    cursor = connection.cursor()
    print(f"{back_black}{fore_yellow}Ledlerin yanıp yanmadığını kontrol ediniz{reset}")
    db_led = test_led()
    print(f"{back_black}{fore_yellow}5 saniye içinde USER BUTTON basınız{reset}")
    db_usrbtn = check_button_pressed(5,5) #User button
    print(f"{back_black}{fore_yellow}5 saniye içinde RESET BUTTON basınız{reset}")
    db_rstbtn = check_button_pressed(6,5) #Reset button
    db_rtc = rtc()
    db_tpm = tpm()
    db_tmpsnsr = i2c_device_detected(0x4F)
    db_uspc = i2c_device_detected(0x08)
    db_cr = i2c_device_detected(0x40)
    db_adc = i2c_device_detected(0x48)
    db_cellular = cellular_modem()
    if db_cellular: 
        db_iccid = get_iccid()
        db_imei = get_imei()
        db_firmware = get_firmware()
    else:
        db_iccid = "0"
        db_imei = "0"
        db_firmware = "0"
    print(db_led, db_usrbtn, db_rstbtn, db_rtc, db_tpm, db_tmpsnsr, db_uspc, db_cr, db_adc, db_cellular, db_iccid, db_imei, db_firmware)
    cursor.execute('''INSERT INTO tablo (led, usrbtn, rstbtn, rtc, tpm, tmpsnsr, uspc, cr, adc, cellular, iccid, imei, firmware)
                      VALUES (
                            CASE WHEN ? THEN 'True' ELSE 'False' END,
                            CASE WHEN ? THEN 'True' ELSE 'False' END,
                            CASE WHEN ? THEN 'True' ELSE 'False' END,
                            CASE WHEN ? THEN 'True' ELSE 'False' END,
                            CASE WHEN ? THEN 'True' ELSE 'False' END,
                            CASE WHEN ? THEN 'True' ELSE 'False' END,
                            CASE WHEN ? THEN 'True' ELSE 'False' END,
                            CASE WHEN ? THEN 'True' ELSE 'False' END,
                            CASE WHEN ? THEN 'True' ELSE 'False' END,
                            CASE WHEN ? THEN 'True' ELSE 'False' END,
                            ?, ?, ?)''', 
                   (db_led, db_usrbtn, db_rstbtn, db_rtc, db_tpm, db_tmpsnsr,db_uspc, db_cr, db_adc, db_cellular, db_iccid, db_imei, db_firmware))
    connection.commit()
    connection.close()

if __name__ == "__main__":
    main()