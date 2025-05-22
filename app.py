from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    session,
    send_from_directory,
    g,
    redirect,
    url_for,
    flash,
)
from flask_session import Session
from openai import OpenAI
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os
from functools import wraps
from datetime import datetime


import hemis_api
from info import fetch_student_data_with_token
import schedule_handler
from chatbot import chatbot_bp
from data import tasks as static_tasks_data

load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static")


app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "sizning_juda_maxfiy_kalitingiz_shu_yerda"),
    SESSION_TYPE="filesystem",
    SESSION_FILE_DIR=os.path.join(
        os.path.abspath(os.path.dirname(__file__)), ".flask_session"
    ),
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_NAME="elektron_talim_sessiya_cookie",
    UPLOAD_FOLDER=os.path.join(
        os.path.abspath(os.path.dirname(__file__)), "data", "uploads"
    ),
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,
    RUHSAT_ETILGAN_FAYLLAR={
        "png",
        "jpg",
        "jpeg",
        "gif",
        "webp",
        "pdf",
        "doc",
        "docx",
        "txt",
        "csv",
        "xls",
        "xlsx",
        "py",
        "js",
        "java",
        "cpp",
        "zip",
        "rar",
        "html",
        "css",
        "md",
    },
    OPENAI_MODEL=os.getenv("OPENAI_MODEL", "gpt-4o"),
    MAX_TOKENS_RESPONSE=int(os.getenv("MAX_TOKENS_RESPONSE", 3000)),
)


api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    app.config["OPENAI_CLIENT"] = OpenAI(api_key=api_key)
else:
    app.logger.warning(
        "OPENAI_API_KEY topilmadi. Chatbot funksionalligi cheklangan bo'lishi mumkin."
    )
    app.config["OPENAI_CLIENT"] = None


Session(app)


os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "hemis_token" not in session:
            flash("Iltimos, tizimga kiring.", "warning")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)

    return decorated_function


@app.before_request
def load_global_data_to_g():
    g.profil = session.get("hemis_profile_data", {})
    g.hemis_user_login = session.get("hemis_user_login")
    hemis_token = session.get("hemis_token")

    if hemis_token and (not g.profil or not g.profil.get("full_name")):

        if not getattr(g, "_profile_loaded_this_request", False):
            app.logger.info(
                f"HEMIS dan profil ma'lumotlari {g.hemis_user_login} uchun so'ralmoqda..."
            )
            profile_result = fetch_student_data_with_token(hemis_token)
            if profile_result and profile_result.get("success"):
                g.profil = profile_result.get("data", {})
                session["hemis_profile_data"] = g.profil
                app.logger.info(
                    f"Profil ma'lumotlari {g.profil.get('full_name')} uchun g ga yuklandi va sessiyaga saqlandi."
                )
            else:
                app.logger.warning(
                    f"HEMIS dan profil ma'lumotlarini olishda xatolik ({g.hemis_user_login}): {profile_result.get('error') if profile_result else 'Noma`lum xato'}"
                )

            g._profile_loaded_this_request = True
    elif not hemis_token:
        session.pop("hemis_profile_data", None)
        g.profil = {}


@app.route("/")
def root_redirect():
    if "hemis_token" in session:
        return redirect(url_for("chatbot.chatbot_sahifasi"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        hemis_login = request.form.get("hemis_login")
        hemis_password = request.form.get("hemis_password")

        if not hemis_login or not hemis_password:
            flash("Login va parol kiritilishi shart.", "danger")
            return render_template("login.html", title="Tizimga Kirish")

        token_data = hemis_api.get_auth_token_with_credentials(
            hemis_login, hemis_password
        )

        if token_data and token_data.get("success") and token_data.get("token"):
            session["hemis_token"] = token_data["token"]
            session["hemis_user_login"] = hemis_login
            session.permanent = True

            profile_result = fetch_student_data_with_token(token_data["token"])
            if profile_result and profile_result.get("success"):
                session["hemis_profile_data"] = profile_result.get("data", {})
                app.logger.info(
                    f"Login paytida profil ma'lumotlari ({profile_result.get('data', {}).get('full_name')}) sessiyaga saqlandi."
                )
            else:
                app.logger.warning(
                    f"Login paytida profil ma'lumotlarini olishda xatolik: {profile_result.get('error') if profile_result else 'Noma`lum xato'}"
                )
                session["hemis_profile_data"] = {}

            flash("Tizimga muvaffaqiyatli kirdingiz!", "success")
            next_url = request.args.get("next")
            return redirect(next_url or url_for("chatbot.chatbot_sahifasi"))
        else:
            error_message = (
                token_data.get("error", "Login yoki parol xato.")
                if token_data
                else "Login yoki parol xato."
            )
            flash(error_message, "danger")
            return render_template(
                "login.html", title="Tizimga Kirish", hemis_login=hemis_login
            )

    return render_template("login.html", title="Tizimga Kirish")


@app.route("/logout")
@login_required
def logout():
    session.pop("hemis_token", None)
    session.pop("hemis_user_login", None)
    session.pop("suhbat_tarixi", None)
    session.pop("hemis_profile_data", None)
    g.profil = {}
    flash("Siz tizimdan muvaffaqiyatli chiqdingiz.", "info")
    return redirect(url_for("login"))


@app.route("/dars_jadvali")
@login_required
def dars_jadvali_route():
    hemis_token = session.get("hemis_token")

    kontekst_data = schedule_handler.get_schedule_data_for_page(
        request.args, hemis_api_token=hemis_token, flask_app_logger=app.logger
    )
    kontekst_data["title"] = "Dars Jadvali"
    return render_template("schedule.html", **kontekst_data)


def format_timestamp_to_date(ts, default_text="Muddati belgilanmagan"):
    if ts and isinstance(ts, (int, float)) and ts > 0:
        try:
            return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d")
        except (ValueError, TypeError, OSError) as e:
            app.logger.warning(f"Timestampni formatlashda xato (ts: {ts}): {e}")
            return "Noma'lum muddat"
    return default_text


@app.route("/topshiriqlar")
@login_required
def topshiriqlar_route():
    app.logger.info("Topshiriqlar sahifasiga kirildi (Statik ma'lumotlar bilan).")

    processed_tasks = []
    error_message = None

    raw_tasks = static_tasks_data.toplangan_topsiriqlar

    if not raw_tasks:
        flash("Hozircha siz uchun topshiriqlar mavjud emas.", "info")
    else:
        for i, task_item in enumerate(raw_tasks):
            subject_display = task_item.get("name", f"Nomsiz topshiriq")
            task_type_name = task_item.get("taskType", {}).get("name", "")
            training_type_name = task_item.get("trainingType", {}).get("name", "")

            type_display_parts = []
            if task_type_name:
                type_display_parts.append(task_type_name)
            if training_type_name:
                type_display_parts.append(training_type_name)

            type_final_display = (
                " / ".join(filter(None, type_display_parts))
                if type_display_parts
                else "Noma'lum tur"
            )

            deadline_ts = task_item.get("deadline_timestamp")
            if deadline_ts:
                deadline_str = format_timestamp_to_date(deadline_ts)
            else:
                deadline_str = format_timestamp_to_date(task_item.get("deadline"))

            processed_tasks.append(
                {
                    "id": task_item.get("id", f"static_{i}"),
                    "subject": subject_display,
                    "description": task_item.get("comment", ""),
                    "deadline": deadline_str,
                    "max_ball": task_item.get("max_ball", 0),
                    "type": type_final_display,
                    "files": task_item.get("files", []),
                }
            )

        if not processed_tasks:
            flash(
                "Topshiriqlarni qayta ishlashda muammo. Hozircha topshiriqlar yo'q.",
                "warning",
            )

    return render_template(
        "tasks.html",
        tasks_data=processed_tasks,
        title="Topshiriqlar",
        error_message=error_message,
    )


@app.route("/davomat")
@login_required
def davomat_route():

    return render_template("attendance.html", initial_error=None, title="Davomat")


@app.route("/mening_malumotlarim")
@login_required
def mening_malumotlarim_route():
    talaba_data = g.get("profil")
    xato_xabari = None

    if not talaba_data or not talaba_data.get("full_name"):
        app.logger.warning(
            "`g.profil` da ma'lumot yetarli emas yoki yo'q. Qayta so'ralmoqda..."
        )
        hemis_token = session.get("hemis_token")
        if hemis_token:
            natija = fetch_student_data_with_token(hemis_token)
            if natija and natija.get("success"):
                talaba_data = natija.get("data")
                g.profil = talaba_data
                session["hemis_profile_data"] = talaba_data
            else:
                xato_xabari = natija.get("error", "Maʼlumotlarni olishda xatolik.")
                flash(xato_xabari, "danger")
                app.logger.error(
                    f"Mening ma'lumotlarim sahifasida profilni qayta yuklashda xato: {xato_xabari}"
                )
        else:
            xato_xabari = "Avtorizatsiya tokeni topilmadi."
            flash(xato_xabari, "danger")
            app.logger.error(
                "Mening ma'lumotlarim: Token topilmadi, garchi login_required dan o'tgan bo'lsa ham."
            )
            return redirect(url_for("login"))

    return render_template(
        "profile.html",
        title="Mening ma'lumotlarim",
        student_data=talaba_data,
        error_message=xato_xabari,
    )


@app.route("/api/hemis/semesters")
@login_required
def api_get_hemis_semesters():
    token = session.get("hemis_token")

    if not token:
        return jsonify({"success": False, "error": "Token not found"}), 401
    res = hemis_api.get_available_semesters(token)
    return jsonify(res), (200 if res.get("success") else 500)


@app.route("/api/hemis/attendance")
@login_required
def api_get_hemis_attendance():
    token = session.get("hemis_token")
    if not token:
        return jsonify({"success": False, "error": "Token not found"}), 401
    sem_id = request.args.get("semester_id", "all")
    res = hemis_api.get_student_attendance_summary(token, semester_id=sem_id)
    return jsonify(res), (200 if res.get("success") else 500)


@app.route("/yuklamalar/<path:fayl_nomi>")
@login_required
def yuklangan_fayl_route(fayl_nomi):

    xavfsiz_fayl_nomi = secure_filename(fayl_nomi)
    if xavfsiz_fayl_nomi != fayl_nomi:
        flash("Noto'g'ri fayl nomi.", "danger")
        return redirect(request.referrer or url_for("chatbot.chatbot_sahifasi"))

    try:
        return send_from_directory(
            app.config["UPLOAD_FOLDER"], xavfsiz_fayl_nomi, as_attachment=False
        )
    except FileNotFoundError:
        flash("Fayl topilmadi.", "warning")
        return redirect(request.referrer or url_for("chatbot.chatbot_sahifasi"))


app.register_blueprint(chatbot_bp, url_prefix="/chat")


if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5001))

    debug_mode = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "t")
    if os.getenv("FLASK_ENV") == "production":
        debug_mode = False

    app.logger.info(
        f"Flask ilovasi {port}-portda {'debug' if debug_mode else 'production'} rejimida ishga tushirilmoqda."
    )
    app.run(debug=debug_mode, host="0.0.0.0", port=port)



