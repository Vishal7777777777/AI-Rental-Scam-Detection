import json, os
from datetime import datetime
from decimal import Decimal
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from mysql.connector import Error
from db import get_connection, init_db
from ml_model import analyze_listing

load_dotenv()
app=Flask(__name__)
CORS(app, resources={r"/api/*":{"origins":"*"}})

def serial(row):
    out=dict(row)
    for k,v in out.items():
        if isinstance(v, Decimal): out[k]=float(v)
        elif isinstance(v, datetime): out[k]=v.isoformat()
        elif k=="signals" and isinstance(v,str):
            try: out[k]=json.loads(v)
            except ValueError: out[k]=[]
    return out

def fetch(query, params=()):
    conn=get_connection(); cur=conn.cursor(dictionary=True); cur.execute(query,params)
    rows=cur.fetchall(); cur.close(); conn.close()
    return [serial(x) for x in rows]

@app.get("/api/health")
def health():
    try:
        conn=get_connection(); cur=conn.cursor(); cur.execute("SELECT 1"); cur.fetchone()
        cur.close(); conn.close()
        return jsonify({"status":"ok","database":"connected","model":"loaded"})
    except Error as e: return jsonify({"status":"error","database":"disconnected","message":str(e)}),503

@app.get("/api/stats")
def stats():
    try:
        a=fetch("SELECT COUNT(*) total, COALESCE(SUM(risk_level='High'),0) high_risk, COALESCE(SUM(risk_level='Medium'),0) medium_risk, COALESCE(SUM(risk_level='Low'),0) low_risk FROM listings")[0]
        b=fetch("SELECT COUNT(*) total_reports, COALESCE(SUM(status='Pending'),0) pending_reports FROM reports")[0]
        return jsonify({**a,**b})
    except Error as e: return jsonify({"error":str(e)}),503

@app.get("/api/listings")
def listings():
    search=request.args.get("search","").strip(); risk=request.args.get("risk","").strip()
    q="SELECT * FROM listings WHERE 1=1"; p=[]
    if search:
        q+=" AND (title LIKE %s OR description LIKE %s OR location LIKE %s)"
        s=f"%{search}%"; p.extend([s,s,s])
    if risk in ("Low","Medium","High"): q+=" AND risk_level=%s"; p.append(risk)
    q+=" ORDER BY created_at DESC LIMIT 100"
    try: return jsonify(fetch(q,tuple(p)))
    except Error as e: return jsonify({"error":str(e)}),503

@app.post("/api/analyze")
def analyze():
    d=request.get_json(silent=True) or {}
    title=str(d.get("title","")).strip(); description=str(d.get("description","")).strip()
    location=str(d.get("location","")).strip(); currency=str(d.get("currency","INR")).strip().upper()[:10] or "INR"
    contact=str(d.get("contact_method","")).strip()
    if not title or not description: return jsonify({"error":"Title and description are required."}),400
    if len(title)>200 or len(description)>10000: return jsonify({"error":"Title max 200 characters; description max 10,000."}),400
    try:
        rent=float(d["monthly_rent"]) if d.get("monthly_rent") not in (None,"") else None
        if rent is not None and rent<0: raise ValueError()
    except (ValueError,TypeError): return jsonify({"error":"Monthly rent must be a non-negative number."}),400
    result=analyze_listing(title,description,location,rent,currency,contact)
    try:
        conn=get_connection(); cur=conn.cursor()
        cur.execute("""INSERT INTO listings (title,description,location,monthly_rent,currency,contact_method,risk_score,risk_level,prediction,signals)
          VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
          (title,description,location,rent,currency,contact,result["risk_score"],result["risk_level"],result["prediction"],json.dumps(result["signals"])))
        conn.commit(); ident=cur.lastrowid; cur.close(); conn.close()
        return jsonify({"id":ident,"title":title,"description":description,"location":location,"monthly_rent":rent,"currency":currency,"contact_method":contact,**result}),201
    except Error as e: return jsonify({"error":f"Could not save analysis to MySQL: {e}"}),503

@app.post("/api/reports")
def create_report():
    d=request.get_json(silent=True) or {}; ident=d.get("listing_id")
    reason=str(d.get("reason","")).strip(); details=str(d.get("details","")).strip()
    allowed={"Suspicious payment request","Fake or copied photos","Incorrect property details","Other"}
    if not isinstance(ident,int) or reason not in allowed: return jsonify({"error":"Choose a valid listing and report reason."}),400
    try:
        conn=get_connection(); cur=conn.cursor(); cur.execute("SELECT id FROM listings WHERE id=%s",(ident,))
        if not cur.fetchone(): cur.close(); conn.close(); return jsonify({"error":"Listing analysis not found."}),404
        cur.execute("INSERT INTO reports (listing_id,reason,details) VALUES (%s,%s,%s)",(ident,reason,details[:2000]))
        conn.commit(); rid=cur.lastrowid; cur.close(); conn.close()
        return jsonify({"id":rid,"status":"Pending","message":"Report submitted for review."}),201
    except Error as e: return jsonify({"error":str(e)}),503

@app.get("/api/reports")
def reports():
    try:
        return jsonify(fetch("""SELECT r.id,r.listing_id,r.reason,r.details,r.status,r.created_at,l.title
          FROM reports r JOIN listings l ON l.id=r.listing_id ORDER BY r.created_at DESC LIMIT 100"""))
    except Error as e: return jsonify({"error":str(e)}),503

if __name__=="__main__":
    try:
        init_db(); print("MySQL connected successfully; tables are ready.")
    except Error as e:
        print("MySQL connection failed. Check MySQL service, database, and backend/.env credentials.")
        print(f"Details: {e}"); raise SystemExit(1)
    app.run(host=os.getenv("FLASK_HOST","127.0.0.1"),port=int(os.getenv("FLASK_PORT","5000")),debug=os.getenv("FLASK_DEBUG","true").lower()=="true")
