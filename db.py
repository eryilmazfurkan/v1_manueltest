import sqlite3

connection = sqlite3.connect('results.db')
cursor = connection.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS tablo (
                    id INTEGER PRIMARY KEY,
                    led BOOLEAN NOT NULL,
                    usrbtn BOOLEAN NOT NULL,
                    rstbtn BOOLEAN NOT NULL,
                    rtc BOOLEAN NOT NULL,
                    tpm BOOLEAN NOT NULL,
                    tmpsnsr BOOLEAN NOT NULL,
                    uspc BOOLEAN NOT NULL,
                    cr BOOLEAN NOT NULL,
                    adc BOOLEAN NOT NULL,
                    cellular BOOLEAN NOT NULL,
                    iccid TEXT NOT NULL,
                    imei TEXT NOT NULL,
                    firmware TEXT NULL
                )''')