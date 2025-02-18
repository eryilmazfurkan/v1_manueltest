import sqlite3

connection = sqlite3.connect('results.db')
cursor = connection.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS tablo (
                    id INTEGER PRIMARY KEY,
                    test_result TEXT NOT NULL,
                    operator TEXT NOT NULL, 
                    desk TEXT NOT NULL,
                    pcb TEXT NOT NULL,
                    pcb_arka TEXT NOT NULL,
                    led BOOLEAN NOT NULL,
                    usrbtn BOOLEAN NOT NULL,
                    rstbtn BOOLEAN NOT NULL,
                    rtc BOOLEAN NOT NULL,
                    tbm BOOLEAN NOT NULL,
                    tmpsnsr BOOLEAN NOT NULL,
                    uspc BOOLEAN NOT NULL,
                    cr BOOLEAN NOT NULL,
                    adc BOOLEAN NOT NULL,
                    cellular BOOLEAN NOT NULL,
                    iccid TEXT NOT NULL,
                    imei TEXT NOT NULL,
                    firmware TEXT NULL,
                    eth0 TEXT NULL,
                    eth1 TEXT NULL,
                    usb TEXT NULL
                )''')