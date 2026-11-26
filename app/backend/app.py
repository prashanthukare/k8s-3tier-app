# Backend API for the 3-tier Kubernetes app.
# It counts page visits and stores the count in the MySQL database.
import os
import time

import mysql.connector
from flask import Flask, jsonify

app = Flask(__name__)

# These values come from the ConfigMap and Secret in the k8s/ folder.
DB_HOST = os.environ.get("DB_HOST", "mysql-service")
DB_NAME = os.environ.get("DB_NAME", "appdb")
DB_USER = os.environ.get("DB_USER", "appuser")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")


def get_connection():
    # Retry for up to 60 seconds: the database pod may still be starting.
    for _ in range(30):
        try:
            return mysql.connector.connect(
                host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
            )
        except mysql.connector.Error:
            time.sleep(2)
    raise RuntimeError("Could not connect to the database")


def ensure_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS visits (id INT PRIMARY KEY, count INT NOT NULL)")
    cur.execute("INSERT IGNORE INTO visits (id, count) VALUES (1, 0)")
    conn.commit()
    cur.close()
    conn.close()


ensure_table()


@app.route("/api/health")
def health():
    # Used by the Kubernetes liveness and readiness probes.
    return jsonify(status="ok")


@app.route("/api/visits")
def visits():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE visits SET count = count + 1 WHERE id = 1")
    conn.commit()
    cur.execute("SELECT count FROM visits WHERE id = 1")
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return jsonify(visits=count)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
