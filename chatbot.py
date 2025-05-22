from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    session,
    current_app,
    g,
    url_for,
    redirect,
)
from openai import OpenAI, APIError
from openai.types.chat import ChatCompletionMessage, ChatCompletionMessageToolCall
import os
import base64
import datetime
import uuid
from PIL import Image
import pytesseract
from pdf2image import convert_from_bytes
import PyPDF2
import docx
import pandas as pd
import logging
from werkzeug.utils import secure_filename
import re
from functools import wraps
import json
from typing import List, Dict, Any, Optional, Union
import io


import hemis_api
from info import fetch_student_data_with_token


logger = logging.getLogger(__name__)

chatbot_bp = Blueprint(
    "chatbot", __name__, template_folder="templates", static_folder="static"
)


def login_required_chatbot(f: Any) -> Any:
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        if "hemis_token" not in session:
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)

    return decorated_function


def faylga_ruxsat(fayl_nomi_asl: Optional[str]) -> bool:
    if not isinstance(fayl_nomi_asl, str) or not fayl_nomi_asl:
        return False
    ruhsat_etilgan_fayllar: set[str] = current_app.config.get(
        "RUHSAT_ETILGAN_FAYLLAR", set()
    )
    if "." not in fayl_nomi_asl:
        return False
    kengaytma = fayl_nomi_asl.rsplit(".", 1)[1].lower()
    return kengaytma in ruhsat_etilgan_fayllar


def faylni_saqla(fayl_obyekti: Any) -> Optional[str]:
    fayl_nomi: Optional[str] = getattr(fayl_obyekti, "filename", None)
    if (
        fayl_obyekti
        and isinstance(fayl_nomi, str)
        and fayl_nomi
        and faylga_ruxsat(fayl_nomi)
    ):
        asl_nom = secure_filename(fayl_nomi)
        if not asl_nom:
            logger.warning(
                f"Fayl nomi xavfsizlashtirilgandan keyin bo'sh qoldi: aslnomi='{fayl_nomi}'"
            )
            return None
        nom_qism, kengaytma_qism = os.path.splitext(asl_nom)
        noyob_nom = f"{nom_qism[:20]}_{uuid.uuid4().hex[:8]}{kengaytma_qism}"
        upload_folder = current_app.config.get("UPLOAD_FOLDER")
        if not upload_folder or not isinstance(upload_folder, str):
            logger.error("UPLOAD_FOLDER konfiguratsiyasi topilmadi.")
            return None
        fayl_yuli = os.path.join(upload_folder, noyob_nom)
        try:
            fayl_obyekti.save(fayl_yuli)
            logger.info(f"Fayl saqlandi: {fayl_yuli} (asl: {asl_nom})")
            return noyob_nom
        except Exception as xato:
            logger.error(f"Faylni saqlashda xato ({asl_nom}): {xato}", exc_info=True)
            return None
    elif fayl_obyekti and fayl_nomi:
        logger.warning(f"Ruxsat etilmagan fayl turi: {fayl_nomi}")
    return None


def fayldan_matn_ol(fayl_yuli: str, asl_fayl_nomi: str) -> str:
    kengaytma = asl_fayl_nomi.rsplit(".", 1)[-1].lower() if "." in asl_fayl_nomi else ""
    matn = (
        f"[{asl_fayl_nomi} faylidan matn olinmadi yoki format qo'llab-quvvatlanmaydi]"
    )
    logger.info(f"'{asl_fayl_nomi}' ({kengaytma}) faylidan matn olinmoqda...")
    try:
        if kengaytma in [
            "txt",
            "py",
            "js",
            "html",
            "css",
            "md",
            "log",
            "json",
            "xml",
            "csv",
        ]:

            with open(fayl_yuli, "r", encoding="utf-8", errors="ignore") as f:
                matn = f.read()
            if kengaytma == "csv" and len(matn.splitlines()) > 10:
                matn = (
                    "\n".join(matn.splitlines()[:10])
                    + "\n[...CSV fayl qisqartirildi...]"
                )
        elif kengaytma == "docx":
            doc = docx.Document(fayl_yuli)
            matn = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        elif kengaytma == "pdf":
            extracted_text_parts = []
            try:
                with open(fayl_yuli, "rb") as f_pdf:
                    reader = PyPDF2.PdfReader(f_pdf)
                    if reader.is_encrypted:
                        try:
                            reader.decrypt("")
                        except Exception as decrypt_err:
                            logger.warning(
                                f"Parollangan PDF ({asl_fayl_nomi}) ni ochib bo'lmadi: {decrypt_err}"
                            )
                            return f"[{asl_fayl_nomi} parollangan va ochilmadi.]"

                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text and page_text.strip():
                            extracted_text_parts.append(page_text.strip())
                matn = "\n\n".join(filter(None, extracted_text_parts))
            except Exception as pypdf_err:
                logger.error(
                    f"PyPDF2 bilan PDF ({asl_fayl_nomi}) o'qishda xato: {pypdf_err}"
                )
                matn = ""

            if not matn.strip():
                logger.info(
                    f"PDF ({asl_fayl_nomi}) da PyPDF2 matn topmadi yoki xatolik, OCR ishlatilmoqda..."
                )
                tesseract_cmd = getattr(pytesseract.pytesseract, "tesseract_cmd", None)
                poppler_path = os.getenv("POPPLER_PATH")
                if (
                    tesseract_cmd
                    and os.path.exists(tesseract_cmd)
                    and poppler_path
                    and os.path.exists(poppler_path)
                ):
                    try:
                        images = convert_from_bytes(
                            open(fayl_yuli, "rb").read(),
                            dpi=200,
                            poppler_path=poppler_path,
                        )
                        ocr_texts = [
                            pytesseract.image_to_string(
                                img, lang="uzb_cyrl+uzb_latn+rus+eng"
                            )
                            for img in images
                        ]
                        matn = "\n\n".join(filter(None, [t.strip() for t in ocr_texts]))
                        if not matn.strip():
                            matn = f"[{asl_fayl_nomi} faylidan OCR orqali ham matn topilmadi.]"
                    except Exception as ocr_err:
                        logger.error(
                            f"PDF OCR ({asl_fayl_nomi}) da xato: {ocr_err}",
                            exc_info=True,
                        )
                        matn = f"[{asl_fayl_nomi} faylini OCR qilishda xatolik.]"
                else:
                    missing_tools = []
                    if not (tesseract_cmd and os.path.exists(tesseract_cmd)):
                        missing_tools.append("Tesseract")
                    if not (poppler_path and os.path.exists(poppler_path)):
                        missing_tools.append("Poppler")
                    logger.warning(
                        f"PDF OCR uchun kerakli vositalar ({', '.join(missing_tools)}) topilmadi/sozlanmagan."
                    )
                    matn = f"[{asl_fayl_nomi} faylidan matn olinmadi (OCR uchun {', '.join(missing_tools)} kerak).]"
        elif kengaytma in ["xls", "xlsx"]:
            try:
                df = pd.read_excel(fayl_yuli, sheet_name=None)
                excel_content_parts = []
                for sheet_name, sheet_df in df.items():
                    excel_content_parts.append(
                        f"List: {sheet_name}\n{sheet_df.head().to_string(index=False)}"
                    )
                matn = "\n\n---\n\n".join(excel_content_parts)
                if len(matn) > 300000:
                    matn = matn[:300000] + "\n[...Excel fayl mazmuni qisqartirildi...]"
            except Exception as e_excel:
                logger.error(
                    f"Excel ({asl_fayl_nomi}) faylini o'qishda xato: {e_excel}"
                )
                matn = f"[{asl_fayl_nomi} Excel faylini o'qishda xatolik.]"
        elif kengaytma in ["zip", "rar", "7z", "tar", "gz"]:
            matn = f"'{asl_fayl_nomi}' arxiv fayli yuklandi. Arxiv tarkibini ko'rsatish imkoniyati hozircha mavjud emas."
        else:
            matn = f"[{asl_fayl_nomi} ({kengaytma}) fayl formatidan matn ajratib olish qo'llab-quvvatlanmaydi.]"

    except Exception as e:
        logger.error(
            f"Fayldan matn olishda umumiy xato ({asl_fayl_nomi}): {e}", exc_info=True
        )
        matn = f"[{asl_fayl_nomi} faylini o'qishda kutilmagan xatolik yuz berdi.]"

    logger.info(
        f"'{asl_fayl_nomi}' dan olingan matn (qisqa): {matn.replace(chr(10), ' ')[:150]}..."
    )
    return (
        matn.strip()
        if matn
        else f"[{asl_fayl_nomi} faylidan matn ajratib olinmadi yoki fayl bo'sh.]"
    )


def rasm_base64_qil(fayl_yuli: str, asl_fayl_nomi: str) -> Optional[str]:
    try:
        img = Image.open(fayl_yuli)

        max_size_kb = current_app.config.get("MAX_IMAGE_SIZE_KB_FOR_OPENAI", 4000)

        quality = 85
        buffered = None
        pil_format = None
        for _ in range(5):
            buffered = io.BytesIO()
            kengaytma = asl_fayl_nomi.rsplit(".", 1)[-1].lower()
            pil_format = kengaytma.upper()
            if pil_format == "JPG":
                pil_format = "JPEG"
            if pil_format not in Image.SAVE:
                pil_format = "JPEG"

            temp_img = img.copy()
            if temp_img.mode == "P" and pil_format != "GIF":
                temp_img = temp_img.convert("RGBA")
            if temp_img.mode == "RGBA" and pil_format == "JPEG":
                temp_img = temp_img.convert("RGB")

            save_params = {}
            if pil_format == "JPEG":
                save_params["quality"] = quality
            elif pil_format == "WEBP":
                save_params["quality"] = quality

            temp_img.save(buffered, format=pil_format, **save_params)

            if buffered.tell() / 1024 <= max_size_kb:
                break
            quality -= 10
            if quality < 20:
                break
        if buffered is None or pil_format is None:
            logger.error(
                f"Rasm ({asl_fayl_nomi}) uchun base64 kodlashda ichki xatolik (buffered yoki pil_format yo'q)."
            )
            return None
        if buffered.tell() / 1024 > max_size_kb:
            logger.warning(
                f"Rasm ({asl_fayl_nomi}) hajmini {max_size_kb}KB gacha kichraytirib bo'lmadi. Joriy hajm: {buffered.tell() / 1024:.2f}KB"
            )

        mime_type = f"image/{pil_format.lower()}"
        return f"data:{mime_type};base64,{base64.b64encode(buffered.getvalue()).decode('utf-8')}"
    except FileNotFoundError:
        logger.error(f"Rasm base64 qilishda fayl topilmadi: {fayl_yuli}")
    except Exception as e:
        logger.error(
            f"Rasmni base64 qilishda xato ({asl_fayl_nomi}): {e}", exc_info=True
        )
    return None


def format_tarix_shablonga(tarix_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    formatlangan_list = []
    if tarix_list:
        for xabar_item in tarix_list:
            yangi_item = xabar_item.copy()
            vaqt_iso = yangi_item.get("vaqt")
            if isinstance(vaqt_iso, str):
                try:
                    dt_obj = datetime.datetime.fromisoformat(vaqt_iso)
                    yangi_item["vaqt_str"] = dt_obj.strftime("%H:%M")
                except ValueError:
                    yangi_item["vaqt_str"] = vaqt_iso
            elif isinstance(vaqt_iso, datetime.datetime):
                yangi_item["vaqt_str"] = vaqt_iso.strftime("%H:%M")
            else:
                yangi_item["vaqt_str"] = "--:--"
            formatlangan_list.append(yangi_item)
    return formatlangan_list


def markdown_kodni_htmlga_ogir(matn: Optional[str]) -> str:
    if matn is None:
        return ""

    parts = re.split(r"(```(?:\w*\n)?[\s\S]*?```)", matn)
    html_parts = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            match = re.match(r"```(\w*)\n?([\s\S]*?)```", part)
            lang = match.group(1) if match and match.group(1) else "plaintext"
            code = match.group(2) if match and match.group(2) else part[3:-3]
            escaped_code = (
                code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            )
            html_parts.append(
                f'<div class="code-block-container"><pre><code class="language-{lang.lower().strip()}">{escaped_code.strip()}</code></pre></div>'
            )
        else:

            part_with_inline_code = re.sub(r"`([^`\n]+?)`", r"<code>\1</code>", part)
            html_parts.append(part_with_inline_code.replace("\n", "<br>"))
    return "".join(html_parts)


@chatbot_bp.route("/")
@login_required_chatbot
def chatbot_sahifasi() -> str:
    current_app.logger.info(
        f"Chatbot sahifasi. Sessiya: {dict(session).get('hemis_user_login', 'Noma`lum')}"
    )
    if "suhbat_tarixi" not in session:
        session["suhbat_tarixi"] = []
    return render_template(
        "chatbot.html",
        suhbat_tarixi=format_tarix_shablonga(session.get("suhbat_tarixi", [])),
        title="Chatbot",
    )


tools_definition = [
    {
        "type": "function",
        "function": {
            "name": "get_student_schedule",
            "description": "Talabaning belgilangan sana(lar) uchun dars jadvalini oladi. Agar sana berilmasa, bugungi dars jadvali olinadi. Sana YYYY-MM-DD formatida bo'lishi kerak.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_date": {
                        "type": "string",
                        "description": "Jadval kerak bo'lgan sana (YYYY-MM-DD). 'bugun' ham ishlatilishi mumkin. Agar start_date va end_date berilsa, bu parametr e'tiborga olinmaydi.",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Jadval oralig'ining boshlanish sanasi (YYYY-MM-DD).",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Jadval oralig'ining tugash sanasi (YYYY-MM-DD).",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_student_absences",
            "description": "Talabaning belgilangan davr uchun sababsiz qoldirgan darslari sonini va tafsilotlarini oladi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period_description": {
                        "type": "string",
                        "description": "Davr tavsifi, masalan, 'oxirgi 7 kun', 'oxirgi 30 kun', 'joriy oy', 'o'tgan oy', 'maxsus oraliq'. Agar 'maxsus oraliq' bo'lsa, start_date va end_date kerak.",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Oraliqning boshlanish sanasi (YYYY-MM-DD). `period_description` 'maxsus oraliq' bo'lganda ishlatiladi.",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Oraliqning tugash sanasi (YYYY-MM-DD). `period_description` 'maxsus oraliq' bo'lganda ishlatiladi.",
                    },
                },
                "required": ["period_description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_student_profile_info",
            "description": "Talabaning HEMIS tizimidagi shaxsiy ma'lumotlarini oladi. Agar aniq bir bo'lim yoki maydon so'ralsa, faqat o'shani qaytaradi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "section_or_field": {
                        "type": "string",
                        "description": "Profilning kerakli qismi (masalan, 'umumiy', 'o'quv', 'manzil', 'bog'lanish') yoki aniq maydon nomi (masalan, 'to'liq_ism', 'guruh_nomi', 'telefon_raqami', 'email', 'kursi', 'fakulteti', 'mutaxassisligi'). Agar bo'sh bo'lsa, asosiy ma'lumotlar qaytariladi.",
                    }
                },
                "required": [],
            },
        },
    },
]


def _parse_date_from_llm(
    date_str: Optional[str], default_to_today: bool = False
) -> Optional[datetime.date]:
    if not date_str:
        return datetime.date.today() if default_to_today else None
    if date_str.lower() == "bugun":
        return datetime.date.today()
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        logger.warning(f"LLM dan kelgan sanani o'qishda xato: '{date_str}'")

        try:
            return datetime.datetime.strptime(date_str, "%d.%m.%Y").date()
        except ValueError:
            pass
        try:
            return datetime.datetime.strptime(date_str, "%d-%m-%Y").date()
        except ValueError:
            pass
    return None


def _execute_get_student_schedule(
    args: Dict[str, Any], hemis_token: str, user_profile: Dict[str, Any]
) -> str:
    logger.info(f"Tool chaqirildi: get_student_schedule, argumentlar: {args}")
    target_date_str = args.get("target_date")
    start_date_str = args.get("start_date")
    end_date_str = args.get("end_date")

    target_date = _parse_date_from_llm(
        target_date_str, default_to_today=not (start_date_str and end_date_str)
    )
    start_date = _parse_date_from_llm(start_date_str)
    end_date = _parse_date_from_llm(end_date_str)

    group_id = user_profile.get("group", {}).get("id")

    current_semester_id = user_profile.get("semester", {}).get("id")

    if not (group_id and current_semester_id):
        return "Dars jadvalini olish uchun sizning guruhingiz yoki joriy semestr ma'lumotlari topilmadi. Profilingizni tekshiring."

    if start_date and end_date:
        if start_date > end_date:
            return "Boshlanish sanasi tugash sanasidan keyin bo'lishi mumkin emas."

        target_date = start_date
        note_for_range = f"\n(Izoh: Hozircha faqat {start_date.strftime('%d-%m-%Y')} uchun ko'rsatildi. Oraliq uchun to'liq funksionallik keyinroq qo'shiladi.)"
    elif not target_date:
        return "Dars jadvalini olish uchun sana aniqlanmadi (masalan, 'bugun' yoki 'YYYY-MM-DD')."

    raw_schedule_response = hemis_api.get_raw_schedule_data(
        hemis_token, str(group_id), str(current_semester_id), current_app.logger
    )

    if raw_schedule_response.get("error") or not raw_schedule_response.get("success"):
        return f"Dars jadvalini olishda HEMIS API bilan xatolik: {raw_schedule_response.get('message', 'Noma`lum xato')}"

    lessons_for_semester = raw_schedule_response.get("data", [])
    date_lessons = []
    note_for_range = None

    for lesson in lessons_for_semester:
        lesson_timestamp = lesson.get("lesson_date")
        if lesson_timestamp is not None:
            try:
                lesson_dt = datetime.datetime.fromtimestamp(int(lesson_timestamp))
                current_app.logger.info(
                    f"lesson_date: {lesson_dt.date()}, target_date: {target_date}"
                )
                if lesson_dt.date() == target_date:
                    date_lessons.append(lesson)
            except (ValueError, TypeError, OSError):
                pass

    if not date_lessons:
        return f"{target_date.strftime('%d-%m-%Y')} uchun dars jadvalingizda darslar topilmadi."

    response_text = f"{target_date.strftime('%d-%m-%Y')} uchun dars jadvalingiz:\n"
    date_lessons.sort(
        key=lambda x: (
            x.get("lessonPair", {}).get("code", "99"),
            x.get("lessonPair", {}).get("startTime", "99:99"),
        )
    )
    for lesson in date_lessons:
        subject_name = lesson.get("subject", {}).get("name", "N/A")
        pair = lesson.get("lessonPair", {})
        start = pair.get("startTime", "N/A")
        end = pair.get("endTime", "N/A")
        employee = lesson.get("employee", {}).get("name", "N/A")
        ttype = lesson.get("trainingType", {}).get("name", "N/A")
        auditorium = lesson.get("auditorium", {}).get("name", "N/A")
        response_text += f"- {start}-{end}: **{subject_name}** ({ttype})\n  O'qituvchi: {employee}\n  Xona: {auditorium}\n\n"

    return response_text + (note_for_range if note_for_range else "")


def _execute_get_student_absences(args: Dict[str, Any], hemis_token: str) -> str:
    logger.info(f"Tool chaqirildi: get_student_absences, argumentlar: {args}")
    period_desc = args.get("period_description", "").lower()
    start_date_str = args.get("start_date")
    end_date_str = args.get("end_date")

    today = datetime.date.today()
    start_date_calc: Optional[datetime.date] = None
    end_date_calc: Optional[datetime.date] = None
    period_display_name = period_desc

    if "oxirgi 7 kun" in period_desc or "bir hafta" in period_desc:
        end_date_calc = today - datetime.timedelta(days=1)
        start_date_calc = end_date_calc - datetime.timedelta(days=6)
        period_display_name = f"{start_date_calc.strftime('%d.%m.%Y')} - {end_date_calc.strftime('%d.%m.%Y')}"
    elif "oxirgi 30 kun" in period_desc or "bir oy" in period_desc:
        end_date_calc = today - datetime.timedelta(days=1)
        start_date_calc = end_date_calc - datetime.timedelta(days=29)
        period_display_name = f"{start_date_calc.strftime('%d.%m.%Y')} - {end_date_calc.strftime('%d.%m.%Y')}"
    elif "joriy oy" in period_desc:
        start_date_calc = today.replace(day=1)
        end_date_calc = today
        period_display_name = f"{start_date_calc.strftime('%B %Y')}"
    elif "o'tgan oy" in period_desc or "oldingi oy" in period_desc:
        first_day_current_month = today.replace(day=1)
        end_date_calc = first_day_current_month - datetime.timedelta(days=1)
        start_date_calc = end_date_calc.replace(day=1)
        period_display_name = f"{start_date_calc.strftime('%B %Y')}"
    elif start_date_str and end_date_str:
        start_date_calc = _parse_date_from_llm(start_date_str)
        end_date_calc = _parse_date_from_llm(end_date_str)
        if not (start_date_calc and end_date_calc):
            return "Maxsus oraliq uchun sanalar noto'g'ri formatda yoki berilmagan (YYYY-MM-DD)."
        if start_date_calc > end_date_calc:
            return f"Boshlanish sanasi ({start_date_calc.strftime('%d.%m.%Y')}) tugash sanasidan ({end_date_calc.strftime('%d.%m.%Y')}) keyin bo'lishi mumkin emas."
        period_display_name = f"{start_date_calc.strftime('%d.%m.%Y')} - {end_date_calc.strftime('%d.%m.%Y')}"
    else:

        logger.warning(
            f"Noma'lum davr tavsifi: '{period_desc}'. Oxirgi 7 kunga qaytarilyapti."
        )
        end_date_calc = today - datetime.timedelta(days=1)
        start_date_calc = end_date_calc - datetime.timedelta(days=6)
        period_display_name = f"{start_date_calc.strftime('%d.%m.%Y')} - {end_date_calc.strftime('%d.%m.%Y')} (standart)"

    attendance_response = hemis_api.get_student_attendance_summary(
        hemis_token, semester_id=None
    )

    unexcused_count = 0
    excused_count = 0
    absent_lessons_details = []

    if attendance_response.get("success") and attendance_response.get("data"):
        records = attendance_response.get("data", {}).get("records", [])
        for record in records:
            try:
                lesson_date_obj = datetime.datetime.strptime(
                    record["dars_sanasi"], "%Y-%m-%d"
                ).date()
                if start_date_calc <= lesson_date_obj <= end_date_calc:
                    if record.get("status_type") == "unexcused":
                        unexcused_count += 1
                        absent_lessons_details.append(
                            f"- {record['dars_sanasi']}: {record.get('fan_nomi', 'N/A')} (Sababsiz)"
                        )
                    elif record.get("status_type") == "excused":
                        excused_count += 1

            except (ValueError, TypeError):
                pass

        response_str = f"'{period_display_name}' davri uchun davomatingiz:\n"
        response_str += f"- Sababsiz qoldirilgan darslar: **{unexcused_count}** ta\n"
        response_str += f"- Sababli qoldirilgan darslar: **{excused_count}** ta\n"
        if unexcused_count > 0 and absent_lessons_details:
            response_str += (
                "\nSababsiz qoldirilgan darslar ro'yxati (ba'zilari):\n"
                + "\n".join(absent_lessons_details[:5])
            )
            if len(absent_lessons_details) > 5:
                response_str += "\n..."
        return response_str
    else:
        return f"Davomat ma'lumotlarini olishda HEMIS API bilan xatolik: {attendance_response.get('error', 'Noma`lum xato')}"


def _execute_get_student_profile_info(args: Dict[str, Any], hemis_token: str) -> str:
    logger.info(f"Tool chaqirildi: get_student_profile_info, argumentlar: {args}")
    section_or_field = args.get("section_or_field", "").lower()

    profile_response = fetch_student_data_with_token(hemis_token)
    if not profile_response.get("success"):
        return f"Profil ma'lumotlarini olishda xatolik: {profile_response.get('error', 'Noma`lum xato')}"

    data = profile_response.get("data", {})
    if not data:
        return "Profil ma'lumotlari bo'sh."

    profile_field_map_uz = {
        "to'liq ism": ("full_name", "To'liq ism-sharifi"),
        "ism": ("first_name", "Ism"),
        "familiya": ("second_name", "Familiya"),
        "otasining ismi": ("third_name", "Otasining ismi"),
        "guruh": ("group_name", "Guruh"),
        "fakultet": ("faculty_name", "Fakultet"),
        "universitet": ("university_name_display", "Universitet"),
        "telefon": ("phone", "Telefon raqami"),
        "email": ("email", "Email"),
        "kurs": ("level_name", "Kursi"),
        "bosqich": ("level_name", "Bosqichi (Kursi)"),
        "mutaxassislik": ("specialty_name", "Mutaxassislik"),
        "yo'nalish": ("specialty_name", "Ta'lim yo'nalishi (Mutaxassislik)"),
        "tug'ilgan sana": ("birth_date_formatted", "Tug'ilgan sanasi"),
        "id raqam": ("student_id_number", "Talaba ID raqami"),
        "ta'lim turi": ("educationType_name", "Ta'lim turi"),
        "ta'lim shakli": ("educationForm_name", "Ta'lim shakli"),
        "manzil": ("address", "Manzili (to'liq)"),
        "viloyat": ("province_name", "Viloyati"),
        "tuman": ("district_name", "Tumani"),
    }

    response_parts = []
    if not section_or_field or section_or_field in [
        "hammasi",
        "barchasi",
        "umumiy",
        "profil",
    ]:
        response_parts.append("Sizning profilingizdagi asosiy ma'lumotlar:")
        for key_uz, (data_key, label_uz) in profile_field_map_uz.items():
            if data_key in ["first_name", "second_name", "third_name"]:
                continue
            value = data.get(data_key, "Kiritilmagan")
            if value and value != "Kiritilmagan" and value != "Noma'lum":
                response_parts.append(f"- {label_uz}: {value}")
    else:
        found = False
        for key_uz, (data_key, label_uz) in profile_field_map_uz.items():
            if section_or_field == key_uz or section_or_field == data_key:
                value = data.get(data_key, "Bu ma'lumot kiritilmagan yoki topilmadi.")
                response_parts.append(f"{label_uz}: {value}")
                found = True
                break
        if not found:
            response_parts.append(
                f"'{section_or_field}' bo'yicha aniq ma'lumot topilmadi. Mavjud maydonlardan birini so'rang (masalan, 'guruh', 'telefon', 'kurs')."
            )

    return "\n".join(response_parts)


@chatbot_bp.route("/xabar_yuborish", methods=["POST"])
@login_required_chatbot
def xabar_yuborish_api() -> Any:

    current_app.logger.info(
        f"Xabar yuborish API (to'liq). Sessiya: {dict(session).get('hemis_user_login', 'Noma`lum')}"
    )
    openai_client: Optional[OpenAI] = current_app.config.get("OPENAI_CLIENT")
    if not openai_client:
        logger.error("OpenAI mijozi topilmadi.")

        error_msg_no_client = "Chatbot hozirda mavjud emas (serverda sozlanmagan)."
        session["suhbat_tarixi"].append(
            {
                "tur": "assistant",
                "xabar_xom": error_msg_no_client,
                "xabar_html": markdown_kodni_htmlga_ogir(error_msg_no_client),
                "fayllar": [],
                "vaqt": datetime.datetime.now().isoformat(),
            }
        )
        session.modified = True
        return (
            jsonify(
                {
                    "xabar": markdown_kodni_htmlga_ogir(error_msg_no_client),
                    "fayllar": [],
                }
            ),
            503,
        )

    foydalanuvchi_matni = request.form.get("message", "").strip()
    yuklangan_fayllar: List[Any] = request.files.getlist("files")
    hemis_token = session.get("hemis_token")

    if "suhbat_tarixi" not in session:
        session["suhbat_tarixi"] = []

    saqlangan_fayl_nomlari_user: List[str] = []
    for fayl in yuklangan_fayllar:
        saqlangan_nom = faylni_saqla(fayl)
        if saqlangan_nom:
            saqlangan_fayl_nomlari_user.append(saqlangan_nom)
        elif fayl.filename:
            logger.warning(f"'{fayl.filename}' fayli saqlanmadi.")

    current_user_message_entry = {
        "tur": "user",
        "xabar_xom": foydalanuvchi_matni,
        "xabar_html": markdown_kodni_htmlga_ogir(foydalanuvchi_matni),
        "fayllar": saqlangan_fayl_nomlari_user,
        "vaqt": datetime.datetime.now().isoformat(),
    }
    session["suhbat_tarixi"].append(current_user_message_entry)
    session.modified = True

    user_profile_data = g.get("profil", {})
    if not user_profile_data.get("id") and hemis_token:
        profile_res = fetch_student_data_with_token(hemis_token)
        if profile_res.get("success"):
            user_profile_data = profile_res.get("data", {})
            g.profil = user_profile_data
            session["hemis_profile_data"] = user_profile_data

    messages_for_openai: List[Dict[str, Any]] = [
        {
            "role": "system",
            "content": """Siz O'zbekistondagi talabalar uchun "Elektron Ta'lim Yordamchisi" chatbotsiz. Asosiy vazifalaringiz: ta'limga oid savollarga javob berish, tushunchalarni izohlash, masalalar yechishda yo'naltirish, ilmiy ishlar uchun maslahatlar berish, yuklangan fayllar (rasm, PDF, DOCX, TXT) tahlili. O'zbek, rus, ingliz tillarida muloqot qilasiz. Sizga berilgan funksiyalardan (tools) foydalanib, talabaning dars jadvali, davomati va shaxsiy ma'lumotlari haqidagi savollariga javob bera olasiz. Agar foydalanuvchi so'rovi funksiya chaqirishni talab qilsa, tegishli funksiyani chaqiring. Agar so'rov umumiy bo'lsa, o'zingiz javob bering. Sanalarni (masalan, 'bugun', 'ertaga', '15-mart 2024') YYYY-MM-DD formatiga o'tkazib bering.""",
        }
    ]

    for suhbat_item in session.get("suhbat_tarixi", []):
        rol = suhbat_item.get("tur")
        kontent_xom = suhbat_item.get("xabar_xom", "")
        fayllar = suhbat_item.get("fayllar", [])

        openai_message_content: Union[str, List[Dict[str, Any]]] = kontent_xom

        if rol == "user" and fayllar:
            content_parts: List[Dict[str, Any]] = []
            if kontent_xom:
                content_parts.append({"type": "text", "text": kontent_xom})

            for saqlangan_nom in fayllar:
                upload_folder = current_app.config.get("UPLOAD_FOLDER")
                if not upload_folder:
                    continue
                fayl_yuli = os.path.join(upload_folder, saqlangan_nom)

                asl_fayl_nomi_qayta = (
                    "_".join(saqlangan_nom.split("_")[:-1])
                    + os.path.splitext(saqlangan_nom)[-1]
                )
                if not asl_fayl_nomi_qayta or len(asl_fayl_nomi_qayta) < 2:
                    asl_fayl_nomi_qayta = saqlangan_nom

                kengaytma = (
                    saqlangan_nom.rsplit(".", 1)[-1].lower()
                    if "." in saqlangan_nom
                    else ""
                )
                if kengaytma in ["png", "jpg", "jpeg", "gif", "webp"]:
                    base64_rasm = rasm_base64_qil(fayl_yuli, asl_fayl_nomi_qayta)
                    if base64_rasm:
                        content_parts.append(
                            {
                                "type": "image_url",
                                "image_url": {"url": base64_rasm, "detail": "auto"},
                            }
                        )
                else:
                    matn = fayldan_matn_ol(fayl_yuli, asl_fayl_nomi_qayta)
                    MAX_LEN = current_app.config.get(
                        "MAX_FILE_TEXT_LENGTH_FOR_OPENAI", 150000
                    )
                    if len(matn) > MAX_LEN:
                        matn = matn[:MAX_LEN] + "\n[...MATN QISQARTIRILDI...]"
                    content_parts.append(
                        {
                            "type": "text",
                            "text": f"\n[Yuklangan fayl: '{asl_fayl_nomi_qayta}']\n{matn}\n[/Yuklangan fayl]",
                        }
                    )

            if content_parts:
                openai_message_content = content_parts

        if rol and (kontent_xom or (rol == "user" and fayllar)):
            messages_for_openai.append({"role": rol, "content": openai_message_content})
        elif (
            rol == "tool"
            and suhbat_item.get("tool_call_id")
            and suhbat_item.get("name")
        ):
            messages_for_openai.append(
                {
                    "tool_call_id": suhbat_item.get("tool_call_id"),
                    "role": "tool",
                    "name": suhbat_item.get("name"),
                    "content": kontent_xom,
                }
            )

    try:
        logger.info(
            f"OpenAI APIga so'rov (tools bilan). Xabarlar soni: {len(messages_for_openai)}"
        )
        if not messages_for_openai[-1]["role"] == "user":
            logger.warning(
                "OpenAI ga yuborilayotgan xabarlar ro'yxati user xabari bilan tugamadi."
            )

        first_response: ChatCompletionMessage = (
            openai_client.chat.completions.create(
                model=str(current_app.config.get("OPENAI_MODEL", "gpt-4o")),
                messages=messages_for_openai,
                tools=tools_definition,
                tool_choice="auto",
            )
            .choices[0]
            .message
        )

        tool_calls: Optional[List[ChatCompletionMessageToolCall]] = (
            first_response.tool_calls
        )

        if tool_calls:
            logger.info(f"OpenAI funksiya chaqirishni so'radi: {tool_calls}")
            messages_for_openai.append(first_response.model_dump())

            available_python_functions = {
                "get_student_schedule": lambda args: _execute_get_student_schedule(
                    args, hemis_token or "", user_profile_data
                ),
                "get_student_absences": lambda args: _execute_get_student_absences(
                    args, hemis_token or ""
                ),
                "get_student_profile_info": lambda args: _execute_get_student_profile_info(
                    args, hemis_token or ""
                ),
            }

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_python_functions.get(function_name)

                tool_response_content = f"'{function_name}' nomli funksiya topilmadi yoki chaqirib bo'lmadi."
                if function_to_call:
                    try:
                        function_args = json.loads(tool_call.function.arguments)
                        if not hemis_token and function_name in [
                            "get_student_schedule",
                            "get_student_absences",
                            "get_student_profile_info",
                        ]:
                            tool_response_content = "Bu amal uchun avtorizatsiya tokeni (tizimga kirish) zarur."
                        else:
                            tool_response_content = function_to_call(function_args)
                        logger.info(
                            f"'{function_name}' bajarildi. Natija (qisqa): {str(tool_response_content)[:100]}..."
                        )
                    except json.JSONDecodeError as je:
                        logger.error(
                            f"JSON argumentlarni o'qishda xato ({function_name}): {tool_call.function.arguments}, Xato: {je}"
                        )
                        tool_response_content = f"'{function_name}' funksiyasi uchun argumentlar noto'g'ri formatda."
                    except Exception as e_func:
                        logger.error(
                            f"'{function_name}' funksiyasini bajarishda xato: {e_func}",
                            exc_info=True,
                        )
                        tool_response_content = f"'{function_name}' funksiyasini bajarishda kutilmagan xatolik."

                messages_for_openai.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": tool_response_content,
                    }
                )

        else:
            final_bot_response_xom = (
                first_response.content or "Kechirasiz, hozir javob bera olmayman."
            )

        logger.info("Funksiya natijalari bilan OpenAI ga ikkinchi so'rov yuborilmoqda.")
        second_response_msg: ChatCompletionMessage = (
            openai_client.chat.completions.create(
                model=str(current_app.config.get("OPENAI_MODEL", "gpt-4o")),
                messages=messages_for_openai,
            )
            .choices[0]
            .message
        )
        final_bot_response_xom = (
            second_response_msg.content or "Funksiya natijasini qayta ishlab bo'lmadi."
        )

        session["suhbat_tarixi"].append(
            {
                "tur": "assistant",
                "xabar_xom": final_bot_response_xom,
                "xabar_html": markdown_kodni_htmlga_ogir(final_bot_response_xom),
                "fayllar": [],
                "vaqt": datetime.datetime.now().isoformat(),
            }
        )
        session.modified = True
        current_app.logger.info(
            f"Yakuniy javob jo'natilmoqda: {final_bot_response_xom[:100]}..."
        )
        return jsonify(
            {"xabar": markdown_kodni_htmlga_ogir(final_bot_response_xom), "fayllar": []}
        )

    except APIError as e:
        status_code_val = getattr(e, "status_code", 503)
        error_message_val = getattr(e, "message", str(e))
        logger.error(
            f"OpenAI API xatoligi: {status_code_val} - {error_message_val}",
            exc_info=True,
        )
        error_text = f"OpenAI bilan bog'lanishda xatolik ({status_code_val})."

        session["suhbat_tarixi"].append(
            {
                "tur": "assistant",
                "xabar_xom": error_text,
                "xabar_html": markdown_kodni_htmlga_ogir(error_text),
                "fayllar": [],
                "vaqt": datetime.datetime.now().isoformat(),
            }
        )
        session.modified = True
        return jsonify(
            {"xabar": markdown_kodni_htmlga_ogir(error_text), "fayllar": []}
        ), (status_code_val if isinstance(status_code_val, int) else 503)

    except Exception as e_umumiy:
        logger.error(
            f"Xabar yuborishda kutilmagan umumiy xato: {e_umumiy}", exc_info=True
        )
        error_text_gen = "Chatbotda noma'lum server xatoligi yuz berdi."
        session["suhbat_tarixi"].append(
            {
                "tur": "assistant",
                "xabar_xom": error_text_gen,
                "xabar_html": markdown_kodni_htmlga_ogir(error_text_gen),
                "fayllar": [],
                "vaqt": datetime.datetime.now().isoformat(),
            }
        )
        session.modified = True
        return (
            jsonify(
                {"xabar": markdown_kodni_htmlga_ogir(error_text_gen), "fayllar": []}
            ),
            500,
        )


@chatbot_bp.route("/tarixni_tozalash", methods=["POST"])
@login_required_chatbot
def tarixni_tozalash_api() -> Any:
    session.pop("suhbat_tarixi", None)
    session.modified = True
    logger.info("Suhbat tarixi tozalandi.")
    return jsonify(
        {"muvaffaqiyat": True, "xabar": "Suhbat tarixi muvaffaqiyatli tozalandi."}
    )
