
import datetime
import random


subjects = [
    "Web dasturlash (Django/Flask)",
    "Mobil ilovalar (Android/iOS)",
    "Ma'lumotlar bazasini loyihalash",
    "Dasturiy ta'minotni testlash",
    "Algoritmlar va ma'lumotlar tuzilmalari",
    "Obyektga yo'naltirilgan dasturlash",
    "Python dasturlash tili",
    "JavaScript va Frontend texnologiyalari",
    "Bulutli texnologiyalar (AWS/Azure)",
    "Kiberxavfsizlik asoslari"
]

task_types = [
    "Amaliy ish",
    "Mustaqil ish",
    "Laboratoriya ishi",
    "Kurs ishi",
    "Referat",
    "Taqdimot tayyorlash"
]

descriptions_templates = [
    "{} bo'yicha {}. Barcha materiallarni PDF formatida yuklang.",
    "{} fanidan {}. Loyiha kodini GitHub'ga yuklab, havolasini topshiring.",
    "{} mavzusida {}. Ishni o'z vaqtida topshirishga harakat qiling.",
    "{} uchun {}. Detallashtirilgan hisobot talab etiladi.",
    "{} fanidan navbatdagi {}. Guruh bo'lib ishlash mumkin."
]

def generate_random_deadline():
    days_ahead = random.randint(7, 60) 
    deadline_date = datetime.date.today() + datetime.timedelta(days=days_ahead)
    return deadline_date.strftime("%Y-%m-%d")

toplangan_topsiriqlar = []
for i in range(10): 
    subject = random.choice(subjects)
    task_type_name = random.choice(task_types)
    description_template = random.choice(descriptions_templates)
    
    
    
    task_item = {
        "name": f"{subject} - {task_type_name} #{i+1}", 
        "taskType": {"name": task_type_name},
        "trainingType": {"name": random.choice(["Ma'ruza", "Amaliyot", "Seminar"])}, 
        "comment": description_template.format(subject, task_type_name.lower()),
        "deadline_timestamp": (datetime.datetime.strptime(generate_random_deadline(), "%Y-%m-%d")).timestamp(),
        "max_ball": random.choice([5, 10, 15, 20]),
        "files": [] 
    }
    toplangan_topsiriqlar.append(task_item)

