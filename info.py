import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv
import logging


logger_info = logging.getLogger(__name__)
if not logger_info.hasHandlers():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


project_root = os.path.dirname(os.path.abspath(__file__))
dotenv_path_in_bot = os.path.join(project_root, ".env")
dotenv_path_above_bot = os.path.join(os.path.dirname(project_root), ".env")

if os.path.exists(dotenv_path_in_bot):
    load_dotenv(dotenv_path_in_bot, override=True)
elif os.path.exists(dotenv_path_above_bot):
    load_dotenv(dotenv_path_above_bot, override=True)
else:
    load_dotenv(override=True)


def fetch_student_data_with_token(token):
    """Berilgan API tokeni yordamida talabaning profil ma'lumotlarini oladi."""
    if not token:
        logger_info.warning("fetch_student_data_with_token: API tokeni berilmadi.")
        return {"success": False, "error": "API tokeni berilmadi."}

    profile_url = os.getenv(
        "HEMIS_PROFILE_URL", "https://student.samtuit.uz/rest/v1/account/me"
    )

    try:
        headers = {"Authorization": f"Bearer {token}"}
        logger_info.debug(
            f"Profil ma'lumotlari {profile_url} dan berilgan token bilan so'ralmoqda."
        )
        profile_response = requests.get(profile_url, headers=headers, timeout=15)
        profile_response.raise_for_status()

        profile_data_full = profile_response.json()

        if not profile_data_full.get("success") or not profile_data_full.get("data"):
            error_msg = profile_data_full.get(
                "message",
                "Profil ma'lumotlari API dan olinmadi yoki xatolik yuz berdi.",
            )
            logger_info.warning(
                f"Profil ma'lumotlarini olishda muvaffaqiyatsizlik: {error_msg}"
            )

            if profile_response.status_code == 401:
                error_msg = "Avtorizatsiya tokeni yaroqsiz yoki muddati o'tgan. Iltimos, qayta kiring."
            return {
                "success": False,
                "error": f"Profil ma'lumotlarini olishda xatolik: {error_msg}",
            }

        student_details = profile_data_full["data"]

        birth_timestamp = student_details.get("birth_date")
        if birth_timestamp:
            try:
                student_details["birth_date_formatted"] = datetime.utcfromtimestamp(
                    int(birth_timestamp)
                ).strftime("%d-%m-%Y")
            except (TypeError, ValueError, OSError) as e:
                logger_info.warning(
                    f"Tug'ilgan sanani formatlashda xatolik (timestamp: {birth_timestamp}): {e}"
                )
                student_details["birth_date_formatted"] = "Noma'lum sana"
        else:
            student_details["birth_date_formatted"] = "Kiritilmagan"

        def get_nested_name(
            data_dict, parent_key, name_key="name", default_value="Noma'lum"
        ):
            parent_obj = data_dict.get(parent_key)
            if isinstance(parent_obj, dict):
                return parent_obj.get(name_key, default_value)
            return default_value

        student_details["gender_name"] = get_nested_name(student_details, "gender")
        student_details["faculty_name"] = get_nested_name(student_details, "faculty")
        student_details["specialty_name"] = get_nested_name(
            student_details, "specialty"
        )
        student_details["educationType_name"] = get_nested_name(
            student_details, "educationType"
        )
        student_details["educationForm_name"] = get_nested_name(
            student_details, "educationForm"
        )
        student_details["paymentForm_name"] = get_nested_name(
            student_details, "paymentForm"
        )
        student_details["level_name"] = get_nested_name(student_details, "level")
        student_details["group_name"] = get_nested_name(student_details, "group")

        group_data = student_details.get("group")
        if isinstance(group_data, dict):
            education_lang_data = group_data.get("educationLang")
            if isinstance(education_lang_data, dict):
                student_details["group_educationLang_name"] = education_lang_data.get(
                    "name", "Noma'lum"
                )
            else:
                student_details["group_educationLang_name"] = "Noma'lum"
        else:
            student_details["group_educationLang_name"] = "Noma'lum"

        semester_data = student_details.get("semester")
        if isinstance(semester_data, dict):
            student_details["semester_name"] = semester_data.get("name", "Noma'lum")
            education_year_data = semester_data.get("education_year")
            if isinstance(education_year_data, dict):
                student_details["semester_education_year_name"] = (
                    education_year_data.get("name", "Noma'lum")
                )
            else:
                student_details["semester_education_year_name"] = "Noma'lum"
        else:
            student_details["semester_name"] = "Noma'lum"
            student_details["semester_education_year_name"] = "Noma'lum"

        student_details["country_name"] = get_nested_name(student_details, "country")
        student_details["province_name"] = get_nested_name(student_details, "province")
        student_details["district_name"] = get_nested_name(student_details, "district")
        student_details["image_url"] = student_details.get("image")
        student_details["_fetched_at_str"] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        university_info = student_details.get("university")
        if isinstance(university_info, dict):
            student_details["university_name_display"] = university_info.get(
                "name", "Noma'lum"
            )
        elif isinstance(university_info, str):
            student_details["university_name_display"] = university_info
        else:
            student_details["university_name_display"] = "Noma'lum"

        logger_info.info(
            f"Profil ma'lumotlari {student_details.get('full_name', 'Noma`lum talaba')} uchun muvaffaqiyatli olindi."
        )
        return {"success": True, "data": student_details}

    except requests.exceptions.HTTPError as e:
        error_message = f"Profil ma'lumotlarini olishda HTTP xatolik: {e.response.status_code} {e.response.reason}"
        if e.response.status_code == 401:
            error_message = "Avtorizatsiya tokeni yaroqsiz yoki muddati o'tgan. Iltimos, qayta kiring."
        logger_info.error(error_message, exc_info=True)
        return {"success": False, "error": error_message}
    except requests.exceptions.ConnectionError:
        logger_info.error(
            "Profil ma'lumotlarini olishda ulanish xatosi.", exc_info=True
        )
        return {
            "success": False,
            "error": "Profil ma'lumotlarini olishda ulanish xatosi. Internet aloqangizni tekshiring.",
        }
    except requests.exceptions.Timeout:
        logger_info.error(
            "Profil ma'lumotlarini olish uchun so'rov vaqti tugadi.", exc_info=True
        )
        return {
            "success": False,
            "error": "Profil ma'lumotlarini olish uchun so'rov vaqti tugadi.",
        }
    except requests.exceptions.RequestException as e:
        logger_info.error(
            f"Profil ma'lumotlarini olishda umumiy so'rov xatoligi: {str(e)}",
            exc_info=True,
        )
        return {
            "success": False,
            "error": f"Profil ma'lumotlarini olishda umumiy so'rov xatoligi.",
        }
    except json.JSONDecodeError:
        logger_info.error(
            "Profil ma'lumotlarini olishda serverdan kelgan javobni o'qishda xatolik.",
            exc_info=True,
        )
        return {
            "success": False,
            "error": "Profil ma'lumotlarini olishda serverdan kelgan javobni o'qishda xatolik.",
        }
    except Exception as e:
        logger_info.error(
            f"Profil ma'lumotlarini qayta ishlashda kutilmagan xatolik: {str(e)}",
            exc_info=True,
        )
        return {
            "success": False,
            "error": f"Profil ma'lumotlarini qayta ishlashda kutilmagan xatolik.",
        }


if __name__ == "__main__":
    print("info.py dan fetch_student_data_with_token funksiyasini test qilish...")

    HEMIS_LOGIN_FOR_TEST = os.getenv("HEMIS_LOGIN")
    HEMIS_PASSWORD_FOR_TEST = os.getenv("HEMIS_PASSWORD")

    if not HEMIS_LOGIN_FOR_TEST or not HEMIS_PASSWORD_FOR_TEST:
        print(
            "!!! Test uchun HEMIS_LOGIN yoki HEMIS_PASSWORD .env faylida topilmadi. Testni davom ettirib bo'lmaydi."
        )
    else:
        print(f"Test uchun HEMIS Login: {HEMIS_LOGIN_FOR_TEST[:4]}...")

        try:
            import hemis_api

            token_response = hemis_api.get_auth_token_with_credentials(
                HEMIS_LOGIN_FOR_TEST, HEMIS_PASSWORD_FOR_TEST
            )

            if token_response and token_response.get("success"):
                test_token = token_response.get("token")
                if test_token:
                    print(
                        f"Test uchun token olindi (qisqartirilgan): {test_token[:15]}..."
                    )
                else:
                    print("Token olishda xatolik: token qiymati None.")

                result = fetch_student_data_with_token(test_token)
                if result["success"]:
                    print("Ma'lumotlar (token bilan) muvaffaqiyatli olindi:")
                    print(f"  Ism: {result['data'].get('full_name')}")
                    print(f"  Fakultet: {result['data'].get('faculty_name')}")
                    print(f"  Guruh: {result['data'].get('group_name')}")
                    print(
                        f"  Universitet: {result['data'].get('university_name_display')}"
                    )
                    print(f"  Olingan vaqt: {result['data'].get('_fetched_at_str')}")
                else:
                    print(
                        f"Token bilan ma'lumot olishda xatolik yuz berdi: {result['error']}"
                    )
            else:
                print(
                    f"Test uchun token olishda xatolik: {token_response.get('error', 'Noma`lum xato')}"
                )
        except ImportError:
            print(
                "Xatolik: hemis_api.py modulini import qilib bo'lmadi. Testni o'tkazib bo'lmaydi."
            )
        except Exception as e_test:
            print(f"Test jarayonida kutilmagan xatolik: {e_test}")
