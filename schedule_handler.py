import requests
import json
from datetime import datetime, timedelta, date
import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from collections import defaultdict
import logging


logger_sh = logging.getLogger(__name__)
if not logger_sh.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s [%(levelname)s] - %(message)s",
    )

try:
    env_path = find_dotenv(usecwd=True, raise_error_if_not_found=False)
    if env_path and Path(env_path).exists():
        load_dotenv(dotenv_path=env_path, override=True)
except Exception as e:
    logger_sh.error(
        f"schedule_handler: .env faylini yuklashda xatolik: {e}", exc_info=True
    )


HAFTA_KUNLARI_UZ = {
    0: "Dushanba",
    1: "Seshanba",
    2: "Chorshanba",
    3: "Payshanba",
    4: "Juma",
    5: "Shanba",
    6: "Yakshanba",
}
BASE_API_URL = os.getenv("HEMIS_BASE_URL", "https://student.samtuit.uz/rest/v1")
PAIR_STANDARD_TIMES = {
    "01": {"startTime": "08:30", "endTime": "09:50"},
    "02": {"startTime": "10:00", "endTime": "11:20"},
    "03": {"startTime": "11:30", "endTime": "12:50"},
    "04": {"startTime": "13:30", "endTime": "14:50"},
    "05": {"startTime": "15:00", "endTime": "16:20"},
    "06": {"startTime": "16:30", "endTime": "17:50"},
    "07": {"startTime": "18:00", "endTime": "19:20"},
    "11": {"startTime": "08:30", "endTime": "09:50"},
    "12": {"startTime": "10:00", "endTime": "11:20"},
    "13": {"startTime": "11:30", "endTime": "12:50"},
    "14": {"startTime": "13:30", "endTime": "14:50"},
    "15": {"startTime": "15:00", "endTime": "16:20"},
    "16": {"startTime": "16:30", "endTime": "17:50"},
    "17": {"startTime": "18:00", "endTime": "19:20"},
    "99": {"startTime": "N/A", "endTime": "N/A"},
}


def get_status_messages():
    return {"errors": [], "warnings": [], "successes": [], "infos": []}


def make_api_request(
    endpoint, token, params=None, method="GET", data=None, app_logger=None
):
    current_logger = app_logger if app_logger else logger_sh
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    url = f"{BASE_API_URL}/{endpoint}"

    log_params_str = str(params)[:200] if params else "{}"
    log_data_str = (
        str({k: (v if k != "password" else "***") for k, v in data.items()})[:200]
        if isinstance(data, dict)
        else "Ma'lumotlar yo'q"
    )

    current_logger.debug(
        f"API so'rovi: {method} {url} | Parametrlar: {log_params_str} | Ma'lumotlar: {log_data_str}"
    )

    response = None
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=20)
        elif method == "POST":
            response = requests.post(
                url, headers=headers, json=data, params=params, timeout=20
            )
        else:
            current_logger.error(f"Noto'g'ri HTTP metodi ishlatildi: {method}")

            return {
                "error": True,
                "message": f"Dasturiy xatolik: Noto'g'ri HTTP metodi ({method})",
                "status_code": 500,
                "type": "InternalValueError",
            }

        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        error_details = "Serverdan xato tafsilotlari olinmadi"
        status_code = "N/A"
        response_text = ""
        if http_err.response is not None:
            status_code = http_err.response.status_code
            response_text = http_err.response.text[:500]
            try:
                error_content = http_err.response.json()
                error_details = error_content.get(
                    "message", error_content.get("error", response_text[:200])
                )
            except ValueError:
                error_details = response_text[:200]

        current_logger.error(
            f"HEMIS API HTTP xatolik ({method} {url}): Status {status_code}, Javob: {response_text}"
        )
        user_message = f"API serverida xatolik ({status_code})."
        if status_code == 401:
            user_message = "Avtorizatsiya tokeni yaroqsiz yoki muddati o'tgan. Qaytadan tizimga kiring."
        elif error_details and error_details != "Serverdan xato tafsilotlari olinmadi":
            user_message += f" Server javobi: {error_details}"
        return {
            "error": True,
            "message": user_message,
            "status_code": status_code,
            "type": "HTTPError",
            "details": error_details,
        }
    except requests.exceptions.Timeout:
        current_logger.error(f"HEMIS API Timeout ({method} {url})")
        return {
            "error": True,
            "message": "API serveridan javob olish vaqti tugadi (Timeout).",
            "status_code": 408,
            "type": "Timeout",
        }
    except requests.exceptions.ConnectionError:
        current_logger.error(f"HEMIS API Connection Error ({method} {url})")
        return {
            "error": True,
            "message": "API serveriga ulanishda muammo (ConnectionError). Internet aloqasini tekshiring.",
            "status_code": 503,
            "type": "ConnectionError",
        }
    except requests.exceptions.RequestException as req_err:
        current_logger.error(
            f"HEMIS API umumiy so'rov xatoligi ({method} {url}): {req_err}"
        )
        return {
            "error": True,
            "message": f"Tarmoq yoki API so'rovida noma'lum xatolik: {req_err}",
            "status_code": 500,
            "type": "RequestException",
        }
    except json.JSONDecodeError as json_err:
        response_text_for_log = (
            response.text[:200]
            if "response" in locals()
            and response is not None
            and hasattr(response, "text")
            else "N/A"
        )
        current_logger.error(
            f"HEMIS API javobini JSON o'qishda xatolik ({method} {url}): {json_err}. Javob boshi: {response_text_for_log}"
        )
        return {
            "error": True,
            "message": "API serveridan kelgan javobni tushunib bo'lmadi (JSON xatosi).",
            "status_code": 500,
            "type": "JSONDecodeError",
        }
    except Exception as e:
        current_logger.error(
            f"HEMIS API da noma'lum umumiy xatolik ({method} {url}): {e}", exc_info=True
        )
        return {
            "error": True,
            "message": f"API so'rovida kutilmagan noma'lum xatolik: {str(e)[:100]}",
            "status_code": 500,
            "type": "Exception",
        }


def get_schedule_data_for_page(request_args, hemis_api_token, flask_app_logger=None):
    current_logger = flask_app_logger if flask_app_logger else logger_sh
    messages = get_status_messages()

    if not hemis_api_token:
        error_msg = "DIQQAT: API tokeni mavjud emas. Dars jadvalini ko'rsatib bo'lmaydi. Iltimos, tizimga qayta kiring."
        messages["errors"].append(error_msg)
        current_logger.error(error_msg)
        return {
            "messages": messages,
            "semesters": [],
            "weeks": [],
            "schedule_data": [],
            "group_id_display": "Noma'lum",
            "selected_semester_id": None,
            "selected_week_id": None,
            "hafta_kunlari_uz": HAFTA_KUNLARI_UZ,
            "title": "Dars Jadvali",
        }

    semesters_data = [
        {"id": "11", "name": "1-semestr"},
        {"id": "12", "name": "2-semestr"},
        {"id": "13", "name": "3-semestr"},
        {"id": "14", "name": "4-semestr"},
        {"id": "15", "name": "5-semestr"},
        {"id": "16", "name": "6-semestr"},
        {"id": "17", "name": "7-semestr"},
        {"id": "18", "name": "8-semestr"},
    ]

    weeks_data = []
    schedule_data_processed = []
    group_id_display = "Noma'lum"
    group_id_for_schedule = None

    selected_semester_id_str = request_args.get("semester_id")
    selected_semester_id = selected_semester_id_str

    selected_week_start_date_str = request_args.get("week_id")

    profile_response = make_api_request(
        "account/me", token=hemis_api_token, app_logger=current_logger
    )
    if profile_response.get("error"):
        if profile_response.get("status_code") == 401:
            messages["errors"].append(
                "Avtorizatsiya tokeni bilan muammo. Iltimos, tizimga qayta kiring."
            )
            hemis_api_token = None
    elif profile_response.get("data"):
        current_group_data = profile_response.get("data", {}).get("group", {})
        if current_group_data and current_group_data.get("id"):
            group_id_for_schedule = str(current_group_data.get("id"))
            group_name_display = current_group_data.get("name", group_id_for_schedule)
            group_id_display = f"{group_name_display} (ID: {group_id_for_schedule})"
        else:
            default_group_id = os.getenv("DEFAULT_GROUP_ID")
            if default_group_id:
                group_id_for_schedule = default_group_id
                group_id_display = f"Standart guruh"
    else:

        messages["warnings"].append(
            "Profil ma'lumotlari API dan bo'sh yoki xato bilan qaytdi. Guruh ID sini aniqlab bo'lmadi."
        )
        default_group_id = os.getenv("DEFAULT_GROUP_ID")
        if default_group_id:
            group_id_for_schedule = default_group_id
            group_id_display = f"Standart guruh"

    if not hemis_api_token:
        if not any(
            "Avtorizatsiya bilan bog'liq muammo" in err for err in messages["errors"]
        ):

            messages["errors"].append(
                "Avtorizatsiya bilan bog'liq muammo tufayli dars jadvali olinmadi."
            )
        return {
            "messages": messages,
            "semesters": semesters_data,
            "weeks": [],
            "schedule_data": [],
            "group_id_display": group_id_display,
            "selected_semester_id": selected_semester_id,
            "selected_week_id": selected_week_start_date_str,
            "hafta_kunlari_uz": HAFTA_KUNLARI_UZ,
            "title": "Dars Jadvali",
        }

    lessons_for_selected_semester = []
    if selected_semester_id and group_id_for_schedule:
        schedule_params = {
            "group": group_id_for_schedule,
            "semester": str(selected_semester_id),
        }
        current_logger.info(
            f"Dars jadvali uchun so'rov yuborilmoqda: params={schedule_params}"
        )
        schedule_response = make_api_request(
            "education/schedule",
            token=hemis_api_token,
            params=schedule_params,
            app_logger=current_logger,
        )

        if schedule_response.get("error"):

            messages["warnings"].append(
                f"Dars jadvalini olishda muammo: {schedule_response.get('message')}"
            )
            if schedule_response.get("status_code") == 401:
                messages["errors"].append(
                    "Dars jadvalini olishda avtorizatsiya muammosi. Qaytadan tizimga kiring."
                )
        elif schedule_response.get("data") and isinstance(
            schedule_response.get("data"), list
        ):
            lessons_for_selected_semester = schedule_response["data"]
            sem_name_obj = next(
                (
                    s
                    for s in semesters_data
                    if str(s["id"]) == str(selected_semester_id)
                ),
                None,
            )
            sem_name_str = (
                sem_name_obj["name"]
                if sem_name_obj
                else f"{selected_semester_id}-semestr"
            )

            if not lessons_for_selected_semester:

                messages["infos"].append(
                    f"Tanlangan '{sem_name_str}' uchun dars jadvali bo'sh yoki topilmadi."
                )
            else:
                unique_week_starts = {}
                for lesson in lessons_for_selected_semester:
                    lesson_timestamp = lesson.get("lesson_date")
                    if lesson_timestamp is not None:
                        try:
                            dt_object_utc = datetime.utcfromtimestamp(
                                int(lesson_timestamp)
                            )
                            actual_lesson_dt = dt_object_utc

                            week_start_dt = actual_lesson_dt.date() - timedelta(
                                days=actual_lesson_dt.weekday()
                            )
                            week_end_dt = week_start_dt + timedelta(days=6)

                            week_id_str = week_start_dt.isoformat()
                            if week_id_str not in unique_week_starts:
                                unique_week_starts[week_id_str] = {
                                    "id": week_id_str,
                                    "name": f"{week_start_dt.strftime('%d.%m.%Y')} - {week_end_dt.strftime('%d.%m.%Y')}",
                                }
                        except (ValueError, TypeError, OverflowError) as date_conv_err:

                            current_logger.warning(
                                f"Dars sanasini ('{lesson_timestamp}') konvertatsiya qilishda xato: {date_conv_err}. Dars ID: {lesson.get('id', 'N/A')}"
                            )

                weeks_data = sorted(
                    list(unique_week_starts.values()), key=lambda w: w["id"]
                )
        else:

            error_msg_detail = schedule_response.get(
                "message", "Noma'lum xato yoki ma'lumotlar formati noto'g'ri."
            )
            messages["warnings"].append(
                f"Dars jadvalini olishda muammo: {error_msg_detail}"
            )
            current_logger.warning(
                f"Dars jadvali API javobi muvaffaqiyatsiz yoki 'data' qismi yo'q/list emas: {str(schedule_response)[:500]}"
            )

    if (
        selected_semester_id
        and selected_week_start_date_str
        and lessons_for_selected_semester
    ):
        try:
            selected_week_start_dt_obj = date.fromisoformat(
                selected_week_start_date_str
            )
            selected_week_end_dt_obj = selected_week_start_dt_obj + timedelta(days=6)

            lessons_by_actual_date = defaultdict(list)

            for lesson_from_api in lessons_for_selected_semester:
                lesson_timestamp = lesson_from_api.get("lesson_date")
                if lesson_timestamp is not None:
                    try:
                        lesson_start_dt_utc = datetime.utcfromtimestamp(
                            int(lesson_timestamp)
                        )
                        actual_lesson_date_obj = lesson_start_dt_utc.date()

                        if (
                            selected_week_start_dt_obj
                            <= actual_lesson_date_obj
                            <= selected_week_end_dt_obj
                        ):
                            lesson_for_template = lesson_from_api.copy()
                            lesson_for_template["actual_datetime_obj"] = (
                                lesson_start_dt_utc
                            )

                            lesson_pair_data = lesson_from_api.get("lessonPair", {})
                            lesson_pair_data = (
                                lesson_pair_data
                                if isinstance(lesson_pair_data, dict)
                                else {}
                            )

                            lesson_pair_for_shablon = lesson_pair_data.copy()
                            pair_code = str(lesson_pair_data.get("code", "99"))
                            lesson_for_template["pair_code_for_sort"] = pair_code

                            api_start_time = lesson_pair_data.get("startTime")
                            api_end_time = lesson_pair_data.get("endTime")

                            lesson_pair_for_shablon["startTime"] = (
                                api_start_time
                                if api_start_time
                                and isinstance(api_start_time, str)
                                and api_start_time.strip()
                                else PAIR_STANDARD_TIMES.get(pair_code, {}).get(
                                    "startTime"
                                )
                            )
                            lesson_pair_for_shablon["endTime"] = (
                                api_end_time
                                if api_end_time
                                and isinstance(api_end_time, str)
                                and api_end_time.strip()
                                else PAIR_STANDARD_TIMES.get(pair_code, {}).get(
                                    "endTime"
                                )
                            )

                            lesson_for_template["lessonPair"] = lesson_pair_for_shablon
                            lessons_by_actual_date[actual_lesson_date_obj].append(
                                lesson_for_template
                            )
                    except (ValueError, TypeError, OverflowError) as date_filter_err:

                        current_logger.warning(
                            f"Tanlangan hafta uchun darslarni filterlashda sana konvertatsiyasida xato (dars sanasi: '{lesson_timestamp}'): {date_filter_err}"
                        )

            if not lessons_by_actual_date:
                week_name_display = next(
                    (
                        w["name"]
                        for w in weeks_data
                        if w["id"] == selected_week_start_date_str
                    ),
                    selected_week_start_date_str,
                )

                messages["infos"].append(
                    f"Tanlangan hafta ({week_name_display}) uchun dars topilmadi."
                )
            else:
                for date_key_sorted in sorted(lessons_by_actual_date.keys()):
                    lessons_on_this_date = lessons_by_actual_date[date_key_sorted]
                    sorted_lessons_items = sorted(
                        lessons_on_this_date,
                        key=lambda x: x.get("pair_code_for_sort", "99"),
                    )

                    schedule_data_processed.append(
                        {
                            "lessons": sorted_lessons_items,
                            "date_str": date_key_sorted.strftime("%d.%m.%Y"),
                            "weekday_idx": date_key_sorted.weekday(),
                        }
                    )
        except ValueError as e:

            messages["errors"].append(
                f"Tanlangan hafta ID si ('{selected_week_start_date_str}') noto'g'ri sana formatida: {e}"
            )
            current_logger.error(
                f"Noto'g'ri hafta ID formati ('{selected_week_start_date_str}'): {e}",
                exc_info=True,
            )
        except Exception as e_filter:

            messages["errors"].append(
                f"Hafta bo'yicha filtrlashda kutilmagan xatolik: {str(e_filter)[:100]}"
            )
            current_logger.error(f"Hafta filtrlashda xato: {e_filter}", exc_info=True)

    if not selected_semester_id and semesters_data:
        messages["infos"].append(
            "Dars jadvalini ko'rish uchun avval semestrni tanlang."
        )
    elif (
        selected_semester_id
        and not weeks_data
        and not messages["errors"]
        and not any(
            "uchun dars jadvali bo'sh" in info_msg for info_msg in messages["infos"]
        )
    ):
        messages["infos"].append(
            "Tanlangan semestr uchun haftalar topilmadi yoki darslar mavjud emas."
        )
    elif (
        selected_semester_id
        and weeks_data
        and not selected_week_start_date_str
        and not schedule_data_processed
        and not messages["errors"]
    ):
        messages["infos"].append("Dars jadvalini ko'rish uchun haftani tanlang.")
    elif not semesters_data and not messages["errors"]:
        messages["infos"].append(
            "Semestrlar ro'yxati topilmadi. Keyinroq urinib ko'ring yoki administrator bilan bog'laning."
        )

    return {
        "messages": messages,
        "semesters": semesters_data,
        "weeks": weeks_data,
        "schedule_data": schedule_data_processed,
        "group_id_display": group_id_display,
        "selected_semester_id": (
            str(selected_semester_id) if selected_semester_id is not None else None
        ),
        "selected_week_id": selected_week_start_date_str,
        "hafta_kunlari_uz": HAFTA_KUNLARI_UZ,
        "title": "Dars Jadvali",
    }
