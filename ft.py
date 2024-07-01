import smbus
import time
import subprocess
import RPi.GPIO as GPIO
import re
from datetime import datetime
import os
import sqlite3
from db import *
from loguru import logger

logger.add("logfile_{time:YYYY-MM-DD}.log", rotation="00:00", enqueue=True)

fore_white = "\033[37m"
fore_blue = "\033[34m"
fore_red = "\033[31m"
italic = "\033[3m"
back_yellow = "\033[43m"
fore_yellow = "\033[33m"
back_black = "\033[40m"
reset = "\033[0m"

i2cadresss_tmpsnsr = 0x4F
i2cadresss_uspc = 0x08
i2cadresss_cr = 0x40
i2cadresss_adc  = 0x48

def i2c_device_detected(address, i2c_bus='1'):
    try:
        result = subprocess.run(['i2cdetect', '-y', i2c_bus], capture_output=True, text=True)
        return format(address, '02x') in result.stdout #Convert the given address to a 2-digit hexadecimal string
    except subprocess.CalledProcessError as e:
        logger.error(f"Error detecting I2C device at address {address}: {e}")
        return False

#Checks whether the LEDs in the I/O expander connected to address 0x20 are working or not.
def test_led():
    led_values = [0xFF, 0xFC, 0xDD, 0xBD, 0x7D, 0xF9, 0xF5, 0xED]
    dev_addr = 0x20         #The I2C address of the device (0x20)
    conf_addr = 0x03    
    write_addr = 0x01   
    output_data = 0xFD      #Turn off all LEDs

    try:
        if i2c_device_detected(dev_addr):
            bus = smbus.SMBus(1)
            bus.write_byte_data(dev_addr, conf_addr, 0x00)

            for value in led_values:
                bus.write_byte_data(dev_addr, write_addr, value)
                #TODO: ledler arası bekleme süresini ayarla
                time.sleep(5)
                bus.write_byte_data(dev_addr, write_addr, output_data)

            while True:
                #TODO: user_inputu yorum satırından çıkar
                user_input = input(f"{fore_white}LED'leri Kontrol Edin. Tüm LED'ler yanıyorsa{fore_blue}{italic} E {reset}{fore_white}yanmıyorsa{fore_red}{italic} H {reset}{fore_white}giriniz: {reset}")
                #user_input = 'E'
                if user_input.upper() == 'E':
                    return True
                elif user_input.upper() == 'H':
                    return False
                else:
                    logger.warning("Invalid input. Please enter 'E' or 'H'.")
        else:
            return False
    except Exception as e:
        logger.error(f"Error testing LED: {e}")
        return False
    
def check_button_pressed(button_pin, timeout = 10):
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
    except Exception as e:
        logger.error(f"Error checking button press: {e}")
    finally:
        GPIO.cleanup()
    
    return button_pressed


def rtc():
    try:
        i2cdetect_result = subprocess.run(['i2cdetect', '-y', '0'], stdout=subprocess.PIPE)
        i2cdetect_output = i2cdetect_result.stdout.decode('utf-8')
        if 'UU' in i2cdetect_output or '51' in i2cdetect_output:
            return True
        else:
            return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Error checking RTC: {e}")
        return False

def tbm():
    try:
        os.chdir("/home/pi/ws/tbm/eltt2")
        response = subprocess.check_output(['sudo', './eltt2', '-g']).decode("utf8")
        check_tbm = "TPM_PT_FAMILY_INDICATOR:"
        if check_tbm in response:
            return True
        else:
            return False
    except Exception as e:
    #except subprocess.CalledProcessError as e:
        logger.error(f"Error checking TBM: {e}")
        return False

def uspc_pd(address):
    return i2c_device_detected(address)

def currentsensor(address):
    return i2c_device_detected(address)

def adc(address):
    return i2c_device_detected(address)

def cellular_modem():
    for attempt in range(10):
            try:
                output = subprocess.run(['lsusb'], stdout=subprocess.PIPE).stdout.decode('utf-8')
                check_module_vid_pid = "2c7c:0125"
                if check_module_vid_pid in output:
                    return True
                else:
                    return False
            except subprocess.CalledProcessError as e:
                logger.error(f"Error checking cellular modem: {e}")
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
                    return 0
            except subprocess.CalledProcessError as e:
                logger.error(f"Error getting ICCID: {e}")
                return 0
    else:
        return 0 
    
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
                    return 0
            except subprocess.CalledProcessError as e:
                logger.error(f"Error getting IMEI: {e}")
                return 0         
    else:
        return 0
    
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
                    return 0
            except subprocess.CalledProcessError as e:
                logger.error(f"Error getting firmware: {e}")
                return 0
    else:
        return 0           
    
def main():
    try:
        connection = sqlite3.connect('results.db')
        cursor = connection.cursor()
        print(f"{back_black}{fore_yellow}Ledlerin yanıp yanmadığını kontrol ediniz{reset}")
        result_led = test_led()
        print(f"{back_black}{fore_yellow}10 saniye içinde USER BUTTON basınız{reset}")
        #TODO: check_button_pressed(5, 1) bekleme süresini ayarla
        result_usrbtn = check_button_pressed(5, 10) #User button
        print(f"{back_black}{fore_yellow}10 saniye içinde RESET BUTTON basınız{reset}")
        #TODO: check_button_pressed(5, 1) bekleme süresini ayarla
        result_rstbtn = check_button_pressed(6, 10) #Reset button
        result_rtc = rtc()
        result_tbm = tbm()
        result_tmpsnsr = i2c_device_detected(i2cadresss_tmpsnsr)
        result_uspc = i2c_device_detected(i2cadresss_uspc)
        result_cr = i2c_device_detected(i2cadresss_cr)
        result_adc = i2c_device_detected(i2cadresss_adc)
        result_cellular = cellular_modem()
        if result_cellular: 
            result_iccid = get_iccid()
            result_imei = get_imei()
            result_firmware = get_firmware()
        else:
            result_iccid = "0"
            result_imei = "0"
            result_firmware = "0"
        logger.info(f"Results: {result_led}, {result_usrbtn}, {result_rstbtn}, {result_rtc}, {result_tbm}, {result_tmpsnsr}, {result_uspc}, {result_cr}, {result_adc}, {result_cellular}, {result_iccid}, {result_imei}, {result_firmware}")
        cursor.execute('''INSERT INTO tablo (led, usrbtn, rstbtn, rtc, tbm, tmpsnsr, uspc, cr, adc, cellular, iccid, imei, firmware)
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
                       (result_led, result_usrbtn, result_rstbtn, result_rtc, result_tbm, result_tmpsnsr, result_uspc, result_cr, result_adc, result_cellular, result_iccid, result_imei, result_firmware))
        connection.commit()
    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
    finally:
        connection.close()

if __name__ == "__main__":
    main()