import os

# Paramètres
BASE_DIR = os.path.abspath(".")
OUTPUT_FILE = "structure.txt"

# Extensions de fichiers à exclure (ex: .py, .pyc, .log, etc.)
EXCLUDED_EXTENSIONS = {".py", ".pyc", ".pyo", ".db", ".sqlite3", ".log", ".PNG", ".jpg"}

# Noms de dossiers à exclure (exclusion récursive)
EXCLUDED_DIRS = {"__pycache__", ".git", "venv", "env", "migrations", "node_modules","admin","debug_toolbar","django_extensions"}

def is_excluded_file(filename):
    _, ext = os.path.splitext(filename)
    return ext in EXCLUDED_EXTENSIONS

def print_tree(directory, prefix="", output_lines=[]):
    try:
        entries = sorted(os.listdir(directory))
    except PermissionError:
        return

    entries = [e for e in entries if e not in EXCLUDED_DIRS]
    total = len(entries)

    for i, entry in enumerate(entries):
        path = os.path.join(directory, entry)
        connector = "└── " if i == total - 1 else "├── "
        line = f"{prefix}{connector}{entry}"
        output_lines.append(line)

        if os.path.isdir(path) and entry not in EXCLUDED_DIRS:
            extension = "    " if i == total - 1 else "│   "
            print_tree(path, prefix + extension, output_lines)
        elif not is_excluded_file(entry):
            continue

def generate_structure():
    output_lines = [f"Structure du projet Django depuis : {BASE_DIR}", ""]
    print_tree(BASE_DIR, "", output_lines)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
    print(f"✅ Structure sauvegardée dans '{OUTPUT_FILE}'")

if __name__ == "__main__":
    generate_structure()
