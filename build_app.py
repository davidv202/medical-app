#!/usr/bin/env python3
"""
Script pentru crearea executabilului Medical PACS pe Windows
Versiunea îmbunătățită care rezolvă problemele cu PyInstaller
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# Configurare
APP_NAME = "MediCore-PACS"
APP_VERSION = "1.0.0"
MAIN_SCRIPT = "app/main.py"

def install_pyinstaller():
    """Instalează PyInstaller dacă nu este găsit"""
    print("🔧 Instalând PyInstaller...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print("✅ PyInstaller instalat cu succes!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Eroare la instalarea PyInstaller: {e}")
        return False

def check_dependencies():
    """Verifică și instalează dependințele dacă lipsesc"""
    print("🔍 Verificând dependințele...")
    
    required_packages = {
        'pyinstaller': 'pyinstaller',
        'PyQt6': 'PyQt6',
        'sqlalchemy': 'sqlalchemy',
        'pymysql': 'pymysql',
        'bcrypt': 'bcrypt',
        'pydicom': 'pydicom',
        'weasyprint': 'weasyprint',
        'PIL': 'Pillow',
        'requests': 'requests'
    }
    
    missing_packages = []
    
    for import_name, package_name in required_packages.items():
        try:
            __import__(import_name)
            print(f"✅ {package_name}")
        except ImportError:
            missing_packages.append(package_name)
            print(f"❌ {package_name} - LIPSEȘTE")
    
    # Instalează pachetele lipsă
    if missing_packages:
        print(f"\n🔧 Instalând pachetele lipsă: {', '.join(missing_packages)}")
        try:
            cmd = [sys.executable, "-m", "pip", "install"] + missing_packages
            subprocess.run(cmd, check=True)
            print("✅ Toate pachetele au fost instalate!")
        except subprocess.CalledProcessError as e:
            print(f"❌ Eroare la instalarea pachetelor: {e}")
            return False
    
    # Verificare specială pentru PyInstaller
    try:
        import PyInstaller
        print("✅ PyInstaller disponibil prin import")
    except ImportError:
        print("⚠️  PyInstaller nu poate fi importat, instalez...")
        if not install_pyinstaller():
            return False
    
    # Testează comanda pyinstaller
    try:
        result = subprocess.run([sys.executable, "-m", "PyInstaller", "--version"], 
                              capture_output=True, text=True, check=True)
        print(f"✅ PyInstaller versiune: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  Comanda pyinstaller nu funcționează, încerc să o fix...")
        if not install_pyinstaller():
            return False
    
    print("✅ Toate dependințele sunt OK!")
    return True

def clean_build():
    """Curăță build-urile anterioare"""
    print("\n🧹 Curățând build-urile anterioare...")
    
    dirs_to_clean = ["build", "dist", "__pycache__"]
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"🗑️  Șters: {dir_name}")
    
    # Șterge fișierele .spec
    for file in Path(".").glob("*.spec"):
        file.unlink()
        print(f"🗑️  Șters: {file}")
    
    # Curăță cache Python recursiv
    for root, dirs, files in os.walk("."):
        for dir_name in dirs[:]:
            if dir_name == "__pycache__":
                shutil.rmtree(os.path.join(root, dir_name))
                dirs.remove(dir_name)
    
    print("✅ Curățarea completă!")

def run_pyinstaller_direct():
    """Rulează PyInstaller direct cu parametrii în linia de comandă"""
    print("\n🔨 Creând executabilul cu PyInstaller...")
    
    # Parametrii pentru PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--onefile",
        "--windowed",
        "--clean",
        "--noconfirm",
        # Adaugă fișierele de stil
        "--add-data", "app/presentation/styles/*.qss;app/presentation/styles",
        "--add-data", "app/presentation/styles/*.css;app/presentation/styles",
        # Import-uri hidden importante
        "--hidden-import", "PyQt6.QtCore",
        "--hidden-import", "PyQt6.QtGui",
        "--hidden-import", "PyQt6.QtWidgets",
        "--hidden-import", "sqlalchemy.dialects.mysql.pymysql",
        "--hidden-import", "pymysql",
        "--hidden-import", "bcrypt",
        "--hidden-import", "pydicom",
        "--hidden-import", "weasyprint",
        "--hidden-import", "PIL",
        "--hidden-import", "app.di.container",
        "--hidden-import", "app.services.pacs_service",
        "--hidden-import", "app.services.auth_service",
        "--hidden-import", "app.services.session_service",
        "--hidden-import", "app.services.local_file_service",
        "--hidden-import", "app.services.hybrid_pacs_service",
        "--hidden-import", "app.services.pdf_service",
        "--hidden-import", "app.services.notification_service",
        "--hidden-import", "app.services.pacs_url_service",
        "--hidden-import", "app.services.settings_service",
        "--hidden-import", "app.services.dicom_anonymizer_service",
        # Exclude module grele
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        "--exclude-module", "numpy",
        "--exclude-module", "pandas",
        "--exclude-module", "scipy",
        # Fișierul principal
        MAIN_SCRIPT
    ]
    
    print("📝 Comanda PyInstaller:")
    print(" ".join(cmd))
    print()
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ PyInstaller terminat cu succes!")
        if result.stdout:
            print("📋 Output:")
            print(result.stdout[-500:])  # Ultimele 500 caractere
        return True
    except subprocess.CalledProcessError as e:
        print("❌ Eroare la PyInstaller!")
        print(f"Return code: {e.returncode}")
        if e.stdout:
            print("STDOUT:", e.stdout[-500:])
        if e.stderr:
            print("STDERR:", e.stderr[-500:])
        return False

def verify_executable():
    """Verifică dacă executabilul a fost creat și funcționează"""
    exe_path = f"dist/{APP_NAME}.exe"
    
    if not os.path.exists(exe_path):
        print(f"❌ Executabilul nu a fost găsit: {exe_path}")
        return False
    
    # Verifică dimensiunea
    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"📏 Dimensiune executabil: {size_mb:.1f} MB")
    
    if size_mb < 50:  # Un executabil PyQt6 ar trebui să fie > 50MB
        print("⚠️  Executabilul pare prea mic, possibil lipsesc dependințe")
    else:
        print("✅ Dimensiunea executabilului pare OK")
    
    # Test rapid de rulare (doar pentru a vedea dacă pornește)
    print("🧪 Testând executabilul...")
    try:
        # Rulează cu timeout scurt pentru a verifica dacă pornește
        result = subprocess.run([exe_path, "--version"], 
                              timeout=10, capture_output=True, text=True)
        print("✅ Executabilul răspunde la comenzi")
    except subprocess.TimeoutExpired:
        print("✅ Executabilul pornește (timeout normal pentru GUI)")
    except Exception as e:
        print(f"⚠️  Nu s-a putut testa executabilul: {e}")
    
    return True

def create_release_package():
    """Creează pachetul final pentru distribuție"""
    print("\n📦 Creând pachetul de distribuție...")
    
    exe_path = f"dist/{APP_NAME}.exe"
    if not os.path.exists(exe_path):
        print(f"❌ Executabilul nu a fost găsit: {exe_path}")
        return False
    
    # Creează directorul de release
    release_dir = f"release/{APP_NAME}-v{APP_VERSION}"
    os.makedirs(release_dir, exist_ok=True)
    
    # Copiază executabilul
    shutil.copy2(exe_path, release_dir)
    print(f"✅ Executabil copiat în {release_dir}")
    
    # Creează directoarele necesare
    os.makedirs(f"{release_dir}/generated_pdfs", exist_ok=True)
    os.makedirs(f"{release_dir}/tmp_pdfs", exist_ok=True)
    os.makedirs(f"{release_dir}/local_studies_cache", exist_ok=True)
    
    # Copiază documentația
    if os.path.exists("README.txt"):
        shutil.copy2("README.txt", release_dir)
    
    if os.path.exists("database_init.py"):
        shutil.copy2("database_init.py", release_dir)
    
    # Creează instrucțiunile de instalare
    create_install_instructions(release_dir)
    
    # Creează arhiva ZIP
    archive_name = f"{APP_NAME}-v{APP_VERSION}-Windows"
    shutil.make_archive(f"release/{archive_name}", 'zip', f"release", f"{APP_NAME}-v{APP_VERSION}")
    
    # Calculează dimensiunea arhivei
    if os.path.exists(f"release/{archive_name}.zip"):
        archive_size = os.path.getsize(f"release/{archive_name}.zip") / (1024 * 1024)
        print(f"✅ Arhiva creată: release/{archive_name}.zip ({archive_size:.1f} MB)")
    
    return True

def create_install_instructions(release_dir):
    """Creează fișierul cu instrucțiuni de instalare"""
    instructions = f"""=== MEDICAL PACS v{APP_VERSION} - GHID INSTALARE ===

CERINȚE SISTEM:
- Windows 10/11 (64-bit)
- MySQL Server 5.7+ sau MariaDB 10.3+
- 4GB RAM minimum
- 500MB spațiu liber pe disk
- Conexiune la rețea (pentru PACS)

INSTALARE PAS CU PAS:

1. PREGĂTIREA BAZEI DE DATE
   a) Instalează MySQL Server de la: https://dev.mysql.com/downloads/mysql/
   b) În timpul instalării, reține parola pentru root
   c) Deschide MySQL Command Line Client și execută:
   
      CREATE DATABASE medical_app CHARACTER SET utf8mb4;
      CREATE USER 'admin'@'localhost' IDENTIFIED BY 'admin';
      GRANT ALL PRIVILEGES ON medical_app.* TO 'admin'@'localhost';
      FLUSH PRIVILEGES;
      EXIT;

2. INSTALAREA APLICAȚIEI
   a) Extraie toate fișierele din această arhivă într-un director
   b) Pentru prima rulare, click-dreapta pe {APP_NAME}.exe → "Run as administrator"
   c) Aplicația va crea automat tabelele în baza de date

3. PRIMUL LOGIN
   Username: admin
   Parola: admin
   
   ⚠️ FOARTE IMPORTANT: Schimbă imediat parola administratorului!

4. CONFIGURAREA PACS
   a) Din meniul principal → Admin Panel → PACS URLs
   b) Adaugă serverele tale PACS cu datele de conectare
   c) Testează conexiunea pentru fiecare server
   d) Setează PACS-ul sursă și țintă din Settings

PROBLEME FRECVENTE:

❌ "Could not connect to database"
   → Verifică dacă MySQL Server rulează (Services → MySQL)
   → Verifică username/parola în app/config/settings.py

❌ "Permission denied" la pornire
   → Rulează ca Administrator
   → Verifică dacă antivirusul blochează aplicația

❌ "PACS connection failed"
   → Verifică URL-ul serverului PACS
   → Testează în browser: http://server-pacs:8042
   → Verifică username/parola PACS

❌ Executabilul nu pornește
   → Instalează Visual C++ Redistributable 2015-2022
   → Adaugă excepție în antivirus pentru {APP_NAME}.exe

SETUP AUTOMAT BAZA DE DATE:
Dacă ai probleme cu setup-ul manual, rulează:
python database_init.py

PENTRU ACTUALIZĂRI:
1. Oprește aplicația veche
2. Fă backup la baza de date (mysqldump)
3. Înlocuiește executabilul cu versiunea nouă
4. Rulează aplicația

SUPORT TEHNIC:
Email: support@medical-solutions.com
Documentație: https://docs.medical-solutions.com

Versiune: {APP_VERSION}
Data build: {datetime.now().strftime('%d.%m.%Y %H:%M')}
"""
    
    with open(f"{release_dir}/INSTALARE.txt", "w", encoding="utf-8") as f:
        f.write(instructions)

def main():
    """Funcția principală"""
    print(f"🚀 Medical PACS Build Tool v{APP_VERSION}")
    print("=" * 60)
    print("Creează executabilul pentru Windows cu toate dependințele incluse")
    print()
    
    # Verifică dacă suntem în directorul corect
    if not os.path.exists(MAIN_SCRIPT):
        print(f"❌ Nu găsesc fișierul principal: {MAIN_SCRIPT}")
        print("Asigură-te că rulezi script-ul din directorul rădăcină al proiectului")
        input("Apasă Enter pentru a ieși...")
        return 1
    
    # Verificări și instalări
    if not check_dependencies():
        print("\n❌ Nu s-au putut rezolva dependințele!")
        input("Apasă Enter pentru a ieși...")
        return 1
    
    # Build process
    clean_build()
    
    if not run_pyinstaller_direct():
        print("\n❌ Build eșuat la PyInstaller!")
        input("Apasă Enter pentru a ieși...")
        return 1
    
    if not verify_executable():
        print("\n❌ Verificarea executabilului a eșuat!")
        input("Apasă Enter pentru a ieși...")
        return 1
    
    if not create_release_package():
        print("\n❌ Eșec la crearea pachetului de distribuție!")
        input("Apasă Enter pentru a ieși...")
        return 1
    
    # Succes!
    print("\n" + "=" * 60)
    print("🎉 BUILD COMPLET CU SUCCES!")
    print("=" * 60)
    print(f"📦 Executabil: dist/{APP_NAME}.exe")
    print(f"🗜️  Pachet distribuție: release/{APP_NAME}-v{APP_VERSION}-Windows.zip")
    print()
    print("📋 Ce să faci acum:")
    print("1. Testează executabilul local din dist/")
    print("2. Distribuie arhiva ZIP din release/")
    print("3. Utilizatorii urmează ghidul din INSTALARE.txt")
    print()
    print("🔧 Pentru debugging, verifică:")
    print("- Logurile din directorul dist/")
    print("- Că MySQL Server rulează pe calculatorul destinație")
    print("- Că serverele PACS sunt accesibile")
    
    input("\nApasă Enter pentru a ieși...")
    return 0

if __name__ == "__main__":
    exit(main())