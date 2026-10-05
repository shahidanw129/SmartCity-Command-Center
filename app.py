import os, sqlite3, csv, io
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash

BASE=os.path.abspath(os.path.dirname(__file__))
DB=os.path.join(BASE,"smartcity.db")
app=Flask(__name__)
app.secret_key=os.environ.get("SECRET_KEY","change-this-secret-key-before-deploying")
app.config["MAX_CONTENT_LENGTH"]=5*1024*1024

def conn():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init_db():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT DEFAULT 'operator');
        CREATE TABLE IF NOT EXISTS incidents(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, category TEXT NOT NULL, severity TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Reported', location TEXT, lat REAL, lng REAL, description TEXT, reporter TEXT, assigned_to TEXT, created_at TEXT, updated_at TEXT);
        CREATE TABLE IF NOT EXISTS activity(id INTEGER PRIMARY KEY AUTOINCREMENT, message TEXT, created_at TEXT);
        """)
        if not c.execute("SELECT id FROM users WHERE username='admin'").fetchone():
            c.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)",("admin",generate_password_hash(os.environ.get("ADMIN_PASSWORD","Admin@123")),"admin"))
        if c.execute("SELECT COUNT(*) n FROM incidents").fetchone()["n"]==0:
            samples=[
            ("Road accident near CG Road","Accident","Critical","Dispatched","CG Road, Ahmedabad",23.026,72.561,"Two-vehicle collision reported. Medical response requested.","Demo Citizen","Rapid Response"),
            ("Water leakage in residential lane","Water","High","In Progress","Navrangpura, Ahmedabad",23.039,72.562,"Continuous water leakage reported by resident.","Demo Citizen","Water Department"),
            ("Traffic congestion at junction","Traffic","Medium","Reported","Ashram Road, Ahmedabad",23.036,72.575,"Heavy congestion during peak hour.","Traffic Sensor","Traffic Unit"),
            ("Streetlight outage","Infrastructure","Low","Resolved","Satellite, Ahmedabad",23.026,72.510,"Streetlight not functioning.","Demo Citizen","Electricity Team"),
            ("Garbage overflow","Sanitation","Medium","In Progress","Maninagar, Ahmedabad",22.997,72.601,"Overflowing community bin.","Field Officer","Sanitation Team")]
            now=datetime.now().isoformat(timespec="seconds")
            for s in samples:
                c.execute("""INSERT INTO incidents(title,category,severity,status,location,lat,lng,description,reporter,assigned_to,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",(*s,now,now))
            c.execute("INSERT INTO activity(message,created_at) VALUES(?,?)",("Demo incident data initialized",now))
def log(message):
    with conn() as c:c.execute("INSERT INTO activity(message,created_at) VALUES(?,?)",(message,datetime.now().isoformat(timespec="seconds")))
def login_required(f):
    @wraps(f)
    def w(*a,**k):
        if "user" not in session: return redirect(url_for("login",next=request.path))
        return f(*a,**k)
    return w
@app.context_processor
def common():
    return {"current_user":session.get("user"),"current_role":session.get("role")}
@app.route("/")
def index():
    if "user" in session:return redirect(url_for("dashboard"))
    return render_template("login.html")
@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        u=request.form.get("username","").strip(); p=request.form.get("password","")

        # Academic demo mode: accept any non-empty username/email and password.
        # This keeps the project easy to demonstrate without requiring account setup.
        # It is intentionally NOT suitable for a production authentication system.
        if u and p:
            with conn() as c:
                row=c.execute("SELECT * FROM users WHERE username=?",(u,)).fetchone()
                if not row:
                    c.execute(
                        "INSERT INTO users(username,password,role) VALUES(?,?,?)",
                        (u,generate_password_hash(p),"operator")
                    )
                    role="operator"
                else:
                    role=row["role"]

            session["user"]=u
            session["role"]=role
            log(f"{u} signed in (demo access)")
            return redirect(request.args.get("next") or url_for("dashboard"))

        flash("Please enter both username/email and password.","danger")
    return render_template("login.html")
@app.route("/logout")
def logout():
    session.clear();return redirect(url_for("login"))
@app.route("/dashboard")
@login_required
def dashboard():
    with conn() as c:
        rows=c.execute("SELECT * FROM incidents ORDER BY id DESC LIMIT 6").fetchall()
        allr=c.execute("SELECT severity,status,category FROM incidents").fetchall()
        activity=c.execute("SELECT * FROM activity ORDER BY id DESC LIMIT 6").fetchall()
    return render_template("dashboard.html",recent=rows,stats=stats(allr),activity=activity)
def stats(rows):
    return {"total":len(rows),"critical":sum(r["severity"]=="Critical" for r in rows),"active":sum(r["status"] not in ("Resolved","Closed") for r in rows),"resolved":sum(r["status"] in ("Resolved","Closed") for r in rows),
    "by_category":{k:sum(r["category"]==k for r in rows) for k in sorted(set(r["category"] for r in rows))}}
@app.route("/incidents")
@login_required
def incidents():
    q=request.args.get("q","").strip(); status=request.args.get("status",""); severity=request.args.get("severity","")
    sql="SELECT * FROM incidents WHERE 1=1"; args=[]
    if q: sql+=" AND (title LIKE ? OR location LIKE ? OR category LIKE ?)";args += [f"%{q}%"]*3
    if status:sql+=" AND status=?";args.append(status)
    if severity:sql+=" AND severity=?";args.append(severity)
    sql+=" ORDER BY CASE severity WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END, id DESC"
    with conn() as c: rows=c.execute(sql,args).fetchall()
    return render_template("incidents.html",incidents=rows,q=q,status=status,severity=severity)
@app.route("/incidents/new",methods=["GET","POST"])
@login_required
def new_incident():
    if request.method=="POST":
        title=request.form.get("title","").strip();cat=request.form.get("category","Other");sev=request.form.get("severity","Medium")
        if not title:flash("Incident title is required","danger")
        else:
            now=datetime.now().isoformat(timespec="seconds")
            try:lat=float(request.form.get("lat") or 0);lng=float(request.form.get("lng") or 0)
            except ValueError:lat=lng=0
            with conn() as c:c.execute("""INSERT INTO incidents(title,category,severity,status,location,lat,lng,description,reporter,assigned_to,created_at,updated_at)
            VALUES(?,?,?,'Reported',?,?,?,?,?,?,?,?)""",(title,cat,sev,request.form.get("location",""),lat,lng,request.form.get("description",""),session["user"],request.form.get("assigned_to","Unassigned"),now,now))
            log(f"New {sev.lower()} incident reported: {title}");flash("Incident reported successfully","success");return redirect(url_for("incidents"))
    return render_template("incident_form.html")
@app.route("/incidents/<int:iid>",methods=["GET","POST"])
@login_required
def incident_detail(iid):
    with conn() as c: item=c.execute("SELECT * FROM incidents WHERE id=?",(iid,)).fetchone()
    if not item:return "Incident not found",404
    if request.method=="POST":
        status=request.form.get("status",item["status"]);assignee=request.form.get("assigned_to",item["assigned_to"])
        now=datetime.now().isoformat(timespec="seconds")
        with conn() as c:c.execute("UPDATE incidents SET status=?,assigned_to=?,updated_at=? WHERE id=?",(status,assignee,now,iid))
        log(f"Incident #{iid} updated to {status}");flash("Incident updated","success");return redirect(url_for("incident_detail",iid=iid))
    return render_template("incident_detail.html",item=item)
@app.route("/map")
@login_required
def city_map():
    with conn() as c: rows=c.execute("SELECT * FROM incidents WHERE lat IS NOT NULL AND lng IS NOT NULL AND lat!=0 AND lng!=0").fetchall()
    return render_template("map.html",points=[dict(r) for r in rows])
@app.route("/analytics")
@login_required
def analytics():
    with conn() as c: rows=c.execute("SELECT * FROM incidents").fetchall()
    s=stats(rows)
    severity={k:sum(r["severity"]==k for r in rows) for k in ["Critical","High","Medium","Low"]}
    statuses={k:sum(r["status"]==k for r in rows) for k in ["Reported","Dispatched","In Progress","Resolved","Closed"]}
    return render_template("analytics.html",stats=s,severity=severity,statuses=statuses)
@app.route("/teams")
@login_required
def teams():
    teams=[("Rapid Response","Emergency","Available","3 units"),("Traffic Unit","Traffic","On duty","5 units"),("Water Department","Utilities","On duty","2 crews"),("Sanitation Team","Public works","Available","4 crews"),("Medical Response","Healthcare","Standby","2 ambulances"),("Electricity Team","Infrastructure","On duty","3 crews")]
    return render_template("teams.html",teams=teams)
@app.route("/services")
@login_required
def services():
    items=[("Traffic & Mobility","Congestion reports, route impact and traffic-unit coordination","traffic-cone"),("Water & Utilities","Leakage, outage and infrastructure issue tracking","droplets"),("Public Safety","Incident intake, triage and response coordination","shield-check"),("Sanitation","Waste overflow and cleanliness issue management","recycle"),("Emergency Response","Priority queues, dispatch tracking and escalation","siren"),("Citizen Services","Community reporting and transparent status updates","users")]
    return render_template("services.html",items=items)
@app.route("/reports")
@login_required
def reports():return render_template("reports.html")
@app.route("/reports/export.csv")
@login_required
def export_csv():
    with conn() as c: rows=c.execute("SELECT id,title,category,severity,status,location,description,reporter,assigned_to,created_at,updated_at FROM incidents ORDER BY id DESC").fetchall()
    out=io.StringIO();w=csv.writer(out);w.writerow(rows[0].keys() if rows else ["id","title","category","severity","status","location","description","reporter","assigned_to","created_at","updated_at"])
    for r in rows:w.writerow(list(r))
    res=make_response(out.getvalue());res.headers["Content-Disposition"]="attachment; filename=smartcity_incidents.csv";res.headers["Content-Type"]="text/csv";return res
@app.route("/settings",methods=["GET","POST"])
@login_required
def settings():
    if request.method=="POST":
        old=request.form.get("old_password","");new=request.form.get("new_password","")
        with conn() as c:row=c.execute("SELECT * FROM users WHERE username=?",(session["user"],)).fetchone()
        if not check_password_hash(row["password"],old):flash("Current password is incorrect","danger")
        elif len(new)<8:flash("New password must contain at least 8 characters","danger")
        else:
            with conn() as c:c.execute("UPDATE users SET password=? WHERE username=?",(generate_password_hash(new),session["user"]))
            flash("Password updated","success")
    return render_template("settings.html")
@app.route("/api/summary")
@login_required
def api_summary():
    with conn() as c:rows=c.execute("SELECT severity,status,category FROM incidents").fetchall()
    return jsonify(stats(rows))
@app.errorhandler(413)
def too_large(e):return "Upload/request too large (limit 5 MB).",413
@app.route("/health")
def health():return jsonify(status="ok",service="Smart City Command Center")
init_db()
if __name__=="__main__":app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)),debug=False)
