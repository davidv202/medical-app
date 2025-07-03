#!/usr/bin/env python3
"""
Medical PACS Application - Database Initialization Script
=========================================================
Doar crearea bazei de date și tabelelor - fără utilizatori MySQL
"""

import sys
import os

# Verifică că suntem în directorul corect
if not os.path.exists('app'):
    print("❌ EROARE: Directorul 'app' nu a fost găsit!")
    print("   Rulează scriptul din directorul rădăcină al proiectului.")
    input("Apasă Enter pentru a ieși...")
    sys.exit(1)

# Adaugă directorul curent la Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print("🏥 Medical PACS - Inițializare Bază de Date")
print("=" * 50)

# Verifică dependențele
missing_deps = []

try:
    import sqlalchemy
    print("✅ SQLAlchemy găsit")
except ImportError:
    missing_deps.append("sqlalchemy")

try:
    import pymysql
    print("✅ PyMySQL găsit")
except ImportError:
    missing_deps.append("pymysql")

try:
    import bcrypt
    print("✅ bcrypt găsit")
except ImportError:
    missing_deps.append("bcrypt")

if missing_deps:
    print(f"❌ Lipsesc dependențele: {', '.join(missing_deps)}")
    print("   Instalează cu: pip install " + " ".join(missing_deps))
    input("Apasă Enter pentru a ieși...")
    sys.exit(1)

# Importă modulele aplicației
try:
    from app.database.models import Base, User, PacsUrl, AppSettings, ReportTitle, RoleEnum
    from app.config.settings import Settings
    print("✅ Module aplicație încărcate")
except ImportError as e:
    print(f"❌ Nu pot încărca modulele aplicației: {e}")
    print("   Verifică că toate fișierele sunt în locul corect.")
    input("Apasă Enter pentru a ieși...")
    sys.exit(1)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import time


def wait_for_database(db_uri, max_attempts=30):
    """Așteaptă ca baza de date să fie disponibilă"""

    # Extrage URI-ul de bază (fără numele bazei de date)
    parts = db_uri.split('/')
    base_uri = '/'.join(parts[:-1])

    for attempt in range(max_attempts):
        try:
            print(f"   Încercare {attempt + 1}/{max_attempts}...")
            test_engine = create_engine(
                base_uri,
                connect_args={'connect_timeout': 5}
            )
            with test_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            test_engine.dispose()
            print("✅ MariaDB este gata!")
            return True
        except Exception as e:
            if attempt < max_attempts - 1:
                print(f"   ⏳ MariaDB nu este încă gata, aștept 2 secunde...")
                time.sleep(2)
            else:
                print(f"❌ MariaDB nu răspunde după {max_attempts} încercări: {e}")
                raise

    return False


def main():
    """Funcția principală de inițializare"""

    # Obține configurația
    settings = Settings()
    db_uri = settings.DB_URI

    print(f"📊 Conectare la: {db_uri}")

    # Confirmă inițializarea
    response = input("\nVrei să continui cu inițializarea bazei de date? ACEST PROCES VA ȘTERGE DATELE EXISTENTE! (y/N): ")
    if response.lower() not in ['y', 'yes', 'da']:
        print("❌ Inițializare anulată.")
        return

    try:
        # Așteaptă ca MariaDB să fie gata (maxim 60 secunde)
        print("⏳ Aștept ca MariaDB să fie gata...")
        wait_for_database(db_uri)

        # Creează baza de date dacă nu există
        create_database_if_needed(db_uri)

        # Creează engine-ul cu retry și timeouts
        engine = create_engine(
            db_uri,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=3600,
            connect_args={
                'connect_timeout': 60,
                'read_timeout': 60,
                'write_timeout': 60
            }
        )

        # ȘTERGE tabelele existente pentru a le recrea cu structura nouă
        print("🗑️ Ștergere tabele existente...")
        try:
            Base.metadata.drop_all(engine)
            print("✅ Tabele existente șterse!")
        except Exception as e:
            print(f"⚠️ Nu s-au putut șterge tabelele existente (probabil nu existau): {e}")

        # Creează tabelele
        print("📋 Creare tabele noi...")
        Base.metadata.create_all(engine)
        print("✅ Tabele create cu structura nouă!")

        # Adaugă datele default
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            add_default_users(session)
            add_default_pacs(session)
            add_default_settings(session)
            add_default_report_titles(session)

            session.commit()
            print("✅ Date default adăugate!")

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
            engine.dispose()

        # Afișează rezumatul
        print("\n🎉 INIȚIALIZARE COMPLETĂ!")
        print("-" * 30)
        print("Tabele create:")
        print("  📊 users - Utilizatori aplicație (cu titulatura)")
        print("  🏥 pacs_urls - Configurații PACS")
        print("  ⚙️ app_settings - Setări aplicație")
        print("  📄 report_titles - Titluri rapoarte")
        print("\nConturi utilizator:")
        print("  👤 admin / admin123 (Administrator)")
        print("  👤 dr.popescu / doctor123 (Dr. Ioan Popescu)")
        print("  👤 univ.dr.georgescu / radiolog123 (Univ. Dr. Alexandru Georgescu)")
        print("\nTitluri rapoarte default:")
        print("  📋 Scintigrame specializate medicale")
        print("  📋 Investigații nucleare complete")
        print("\n⚠️  Schimbă parolele după prima autentificare!")
        print("\n🚀 Acum poți rula aplicația cu: python app/main.py")

    except Exception as e:
        print(f"❌ Eroare: {e}")
        import traceback
        traceback.print_exc()

    input("\nApasă Enter pentru a ieși...")


def create_database_if_needed(db_uri):
    """Creează baza de date dacă nu există"""

    # Extrage numele bazei de date din URI
    parts = db_uri.split('/')
    database_name = parts[-1]
    base_uri = '/'.join(parts[:-1])

    print(f"🔍 Verifică dacă baza de date '{database_name}' există...")

    try:
        temp_engine = create_engine(
            base_uri,
            connect_args={
                'connect_timeout': 30,
                'read_timeout': 30,
                'write_timeout': 30
            }
        )
        with temp_engine.connect() as conn:
            result = conn.execute(text(f"SHOW DATABASES LIKE '{database_name}'"))
            if result.fetchone() is None:
                print(f"📚 Creare bază de date '{database_name}'...")
                conn.execute(
                    text(f"CREATE DATABASE `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                conn.commit()
                print(f"✅ Baza de date '{database_name}' creată!")
            else:
                print(f"✅ Baza de date '{database_name}' există deja")
        temp_engine.dispose()

    except Exception as e:
        print(f"❌ Eroare la crearea bazei de date: {e}")
        raise


def add_default_users(session):
    """Adaugă utilizatori default pentru aplicație cu titulatura"""

    print("👤 Creare utilizatori default cu titulatura...")

    # Hash-urile pentru parole
    admin_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    doctor1_hash = bcrypt.hashpw("doctor123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    doctor2_hash = bcrypt.hashpw("radiolog123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    users = [
        User(
            username="admin",
            password=admin_hash,
            role=RoleEnum.admin,
            first_name="Administrator",
            last_name="System",
            title=None
        ),
        User(
            username="dr.popescu",
            password=doctor1_hash,
            role=RoleEnum.doctor,
            first_name="Ioan",
            last_name="Popescu",
            title="Dr."  # Doctor cu titulatura
        ),
        User(
            username="univ.dr.georgescu",
            password=doctor2_hash,
            role=RoleEnum.doctor,
            first_name="Alexandru",
            last_name="Georgescu",
            title="Univ. Dr."  # Doctor universitar
        )
    ]

    for user in users:
        session.add(user)
        if user.title:
            print(f"  ✅ {user.username} ({user.title} {user.first_name} {user.last_name})")
        else:
            print(f"  ✅ {user.username} ({user.first_name} {user.last_name} - {user.role.value})")


def add_default_pacs(session):
    """Adaugă PACS-uri default"""

    print("🏥 Creare PACS-uri default...")

    pacs_list = [
        PacsUrl(
            name="Local Orthanc Primary",
            url="http://localhost:8042",
            username="orthanc",
            password="orthanc"
        ),
        PacsUrl(
            name="Local Orthanc Secondary",
            url="http://localhost:8052",
            username="orthanc",
            password="orthanc"
        ),
        PacsUrl(
            name="Test PACS Server",
            url="http://192.168.1.100:8042",
            username="pacs_user",
            password="pacs_pass"
        )
    ]

    for pacs in pacs_list:
        session.add(pacs)
        print(f"  ✅ {pacs.name}")


def add_default_settings(session):
    """Adaugă setări default"""

    print("⚙️ Creare setări default...")

    settings = [
        AppSettings(
            setting_key="source_pacs_id",
            setting_value="1",
            description="PACS sursă pentru citire"
        ),
        AppSettings(
            setting_key="target_pacs_id",
            setting_value="2",
            description="PACS țintă pentru trimitere"
        ),
        AppSettings(
            setting_key="app_version",
            setting_value="2.0.0",
            description="Versiunea aplicației"
        ),
        AppSettings(
            setting_key="installation_date",
            setting_value=datetime.now().isoformat(),
            description="Data instalării"
        ),
        AppSettings(
            setting_key="auto_anonymize",
            setting_value="true",
            description="Anonimizare automată DICOM"
        ),
        AppSettings(
            setting_key="pdf_include_title",
            setting_value="true",
            description="Include titulatura în documentele PDF"
        )
    ]

    for setting in settings:
        session.add(setting)
        print(f"  ✅ {setting.setting_key}")


def add_default_report_titles(session):
    """Adaugă titluri default pentru rapoarte"""

    print("📄 Creare titluri rapoarte default...")

    report_titles = [
        ReportTitle(
            title_text="Scintigrama renala statica cu 99mTc- DMSA"
        ),
        ReportTitle(
            title_text="Scintigrama renala dinamica cu 99mTc- DTPA"
        ),
        ReportTitle(
            title_text="Scintigrama renala dinamica cu 99mTc- MAG3"
        ),
        ReportTitle(
            title_text="Scintigrama tiroidiana cu 99mTcO4"
        ),
        ReportTitle(
            title_text="Scintigrama tiroidiana cu 131INa"
        ),
        ReportTitle(
            title_text="Scintigrama tiroidiana cu 99mTc + FID-MIBI"
        ),
        ReportTitle(
            title_text="Scintigrama osoasa cu 99mTc – HDP"
        ),
        ReportTitle(
            title_text="Scintigrama paratiroidiana cu 99mTc-FID-MIBI"
        ),
        ReportTitle(
            title_text="Scintigrama miocardica cu 99mTc- FID-MIBI cu test la efort si de repaus"
        ),
        ReportTitle(
            title_text="Scintigrama miocardica cu 99mTc- FID-MIBI cu test la efort"
        ),
        ReportTitle(
            title_text="Scintigrama miocardica cu 99mTc- FID-MIBI de repaus"
        ),
        ReportTitle(
            title_text="Scintigrama pulmonara cu 99mTc- MAASOL"
        ),
        ReportTitle(
            title_text="Scintigrama tumorala cu 99mTc +Tektrotyd"
        ),
        ReportTitle(
            title_text="Scintigrama Corp Intreg cu 99mTc-FID-MIBI"
        ),
        ReportTitle(
            title_text="Diverticul Meckel"
        ),
        ReportTitle(
            title_text="Scintigrama ganglion santinela cu 99mTc – NANOSCAN"
        ),
        ReportTitle(
            title_text="Scintigrama ganglion santinela cu 99mTc - NANOHSA"
        ),
        ReportTitle(
            title_text="Scintigrama de orbita cu 99mTc - DTPA"
        ),
        ReportTitle(
            title_text="Limfoscintigrafie cu 99mTc – NANOSCAN"
        ),
        ReportTitle(
            title_text="Limfoscintigrafie cu 99mTc – NANOHSA"
        ),
        ReportTitle(
            title_text="Scintigrama hepatica cu 99mTc + NANOSCAN"
        ),
        ReportTitle(
            title_text="Scintigrama hepatica cu 99mTc + NANOHSA"
        ),
        ReportTitle(
            title_text="Scintigrama hematii marcate cu 99mTc + PYP"
        ),
        ReportTitle(
            title_text="Scintigrama timica cu 99mTc-FID-MIBI"
        ),
        ReportTitle(
            title_text="Scintigrama Corp Intreg cu 131INa"
        ),
        ReportTitle(
            title_text="Scintigrama evacuare gastrica cu 99mTc-DTPA"
        )
    ]

    for title in report_titles:
        session.add(title)
        print(f"  ✅ {title.title_text}")


if __name__ == "__main__":
    main()