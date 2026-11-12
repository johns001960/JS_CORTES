from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, date, timedelta
import sqlite3, os
import requests

TELEGRAM_TOKEN = "9089939507:AAH9j4QrWJe3mSJ_lhbwUy-E68WLPAltoCQ"
TELEGRAM_CHAT_ID = "7309218518"

def enviar_telegram(mensagem):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": mensagem}, timeout=5)
    except:
        pass

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "TROQUE-ESTA-CHAVE-ANTES-DE-PUBLICAR")
DB = os.path.join(os.path.dirname(__file__), "js_cortes.db")

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS payment_methods (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY,
            customer_name TEXT NOT NULL,
            phone TEXT,
            service_id INTEGER NOT NULL,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Agendado',
            amount_paid REAL NOT NULL DEFAULT 0,
            payment_method TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(service_id) REFERENCES services(id)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS unique_active_slot
        ON appointments(appointment_date, appointment_time)

               
        WHERE status != 'Cancelado';
        """)
        for name in ["Pix", "Dinheiro", "Cartão"]:
                con.execute("INSERT OR IGNORE INTO payment_methods (name, active) VALUES (?, 1)", (name,))
        if not con.execute("SELECT id FROM admins LIMIT 1").fetchone():
            con.execute("INSERT INTO admins(username,password_hash) VALUES(?,?)",
                        ("admin", generate_password_hash("troque123")))
        if not con.execute("SELECT id FROM services LIMIT 1").fetchone():
            con.executemany("INSERT INTO services(name,price) VALUES(?,?)", [
                ("Corte de cabelo", 30), ("Barba", 20),
                ("Sobrancelha", 10), ("Pigmentação", 25),
                ("Corte + barba", 45)
            ])

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def valid_date(value):
    try:
        parsed = date.fromisoformat(value)
        return parsed >= date.today()
    except (TypeError, ValueError):
        return False

@app.route("/")
def home():
    with db() as con:
        services = con.execute("SELECT * FROM services WHERE active=1 ORDER BY name").fetchall()
    return render_template("booking.html", services=services, today=date.today().isoformat())

@app.route("/horarios")
def available_times():
    day = request.args.get("date", "")
    if not day:
        return {"times": []}
    try:
        datetime.strptime(day, "%Y-%m-%d")
    except ValueError:
        return {"times": []}
    with db() as con:
        booked = con.execute("""
            SELECT appointment_time FROM appointments
            WHERE appointment_date=? AND status != 'Cancelado'
        """, (day,)).fetchall()
    occupied = {r["appointment_time"] for r in booked}
    # Altere esta lista para ajustar os horários de atendimento da barbearia.
    slots = ["09:00", "10:00", "11:00",
         "13:00", "14:00", "15:00", "16:00", "17:00"]
    return {"times": [t for t in slots if t not in occupied]}

@app.route("/agendar", methods=["POST"])
def book():
    name = request.form.get("customer_name", "").strip()
    phone = request.form.get("phone", "").strip()
    service_id = request.form.get("service_id", "")
    day = request.form.get("appointment_date", "")
    time = request.form.get("appointment_time", "")
    payment_method = request.form.get("payment_method", "Pix").strip()
    if not name or not service_id or not day or not time:
        flash("Preencha nome, serviço, data e horário.")
        return redirect(url_for("home"))
    if not valid_date(day):
        flash("Escolha uma data válida, a partir de hoje.")
        return redirect(url_for("home"))
    with db() as con:
        service = con.execute("SELECT id, price FROM services WHERE id=? AND active=1", (service_id,)).fetchone()
        if not service:
            flash("Serviço inválido.")
            return redirect(url_for("home"))
        try:
            con.execute("""
                INSERT INTO appointments(customer_name,phone,service_id,appointment_date,
                appointment_time,payment_method,created_at,amount_paid) VALUES(?,?,?,?,?,?,?,?)
            """, (name, phone, service_id, day, time,payment_method, datetime.now().isoformat(timespec="minutes"), service["price"]))
        except sqlite3.IntegrityError:
            flash("Esse horário já foi reservado. Escolha outro.")
            return redirect(url_for("home"))
            enviar_telegram(f"✂️ NOVO AGENDAMENTO - JS CORTES\n\n👤 Nome: {name}\n📞 Telefone: {phone}\n📅 Data: {day} as {time}\n💳 Pagamento: {payment_method}")
    return render_template("success.html", name=name, day=day, time=time)

@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        with db() as con:
            user = con.execute("SELECT * FROM admins WHERE username=?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["admin_id"] = user["id"]
            return redirect(url_for("dashboard"))
        flash("Usuário ou senha incorretos.")
    return render_template("login.html")

@app.route("/admin/sair")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/admin")
@admin_required
def dashboard():
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    with db() as con:
        services = con.execute("SELECT * FROM services ORDER BY name").fetchall()
        appointments = con.execute("""
            SELECT a.*, s.name AS service_name, s.price AS service_price
            FROM appointments a JOIN services s ON s.id=a.service_id
            ORDER BY a.appointment_date DESC, a.appointment_time DESC
        """).fetchall()
        def total(start, end):
            row = con.execute("""
                SELECT COALESCE(SUM(amount_paid),0) AS total FROM appointments
                WHERE status='Concluído' AND appointment_date BETWEEN ? AND ?
            """, (start.isoformat(), end.isoformat())).fetchone()
            return row["total"]
        day_total = total(today, today)
        week_total = total(week_start, today)
        month_total = total(month_start, today)
    return render_template("admin.html", appointments=appointments, services=services,
                           day_total=day_total, week_total=week_total, month_total=month_total,
                           today=today.isoformat())

@app.route("/admin/agendamento/<int:appointment_id>/editar", methods=["GET", "POST"])
@admin_required
def edit_appointment(appointment_id):
    with db() as con:
        appointment = con.execute("SELECT * FROM appointments WHERE id=?", (appointment_id,)).fetchone()
        if not appointment:
            flash("Agendamento não encontrado.")
            return redirect(url_for("dashboard"))
        services = con.execute("SELECT * FROM services ORDER BY name").fetchall()
        if request.method == "POST":
            name = request.form.get("customer_name", "").strip()
            phone = request.form.get("phone", "").strip()
            service_id = request.form.get("service_id", "")
            day = request.form.get("appointment_date", "")
            time = request.form.get("appointment_time", "")
            if not name or not service_id or not time or not valid_date(day):
                flash("Confira o nome, serviço, data e horário.")
                return render_template("edit.html", a=appointment, services=services, today=date.today().isoformat())
            try:
                con.execute("""UPDATE appointments SET customer_name=?, phone=?, service_id=?,
                    appointment_date=?, appointment_time=? WHERE id=?""",
                    (name, phone, service_id, day, time, appointment_id))
            except sqlite3.IntegrityError:
                flash("Esse horário já está ocupado. Escolha outro.")
                return render_template("edit.html", a=appointment, services=services, today=date.today().isoformat())
            flash("Agendamento editado com sucesso.")
            return redirect(url_for("dashboard"))
    return render_template("edit.html", a=appointment, services=services, today=date.today().isoformat())

@app.route("/admin/agendamento/<int:appointment_id>/excluir", methods=["POST"])
@admin_required
def delete_appointment(appointment_id):
    with db() as con:
        row = con.execute("SELECT status FROM appointments WHERE id=?", (appointment_id,)).fetchone()
        if not row:
            flash("Agendamento não encontrado.")
        elif row["status"] == "Concluído":
            flash("Este atendimento já foi concluído. Cancele a exclusão para preservar o histórico financeiro.")
        else:
            con.execute("DELETE FROM appointments WHERE id=?", (appointment_id,))
            flash("Agendamento excluído. O horário foi liberado.")
    return redirect(url_for("dashboard"))

@app.route("/admin/agendamento/<int:appointment_id>/trocar-cliente", methods=["POST"])
@admin_required
def replace_customer(appointment_id):
    name = request.form.get("customer_name", "").strip()
    phone = request.form.get("phone", "").strip()
    if not name:
        flash("Informe o nome do novo cliente.")
        return redirect(url_for("dashboard"))
    with db() as con:
        con.execute("UPDATE appointments SET customer_name=?, phone=? WHERE id=? AND status='Agendado'",
                    (name, phone, appointment_id))
        if con.total_changes:
            flash("Cliente substituído nesse horário.")
        else:
            flash("Não foi possível trocar o cliente. Confira se o agendamento ainda está ativo.")
    return redirect(url_for("dashboard"))

@app.route("/admin/agendamento/<int:appointment_id>/atualizar", methods=["POST"])
@admin_required
def update_appointment(appointment_id):
    status = request.form.get("status", "Agendado")
    if status not in ["Agendado", "Concluído", "Cancelado"]:
        flash("Status inválido.")
        return redirect(url_for("dashboard"))
    try:
        amount = float(request.form.get("amount_paid", "0").replace(",", ".") or 0)
        if amount < 0:
            raise ValueError()
    except ValueError:
        flash("Informe um valor recebido válido.")
        return redirect(url_for("dashboard"))
    method = request.form.get("payment_method", "").strip()
    with db() as con:
        con.execute("""UPDATE appointments SET status=?, amount_paid=?, payment_method=?
                       WHERE id=?""", (status, amount if status == "Concluído" else 0,
                                        method, appointment_id))
    flash("Agendamento atualizado.")
    return redirect(url_for("dashboard"))

@app.route("/admin/servico", methods=["POST"])
@admin_required
def add_service():
    name = request.form.get("name", "").strip()
    try:
        price = float(request.form.get("price", "0").replace(",", "."))
        if not name or price < 0:
            raise ValueError()
    except ValueError:
        flash("Confira o nome e o preço do serviço.")
        return redirect(url_for("dashboard"))
    with db() as con:
        con.execute("INSERT INTO services(name,price) VALUES(?,?)", (name, price))
    flash("Serviço cadastrado.")
    return redirect(url_for("dashboard"))

@app.route("/admin/servico/<int:service_id>/desativar", methods=["POST"])
@admin_required
def disable_service(service_id):
    with db() as con:
        con.execute("UPDATE services SET active=0 WHERE id=?", (service_id,))
    flash("Serviço desativado.")
    return redirect(url_for("dashboard"))

@app.route("/admin/servico/<int:service_id>/ativar", methods=["POST"])
@admin_required
def enable_service(service_id):
    with db() as con:
        con.execute("UPDATE services SET active=1 WHERE id=?", (service_id,))
    flash("Serviço ativado.")
    return redirect(url_for("dashboard"))

@app.route("/admin/servico/<int:service_id>/excluir", methods=["POST"])
@admin_required
def delete_service(service_id):
    with db() as con:
        con.execute("DELETE FROM services WHERE id=?", (service_id,))
    flash("Serviço apagado.")
    return redirect(url_for("dashboard"))

@app.route("/admin/servico/<int:service_id>/editar", methods=["GET", "POST"])
@admin_required
def edit_service(service_id):
    with db() as con:
        if request.method == "POST":
            con.execute("UPDATE services SET name=?, price=? WHERE id=?", (request.form["name"], float(request.form["price"]), service_id))
            flash("Serviço atualizado.")
            return redirect(url_for("dashboard"))
        row = con.execute("SELECT * FROM services WHERE id=?", (service_id,)).fetchone()
    if not row:
        flash("Serviço não encontrado.")
        return redirect(url_for("dashboard"))
    return render_template("editar_servico.html", s=dict(row))   

@app.route("/admin/senha", methods=["POST"])
@admin_required
def change_password():
    current = request.form.get("current_password", "")
    new = request.form.get("new_password", "")
    with db() as con:
        user = con.execute("SELECT * FROM admins WHERE id=?", (session["admin_id"],)).fetchone()
        if not check_password_hash(user["password_hash"], current):
            flash("Senha atual incorreta.")
        elif len(new) < 10:
            flash("A nova senha deve ter pelo menos 10 caracteres.")
        else:
            con.execute("UPDATE admins SET password_hash=? WHERE id=?",
                        (generate_password_hash(new), session["admin_id"]))
            flash("Senha alterada com sucesso.")
    return redirect(url_for("dashboard"))

init_db()
if __name__ == "__main__":
    # Somente para testes no próprio computador. Não publicar com debug=True.
    app.run(debug=True)
