import requests
import json
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
import re
from typing import List, Dict, Any, Optional, Union

load_dotenv()
logger = logging.getLogger(__name__)


LOGIN_URL = os.getenv(
    "HEMIS_LOGIN_URL", "https://student.samtuit.uz/rest/v1/auth/login"
)
ATTENDANCE_URL = os.getenv(
    "HEMIS_ATTENDANCE_URL", "https://student.samtuit.uz/rest/v1/education/attendance"
)
API_TIMEOUT_STR = os.getenv("API_TIMEOUT", "25")
API_TIMEOUT = int(API_TIMEOUT_STR) if API_TIMEOUT_STR.isdigit() else 25


HEMIS_BASE_URL = os.getenv("HEMIS_BASE_URL", "https://student.samtuit.uz/rest/v1")
SUBJECT_TASK_STUDENT_LIST_URL = os.getenv(
    "HEMIS_SUBJECT_TASK_STUDENT_LIST_URL",
    f"{HEMIS_BASE_URL}/data/subject-task-student-list",
)

SCHEDULE_URL = os.getenv("HEMIS_SCHEDULE_URL", f"{HEMIS_BASE_URL}/education/schedule")


def get_auth_token_with_credentials(
    hemis_login: str, hemis_password: str
) -> Dict[str, Any]:
    if not hemis_login or not hemis_password:
        return {
            "success": False,
            "error": "Login va parol kiritilishi shart.",
            "token": None,
        }

    payload = {"login": str(hemis_login), "password": str(hemis_password)}
    headers = {"accept": "application/json", "Content-Type": "application/json"}
    response: Optional[requests.Response] = None
    try:
        logger.debug(f"Avtorizatsiya so'rovi yuborilmoqda: URL={LOGIN_URL}")
        response = requests.post(
            LOGIN_URL, json=payload, headers=headers, timeout=API_TIMEOUT
        )
        response.raise_for_status()
        data: Dict[str, Any] = response.json()
        if (
            data.get("success")
            and isinstance(data.get("data"), dict)
            and "token" in data["data"]
        ):
            logger.info(
                f"Login '{hemis_login[:4]}...' uchun token muvaffaqiyatli olindi."
            )
            return {"success": True, "token": data["data"]["token"], "error": None}
        else:
            error_message = data.get("message", "Token olishda noma'lum xatolik.")
            errors_detail = data.get("errors", "")
            logger.error(
                f"Login '{hemis_login[:4]}...' uchun token olishda xatolik: {error_message} - Tafsilotlar: {errors_detail}"
            )
            user_error_message = (
                "Login yoki parol xato."
                if "login yoki parol xato" in str(error_message).lower()
                or "unauthorized" in str(error_message).lower()
                else str(error_message)
            )
            return {"success": False, "token": None, "error": user_error_message}
    except requests.exceptions.HTTPError as http_err:
        error_text = "N/A"
        status_code_val: Union[str, int] = "N/A"
        specific_message = "Serverda HTTP xatoligi."
        if http_err.response is not None:
            error_text = http_err.response.text
            status_code_val = http_err.response.status_code
            try:
                error_data = http_err.response.json()
                if status_code_val == 401:
                    specific_message = "Login yoki parol xato."
                elif "message" in error_data and isinstance(error_data["message"], str):
                    specific_message = error_data["message"]
                logger.error(
                    f"Login '{hemis_login[:4]}...' uchun token olishda HTTP xatoligi: {status_code_val} - {specific_message} - Javob: {error_text[:200]}"
                )
            except json.JSONDecodeError:
                logger.error(
                    f"Login '{hemis_login[:4]}...' uchun HTTP xatoligi (JSON emas): {status_code_val} - Javob: {error_text[:200]}"
                )
                specific_message = (
                    f"Server xatosi ({status_code_val}). Javob formati noto'g'ri."
                )
        return {
            "success": False,
            "token": None,
            "error": specific_message,
            "status_code": status_code_val,
        }
    except requests.exceptions.Timeout:
        logger.error(
            f"Login '{hemis_login[:4]}...' uchun token olishda Timeout xatoligi: {LOGIN_URL} ga ulanish vaqti tugadi ({API_TIMEOUT}s)."
        )
        return {
            "success": False,
            "token": None,
            "error": "Serverga ulanish vaqti tugadi.",
        }
    except requests.exceptions.RequestException as req_err:
        logger.error(
            f"Login '{hemis_login[:4]}...' uchun token olishda umumiy so'rov xatoligi: {req_err}",
            exc_info=True,
        )
        return {
            "success": False,
            "token": None,
            "error": "Server bilan bog'lanishda umumiy xatolik.",
        }
    except json.JSONDecodeError:
        response_text_debug = (
            response.text[:200] if response and hasattr(response, "text") else "N/A"
        )
        logger.error(
            f"Login '{hemis_login[:4]}...' uchun token olishda JSON javobini o'qishda xatolik. Javob: {response_text_debug}"
        )
        return {
            "success": False,
            "token": None,
            "error": "Serverdan kutilmagan javob formati.",
        }

    return {
        "success": False,
        "token": None,
        "error": "Token olishda noma'lum ichki xatolik.",
    }


def fetch_raw_attendance_data_all(token: str) -> Dict[str, Any]:
    if not token:
        logger.warning("fetch_raw_attendance_data_all: Token berilmadi.")
        return {
            "success": False,
            "error": "Token berilmadi.",
            "data": None,
            "status_code": 400,
        }

    params: Dict[str, Any] = {}
    headers = {"accept": "application/json", "Authorization": f"Bearer {token}"}
    response: Optional[requests.Response] = None
    try:
        logger.info(f"Barcha davomat ma'lumotlari so'ralmoqda: URL={ATTENDANCE_URL}")
        response = requests.get(
            ATTENDANCE_URL, headers=headers, params=params, timeout=API_TIMEOUT
        )
        response.raise_for_status()
        api_response_data: Dict[str, Any] = response.json()
        if api_response_data.get("success", False) and "data" in api_response_data:
            return {
                "success": True,
                "data": api_response_data["data"],
                "error": None,
                "status_code": response.status_code,
            }
        else:
            error_msg = api_response_data.get(
                "message", "API dan ma'lumotlar olinmadi yoki xatolik."
            )
            logger.error(
                f"Barcha davomat ma'lumotlarini olishda API xatoligi: {error_msg}"
            )
            return {
                "success": False,
                "data": None,
                "error": error_msg,
                "status_code": response.status_code if response else 500,
            }

    except requests.exceptions.HTTPError as http_err:
        status_code_val: Union[str, int] = "N/A"
        if http_err.response is not None:
            status_code_val = http_err.response.status_code
        logger.error(
            f"Barcha davomat ma'lumotlarini olishda HTTP xatoligi: {status_code_val} - {http_err}",
            exc_info=True,
        )
        if status_code_val == 401:
            return {
                "success": False,
                "error": "Avtorizatsiya tokeni yaroqsiz yoki muddati o'tgan.",
                "data": None,
                "status_code": 401,
            }
        return {
            "success": False,
            "error": f"Serverda HTTP xatoligi ({status_code_val}).",
            "data": None,
            "status_code": status_code_val,
        }
    except requests.exceptions.RequestException as req_err:
        logger.error(
            f"Barcha davomat ma'lumotlarini olishda umumiy so'rov xatoligi: {req_err}",
            exc_info=True,
        )
        return {
            "success": False,
            "error": "Server bilan bog'lanishda muammo.",
            "data": None,
            "status_code": 503,
        }
    except json.JSONDecodeError as json_err:
        response_text_debug = (
            response.text[:200] if response and hasattr(response, "text") else "N/A"
        )
        logger.error(
            f"Barcha davomat ma'lumotlarini olishda JSON o'qish xatoligi: {json_err}. Javob: {response_text_debug}"
        )
        return {
            "success": False,
            "error": "Serverdan kutilmagan javob formati.",
            "data": None,
            "status_code": 500,
        }

    return {
        "success": False,
        "error": "Davomat ma'lumotlarini olishda noma'lum ichki xatolik.",
        "data": None,
        "status_code": 500,
    }


def format_attendance_data_flattened(
    raw_data_list: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not isinstance(raw_data_list, list):
        logger.warning("Formatlash uchun ma'lumotlar ro'yxat emas yoki bo'sh.")
        return []
    formatted_entries: List[Dict[str, Any]] = []
    for item in raw_data_list:
        try:
            subject_info: Dict[str, Any] = item.get("subject", {})
            semester_info: Dict[str, Any] = item.get("semester", {})
            training_type_info: Dict[str, Any] = item.get("trainingType", {})
            lesson_pair_info: Dict[str, Any] = item.get("lessonPair", {})
            employee_info: Dict[str, Any] = item.get("employee", {})

            lesson_date_readable = "Noma'lum sana"
            raw_lesson_date_val = item.get("lesson_date")
            if raw_lesson_date_val is not None:
                try:
                    lesson_date_readable = datetime.fromtimestamp(
                        int(raw_lesson_date_val)
                    ).strftime("%Y-%m-%d")
                except (TypeError, ValueError, OSError) as e:
                    logger.warning(
                        f"Dars sanasini ('lesson_date': {raw_lesson_date_val}) formatlashda xatolik: {e}."
                    )
                    lesson_date_readable = str(raw_lesson_date_val)

            is_excused_absence: bool = item.get("explicable", False)

            status_type = "unexcused"
            display_status_text = "Sababsiz"
            reason_text_val: str = item.get("reason", "")
            if not reason_text_val:
                reason_text_val = "Noma'lum sabab"

            if is_excused_absence:
                status_type = "excused"
                display_status_text = "Sababli"
                if not item.get("reason"):
                    reason_text_val = "Sababli (aniq sabab kiritilmagan)"
            else:
                if not item.get("reason"):
                    reason_text_val = "Sababsiz"

            formatted_entry: Dict[str, Any] = {
                "fan_nomi": subject_info.get("name", "N/A"),
                "semestr_id": str(semester_info.get("id", "N/A")),
                "semestr_nomi": semester_info.get("name", "N/A"),
                "mashgulot_turi_nomi": training_type_info.get("name", "N/A"),
                "dars_boshlanish_vaqti": lesson_pair_info.get("start_time")
                or lesson_pair_info.get("startTime", "N/A"),
                "dars_tugash_vaqti": lesson_pair_info.get("end_time")
                or lesson_pair_info.get("endTime", "N/A"),
                "oqituvchi_ismi": employee_info.get("name", "N/A"),
                "dars_sanasi": lesson_date_readable,
                "status_type": status_type,
                "display_status_text": display_status_text,
                "sabab_asli": reason_text_val,
            }
            formatted_entries.append(formatted_entry)
        except Exception as e:
            logger.error(
                f"Formatlashda kutilmagan xatolik: {e}. Yozuv: {item}", exc_info=True
            )
    return formatted_entries


def get_available_semesters(token: str) -> Dict[str, Any]:
    if not token:
        return {"success": False, "error": "Token berilmadi", "semesters": []}

    all_attendance_response = fetch_raw_attendance_data_all(token)
    error_msg_prefix = "Semestrlar ro'yxatini olishda xatolik"

    if not all_attendance_response.get("success"):
        api_err = all_attendance_response.get("error", "API dan javob olinmadi")
        status_code_val = all_attendance_response.get("status_code")
        if status_code_val == 401:
            return {
                "success": False,
                "error": "Avtorizatsiya tokeni yaroqsiz yoki muddati o'tgan.",
                "semesters": [],
            }
        logger.error(f"{error_msg_prefix}: {api_err}")
        return {
            "success": False,
            "error": f"{error_msg_prefix}: {api_err}",
            "semesters": [],
        }

    api_data = all_attendance_response.get("data")
    if not isinstance(api_data, list):
        logger.error(f"{error_msg_prefix}: API javobidagi 'data' qismi ro'yxat emas.")
        return {
            "success": False,
            "error": f"{error_msg_prefix}: Ma'lumotlar formati noto'g'ri.",
            "semesters": [],
        }

    unique_semesters: Dict[str, str] = {}
    for item in api_data:
        semester_info: Optional[Dict[str, Any]] = item.get("semester")
        if (
            isinstance(semester_info, dict)
            and "id" in semester_info
            and "name" in semester_info
        ):
            unique_semesters[str(semester_info["id"])] = str(semester_info["name"])

    semesters_list: List[Dict[str, str]] = [
        {"id": sem_id, "name": name} for sem_id, name in unique_semesters.items()
    ]

    def get_semester_sort_key(semester_item: Dict[str, str]) -> Union[int, float]:
        name = semester_item.get("name", "")
        match = re.search(r"(\d+)", name)
        if match:
            return int(match.group(1))
        try:
            sem_id_val = semester_item.get("id")
            if sem_id_val is not None:
                return int(sem_id_val) if str(sem_id_val).isdigit() else float("inf")
            return float("inf")
        except ValueError:
            return float("inf")

    semesters_list.sort(key=get_semester_sort_key)
    return {"success": True, "semesters": semesters_list}


def get_student_attendance_summary(
    token: str, semester_id: Optional[str] = None
) -> Dict[str, Any]:
    if not token:
        return {"success": False, "error": "Token berilmadi.", "data": None}

    all_raw_data_response = fetch_raw_attendance_data_all(token)
    error_msg_prefix = "Davomat ma'lumotlarini olishda xatolik"

    if not all_raw_data_response.get("success"):
        api_err = all_raw_data_response.get("error", "API dan javob olinmadi")
        status_code_val = all_raw_data_response.get("status_code")
        if status_code_val == 401:
            return {
                "success": False,
                "error": "Avtorizatsiya tokeni yaroqsiz yoki muddati o'tgan.",
                "data": None,
            }
        logger.error(f"{error_msg_prefix}: {api_err}")
        return {
            "success": False,
            "error": f"{error_msg_prefix}: {api_err}",
            "data": None,
        }

    api_data = all_raw_data_response.get("data")
    if not isinstance(api_data, list):
        logger.error(f"{error_msg_prefix}: API javobidagi 'data' qismi ro'yxat emas.")
        return {
            "success": False,
            "error": f"{error_msg_prefix}: Ma'lumotlar formati noto'g'ri.",
            "data": None,
        }

    all_items: List[Dict[str, Any]] = api_data
    items_for_processing: List[Dict[str, Any]] = []

    if semester_id and semester_id.lower() != "all":
        logger.info(
            f"Davomat ma'lumotlari '{semester_id}' ID li semestr uchun filtrlanmoqda."
        )
        for item in all_items:
            semester_info: Optional[Dict[str, Any]] = item.get("semester", {})
            if isinstance(semester_info, dict) and str(semester_info.get("id")) == str(
                semester_id
            ):
                items_for_processing.append(item)
    else:
        items_for_processing = all_items

    formatted_records = format_attendance_data_flattened(items_for_processing)

    total_absences = len(formatted_records)
    unexcused_absences = sum(
        1 for r in formatted_records if r.get("status_type") == "unexcused"
    )
    excused_absences = sum(
        1 for r in formatted_records if r.get("status_type") == "excused"
    )

    summary_data: Dict[str, Any] = {
        "umumiy_darslar": total_absences,
        "sababli": excused_absences,
        "sababsiz": unexcused_absences,
        "records": formatted_records,
    }

    logger.info(
        f"{len(formatted_records)} ta davomat yozuvi qaytarildi (semestr: {semester_id if semester_id and semester_id.lower() != 'all' else 'barchasi'})."
    )
    return {"success": True, "data": summary_data}


def fetch_student_tasks_list(
    token: str, params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Talabaga berilgan topshiriqlar ro'yxatini HEMIS API orqali oladi.
    GET /v1/data/subject-task-student-list
    """
    if not token:
        logger.warning("fetch_student_tasks_list: Token berilmadi.")
        return {
            "success": False,
            "error": "Token berilmadi.",
            "data": None,
            "status_code": 400,
        }

    headers = {"accept": "application/json", "Authorization": f"Bearer {token}"}
    actual_params = params.copy() if params else {}
    actual_params.setdefault("limit", 200)

    response: Optional[requests.Response] = None
    try:
        logger.info(
            f"Talaba topshiriqlari ro'yxati so'ralmoqda: URL={SUBJECT_TASK_STUDENT_LIST_URL}, Params={actual_params}"
        )
        response = requests.get(
            SUBJECT_TASK_STUDENT_LIST_URL,
            headers=headers,
            params=actual_params,
            timeout=API_TIMEOUT,
        )
        response.raise_for_status()
        api_response_data: Dict[str, Any] = response.json()

        if api_response_data.get("success", False) and "data" in api_response_data:
            all_tasks = []
            pagination_info = None

            data_content = api_response_data["data"]

            if isinstance(data_content, list) and len(data_content) > 0:
                for group_data in data_content:
                    if (
                        isinstance(group_data, dict)
                        and "items" in group_data
                        and isinstance(group_data["items"], list)
                    ):
                        all_tasks.extend(group_data["items"])
                if (
                    isinstance(data_content[0], dict)
                    and "pagination" in data_content[0]
                ):
                    pagination_info = data_content[0].get("pagination")
                    if isinstance(pagination_info, list) and len(pagination_info) > 0:
                        pagination_info = pagination_info[0]
            elif isinstance(data_content, dict):
                if "items" in data_content and isinstance(data_content["items"], list):
                    all_tasks = data_content["items"]
                if "pagination" in data_content:
                    pagination_info = data_content["pagination"]

            logger.info(f"{len(all_tasks)} ta topshiriq API dan olindi.")
            return {
                "success": True,
                "tasks": all_tasks,
                "pagination": pagination_info,
                "error": None,
                "status_code": response.status_code,
            }
        else:
            error_msg = api_response_data.get(
                "message", "API dan topshiriqlar olinmadi yoki xatolik."
            )
            logger.error(
                f"Talaba topshiriqlarini olishda API xatoligi: {error_msg}. Javob: {api_response_data}"
            )
            return {
                "success": False,
                "tasks": None,
                "pagination": None,
                "error": error_msg,
                "status_code": response.status_code if response else 500,
            }

    except requests.exceptions.HTTPError as http_err:
        status_code_val: Union[str, int] = (
            http_err.response.status_code if http_err.response is not None else "N/A"
        )
        error_text = (
            http_err.response.text
            if http_err.response is not None
            else "No response text"
        )
        logger.error(
            f"Talaba topshiriqlarini olishda HTTP xatoligi: {status_code_val} - {http_err}. Javob: {error_text[:500]}",
            exc_info=True,
        )
        if status_code_val == 401:
            return {
                "success": False,
                "error": "Avtorizatsiya tokeni yaroqsiz yoki muddati o'tgan.",
                "tasks": None,
                "pagination": None,
                "status_code": 401,
            }
        return {
            "success": False,
            "error": f"Serverda HTTP xatoligi ({status_code_val}).",
            "tasks": None,
            "pagination": None,
            "status_code": status_code_val,
        }
    except requests.exceptions.RequestException as req_err:
        logger.error(
            f"Talaba topshiriqlarini olishda umumiy so'rov xatoligi: {req_err}",
            exc_info=True,
        )
        return {
            "success": False,
            "error": "Server bilan bog'lanishda muammo.",
            "tasks": None,
            "pagination": None,
            "status_code": 503,
        }
    except json.JSONDecodeError as json_err:
        response_text_debug = (
            response.text[:500] if response and hasattr(response, "text") else "N/A"
        )
        logger.error(
            f"Talaba topshiriqlarini olishda JSON o'qish xatoligi: {json_err}. Javob boshi: {response_text_debug}"
        )
        return {
            "success": False,
            "error": "Serverdan kutilmagan javob formati.",
            "tasks": None,
            "pagination": None,
            "status_code": 500,
        }

    return {
        "success": False,
        "error": "Topshiriqlarni olishda noma'lum ichki xatolik.",
        "tasks": None,
        "pagination": None,
        "status_code": 500,
    }


def get_raw_schedule_data(
    token: str,
    group_id: str,
    semester_id: str,
    app_logger: Optional[logging.Logger] = None,
) -> Dict[str, Any]:
    """
    Guruh va semestr uchun xom dars jadvali ma'lumotlarini oladi.
    """
    if not token:
        return {
            "success": False,
            "error": "Token berilmadi.",
            "data": None,
            "status_code": 400,
        }
    if not group_id or not semester_id:
        return {
            "success": False,
            "error": "Guruh ID yoki Semestr ID berilmadi.",
            "data": None,
            "status_code": 400,
        }

    current_logger = app_logger if app_logger else logger

    headers = {"Authorization": f"Bearer {token}", "accept": "application/json"}
    params = {"group": group_id, "semester": semester_id, "limit": 500}

    current_logger.info(
        f"Dars jadvali so'ralmoqda: URL={SCHEDULE_URL}, Params={params}"
    )
    response: Optional[requests.Response] = None
    try:
        response = requests.get(
            SCHEDULE_URL, headers=headers, params=params, timeout=API_TIMEOUT
        )
        response.raise_for_status()
        api_response_data: Dict[str, Any] = response.json()

        if api_response_data.get("success", False) and "data" in api_response_data:
            schedule_items = api_response_data["data"]

            if not isinstance(schedule_items, list):
                current_logger.warning(
                    f"Dars jadvali 'data' qismi list emas: {type(schedule_items)}. Javob: {str(api_response_data)[:300]}"
                )

                if (
                    isinstance(schedule_items, dict)
                    and "items" in schedule_items
                    and isinstance(schedule_items["items"], list)
                ):
                    schedule_items = schedule_items["items"]
                else:
                    return {
                        "success": False,
                        "error": "API dan kutilmagan dars jadvali formati.",
                        "data": None,
                        "status_code": 500,
                    }

            current_logger.info(
                f"{len(schedule_items)} ta dars yozuvi API dan olindi (guruh: {group_id}, sem: {semester_id})."
            )
            return {
                "success": True,
                "data": schedule_items,
                "error": None,
                "status_code": response.status_code,
            }
        else:
            error_msg = api_response_data.get(
                "message", "API dan dars jadvali olinmadi yoki xatolik."
            )
            current_logger.error(
                f"Dars jadvalini olishda API xatoligi: {error_msg}. Javob: {api_response_data}"
            )
            return {
                "success": False,
                "data": None,
                "error": error_msg,
                "status_code": response.status_code if response else 500,
            }

    except requests.exceptions.HTTPError as http_err:
        status_code_val = (
            http_err.response.status_code if http_err.response is not None else "N/A"
        )
        error_text = (
            http_err.response.text
            if http_err.response is not None
            else "No response text"
        )
        current_logger.error(
            f"Dars jadvalini olishda HTTP xatoligi: {status_code_val} - {http_err}. Javob: {error_text[:300]}",
            exc_info=True,
        )
        if status_code_val == 401:
            return {
                "success": False,
                "error": "Avtorizatsiya tokeni yaroqsiz yoki muddati o'tgan.",
                "data": None,
                "status_code": 401,
            }
        return {
            "success": False,
            "error": f"Serverda HTTP xatoligi ({status_code_val}).",
            "data": None,
            "status_code": status_code_val,
        }
    except requests.exceptions.RequestException as req_err:
        current_logger.error(
            f"Dars jadvalini olishda umumiy so'rov xatoligi: {req_err}", exc_info=True
        )
        return {
            "success": False,
            "error": "Server bilan bog'lanishda muammo.",
            "data": None,
            "status_code": 503,
        }
    except json.JSONDecodeError as json_err:
        response_text_debug = (
            response.text[:300] if response and hasattr(response, "text") else "N/A"
        )
        current_logger.error(
            f"Dars jadvalini olishda JSON o'qish xatoligi: {json_err}. Javob boshi: {response_text_debug}"
        )
        return {
            "success": False,
            "error": "Serverdan kutilmagan javob formati.",
            "data": None,
            "status_code": 500,
        }

    return {
        "success": False,
        "error": "Dars jadvalini olishda noma'lum ichki xatolik.",
        "data": None,
        "status_code": 500,
    }


if __name__ == "__main__":
    print("HEMIS API Modulini Test Qilish")
    test_login = os.getenv("HEMIS_LOGIN")
    test_password = os.getenv("HEMIS_PASSWORD")

    if not test_login or not test_password:
        print(
            "DIQQAT: Test uchun HEMIS_LOGIN yoki HEMIS_PASSWORD .env faylida topilmadi..."
        )
    else:
        print(f"Test uchun HEMIS Login: {test_login[:4]}...")
        token_response = get_auth_token_with_credentials(test_login, test_password)

        if token_response.get("success") and token_response.get("token"):
            test_token = token_response["token"]
            print(f"\nOlingan Token (qisqartirilgan): {test_token[:15]}...")

            print("\nDars jadvali (xom) so'ralmoqda...")

            test_group_id = os.getenv("TEST_GROUP_ID", "YOUR_TEST_GROUP_ID")
            test_semester_id = os.getenv("TEST_SEMESTER_ID", "YOUR_TEST_SEMESTER_ID")

            if (
                test_group_id != "YOUR_TEST_GROUP_ID"
                and test_semester_id != "YOUR_TEST_SEMESTER_ID"
            ):
                schedule_data_response = get_raw_schedule_data(
                    test_token, test_group_id, test_semester_id
                )
                if schedule_data_response.get("success"):
                    lessons = schedule_data_response.get("data", [])
                    print(f"Olingan darslar soni: {len(lessons)}")
                    if lessons:
                        print(
                            "Birinchi dars namunasi:",
                            json.dumps(lessons[0], indent=2, ensure_ascii=False),
                        )
                else:
                    print(
                        f"Dars jadvalini olishda xatolik: {schedule_data_response.get('error', 'Noma`lum xato')}"
                    )
            else:
                print(
                    "Dars jadvalini test qilish uchun .env faylida TEST_GROUP_ID va TEST_SEMESTER_ID ni sozlang."
                )

        else:
            print(
                f"\nToken olib bo'lmadi: {token_response.get('error')}. Keyingi testlar o'tkazib yuborilmoqda."
            )
