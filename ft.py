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
import yaml

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

result_dict = {
    "test_result": "FAIL",
    "result_led": False,
    "result_usrbtn": False,
    "result_rstbtn": False,
    "result_rtc": False,
    "result_tbm": False,
    "result_tmpsnsr": False,
    "result_uspc": False,
    "result_cr": False,
    "result_adc": False,
    "result_cellular": False,
    "result_iccid": "0",
    "result_imei": "0",
    "result_firmware": "0",
    "result_eth0": False,
    "result_eth1": False,
    "result_usb": False
}

with open("/home/pi/c40_functionaltest/config.yaml", "r") as file:
    config = yaml.safe_load(file)

operator_prefix = config['settings']['operator_prefix']
desk_prefix = config['settings']['desk_prefix']
device_prefix = config['settings']['device_prefix']
tbm_indicator = config['settings']['tbm_indicator']
modem_vid_pid = config['settings']['modem_vid_pid']
firmware_keyword = config['settings']['firmware_keyword']
usb_list = config['settings']['check_usb']


def operator_qr():
    while True:
        operator = input("Operator QR okutunuz: ")
        if operator.startswith(operator_prefix):
            return operator
        else:
            print("Geçerisiz QR girdiniz. Lütfen Operator QR giriniz:")

def desk_qr():
    while True:
        desk = input("Masa QR okutunuz: ")
        if desk.startswith(desk_prefix):
            return desk
        else:
            print("Geçerisiz QR girdiniz. Lütfen MASA QR giriniz:")

def pcb_qr_on():
    while True:
        pcb = input("Device QR ön tarafı okutunuz: ")
        #TODO: device qr kontrolünü değiştir
        if pcb.startswith(device_prefix):
            return pcb
        else:
            #TODO: Uyarı yazısı ekle
            print("Geçerisiz QR girdiniz. Lütfen tekrar QR giriniz:")

def pcb_qr_arka():
    while True:
        pcb = input("Device QR arka tarafı okutunuz: ")
        #TODO: device qr kontrolünü değiştir
        if pcb.startswith(device_prefix):
            return pcb
        else:
            #TODO: Uyarı yazısı ekle
            print("Geçerisiz QR girdiniz. Lütfen tekrar QR giriniz:")

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
                time.sleep(3)
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
        if tbm_indicator in response:
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
                if modem_vid_pid in output:
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
                if firmware_keyword in firmware:
                    return firmware
                else:
                    return 0
            except subprocess.CalledProcessError as e:
                logger.error(f"Error getting firmware: {e}")
                return 0
    else:
        return 0           

def check_eth(eth_no,speed):
    try:
        response = subprocess.check_output(["sudo","ethtool",eth_no]).decode("utf8")
        check_speed =  "Speed: " + speed +  "Mb/s"
        #print(check_speed)
        if check_speed in response:
            return True
        else:
            return False
    except subprocess.CalledProcessError as e:
            logger.error(f"Error getting Ethernet: {e}")
            return False
"""
def check_usb():
    try:
        usb_list = config['settings']['check_usb']
        response = subprocess.check_output(["lsusb"]).decode("utf8")

        for check_usb in usb_list:
            if check_usb not in response:
                return False
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error getting USB devices: {e}")
        return False
    except Exception as e:
        logger.error(f"Error: {e}")
        return False
"""

def check_usb():
    try:
        usb_list = "067b:2303"
        response = subprocess.check_output(["lsusb"]).decode("utf8")
        #print(response)
        if response.count(usb_list) >= 2:
            return True
        else:
            return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Error getting USB devices: {e}")
        return False
    except Exception as e:
        logger.error(f"Error: {e}")
        return False
    
def main():
    try:
        result_operator = operator_qr()
        result_desk = desk_qr()
        result_pcb_on = pcb_qr_on()
        result_pcb_arka = pcb_qr_arka()
        connection = sqlite3.connect('results.db')
        cursor = connection.cursor()
        print(f"{back_black}{fore_yellow}Ledlerin yanıp yanmadığını kontrol ediniz{reset}")
        result_dict["result_led"] = test_led()
        print(f"{back_black}{fore_yellow}10 saniye içinde USER BUTTON basınız{reset}")
        result_dict["result_usrbtn"] = check_button_pressed(5, 10) # User button
        print(f"{back_black}{fore_yellow}10 saniye içinde RESET BUTTON basınız{reset}")
        result_dict["result_rstbtn"] = check_button_pressed(6, 10) # Reset button
        result_dict["result_rtc"] = rtc()
        result_dict["result_tbm"] = tbm()
        result_dict["result_tmpsnsr"] = i2c_device_detected(i2cadresss_tmpsnsr)
        result_dict["result_uspc"] = i2c_device_detected(i2cadresss_uspc)
        result_dict["result_cr"] = i2c_device_detected(i2cadresss_cr)
        result_dict["result_adc"] = i2c_device_detected(i2cadresss_adc)
        result_dict["result_cellular"] = cellular_modem()
        result_dict["result_eth0"] = check_eth("eth0","1000")
        result_dict["result_eth1"] = check_eth("eth1","100")
        result_dict["result_usb"] = check_usb()
        
        if result_dict["result_cellular"]: 
            result_dict["result_iccid"] = get_iccid()
            result_dict["result_imei"] = get_imei()
            result_dict["result_firmware"] = get_firmware()
        else:
            result_dict["result_iccid"] = "0"
            result_dict["result_imei"] = "0"
            result_dict["result_firmware"] = "0"
            
        failed_keys = [key for key, value in result_dict.items() if value is False or value == 0]
        print(failed_keys)
        
        if not failed_keys:
            print("TEST BAŞARILI")
            result_dict["test_result"] = "PASS"
            print(result_dict["test_result"])
            logger.info(f"Results: {result_operator}, {result_desk}, {result_pcb_on}, {result_pcb_arka}, {result_dict['test_result']}, {result_dict['result_led']}, {result_dict['result_usrbtn']}, "
            f"{result_dict['result_rstbtn']}, {result_dict['result_rtc']}, {result_dict['result_tbm']}, "
            f"{result_dict['result_tmpsnsr']}, {result_dict['result_uspc']}, {result_dict['result_cr']}, {result_dict['result_adc']}, "
            f"{result_dict['result_cellular']}, {result_dict['result_iccid']}, {result_dict['result_imei']}, {result_dict['result_firmware']}, "
            f"{result_dict['result_eth0']}, {result_dict['result_eth1']}, {result_dict['result_usb']}")
            cursor.execute('''INSERT INTO tablo (operator, desk, pcb, pcb_arka, test_result, led, usrbtn, rstbtn, rtc, tbm, tmpsnsr, uspc, cr, adc, cellular, iccid, imei, firmware, eth0, eth1, usb)
                          VALUES (?,?,?,?,?,
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
                                ?,?,?,
                                CASE WHEN ? THEN 'True' ELSE 'False' END,
                                CASE WHEN ? THEN 'True' ELSE 'False' END,
                                CASE WHEN ? THEN 'True' ELSE 'False' END)''', 
                       (result_operator, result_desk, result_pcb_on, result_pcb_arka, result_dict["test_result"], result_dict["result_led"], 
                        result_dict["result_usrbtn"], result_dict["result_rstbtn"], result_dict["result_rtc"], 
                        result_dict["result_tbm"], result_dict["result_tmpsnsr"], result_dict["result_uspc"], 
                        result_dict["result_cr"], result_dict["result_adc"], result_dict["result_cellular"], 
                        result_dict["result_iccid"], result_dict["result_imei"], result_dict["result_firmware"], 
                        result_dict["result_eth0"], result_dict["result_eth1"], result_dict["result_usb"]))
            connection.commit()
        else:
            if "result_cellular" not in failed_keys and ("result_iccid" in failed_keys or "result_imei" in failed_keys):
                print("IMEI ya da ICCID bulunamadı")
    
            test_failure_keys = [
                "result_led", "result_usrbtn", "result_rstbtn", "result_rtc",
                "result_tbm", "result_tmpsnsr", "result_uspc", "result_cr",
                "result_adc", "result_cellular", "result_eth0", "result_firmware",
                "result_eth1", "result_usb"
            ]
    
            failed_test_keys = [key for key in test_failure_keys if key in failed_keys]
    
            if failed_test_keys:
                result_dict["test_result"] = "FAIL"
                print(result_dict["test_result"])
                logger.info(f"Results: {result_operator}, {result_desk}, {result_pcb_on}, {result_pcb_arka}, {result_dict['test_result']}, {result_dict['result_led']}, {result_dict['result_usrbtn']}, "
                f"{result_dict['result_rstbtn']}, {result_dict['result_rtc']}, {result_dict['result_tbm']}, "
                f"{result_dict['result_tmpsnsr']}, {result_dict['result_uspc']}, {result_dict['result_cr']}, {result_dict['result_adc']}, "
                f"{result_dict['result_cellular']}, {result_dict['result_iccid']}, {result_dict['result_imei']}, {result_dict['result_firmware']}, "
                f"{result_dict['result_eth0']}, {result_dict['result_eth1']}, {result_dict['result_usb']}")
                cursor.execute('''INSERT INTO tablo (operator, desk, pcb, pcb_arka, test_result, led, usrbtn, rstbtn, rtc, tbm, tmpsnsr, uspc, cr, adc, cellular, iccid, imei, firmware, eth0, eth1, usb)
                            VALUES (?,?,?,?,?,
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
                                ?,?,?,
                                CASE WHEN ? THEN 'True' ELSE 'False' END,
                                CASE WHEN ? THEN 'True' ELSE 'False' END,
                                CASE WHEN ? THEN 'True' ELSE 'False' END)''', 
                        (result_operator, result_desk, result_pcb_on, result_pcb_arka, result_dict["test_result"], result_dict["result_led"], 
                        result_dict["result_usrbtn"], result_dict["result_rstbtn"], result_dict["result_rtc"], 
                        result_dict["result_tbm"], result_dict["result_tmpsnsr"], result_dict["result_uspc"], 
                        result_dict["result_cr"], result_dict["result_adc"], result_dict["result_cellular"], 
                        result_dict["result_iccid"], result_dict["result_imei"], result_dict["result_firmware"], 
                        result_dict["result_eth0"], result_dict["result_eth1"], result_dict["result_usb"]))
                connection.commit()
                print("TEST BAŞARISIZ")
                for key in failed_test_keys:
                    print(key)

    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
    finally:
        connection.close()

if __name__ == "__main__":
    main()