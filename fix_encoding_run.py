import pathlib, shutil

root = pathlib.Path(r"D:\meteo_system")
exts = {".py", ".html", ".js", ".css"}

# ⚠️ raw string-д төгсгөлд \ тавихгүй
skip_contains = [
    "\\venv\\",
    "\\staticfiles\\",
    "\\node_modules\\",
    "\\.git\\",
    "\\static\\admin\\js\\vendor\\",
    "\\static\\vendor\\select2\\",
]

def should_skip(p: pathlib.Path) -> bool:
    s = str(p).lower()
    return any(x.lower() in s for x in skip_contains)

def repair_mojibake(s: str) -> str:
    """
    UTF-8 байтыг latin1 гэж буруу уншсан тохиолдлыг буцааж засна
    """
    try:
        return s.encode("latin1").decode("utf-8")
    except Exception:
        return s

fixed = 0

for p in root.rglob("*"):
    if not p.is_file():
        continue
    if p.suffix.lower() not in exts:
        continue
    if should_skip(p):
        continue

    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue

    # Mojibake шинжтэй файлууд л
    if ("Ð" not in text) and ("Ñ" not in text) and ("Ã" not in text):
        continue

    new = repair_mojibake(text)
    if new != text:
        bak = p.with_suffix(p.suffix + ".bak")
        if not bak.exists():
            shutil.copy2(p, bak)

        p.write_text(new, encoding="utf-8")
        fixed += 1
        print("fixed:", p)

print("DONE. fixed_files =", fixed)
