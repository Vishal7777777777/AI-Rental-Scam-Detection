import os
import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv
load_dotenv()
_pool = None

def get_connection():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="rentshield_pool", pool_size=5,
            host=os.getenv("DB_HOST","localhost"), port=int(os.getenv("DB_PORT","3306")),
            user=os.getenv("DB_USER","root"), password=os.getenv("DB_PASSWORD",""),
            database=os.getenv("DB_NAME","rental_scam_db"))
    return _pool.get_connection()

def init_db():
    conn=get_connection(); cur=conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS listings (
      id INT AUTO_INCREMENT PRIMARY KEY, title VARCHAR(200) NOT NULL, description TEXT NOT NULL,
      location VARCHAR(200) DEFAULT '', monthly_rent DECIMAL(12,2) DEFAULT NULL,
      currency VARCHAR(10) NOT NULL DEFAULT 'INR', contact_method VARCHAR(100) DEFAULT '',
      risk_score INT NOT NULL DEFAULT 0, risk_level VARCHAR(20) NOT NULL DEFAULT 'Low',
      prediction VARCHAR(30) NOT NULL DEFAULT 'Likely legitimate', signals JSON NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      INDEX idx_listings_risk (risk_level), INDEX idx_listings_created (created_at)) ENGINE=InnoDB""")
    cur.execute("""CREATE TABLE IF NOT EXISTS reports (
      id INT AUTO_INCREMENT PRIMARY KEY, listing_id INT NOT NULL, reason VARCHAR(120) NOT NULL,
      details TEXT DEFAULT NULL, status VARCHAR(30) NOT NULL DEFAULT 'Pending',
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      CONSTRAINT fk_reports_listing FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE,
      INDEX idx_reports_status (status)) ENGINE=InnoDB""")
    conn.commit(); cur.close(); conn.close()
