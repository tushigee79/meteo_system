import os
import re

# Нэгтгэсэн файлын нэр
input_file = "full_project_code.txt"

def split_files():
    if not os.path.exists(input_file):
        print(f"Алдаа: '{input_file}' файл олдсонгүй!")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Файлуудыг тусгаарлаж буй хэсгийг хайх (Regex ашиглан)
    # FILE PATH: хэсгээс дараагийн FILE PATH хүртэлх бүх текстийг авна
    pattern = re.compile(r'={50}\nFILE PATH: (.*?)\n={50}\n\n(.*?)(?=\n={50}\nFILE PATH: |\Z)', re.DOTALL)
    
    matches = pattern.findall(content)

    if not matches:
        print("Задлах файл олдсонгүй. Формат буруу байна уу?")
        return

    for file_path, file_content in matches:
        file_path = file_path.strip()
        
        # Шаардлагатай хавтаснуудыг үүсгэх
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Хавтас үүсгэлээ: {directory}")

        # Файлыг бичих
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(file_content.rstrip())
        
        print(f"Сэргээгдсэн: {file_path}")

    print(f"\nАмжилттай! Нийт {len(matches)} файл сэргээгдлээ.")

if __name__ == "__main__":
    split_files()