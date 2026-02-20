
import sqlite3
import datetime
from flask import Flask, request, redirect, url_for, render_template, g

app = Flask(__name__)

DATABASE = "clinic.db"


# ---------- Работа с базой данных ----------

def get_db():
    """
    Получаем соединение с базой данных.
    Объект g — это «глобальный контекст запроса» во Flask.
    """
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row  # строки будут как словари
    return g.db


@app.teardown_appcontext
def close_db(error):
    """
    Закрываем соединение с БД после обработки запроса.
    """
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """
    Создаём таблицы (если их ещё нет) и заполняем тестовыми данными.
    """
    db = get_db()

    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS citizens(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            iin TEXT UNIQUE NOT NULL,
            first_name TEXT,
            last_name TEXT,
            birth_date TEXT
        );

        CREATE TABLE IF NOT EXISTS doctors(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            specialty TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS time_slots(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            is_booked INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        );

        CREATE TABLE IF NOT EXISTS appointments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            citizen_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            slot_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (citizen_id) REFERENCES citizens(id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(id),
            FOREIGN KEY (slot_id) REFERENCES time_slots(id)
        );
        """
    )

    # Если граждан ещё нет — добавим тестовые записи
    cur = db.execute("SELECT COUNT(*) AS c FROM citizens")
    if cur.fetchone()["c"] == 0:
        db.executemany(
            "INSERT INTO citizens (iin, first_name, last_name, birth_date) VALUES (?, ?, ?, ?)",
            [
                ("010101300000", "Алишер", "Касымов", "2001-01-01"),
                ("020202400000", "Диана", "Серикова", "2002-02-02"),
            ],
        )

    # Если врачей ещё нет — добавим тестовых врачей
    cur = db.execute("SELECT COUNT(*) AS c FROM doctors")
    if cur.fetchone()["c"] == 0:
        db.executemany(
            "INSERT INTO doctors (full_name, specialty) VALUES (?, ?)",
            [
                ("Иванов Иван Иванович", "Терапевт"),
                ("Петрова Айгуль Нурлановна", "Педиатр"),
            ],
        )

    # Если слотов ещё нет — создадим расписание на сегодня и завтра
    cur = db.execute("SELECT COUNT(*) AS c FROM time_slots")
    if cur.fetchone()["c"] == 0:
        today = datetime.date.today()
        slots_data = []
        work_hours = [9, 10, 11, 14, 15]  # часы приёма

        # Берём всех врачей из таблицы, чтобы не жестко привязываться к id=1,2
        doctors = db.execute("SELECT id FROM doctors").fetchall()
        for d in doctors:
            doctor_id = d["id"]
            for day_offset in range(2):  # сегодня и завтра
                date_obj = today + datetime.timedelta(days=day_offset)
                date_str = date_obj.isoformat()
                for hour in work_hours:
                    time_str = f"{hour:02d}:00"
                    slots_data.append((doctor_id, date_str, time_str, 0))

        db.executemany(
            "INSERT INTO time_slots (doctor_id, date, time, is_booked) VALUES (?, ?, ?, ?)",
            slots_data,
        )

    db.commit()


@app.before_request
def initialize():
    """
    Хук Flask: выполнится один раз перед первым запросом.
    Здесь мы инициализируем БД.
    """
    init_db()


# ---------- Маршруты (роуты) приложения ----------

@app.route("/", methods=["GET", "POST"])
def index():
    """
    Главная страница: ввод ИИН и проверка наличия гражданина в БД.
    """
    error = None
    if request.method == "POST":
        iin = request.form.get("iin", "").strip()

        if not iin:
            error = "Введите ИИН."
        else:
            db = get_db()
            citizen = db.execute(
                "SELECT * FROM citizens WHERE iin = ?", (iin,)
            ).fetchone()

            if citizen:
                # Если гражданин найден — переходим на страницу записи
                return redirect(url_for("booking", iin=iin))
            else:
                error = "Гражданин с таким ИИН не найден в базе."

    return render_template("index.html", error=error)


@app.route("/booking", methods=["GET", "POST"])
def booking():
    """
    Страница выбора врача и времени приёма.
    """
    iin = request.args.get("iin", "").strip()
    doctor_id = request.args.get("doctor_id")

    if not iin:
        return redirect(url_for("index"))

    db = get_db()
    citizen = db.execute(
        "SELECT * FROM citizens WHERE iin = ?", (iin,)
    ).fetchone()

    if not citizen:
        # Если гражданин не найден (например, база изменилась) — вернём на главную
        return redirect(url_for("index"))

    doctors = db.execute("SELECT * FROM doctors").fetchall()

    slots = []
    doctor_selected = None

    if doctor_id:
        doctor_selected = db.execute(
            "SELECT * FROM doctors WHERE id = ?", (doctor_id,)
        ).fetchone()

        if doctor_selected:
            slots = db.execute(
                """
                SELECT * FROM time_slots
                WHERE doctor_id = ? AND is_booked = 0
                ORDER BY date, time
                """,
                (doctor_id,),
            ).fetchall()

    return render_template(
        "booking.html",
        citizen=citizen,
        doctors=doctors,
        slots=slots,
        doctor_id=doctor_id,
        doctor_selected=doctor_selected
    )


@app.route("/book", methods=["POST"])
def book():
    """
    Обработка формы записи: фиксируем запись в БД.
    """
    iin = request.form.get("iin", "").strip()
    doctor_id = request.form.get("doctor_id")
    slot_id = request.form.get("slot_id")

    if not (iin and doctor_id and slot_id):
        return redirect(url_for("index"))

    db = get_db()

    citizen = db.execute(
        "SELECT * FROM citizens WHERE iin = ?", (iin,)
    ).fetchone()

    if not citizen:
        return redirect(url_for("index"))

    # Проверяем, что слот доступен
    slot = db.execute(
        "SELECT * FROM time_slots WHERE id = ? AND is_booked = 0", (slot_id,)
    ).fetchone()

    if not slot:
        # Слот уже занят или не существует
        return redirect(url_for("booking", iin=iin, doctor_id=doctor_id))

    # Создаём запись
    now = datetime.datetime.now().isoformat(timespec="seconds")

    db.execute(
        """
        INSERT INTO appointments (citizen_id, doctor_id, slot_id, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (citizen["id"], doctor_id, slot_id, now),
    )

    db.execute(
        "UPDATE time_slots SET is_booked = 1 WHERE id = ?", (slot_id,)
    )

    db.commit()

    doctor = db.execute(
        "SELECT * FROM doctors WHERE id = ?", (doctor_id,)
    ).fetchone()

    return render_template(
        "success.html",
        citizen=citizen,
        slot=slot,
        doctor=doctor,
    )


if __name__ == "__main__":
    # Для учебного режима debug=True удобно
    app.run(debug=True)
