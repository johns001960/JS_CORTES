import pathlib, re
p = pathlib.Path("app.py")
txt = p.read_text(encoding="utf-8")
padrao = r'[ \t]*if request\.method == "POST":\s*\n[ \t]*return redirect\(url_for\("admin_calendar"\)\)'
achados = list(re.finditer(padrao, txt))
print(f"Achei {len(achados)} blocos POST vazios")
if not achados:
    print("Nao achei nenhum, me manda print")
else:
    m = achados[-1]
    novo = '''    if request.method == "POST":
        action = request.form.get("action", "")
        if action == "delete_time":
            bid = request.form.get("block_id")
            try:
                con.execute("DELETE FROM blocked_times WHERE id=?", (bid,))
                con.commit()
                flash("Bloqueio removido!")
            except Exception as e:
                print("erro delete_time", e)
            return redirect(url_for("admin_calendar"))
        if action in ("delete", "delete_day", "unblock", "remove"):
            bid = request.form.get("block_id") or request.form.get("id")
            try:
                con.execute("DELETE FROM blocked_days WHERE id=?", (bid,))
                con.commit()
                flash("Bloqueio removido!")
            except Exception as e:
                print("erro delete_day", e)
            return redirect(url_for("admin_calendar"))
        try:
            con.execute("CREATE TABLE IF NOT EXISTS blocked_times (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, time TEXT)")
            date_val = request.form.get("date", "") or request.form.get("block_date", "")
            weekdays = request.form.getlist("weekdays")
            weeks = int(request.form.get("weeks", "1") or 1)
            times = []
            txt_times = request.form.get("times_text", "") or ""
            for t in txt_times.replace(";", ",").split(","):
                t = t.strip()
                if t:
                    times.append(t)
            for t in request.form.getlist("time"):
                t = (t or "").strip()
                if t and t not in times:
                    times.append(t)
            import datetime as _dt
            datas = []
            if date_val:
                datas.append(date_val)
            if weekdays:
                hoje = _dt.date.today()
                for i in range(0, weeks*7):
                    d = hoje + _dt.timedelta(days=i)
                    if str(d.weekday()) in weekdays or str((d.weekday()+1)%7) in weekdays or str(d.isoweekday()%7) in weekdays:
                        datas.append(d.isoformat())
                for w in weekdays:
                    try:
                        con.execute("INSERT INTO blocked_days (date, weekday) VALUES (?, ?)", (date_val or "", int(w)))
                    except Exception:
                        pass
            for d in set(datas):
                for t in times:
                    try:
                        con.execute("INSERT INTO blocked_times (date, time) VALUES (?, ?)", (d, t))
                    except Exception as e:
                        print("erro insert", e)
            con.commit()
            flash("Horarios bloqueados!")
        except Exception as e:
            print("erro bloquear", e)
        return redirect(url_for("admin_calendar"))'''
    txt = txt[:m.start()] + novo + txt[m.end():]
    p.write_text(txt, encoding="utf-8")
    print("app.py: POST CONSERTADO AGORA!")
print("FIM")