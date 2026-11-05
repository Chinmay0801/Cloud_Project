"""CourtBook: sports court slot booking for a college campus (Flask + SQLite)."""
import math
import os
import platform
import sqlite3
import threading
import time
import urllib.request
from collections import defaultdict, deque
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from flask import Flask, Response, g, jsonify, render_template, request

app = Flask(__name__)

# ---------------------------------------------------------------- configuration

COURTS = ["Badminton Court 1", "Badminton Court 2", "Table Tennis", "Gym"]
SLOT_TIMES = [f"{h:02d}:{m}" for h in range(6, 22) for m in ("00", "30")]  # 6:00 AM - 10:00 PM
BOOKING_DAYS = 3  # today and the next 2 days
DAILY_LIMIT = 2
MAX_CONCURRENT = int(os.environ.get("MAX_CONCURRENT", 20))

SLO_MS = 500
SLA_TARGET = 99.9
HEALTH_INTERVAL = 30  # seconds
RESPONSE_WINDOW = 50000  # response times kept in memory

MSG_TAKEN = "Slot just taken by someone else – please pick another"
MSG_DAILY_LIMIT = "Daily limit reached – admission denied"
MSG_BUSY = "Server busy – try again"
MSG_PAST = "This slot has already started – please pick a later one"

# Azure runs in UTC, so "past slot" is judged in campus time. Default is IST.
CAMPUS_TZ = timezone(timedelta(minutes=int(os.environ.get("UTC_OFFSET_MINUTES", 330))))

# gunicorn's --bind=0.0.0.0 listens on 8000; python app.py listens on 5000.
LOCAL_PORT = int(os.environ.get("PORT", 5000))
HEALTH_URL = f"http://127.0.0.1:{LOCAL_PORT if __name__ == '__main__' else 8000}/health"


def resolve_db_path():
    if os.environ.get("DB_PATH"):
        return os.environ["DB_PATH"]
    if os.environ.get("WEBSITE_SITE_NAME"):  # only set on Azure App Service
        return "/home/data/courtbook.db"
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "courtbook.db")


DB_PATH = resolve_db_path()

# ------------------------------------------------------------------- in-memory state

state_lock = threading.Lock()
in_flight = 0
total_requests = 0
response_times = deque(maxlen=RESPONSE_WINDOW)
rejections = {"server_busy": 0, "daily_limit": 0, "past_slot": 0}
health_checks = deque(maxlen=20000)  # (timestamp, ok)
started_at = datetime.now(CAMPUS_TZ)

# ------------------------------------------------------------------------- database


@contextmanager
def db():
    # Autocommit mode: transactions are explicit. Closing without COMMIT rolls back.
    conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with db() as conn:
        # Default rollback journal: WAL is unsafe on Azure's network-mounted /home.
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS courts (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                court_id INTEGER NOT NULL REFERENCES courts(id),
                date TEXT NOT NULL,
                slot_time TEXT NOT NULL,
                student_name TEXT NOT NULL,
                reg_no TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(court_id, date, slot_time)
            );
        """)
        conn.executemany("INSERT OR IGNORE INTO courts (name) VALUES (?)", [(c,) for c in COURTS])


def get_courts(conn):
    return [dict(r) for r in conn.execute("SELECT id, name FROM courts ORDER BY id")]


# -------------------------------------------------------------------------- helpers


def deployment_info():
    """Values App Service sets on the running app. None when running locally."""
    if not os.environ.get("WEBSITE_SITE_NAME"):
        return None
    rows = {
        "App name": os.environ.get("WEBSITE_SITE_NAME"),
        "Address": os.environ.get("WEBSITE_HOSTNAME"),
        "Region": os.environ.get("REGION_NAME"),
        "Plan": os.environ.get("WEBSITE_SKU"),
        "Instance": os.environ.get("WEBSITE_INSTANCE_ID", "")[:8],
        "Python": platform.python_version(),
        "Database": DB_PATH,
    }
    return {label: value for label, value in rows.items() if value}


def now_local():
    return datetime.now(CAMPUS_TZ)


def booking_dates():
    today = now_local().date()
    return [(today + timedelta(days=i)).isoformat() for i in range(BOOKING_DAYS)]


def date_tabs():
    names = ["Today", "Tomorrow"]
    tabs = []
    for i, iso in enumerate(booking_dates()):
        day = datetime.strptime(iso, "%Y-%m-%d")
        tabs.append({
            "date": iso,
            "label": names[i] if i < len(names) else day.strftime("%A"),
            "short": f"{day.strftime('%a')} {day.day} {day.strftime('%b')}",
        })
    return tabs


def is_past(date, slot_time):
    return f"{date} {slot_time}" <= now_local().strftime("%Y-%m-%d %H:%M")


def slot_label(slot_time):
    hour, minute = map(int, slot_time.split(":"))
    return f"{hour % 12 or 12}:{minute:02d} {'AM' if hour < 12 else 'PM'}"


def hour_label(slot_time):
    hour = int(slot_time.split(":")[0])
    return f"{hour % 12 or 12} {'AM' if hour < 12 else 'PM'}"


def first_name(name):
    return name.split()[0] if name.split() else name


def clean_reg_no(value):
    return str(value or "").strip().upper()


def reject(kind, message, status):
    with state_lock:
        rejections[kind] += 1
    return jsonify(error=message), status


# ----------------------------------------------- admission control and SLA middleware


@app.before_request
def admit_request():
    global in_flight
    g.started = time.perf_counter()
    with state_lock:
        in_flight += 1
        overloaded = in_flight > MAX_CONCURRENT
    if overloaded:
        if request.path.startswith("/api/"):
            return reject("server_busy", MSG_BUSY, 503)
        with state_lock:
            rejections["server_busy"] += 1
        return Response(MSG_BUSY, 503, content_type="text/plain; charset=utf-8")


@app.after_request
def record_response_time(response):
    global total_requests
    elapsed_ms = (time.perf_counter() - g.started) * 1000
    with state_lock:
        total_requests += 1
        response_times.append(elapsed_ms)
    return response


@app.teardown_request
def release_request(_exc):
    global in_flight
    with state_lock:
        in_flight -= 1


@app.errorhandler(sqlite3.OperationalError)
def database_busy(_exc):
    # The write lock could not be taken in time; the client can safely retry.
    if request.path.startswith("/api/"):
        return jsonify(error=MSG_BUSY), 503
    return Response(MSG_BUSY, 503, content_type="text/plain; charset=utf-8")


# ------------------------------------------------------------------------------ pages


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/my")
def my_bookings():
    return render_template("my.html")


@app.get("/about")
def about():
    return render_template("about.html", deployment=deployment_info(), db_path=DB_PATH)


@app.get("/health")
def health():
    return jsonify(status="ok", time=now_local().isoformat(timespec="seconds"))


# -------------------------------------------------------------------------------- API


@app.get("/api/slots")
def api_slots():
    tabs = date_tabs()
    date = request.args.get("date") or tabs[0]["date"]
    if date not in [t["date"] for t in tabs]:
        return jsonify(error="Pick one of the available dates"), 400

    with db() as conn:
        courts = get_courts(conn)
        rows = conn.execute(
            "SELECT court_id, slot_time, student_name FROM bookings WHERE date = ?", (date,)
        ).fetchall()

    return jsonify(
        date=date,
        dates=tabs,
        courts=courts,
        slots=[{"time": s, "label": slot_label(s), "past": is_past(date, s)} for s in SLOT_TIMES],
        # Only first names leave the server: this endpoint is public.
        booked={f"{r['court_id']}|{r['slot_time']}": first_name(r["student_name"]) for r in rows},
    )


@app.post("/api/book")
def api_book():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify(error="Send the booking as JSON"), 400

    name = " ".join(str(body.get("name") or "").split())[:60]
    reg_no = clean_reg_no(body.get("reg_no"))[:30]
    date = str(body.get("date") or "")
    slot_time = str(body.get("slot_time") or "")
    try:
        court_id = int(body.get("court_id"))
    except (TypeError, ValueError):
        return jsonify(error="Pick a court"), 400

    if not name or not reg_no:
        return jsonify(error="Enter your name and registration number"), 400
    if date not in booking_dates() or slot_time not in SLOT_TIMES:
        return jsonify(error="Pick a slot from the grid"), 400
    if is_past(date, slot_time):
        return reject("past_slot", MSG_PAST, 400)

    with db() as conn:
        if not conn.execute("SELECT 1 FROM courts WHERE id = ?", (court_id,)).fetchone():
            return jsonify(error="Pick a court"), 400

        # BEGIN IMMEDIATE takes the write lock now, so the daily-limit count and the
        # insert are one atomic step and parallel requests cannot both pass the check.
        conn.execute("BEGIN IMMEDIATE")
        count = conn.execute(
            "SELECT COUNT(*) FROM bookings WHERE reg_no = ? AND date = ?", (reg_no, date)
        ).fetchone()[0]
        if count >= DAILY_LIMIT:
            return reject("daily_limit", MSG_DAILY_LIMIT, 403)
        try:
            cursor = conn.execute(
                "INSERT INTO bookings (court_id, date, slot_time, student_name, reg_no, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (court_id, date, slot_time, name, reg_no, now_local().isoformat(timespec="seconds")),
            )
        except sqlite3.IntegrityError:  # UNIQUE(court_id, date, slot_time) is the slot lock
            return jsonify(error=MSG_TAKEN), 409
        conn.execute("COMMIT")

    return jsonify(id=cursor.lastrowid, date=date, slot_time=slot_time, label=slot_label(slot_time)), 201


@app.get("/api/my")
def api_my():
    reg_no = clean_reg_no(request.args.get("reg_no"))
    if not reg_no:
        return jsonify(error="Enter your registration number"), 400
    with db() as conn:
        rows = conn.execute(
            "SELECT b.id, b.date, b.slot_time, b.student_name, c.name AS court"
            " FROM bookings b JOIN courts c ON c.id = b.court_id"
            " WHERE b.reg_no = ? ORDER BY b.date DESC, b.slot_time",
            (reg_no,),
        ).fetchall()
    return jsonify(bookings=[{
        "id": r["id"],
        "court": r["court"],
        "date": r["date"],
        "day": datetime.strptime(r["date"], "%Y-%m-%d").strftime("%a %d %b"),
        "label": slot_label(r["slot_time"]),
        "cancellable": not is_past(r["date"], r["slot_time"]),
    } for r in rows])


@app.post("/api/cancel")
def api_cancel():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify(error="Send the cancellation as JSON"), 400
    reg_no = clean_reg_no(body.get("reg_no"))
    with db() as conn:
        row = conn.execute(
            "SELECT id, date, slot_time FROM bookings WHERE id = ? AND reg_no = ?",
            (str(body.get("id")), reg_no),
        ).fetchone()
        if not row:
            return jsonify(error="Booking not found"), 404
        if is_past(row["date"], row["slot_time"]):
            return jsonify(error="This slot has already started"), 400
        conn.execute("DELETE FROM bookings WHERE id = ?", (row["id"],))
    return jsonify(ok=True)


# ---------------------------------------------------------------------------- MapReduce


def map_phase(bookings):
    """Emit (court, 1) and (hour, 1) from each booking."""
    pairs = []
    for booking in bookings:
        pairs.append((f"Court: {booking['court']}", 1))
        pairs.append((f"Hour: {hour_label(booking['slot_time'])}", 1))
    return pairs


def shuffle_phase(pairs):
    """Group the emitted values by key."""
    grouped = defaultdict(list)
    for key, value in pairs:
        grouped[key].append(value)
    return dict(grouped)


def reduce_phase(grouped):
    """Sum the counts for each key."""
    return {key: sum(values) for key, values in grouped.items()}


def top_keys(reduced, prefix):
    matches = {k[len(prefix):]: v for k, v in reduced.items() if k.startswith(prefix)}
    if not matches:
        return [], 0
    best = max(matches.values())
    return [k for k, v in matches.items() if v == best], best


@app.get("/admin")
def admin():
    today = booking_dates()[0]
    with db() as conn:
        courts = get_courts(conn)
        counts = {r["court_id"]: r["n"] for r in conn.execute(
            "SELECT court_id, COUNT(*) AS n FROM bookings WHERE date = ? GROUP BY court_id", (today,)
        )}
        bookings = [dict(r) for r in conn.execute(
            "SELECT c.name AS court, b.slot_time FROM bookings b"
            " JOIN courts c ON c.id = b.court_id ORDER BY b.id"
        )]

    utilisation = [{
        "name": c["name"],
        "booked": counts.get(c["id"], 0),
        "percent": round(counts.get(c["id"], 0) / len(SLOT_TIMES) * 100, 1),
    } for c in courts]

    pairs = map_phase(bookings)
    grouped = shuffle_phase(pairs)
    reduced = reduce_phase(grouped)
    final = sorted(reduced.items(), key=lambda item: (-item[1], item[0]))
    peak_hours, peak_count = top_keys(reduced, "Hour: ")
    top_courts, top_count = top_keys(reduced, "Court: ")

    return render_template(
        "admin.html",
        today_total=sum(counts.values()),
        slots_per_court=len(SLOT_TIMES),
        utilisation=utilisation,
        booking_count=len(bookings),
        pairs=pairs,
        grouped=grouped,
        final=final,
        peak_hours=peak_hours,
        peak_count=peak_count,
        top_courts=top_courts,
        top_count=top_count,
    )


# ---------------------------------------------------------------------------------- SLA


def percentile(values, pct):
    ordered = sorted(values)
    return ordered[max(math.ceil(pct / 100 * len(ordered)) - 1, 0)]


def health_monitor():
    time.sleep(5)  # give the server time to start listening
    while True:
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=10) as response:
                ok = response.status == 200
        except Exception:
            ok = False
        with state_lock:
            health_checks.append((now_local(), ok))
        time.sleep(HEALTH_INTERVAL)


@app.get("/sla")
def sla():
    with state_lock:
        total = total_requests
        times = list(response_times)
        checks = list(health_checks)
        rejected = dict(rejections)

    avg_ms = sum(times) / len(times) if times else 0
    p95_ms = percentile(times, 95) if times else 0
    under_slo = sum(t < SLO_MS for t in times) / len(times) * 100 if times else 100

    checks_ok = sum(ok for _, ok in checks)
    availability = checks_ok / len(checks) * 100 if checks else None
    budget_fraction = 1 - SLA_TARGET / 100
    monitored_s = len(checks) * HEALTH_INTERVAL

    met = (availability is None or availability >= SLA_TARGET) and p95_ms <= SLO_MS

    return render_template(
        "sla.html",
        met=met,
        total=total,
        sample_size=len(times),
        window=RESPONSE_WINDOW,
        avg_ms=avg_ms,
        p95_ms=p95_ms,
        under_slo=under_slo,
        slo_ms=SLO_MS,
        availability=availability,
        sla_target=SLA_TARGET,
        checks_total=len(checks),
        checks_ok=checks_ok,
        checks_failed=len(checks) - checks_ok,
        interval=HEALTH_INTERVAL,
        last_check=checks[-1] if checks else None,
        recent_checks=checks[-30:],
        allowed_month_min=30 * 24 * 60 * budget_fraction,
        allowed_day_s=24 * 3600 * budget_fraction,
        budget_s=monitored_s * budget_fraction,
        downtime_s=(len(checks) - checks_ok) * HEALTH_INTERVAL,
        rejected=rejected,
        rejected_total=sum(rejected.values()),
        max_concurrent=MAX_CONCURRENT,
        started_at=started_at,
    )


# -------------------------------------------------------------------------------- start

init_db()
threading.Thread(target=health_monitor, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=LOCAL_PORT, threaded=True)
