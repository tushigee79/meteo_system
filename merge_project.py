import os

# Төслийн бүх кодыг нэгтгэх файлын нэр
output_file = "full_project_code.txt"

# Элдэв хэрэггүй фолдеруудыг алгасах
exclude_dirs = {'__pycache__', 'venv', '.git', 'media', 'static_env', 'migrations'}
# Зөвхөн эдгээр өргөтгөлтэй файлуудыг унших
include_extensions = {'.py', '.html', '.js', '.css'}

def merge_files():
    with open(output_file, 'w', encoding='utf-8') as outfile:
        # Одоо байгаа хавтаснаас эхлэн хайна
        for root, dirs, files in os.walk("."):
            # Хэрэггүй фолдеруудыг хасах
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                file_ext = os.path.splitext(file)[1]
                if file_ext in include_extensions:
                    file_path = os.path.join(root, file)
                    
                    # Merge хийх файлууд руу бичих
                    outfile.write(f"\n{'='*50}\n")
                    outfile.write(f"FILE PATH: {file_path}\n")
                    outfile.write(f"{'='*50}\n\n")
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as infile:
                            outfile.write(infile.read())
                    except Exception as e:
                        outfile.write(f"Error reading file: {e}\n")
                        
    print(f"Амжилттай! Бүх код '{output_file}' дотор хадгалагдлаа.")

if __name__ == "__main__":
    merge_files()