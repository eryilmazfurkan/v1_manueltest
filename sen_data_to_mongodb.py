import os
import time
import yaml
import sqlite3
from pymongo import MongoClient

os.chdir('/home/pi/c40_functionaltest')

def load_config():
    config_file = 'config.yaml'
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    return config

def check_internet():
    try:
        response = os.system("ping -c 1 8.8.8.8")
        if response == 0:
            return True
        else:
            return False
    except:
        return False

def transfer_data(config):
    db_file = config['sqlite_db_path']
    mongo_uri = config['mongodb']['uri']
    mongo_db_name = config['mongodb']['database_name']
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    table_info = {}
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        table_info[table_name] = {
            'column_count': len(columns),
            'column_names': column_names
        }

    conn.close()

    client = MongoClient(mongo_uri)
    db = client[mongo_db_name]

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    for table_name, info in table_info.items():
        collection_name = table_name
        columns = info['column_names']
        
        collection = db[collection_name]
        
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        for row in rows:
            document = {columns[i]: row[i] for i in range(len(columns))}
            collection.insert_one(document)
            
            where_clause = " AND ".join([f"{columns[i]} = ?" for i in range(len(columns))])
            cursor.execute(f"DELETE FROM {table_name} WHERE {where_clause}", row)
            conn.commit()

    conn.close()

    print("Veriler başarıyla MongoDB'ye aktarıldı ve SQLite veritabanından silindi.")

def main():
    config = load_config()
    while True:
        if check_internet():
            transfer_data(config)
        time.sleep(60)

if __name__ == "__main__":
    main()
