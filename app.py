"""
MAMMOUTH — MY ASSISTANT IN MOUTH HEALTH
=========================================================
Versi   : 6.0  "Aurora Clinical"
Stack   : Streamlit + SQLite + (opsional) Ultralytics YOLO
Fitur   : Multi-User Auth (salted PBKDF2), Manajemen Pasien, SQLite Database,
          Data Isolation per klinisi, OLD CARTS Anamnesis, Batch Upload,
          Live Preview & Image Enhancement, AI + Manual Hybrid Detection,
          Sintesis Diagnosis Klinis, Riwayat EMR (cari/filter/status/hapus),
          Ekspor CSV / Excel / PDF, Dashboard Analitik, Ensiklopedia Lesi,
          Panel Admin, Pengaturan Profil & Preferensi, Backup Basis Data.
=========================================================
"""

import io
import os
import uuid
import sqlite3
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image, ImageEnhance, ImageDraw, ImageFont

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

try:
    from fpdf import FPDF
    FPDF_OK = True
except ImportError:
    FPDF_OK = False

# ============================================================
# KONFIGURASI GLOBAL
# ============================================================
APP_VERSION = "6.0 Aurora Clinical"
APP_NAME = "MAMMOUTH"
APP_TAGLINE = "My Assistant In Mouth Health"
DB_FILE = "mammouth.db"

# ------------------------------------------------------------
# DESIGN TOKENS — palet "Aurora Clinical": navy klinis + koral hangat
# ------------------------------------------------------------
NAVY_900 = "#0F1E3D"      # Judul & teks utama
NAVY_700 = "#1B3A6B"      # Warna merek utama (brand)
NAVY_600 = "#234A87"      # Gradasi / hover
NAVY_100 = "#E7ECF6"      # Latar lembut bernuansa navy
CORAL_500 = "#F2703C"     # Aksen CTA / highlight
CORAL_600 = "#DD5A28"     # Hover aksen
CORAL_100 = "#FDEAE0"     # Latar lembut aksen
SLATE_500 = "#64748B"     # Teks sekunder
SLATE_300 = "#CBD5E1"
BORDER_COLOR = "#E7EAF3"
BG_MIST = "#F5F7FC"       # Latar halaman
WHITE = "#FFFFFF"

DANGER = "#EF4444"
DANGER_BG = "#FEF2F2"
WARNING = "#F59E0B"
WARNING_BG = "#FFFBEB"
SUCCESS = "#16A34A"
SUCCESS_BG = "#F0FDF4"

# Dipertahankan agar kompatibel dengan nama variabel versi sebelumnya
PRIMARY = NAVY_700
PRIMARY_LIGHT = NAVY_100
ACCENT = CORAL_500
DARK_TEXT = NAVY_900
GRAY_TEXT = SLATE_500

STATUS_OPTIONS = ["Baru", "Perlu Tindak Lanjut", "Selesai"]

LESION_INFO = {
    "cheek biting": {
        "nama_klinis": "Morsicatio Buccarum (Cheek Biting)",
        "deskripsi": "Kebiasaan menggigit mukosa bukal, mengakibatkan tampilan kasar/bergerigi. Dapat berpotensi menyebabkan ulserasi. Sering terkait faktor stres psikologis.",
        "rekomendasi": "Edukasi penghentian kebiasaan buruk (habit breaking); evaluasi ulang bila lesi menetap >2 minggu.",
        "urgensi": "Rendah",
        "kategori": "Kebiasaan & Trauma",
        "ikon": "🦷",
    },
    "coated tongue": {
        "nama_klinis": "Coated Tongue",
        "deskripsi": "Permukaan lidah tertutup selaput pseudomembran akibat penumpukan debris, keratin tidak terdeskuamasi, dan mikroorganisme.",
        "rekomendasi": "Instruksikan pembersihan mekanis rutin (tongue scraper) dan evaluasi oral hygiene.",
        "urgensi": "Rendah",
        "kategori": "Kebersihan Mulut",
        "ikon": "👅",
    },
    "karies": {
        "nama_klinis": "Karies Gigi",
        "deskripsi": "Demineralisasi jaringan keras gigi oleh asam hasil metabolisme bakteri plak.",
        "rekomendasi": "Pemeriksaan klinis (sondasi/perkusi) dan radiografis lanjutan untuk rencana restorasi atau perawatan saluran akar.",
        "urgensi": "Sedang-Tinggi",
        "kategori": "Restoratif",
        "ikon": "🦠",
    },
    "linea alba": {
        "nama_klinis": "Linea Alba Buccalis",
        "deskripsi": "Garis putih horizontal pada mukosa bukal setinggi bidang oklusal, umumnya akibat tekanan atau friksi oklusal ringan.",
        "rekomendasi": "Bersifat jinak dan fisiologis, umumnya tidak memerlukan tatalaksana khusus.",
        "urgensi": "Rendah",
        "kategori": "Variasi Anatomis",
        "ikon": "➖",
    },
    "lingual varicosites": {
        "nama_klinis": "Lingual Varicosities",
        "deskripsi": "Pelebaran vena (varises) pada permukaan ventral lidah, temuan umum pada individu usia lanjut.",
        "rekomendasi": "Tidak memerlukan tindakan invasif. Edukasi pasien terkait sifat jinak lesi.",
        "urgensi": "Rendah",
        "kategori": "Variasi Anatomis",
        "ikon": "🔵",
    },
    "stain calculus": {
        "nama_klinis": "Stain & Kalkulus",
        "deskripsi": "Deposit terkalsifikasi (kalkulus) dan diskolorasi ekstrinsik pada permukaan gigi.",
        "rekomendasi": "Tindakan scaling dan root planing (SRP) profesional; instruksi DHE.",
        "urgensi": "Sedang",
        "kategori": "Kebersihan Mulut",
        "ikon": "✨",
    },
    "torus": {
        "nama_klinis": "Torus (Palatinus/Mandibularis)",
        "deskripsi": "Eksostosis tulang jinak, umumnya asimtomatik dan lambat membesar.",
        "rekomendasi": "Observasi. Pembedahan hanya diindikasikan bila mengganggu fungsi bicara/pengunyahan atau sebagai persiapan protesa.",
        "urgensi": "Rendah",
        "kategori": "Variasi Anatomis",
        "ikon": "⬜",
    },
    "ulkus traumatikus": {
        "nama_klinis": "Ulkus Traumatikus",
        "deskripsi": "Lesi ulseratif mukosa oral sekunder akibat trauma mekanis (tergigit/gesekan), termal, atau kimiawi.",
        "rekomendasi": "Eliminasi faktor kausatif. Evaluasi ulang dalam 10-14 hari untuk menyingkirkan diagnosis banding keganasan.",
        "urgensi": "Sedang",
        "kategori": "Kebiasaan & Trauma",
        "ikon": "⭕",
    },
}
LESION_KEYS = list(LESION_INFO.keys())

st.set_page_config(
    page_title=f"{APP_NAME} · AI Oral Health",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# INISIALISASI SESSION STATE
# ============================================================
_DEFAULT_STATE = {
    "logged_in": False,
    "active_user": None,
    "user_name": None,
    "user_role": None,
    "is_admin": False,
    "anamnesis_data": None,
    "yolo_version": "YOLOv8",
    "conf_threshold": 0.25,
    "iou_threshold": 0.45,
    "active_patient": None,
    "detection_results": None,
    "detection_cache": {},
    "confirm_delete_log": None,
    "confirm_delete_patient": None,
    "confirm_wipe": False,
    "theme_mode": "Terang",
}
for _k, _v in _DEFAULT_STATE.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ============================================================
# LAPISAN DATABASE (SQLITE)
# ============================================================
def get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT,
                    salt TEXT,
                    full_name TEXT,
                    role TEXT,
                    is_admin INTEGER DEFAULT 0,
                    pref_conf REAL DEFAULT 0.25,
                    pref_iou REAL DEFAULT 0.45,
                    created_at TEXT
                )""")
    c.execute("""CREATE TABLE IF NOT EXISTS patients (
                    patient_id TEXT PRIMARY KEY,
                    owner_user TEXT,
                    name TEXT,
                    age TEXT,
                    gender TEXT,
                    phone TEXT,
                    notes TEXT,
                    created_at TEXT,
                    FOREIGN KEY(owner_user) REFERENCES users(username)
                )""")
    c.execute("""CREATE TABLE IF NOT EXISTS emr_logs (
                    log_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    patient_id TEXT,
                    patient_name TEXT,
                    waktu TEXT,
                    tanggal TEXT,
                    lesi_terdeteksi TEXT,
                    confidence REAL,
                    model_version TEXT,
                    nama_file TEXT,
                    o_onset TEXT, l_location TEXT, d_duration TEXT, c_character TEXT,
                    a_aggravating TEXT, r_relieving TEXT, t_timing TEXT, s_severity INTEGER,
                    suspek_diagnosis TEXT,
                    status TEXT DEFAULT 'Baru',
                    catatan_tambahan TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(username)
                )""")
    conn.commit()
    conn.close()


init_db()

# ------------------------------------------------------------
# AUTENTIKASI
# ------------------------------------------------------------
def hash_password(password: str, salt: str = None):
    if salt is None:
        salt = uuid.uuid4().hex
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return pwd_hash, salt


def create_user(username, password, full_name, role):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    is_first_user = c.fetchone()[0] == 0
    pwd_hash, salt = hash_password(password)
    try:
        c.execute("""INSERT INTO users (username, password_hash, salt, full_name, role, is_admin, created_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?)""",
                  (username.lower().strip(), pwd_hash, salt, full_name.strip(), role.strip(),
                   1 if is_first_user else 0, datetime.now().isoformat()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def verify_login(username, password):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username.lower().strip(),))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    check_hash, _ = hash_password(password, row["salt"])
    if check_hash == row["password_hash"]:
        return dict(row)
    return None


def update_password(username, new_password):
    pwd_hash, salt = hash_password(new_password)
    conn = get_conn()
    conn.execute("UPDATE users SET password_hash=?, salt=? WHERE username=?", (pwd_hash, salt, username))
    conn.commit()
    conn.close()


def update_profile(username, full_name, role):
    conn = get_conn()
    conn.execute("UPDATE users SET full_name=?, role=? WHERE username=?", (full_name, role, username))
    conn.commit()
    conn.close()


def save_prefs(username, conf, iou):
    conn = get_conn()
    conn.execute("UPDATE users SET pref_conf=?, pref_iou=? WHERE username=?", (conf, iou, username))
    conn.commit()
    conn.close()


def count_users():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return n


# ------------------------------------------------------------
# MANAJEMEN PASIEN
# ------------------------------------------------------------
def create_patient(owner, name, age, gender, phone, notes):
    pid = uuid.uuid4().hex[:10]
    conn = get_conn()
    conn.execute("""INSERT INTO patients (patient_id, owner_user, name, age, gender, phone, notes, created_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                 (pid, owner, name.strip(), str(age), gender, phone, notes, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return pid


def get_patients(owner) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM patients WHERE owner_user=? ORDER BY name ASC", conn, params=(owner,))
    conn.close()
    return df


def get_patient(patient_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM patients WHERE patient_id=?", (patient_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_patient(patient_id, name, age, gender, phone, notes):
    conn = get_conn()
    conn.execute("""UPDATE patients SET name=?, age=?, gender=?, phone=?, notes=? WHERE patient_id=?""",
                 (name, str(age), gender, phone, notes, patient_id))
    conn.commit()
    conn.close()


def delete_patient(patient_id, owner):
    conn = get_conn()
    conn.execute("DELETE FROM patients WHERE patient_id=? AND owner_user=?", (patient_id, owner))
    conn.commit()
    conn.close()


# ------------------------------------------------------------
# EMR / RIWAYAT PEMERIKSAAN
# ------------------------------------------------------------
def append_logs(records: list):
    if not records:
        return
    conn = get_conn()
    c = conn.cursor()
    for r in records:
        c.execute("""INSERT INTO emr_logs
                     (log_id, user_id, patient_id, patient_name, waktu, tanggal, lesi_terdeteksi, confidence,
                      model_version, nama_file, o_onset, l_location, d_duration, c_character, a_aggravating,
                      r_relieving, t_timing, s_severity, suspek_diagnosis, status, catatan_tambahan)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (r["ID"], r["user_id"], r.get("patient_id"), r.get("patient_name", "Umum"),
                   r["Waktu"], r["Tanggal"], r["Lesi_Terdeteksi"], r["Confidence"], r["Model_Version"],
                   r["Nama_File"], r.get("O_Onset", "-"), r.get("L_Location", "-"), r.get("D_Duration", "-"),
                   r.get("C_Character", "-"), r.get("A_Aggravating", "-"), r.get("R_Relieving", "-"),
                   r.get("T_Timing", "-"), r.get("S_Severity", 0), r["Suspek_Diagnosis"],
                   r.get("Status", "Baru"), r.get("Catatan", "")))
    conn.commit()
    conn.close()


def load_user_logs(username) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM emr_logs WHERE user_id=? ORDER BY tanggal DESC, waktu DESC",
                      conn, params=(username,))
    conn.close()
    return df


def update_log(log_id, status=None, catatan=None):
    conn = get_conn()
    if status is not None:
        conn.execute("UPDATE emr_logs SET status=? WHERE log_id=?", (status, log_id))
    if catatan is not None:
        conn.execute("UPDATE emr_logs SET catatan_tambahan=? WHERE log_id=?", (catatan, log_id))
    conn.commit()
    conn.close()


def delete_log(log_id, owner):
    conn = get_conn()
    conn.execute("DELETE FROM emr_logs WHERE log_id=? AND user_id=?", (log_id, owner))
    conn.commit()
    conn.close()


def load_all_logs_admin() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql("""SELECT emr_logs.*, users.full_name AS clinician_name
                         FROM emr_logs LEFT JOIN users ON emr_logs.user_id = users.username
                         ORDER BY tanggal DESC, waktu DESC""", conn)
    conn.close()
    return df


def load_all_users_admin() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql("SELECT username, full_name, role, is_admin, created_at FROM users ORDER BY created_at ASC", conn)
    conn.close()
    return df


# ============================================================
# EKSPOR DATA (CSV / EXCEL / PDF)
# ============================================================
def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    try:
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Riwayat EMR")
        return buf.getvalue()
    except Exception:
        return b""


def build_pdf_report(record: dict, clinician_name: str) -> bytes:
    """Membuat laporan pemeriksaan 1 halaman dalam format PDF. Mengembalikan b'' jika fpdf2 tidak tersedia."""
    if not FPDF_OK:
        return b""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(15, 30, 61)
    pdf.cell(0, 10, f"{APP_NAME} — Laporan Skrining Oral", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 6, f"Dibuat oleh {clinician_name} pada {record.get('Tanggal','-')} {record.get('Waktu','-')}", ln=True)
    pdf.ln(4)

    def row(label, value):
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(15, 30, 61)
        pdf.cell(45, 7, str(label), border=0)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(30, 41, 59)
        pdf.multi_cell(0, 7, str(value if value not in (None, "") else "-"))

    pdf.set_draw_color(226, 232, 240)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(242, 112, 60)
    pdf.cell(0, 8, "Data Pasien", ln=True)
    row("Nama Pasien", record.get("patient_name", "Umum"))
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(242, 112, 60)
    pdf.cell(0, 8, "Anamnesis (OLD CARTS)", ln=True)
    row("Onset", record.get("O_Onset"))
    row("Lokasi", record.get("L_Location"))
    row("Durasi", record.get("D_Duration"))
    row("Karakter", record.get("C_Character"))
    row("Faktor Memperberat", record.get("A_Aggravating"))
    row("Faktor Meredakan", record.get("R_Relieving"))
    row("Waktu Muncul", record.get("T_Timing"))
    row("Skala Nyeri (VAS)", f"{record.get('S_Severity', 0)}/10")
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(242, 112, 60)
    pdf.cell(0, 8, "Temuan AI & Sintesis Klinis", ln=True)
    row("Lesi Terdeteksi", record.get("Lesi_Terdeteksi"))
    row("Model", record.get("Model_Version"))
    row("Confidence", record.get("Confidence"))
    row("Suspek Diagnosis", record.get("Suspek_Diagnosis"))
    row("Catatan Tambahan", record.get("Catatan"))

    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(148, 163, 184)
    pdf.multi_cell(0, 5, "Dokumen ini dihasilkan oleh sistem bantu skrining AI dan TIDAK menggantikan "
                          "pemeriksaan serta diagnosis langsung oleh dokter gigi berlisensi.")

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1")
    return bytes(out)


def export_row_to_dict(row: pd.Series) -> dict:
    mapping = {
        "patient_name": "patient_name", "Tanggal": "tanggal", "Waktu": "waktu",
        "O_Onset": "o_onset", "L_Location": "l_location", "D_Duration": "d_duration",
        "C_Character": "c_character", "A_Aggravating": "a_aggravating", "R_Relieving": "r_relieving",
        "T_Timing": "t_timing", "S_Severity": "s_severity", "Lesi_Terdeteksi": "lesi_terdeteksi",
        "Model_Version": "model_version", "Confidence": "confidence", "Suspek_Diagnosis": "suspek_diagnosis",
        "Catatan": "catatan_tambahan",
    }
    return {k: row.get(v, "-") for k, v in mapping.items()}


# ============================================================
# FUNGSI AI: MODEL, INFERENSI, ANOTASI, SINTESIS KLINIS
# ============================================================
@st.cache_resource(show_spinner="Memuat bobot model AI...")
def load_model(version: str):
    if YOLO is None:
        return None
    model_paths = {"YOLOv8": "best.pt", "YOLOv11": "yolov11_best.pt", "YOLOv12": "yolov12_best.pt"}
    path = Path(model_paths.get(version, "best.pt"))
    if not path.exists():
        path = Path("best.pt")
    if path.exists():
        try:
            return YOLO(str(path))
        except Exception:
            return None
    return None


def run_inference(model, pil_image: Image.Image, conf: float, iou: float):
    """Mengembalikan list deteksi: {label, confidence, bbox}. Aman dipanggil meski model None."""
    if model is None:
        return []
    try:
        results = model.predict(pil_image, conf=conf, iou=iou, verbose=False)
    except Exception:
        return []
    detections = []
    for r in results:
        names = r.names
        boxes = getattr(r, "boxes", None)
        if boxes is None:
            continue
        for b in boxes:
            cls_id = int(b.cls[0]) if hasattr(b, "cls") else 0
            label = names.get(cls_id, str(cls_id)) if isinstance(names, dict) else str(cls_id)
            confv = float(b.conf[0]) if hasattr(b, "conf") else 0.0
            xyxy = [float(x) for x in b.xyxy[0]] if hasattr(b, "xyxy") else None
            detections.append({"label": label.lower(), "confidence": confv, "bbox": xyxy})
    return detections


def annotate_image(pil_image: Image.Image, detections: list) -> Image.Image:
    """Menggambar bounding box + label pada citra untuk Live Preview."""
    img = pil_image.convert("RGB").copy()
    if not detections:
        return img
    draw = ImageDraw.Draw(img)
    color = (242, 112, 60)
    for det in detections:
        bbox = det.get("bbox")
        if not bbox:
            continue
        x1, y1, x2, y2 = bbox
        draw.rectangle([x1, y1, x2, y2], outline=color, width=max(2, img.width // 300))
        label_txt = f"{det['label']} {det['confidence']*100:.0f}%"
        text_bbox = draw.textbbox((0, 0), label_txt)
        tw, th = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
        draw.rectangle([x1, max(0, y1 - th - 8), x1 + tw + 10, y1], fill=color)
        draw.text((x1 + 5, max(0, y1 - th - 6)), label_txt, fill="white")
    return img


def enhance_image(pil_image: Image.Image, brightness: float, contrast: float, sharpness: float) -> Image.Image:
    img = pil_image.convert("RGB")
    img = ImageEnhance.Brightness(img).enhance(brightness)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    img = ImageEnhance.Sharpness(img).enhance(sharpness)
    return img


def synthesize_clinical_diagnosis(detections, anamnesis):
    """Menggabungkan hasil deteksi visual + anamnesis OLD CARTS menjadi kesan klinis naratif."""
    if not detections:
        return "Tidak terdeteksi anomali visual. Pertimbangkan observasi berbasis keluhan (OLD CARTS)."
    hasil = []
    seen = set()
    for det in detections:
        key = det if isinstance(det, str) else det.get("label", "")
        key = key.lower()
        if key in seen:
            continue
        seen.add(key)
        if anamnesis:
            sev = int(anamnesis.get("S_Severity", 0) or 0)
            char = str(anamnesis.get("C_Character", "")).lower()
            if key == "karies":
                if sev >= 6 or "denyut" in char or "spontan" in char:
                    hasil.append("Suspek Pulpitis Irreversibel (Karies + nyeri spontan/tajam).")
                elif sev >= 3 or "ngilu" in char or "manis" in char:
                    hasil.append("Suspek Pulpitis Reversibel (Karies + hipersensitivitas).")
                else:
                    hasil.append("Karies Asimtomatik.")
            elif key in ("ulkus traumatikus", "cheek biting"):
                if sev >= 5:
                    hasil.append(f"Lesi traumatik reaktif akut (VAS {sev}/10). Indikasi observasi ketat/topikal.")
                else:
                    hasil.append("Lesi traumatik fase penyembuhan / indolen.")
            elif key == "coated tongue" and sev >= 4:
                hasil.append("Coated Tongue dengan keluhan menyertai — evaluasi halitosis & hidrasi.")
            else:
                hasil.append(f"{LESION_INFO.get(key, {}).get('nama_klinis', key)}.")
        else:
            hasil.append(f"Deteksi Objek: {LESION_INFO.get(key, {}).get('nama_klinis', key)}.")
    return " | ".join(hasil)


def urgency_of(detections) -> str:
    """Urgensi tertinggi di antara semua lesi yang terdeteksi, untuk keperluan badge & KPI."""
    order = {"Rendah": 0, "Sedang": 1, "Sedang-Tinggi": 2, "Tinggi": 3}
    best = "Rendah"
    for det in detections:
        key = (det if isinstance(det, str) else det.get("label", "")).lower()
        u = LESION_INFO.get(key, {}).get("urgensi", "Rendah")
        if order.get(u, 0) > order.get(best, 0):
            best = u
    return best


# ============================================================
# SISTEM DESAIN — "AURORA CLINICAL" (CSS)
# ============================================================
def base_css() -> str:
    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {{ font-family: 'Plus Jakarta Sans', sans-serif !important; }}
    .stApp {{ background-color: {BG_MIST}; }}
    #MainMenu, footer {{ visibility: hidden; }}

    /* ---------- Tipografi umum ---------- */
    h1, h2, h3, h4 {{ color: {NAVY_900}; font-weight: 800; letter-spacing: -0.01em; }}
    p, label, span {{ color: {NAVY_900}; }}

    /* ---------- Header halaman ---------- */
    .mh-page-header {{
        background: linear-gradient(120deg, {NAVY_700} 0%, {NAVY_600} 100%);
        border-radius: 20px; padding: 28px 32px; margin-bottom: 22px;
        display: flex; align-items: center; gap: 18px;
        box-shadow: 0 12px 24px -10px rgba(27, 58, 107, 0.45);
    }}
    .mh-page-header .mh-icon {{
        width: 52px; height: 52px; min-width: 52px; border-radius: 14px;
        background: rgba(255,255,255,0.14); display: flex; align-items: center; justify-content: center;
        font-size: 26px;
    }}
    .mh-page-header h2 {{ color: white; margin: 0; font-size: 1.5rem; }}
    .mh-page-header p {{ color: rgba(255,255,255,0.82); margin: 4px 0 0 0; font-size: 0.92rem; }}

    /* ---------- Kartu dasar ---------- */
    .frost-card {{
        background: {WHITE}; border: 1px solid {BORDER_COLOR}; border-radius: 18px;
        padding: 22px 24px; margin-bottom: 20px;
        box-shadow: 0 2px 10px -4px rgba(15, 30, 61, 0.06);
    }}
    .frost-card h4 {{ margin-top: 0; }}

    /* ---------- KPI / statistik ---------- */
    .kpi-card {{
        background: {WHITE}; border: 1px solid {BORDER_COLOR}; border-radius: 16px;
        padding: 18px 20px; box-shadow: 0 2px 8px -4px rgba(15,30,61,0.06);
        display: flex; flex-direction: column; gap: 4px; height: 100%;
    }}
    .kpi-card .kpi-label {{ color: {SLATE_500}; font-size: 0.78rem; font-weight: 600; }}
    .kpi-card .kpi-value {{ color: {NAVY_900}; font-size: 1.9rem; font-weight: 800; line-height: 1.1; }}
    .kpi-card .kpi-sub {{ color: {SLATE_500}; font-size: 0.75rem; }}
    .kpi-accent {{ border-left: 4px solid {CORAL_500}; }}

    /* ---------- Badge urgensi & status ---------- */
    .badge {{ padding: 5px 12px; border-radius: 20px; font-size: 0.72rem; font-weight: 700; display: inline-block; }}
    .badge-high {{ background-color: {DANGER_BG}; color: #991b1b; border: 1px solid #fecaca; }}
    .badge-med {{ background-color: {WARNING_BG}; color: #b45309; border: 1px solid #fde68a; }}
    .badge-low {{ background-color: {SUCCESS_BG}; color: #166534; border: 1px solid #bbf7d0; }}
    .pill {{ padding: 4px 11px; border-radius: 20px; font-size: 0.72rem; font-weight: 600;
             background: {NAVY_100}; color: {NAVY_700}; display: inline-block; }}

    /* ---------- Kartu lesi (ensiklopedia) ---------- */
    .lesion-card {{
        background: {WHITE}; border: 1px solid {BORDER_COLOR}; border-radius: 18px;
        padding: 20px; height: 100%; box-shadow: 0 2px 10px -4px rgba(15,30,61,0.06);
    }}
    .lesion-card .lesion-icon {{
        width: 44px; height: 44px; border-radius: 12px; background: {CORAL_100};
        display: flex; align-items: center; justify-content: center; font-size: 22px; margin-bottom: 10px;
    }}
    .lesion-card h4 {{ margin: 0 0 2px 0; font-size: 1.02rem; }}
    .lesion-card .lesion-cat {{ color: {CORAL_600}; font-size: 0.72rem; font-weight: 700; margin-bottom: 8px; }}
    .lesion-card p {{ color: {SLATE_500}; font-size: 0.86rem; line-height: 1.45; }}

    /* ---------- Tombol ---------- */
    .stButton>button {{
        background-color: {NAVY_700} !important; color: white !important; border-radius: 10px !important;
        font-weight: 600 !important; border: none !important; padding: 10px 16px !important;
        transition: opacity 0.15s ease;
    }}
    .stButton>button:hover {{ opacity: 0.88; }}
    .stDownloadButton>button {{
        background-color: {WHITE} !important; color: {NAVY_700} !important; border: 1.5px solid {NAVY_700} !important;
        border-radius: 10px !important; font-weight: 600 !important;
    }}

    /* ---------- Sidebar ---------- */
    [data-testid="stSidebar"] {{ background-color: {WHITE} !important; border-right: 1px solid {BORDER_COLOR}; }}
    div.row-widget.stRadio > div > label {{ padding: 10px 12px; border-radius: 10px; margin-bottom: 2px; }}
    div.row-widget.stRadio > div > label[data-checked="true"] {{ background-color: {NAVY_700} !important; }}
    div.row-widget.stRadio > div > label[data-checked="true"] p {{ color: white !important; font-weight: 700 !important; }}

    /* ---------- Tab & expander ---------- */
    .stTabs [data-baseweb="tab"] {{ font-weight: 600; color: {SLATE_500}; }}
    .stTabs [aria-selected="true"] {{ color: {NAVY_700} !important; }}
    .streamlit-expanderHeader {{ font-weight: 700 !important; color: {NAVY_900} !important; }}

    /* ---------- Info banner klinis ---------- */
    .mh-disclaimer {{
        background: {CORAL_100}; border: 1px solid #f7cbb3; border-radius: 12px;
        padding: 12px 16px; font-size: 0.82rem; color: {CORAL_600}; margin: 10px 0 18px 0;
    }}
    .mh-empty {{
        text-align: center; padding: 40px 20px; color: {SLATE_500};
        border: 1.5px dashed {SLATE_300}; border-radius: 16px; background: {WHITE};
    }}
    </style>
    """


def hide_sidebar_css() -> str:
    return "<style>[data-testid='stSidebar'] {display: none;}</style>"


def page_header(icon: str, title: str, subtitle: str):
    st.markdown(f"""
        <div class="mh-page-header">
            <div class="mh-icon">{icon}</div>
            <div><h2>{title}</h2><p>{subtitle}</p></div>
        </div>
    """, unsafe_allow_html=True)


def urgency_badge_class(urgensi: str) -> str:
    if urgensi in ("Tinggi", "Sedang-Tinggi"):
        return "badge-high"
    if urgensi == "Sedang":
        return "badge-med"
    return "badge-low"


def kpi_card(label: str, value, sub: str = "", accent: bool = False):
    cls = "kpi-card kpi-accent" if accent else "kpi-card"
    st.markdown(f"""
        <div class="{cls}">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub">{sub}</div>
        </div>
    """, unsafe_allow_html=True)


# ============================================================
# HALAMAN AUTENTIKASI (LOGIN & SIGN UP)
# ============================================================
def render_auth_page():
    st.markdown(base_css(), unsafe_allow_html=True)
    st.markdown(hide_sidebar_css(), unsafe_allow_html=True)
    st.markdown(f"""
        <style>
        .mh-hero {{
            background: linear-gradient(160deg, {NAVY_900} 0%, {NAVY_700} 55%, {NAVY_600} 100%);
            border-radius: 24px; padding: 42px 34px; color: white; height: 100%;
            box-shadow: 0 20px 40px -18px rgba(15,30,61,0.55);
        }}
        .mh-hero h1 {{ color: white; font-size: 2.1rem; margin: 14px 0 8px 0; }}
        .mh-hero p.sub {{ color: rgba(255,255,255,0.78); font-size: 0.98rem; line-height: 1.5; margin-bottom: 26px; }}
        .mh-feat {{ display: flex; align-items: flex-start; gap: 12px; margin-bottom: 16px; }}
        .mh-feat .dot {{
            width: 34px; height: 34px; min-width: 34px; border-radius: 10px; background: rgba(242,112,60,0.22);
            display: flex; align-items: center; justify-content: center; font-size: 17px;
        }}
        .mh-feat b {{ color: white; font-size: 0.92rem; }}
        .mh-feat span {{ color: rgba(255,255,255,0.72); font-size: 0.82rem; }}
        .mh-badge-ver {{
            display: inline-block; background: rgba(255,255,255,0.12); color: white; font-size: 0.72rem;
            font-weight: 700; padding: 5px 12px; border-radius: 20px; margin-bottom: 6px;
        }}
        .mh-auth-card {{
            background: white; border-radius: 24px; padding: 36px 34px; height: 100%;
            box-shadow: 0 20px 40px -18px rgba(15,30,61,0.16); border: 1px solid {BORDER_COLOR};
        }}
        </style>
    """, unsafe_allow_html=True)

    st.write("")
    col_hero, col_form = st.columns([0.95, 1.15], gap="large")

    with col_hero:
        st.markdown(f"""
            <div class="mh-hero">
                <span class="mh-badge-ver">Versi {APP_VERSION}</span>
                <h1>🦷 {APP_NAME}</h1>
                <p class="sub">{APP_TAGLINE} — asisten skrining kesehatan mulut berbasis AI untuk
                membantu klinisi menyaring, mendokumentasikan, dan menindaklanjuti temuan oral secara cepat dan rapi.</p>
                <div class="mh-feat"><div class="dot">🧠</div><div><b>Deteksi AI + konfirmasi klinisi</b><br><span>YOLOv8/v11/v12 dengan koreksi manual sebelum disimpan.</span></div></div>
                <div class="mh-feat"><div class="dot">📋</div><div><b>Anamnesis OLD CARTS terstruktur</b><br><span>Rekam onset hingga severity dalam satu formulir ringkas.</span></div></div>
                <div class="mh-feat"><div class="dot">🗂️</div><div><b>Rekam medis & pasien per klinisi</b><br><span>Data terisolasi aman per akun, siap diekspor kapan saja.</span></div></div>
            </div>
        """, unsafe_allow_html=True)

    with col_form:
        st.markdown('<div class="mh-auth-card">', unsafe_allow_html=True)
        tab_login, tab_register = st.tabs(["🔒 Masuk", "📝 Buat Akun"])

        with tab_login:
            st.markdown(f"<p style='color:{SLATE_500}; margin-top:-6px;'>Masuk untuk melanjutkan sesi klinis Anda.</p>",
                        unsafe_allow_html=True)
            with st.form("login_form"):
                log_user = st.text_input("Username", placeholder="Masukkan username Anda")
                log_pass = st.text_input("Password", type="password", placeholder="••••••••")
                submitted = st.form_submit_button("MASUK SISTEM", use_container_width=True)
                if submitted:
                    if not log_user or not log_pass:
                        st.warning("Mohon isi username dan password.")
                    else:
                        user_data = verify_login(log_user, log_pass)
                        if user_data:
                            st.session_state.logged_in = True
                            st.session_state.active_user = user_data["username"]
                            st.session_state.user_name = user_data["full_name"]
                            st.session_state.user_role = user_data["role"]
                            st.session_state.is_admin = bool(user_data["is_admin"])
                            st.session_state.conf_threshold = user_data["pref_conf"] or 0.25
                            st.session_state.iou_threshold = user_data["pref_iou"] or 0.45
                            st.toast(f"Selamat datang kembali, {user_data['full_name']}!", icon="👋")
                            st.rerun()
                        else:
                            st.error("Username atau password salah.")

        with tab_register:
            st.markdown(f"<p style='color:{SLATE_500}; margin-top:-6px;'>Akun pertama yang mendaftar otomatis menjadi Administrator.</p>",
                        unsafe_allow_html=True)
            with st.form("register_form"):
                reg_name = st.text_input("Nama Lengkap", placeholder="Contoh: drg. John Doe")
                reg_role = st.text_input("Peran/Jabatan", placeholder="Contoh: Operator Klinis")
                reg_user = st.text_input("Username", placeholder="Pilih username unik")
                reg_pass = st.text_input("Password", type="password", placeholder="Minimal 6 karakter")
                reg_pass2 = st.text_input("Konfirmasi Password", type="password", placeholder="Ulangi password")
                submitted_reg = st.form_submit_button("DAFTAR AKUN BARU", use_container_width=True)
                if submitted_reg:
                    if not (reg_name and reg_role and reg_user and reg_pass):
                        st.warning("Mohon lengkapi seluruh form pendaftaran.")
                    elif len(reg_pass) < 6:
                        st.warning("Password minimal 6 karakter.")
                    elif reg_pass != reg_pass2:
                        st.warning("Konfirmasi password tidak cocok.")
                    else:
                        success = create_user(reg_user, reg_pass, reg_name, reg_role)
                        if success:
                            st.success("Akun berhasil dibuat! Silakan kembali ke tab 'Masuk'.")
                        else:
                            st.error("Username sudah digunakan. Pilih username lain.")
        st.markdown("</div>", unsafe_allow_html=True)


if not st.session_state.logged_in:
    render_auth_page()
    st.stop()


# ============================================================
# CSS UTAMA (SETELAH LOGIN) + SIDEBAR
# ============================================================
st.markdown(base_css(), unsafe_allow_html=True)

MENU_ITEMS = [
    "Dashboard Skrining",
    "Manajemen Pasien",
    "Riwayat Klinis (EMR)",
    "Analitik Data",
    "Ensiklopedia Lesi",
    "Pengaturan Sistem",
]

with st.sidebar:
    st.markdown(f"""
        <div style="margin-bottom: 18px;">
            <h2 style="margin:0; font-size: 1.5rem; font-weight: 800; color:{NAVY_700};">🦷 {APP_NAME}</h2>
            <p style="margin:0; font-size: 0.72rem; font-weight: 600; color:{SLATE_500};">{APP_TAGLINE}</p>
        </div>
    """, unsafe_allow_html=True)

    menu = st.radio("Navigasi", MENU_ITEMS, label_visibility="collapsed")
    st.markdown("---")

    st.markdown(f"<p style='font-size: 0.78rem; font-weight: 700; color: {SLATE_500};'>KONFIGURASI AI</p>",
                unsafe_allow_html=True)
    st.session_state.yolo_version = st.selectbox(
        "Arsitektur Model", ["YOLOv8", "YOLOv11", "YOLOv12"],
        index=["YOLOv8", "YOLOv11", "YOLOv12"].index(st.session_state.yolo_version))
    st.session_state.conf_threshold = st.slider("Confidence Threshold", 0.05, 0.95, float(st.session_state.conf_threshold), 0.05)
    st.session_state.iou_threshold = st.slider("IoU (NMS) Threshold", 0.05, 0.95, float(st.session_state.iou_threshold), 0.05)
    conf_threshold = st.session_state.conf_threshold
    iou_threshold = st.session_state.iou_threshold

    admin_tag = " · Admin" if st.session_state.is_admin else ""
    st.markdown(f"""
        <div style="margin-top: 22px; padding: 14px 16px; background: {NAVY_100}; border-radius: 12px;">
            <p style="margin: 0; font-size: 0.68rem; color: {NAVY_700}; font-weight: 700;">AKUN TERHUBUNG{admin_tag}</p>
            <p style="margin: 4px 0 0 0; font-weight: 700; font-size: 0.9rem; color: {DARK_TEXT};">{st.session_state.user_name}</p>
            <p style="margin: 0; font-size: 0.75rem; color: {GRAY_TEXT};">{st.session_state.user_role}</p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Log Out", key="logout", use_container_width=True):
        for k in ("logged_in", "active_user", "user_name", "user_role", "is_admin", "anamnesis_data",
                  "active_patient", "detection_results", "detection_cache"):
            st.session_state[k] = _DEFAULT_STATE.get(k)
        st.rerun()

model = load_model(st.session_state.yolo_version)
CURRENT_USER = st.session_state.active_user


# ============================================================
# HALAMAN: DASHBOARD SKRINING
# ============================================================
def render_dashboard():
    page_header("🩺", "Skrining Visual Otomatis",
                "Gabungkan interpretasi Computer Vision dan Anamnesis untuk identifikasi anomali rongga mulut.")

    st.markdown("""<div class="mh-disclaimer">⚠️ Hasil AI bersifat bantu-skrining (decision support) dan
                 <b>tidak menggantikan</b> pemeriksaan serta diagnosis definitif oleh dokter gigi berlisensi.
                 Selalu konfirmasi temuan sebelum disimpan.</div>""", unsafe_allow_html=True)

    # ---------- KPI ringkas ----------
    df_logs = load_user_logs(CURRENT_USER)
    today_str = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    n_today = int((df_logs["tanggal"] == today_str).sum()) if not df_logs.empty else 0
    n_week = int((df_logs["tanggal"] >= week_ago).sum()) if not df_logs.empty else 0
    n_followup = int((df_logs["status"] == "Perlu Tindak Lanjut").sum()) if not df_logs.empty else 0
    n_patients = len(get_patients(CURRENT_USER))

    k1, k2, k3, k4 = st.columns(4)
    with k1: kpi_card("Skrining Hari Ini", n_today, "pemeriksaan tercatat")
    with k2: kpi_card("Skrining 7 Hari", n_week, "total minggu berjalan")
    with k3: kpi_card("Perlu Tindak Lanjut", n_followup, "status aktif", accent=(n_followup > 0))
    with k4: kpi_card("Pasien Terdaftar", n_patients, "di akun Anda")

    st.write("")

    # ---------- Pilih pasien ----------
    st.markdown("<div class='frost-card'>", unsafe_allow_html=True)
    st.markdown("<h4>👤 Pasien Pemeriksaan</h4>", unsafe_allow_html=True)
    patients_df = get_patients(CURRENT_USER)
    patient_options = ["Umum / Tidak diketahui"] + (patients_df["name"] + " · " + patients_df["patient_id"]).tolist() if not patients_df.empty else ["Umum / Tidak diketahui"]
    col_p1, col_p2 = st.columns([3, 1])
    with col_p1:
        chosen_patient = st.selectbox("Periksa atas nama", patient_options, label_visibility="collapsed")
    with col_p2:
        quick_add = st.toggle("+ Pasien baru", value=False)
    if quick_add:
        with st.form("quick_add_patient"):
            qc1, qc2, qc3 = st.columns(3)
            qp_name = qc1.text_input("Nama Pasien")
            qp_age = qc2.text_input("Usia")
            qp_gender = qc3.selectbox("Jenis Kelamin", ["L", "P"])
            if st.form_submit_button("Simpan Pasien"):
                if qp_name:
                    create_patient(CURRENT_USER, qp_name, qp_age, qp_gender, "", "")
                    st.success(f"Pasien '{qp_name}' ditambahkan. Pilih dari daftar di atas.")
                    st.rerun()
                else:
                    st.warning("Nama pasien wajib diisi.")
    st.markdown("</div>", unsafe_allow_html=True)

    patient_id, patient_name = None, "Umum"
    if chosen_patient != "Umum / Tidak diketahui":
        patient_name, patient_id = chosen_patient.rsplit(" · ", 1)

    # ---------- ANAMNESIS OLD CARTS ----------
    with st.expander("📝 Formulir Anamnesis (OLD CARTS)", expanded=(st.session_state.anamnesis_data is None)):
        with st.form("anamnesis_form"):
            c1, c2 = st.columns(2, gap="large")
            with c1:
                o_val = st.text_input("Onset (O)", placeholder="Sejak kapan muncul?")
                l_val = st.text_input("Location (L)", placeholder="Lokasi anatomis lesi?")
                d_val = st.text_input("Duration (D)", placeholder="Durasi nyeri/keluhan?")
                c_val = st.text_input("Character (C)", placeholder="Sifat keluhan (tajam, tumpul, berdenyut)?")
            with c2:
                a_val = st.text_input("Aggravating (A)", placeholder="Faktor yang memperparah?")
                r_val = st.text_input("Relieving (R)", placeholder="Faktor yang meredakan?")
                t_val = st.text_input("Timing (T)", placeholder="Waktu munculnya keluhan?")
                s_val = st.slider("Severity (S) - Skala Nyeri (VAS) 0-10", 0, 10, 0)

            if st.form_submit_button("Simpan Anamnesis"):
                st.session_state.anamnesis_data = {
                    "O_Onset": o_val or "-", "L_Location": l_val or "-", "D_Duration": d_val or "-",
                    "C_Character": c_val or "-", "A_Aggravating": a_val or "-", "R_Relieving": r_val or "-",
                    "T_Timing": t_val or "-", "S_Severity": s_val,
                }
                st.success("Anamnesis direkam. AI akan menggunakan konteks ini untuk sintesis diagnosis.")

    if st.session_state.anamnesis_data:
        sev = st.session_state.anamnesis_data.get("S_Severity", 0)
        st.markdown(f"<span class='pill'>VAS {sev}/10</span> &nbsp; "
                    f"<span class='pill'>Lokasi: {st.session_state.anamnesis_data.get('L_Location','-')}</span> &nbsp;"
                    f"<span class='pill'>Onset: {st.session_state.anamnesis_data.get('O_Onset','-')}</span>",
                    unsafe_allow_html=True)

    st.write("")

    # ---------- AKUISISI VISUAL ----------
    st.markdown("<div class='frost-card'>", unsafe_allow_html=True)
    st.markdown("<h4>📸 Akuisisi & Live Preview Citra Klinis</h4>", unsafe_allow_html=True)
    if model is None:
        st.info("Mode Manual aktif — bobot model YOLO tidak ditemukan/`ultralytics` belum terpasang. "
                "Anda tetap dapat mengonfirmasi temuan lesi secara manual di bawah setiap gambar.")

    tab_unggah, tab_kamera = st.tabs(["🖼️ Unggah Gambar (Batch)", "🎥 Kamera Intraoral/Webcam"])
    raw_items = []  # list of (key, filename, PIL.Image)

    with tab_unggah:
        uploaded_files = st.file_uploader(
            "Unggah satu atau beberapa citra intraoral", type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True)
        if uploaded_files:
            for f in uploaded_files:
                try:
                    img = Image.open(f)
                    raw_items.append((f.name, f.name, img))
                except Exception:
                    st.warning(f"Gagal membuka berkas: {f.name}")

    with tab_kamera:
        cam_img = st.camera_input("Ambil citra langsung dari kamera")
        if cam_img is not None:
            img = Image.open(cam_img)
            fname = f"kamera_{datetime.now().strftime('%H%M%S')}.jpg"
            raw_items.append((fname, fname, img))

    st.markdown("</div>", unsafe_allow_html=True)

    if not raw_items:
        st.markdown("""<div class="mh-empty">🦷 Belum ada citra untuk diperiksa.<br>
                     Unggah gambar atau gunakan kamera pada panel di atas untuk memulai skrining.</div>""",
                    unsafe_allow_html=True)
        return

    confirmed_payload = []  # dikumpulkan untuk disimpan ke EMR

    for idx, (key, fname, img) in enumerate(raw_items):
        with st.expander(f"🖼️ Gambar {idx+1} — {fname}", expanded=(len(raw_items) <= 3)):
            col_img, col_ctrl = st.columns([1.1, 1], gap="large")

            with col_img:
                sb1, sb2, sb3 = st.columns(3)
                b = sb1.slider("Brightness", 0.5, 1.8, 1.0, 0.05, key=f"b_{key}_{idx}")
                c = sb2.slider("Contrast", 0.5, 1.8, 1.0, 0.05, key=f"c_{key}_{idx}")
                sh = sb3.slider("Sharpness", 0.0, 3.0, 1.0, 0.1, key=f"s_{key}_{idx}")
                preview_img = enhance_image(img, b, c, sh)

                run_ai = st.button(f"🧠 Jalankan Deteksi AI", key=f"detect_{key}_{idx}",
                                    disabled=(model is None), use_container_width=True)
                result_key = f"det_result_{key}_{idx}"
                if run_ai:
                    with st.spinner("Menjalankan inferensi model..."):
                        dets = run_inference(model, preview_img, conf_threshold, iou_threshold)
                    st.session_state.detection_cache[result_key] = dets

                dets = st.session_state.detection_cache.get(result_key, [])
                display_img = annotate_image(preview_img, dets) if dets else preview_img
                st.image(display_img, use_container_width=True, caption="Live Preview")

            with col_ctrl:
                st.markdown("**Temuan AI**")
                if dets:
                    for d in dets:
                        info = LESION_INFO.get(d["label"], {})
                        st.markdown(f"<span class='badge {urgency_badge_class(info.get('urgensi','Rendah'))}'>"
                                    f"{info.get('nama_klinis', d['label'])} · {d['confidence']*100:.0f}%</span>",
                                    unsafe_allow_html=True)
                elif model is None:
                    st.caption("Model tidak aktif — gunakan konfirmasi manual di bawah.")
                else:
                    st.caption("Belum ada deteksi. Klik 'Jalankan Deteksi AI'.")

                st.markdown("**✅ Konfirmasi Temuan Klinis**")
                ai_labels = [d["label"] for d in dets if d["label"] in LESION_KEYS]
                confirmed = st.multiselect(
                    "Pilih/koreksi lesi final untuk pasien ini",
                    options=LESION_KEYS,
                    default=list(dict.fromkeys(ai_labels)),
                    format_func=lambda k: LESION_INFO[k]["nama_klinis"],
                    key=f"confirm_{key}_{idx}",
                )
                note = st.text_input("Catatan tambahan (opsional)", key=f"note_{key}_{idx}")

                if confirmed:
                    diag = synthesize_clinical_diagnosis(confirmed, st.session_state.anamnesis_data)
                    st.success(f"Kesan klinis: {diag}")
                    confirmed_payload.append({
                        "fname": fname, "confirmed": confirmed, "dets": dets, "diag": diag, "note": note,
                    })

    st.write("")
    if confirmed_payload:
        st.markdown("<div class='frost-card'>", unsafe_allow_html=True)
        st.markdown(f"<h4>💾 Simpan {len(confirmed_payload)} Hasil ke Riwayat Klinis</h4>", unsafe_allow_html=True)
        if st.button("Simpan Semua ke EMR", type="primary", use_container_width=True):
            records = []
            now = datetime.now()
            for item in confirmed_payload:
                avg_conf = (sum(d["confidence"] for d in item["dets"]) / len(item["dets"])) if item["dets"] else 0.0
                records.append({
                    "ID": uuid.uuid4().hex[:12], "user_id": CURRENT_USER,
                    "patient_id": patient_id, "patient_name": patient_name,
                    "Waktu": now.strftime("%H:%M:%S"), "Tanggal": now.strftime("%Y-%m-%d"),
                    "Lesi_Terdeteksi": ", ".join(LESION_INFO[k]["nama_klinis"] for k in item["confirmed"]),
                    "Confidence": round(avg_conf, 3), "Model_Version": st.session_state.yolo_version,
                    "Nama_File": item["fname"],
                    **(st.session_state.anamnesis_data or {}),
                    "Suspek_Diagnosis": item["diag"], "Status": "Baru", "Catatan": item["note"],
                })
            append_logs(records)
            st.toast(f"{len(records)} catatan berhasil disimpan ke Riwayat Klinis.", icon="✅")
            st.session_state.detection_cache = {}
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# HALAMAN: MANAJEMEN PASIEN
# ============================================================
def render_patients():
    page_header("🗂️", "Manajemen Pasien", "Kelola data pasien yang terhubung dengan riwayat pemeriksaan Anda.")

    with st.expander("➕ Tambah Pasien Baru", expanded=False):
        with st.form("add_patient_form"):
            c1, c2, c3 = st.columns(3)
            name = c1.text_input("Nama Lengkap")
            age = c2.text_input("Usia")
            gender = c3.selectbox("Jenis Kelamin", ["L", "P"])
            phone = st.text_input("No. Telepon (opsional)")
            notes = st.text_area("Catatan Medis Umum (alergi, riwayat, dsb.)", placeholder="Opsional")
            if st.form_submit_button("Simpan Pasien", use_container_width=True):
                if name:
                    create_patient(CURRENT_USER, name, age, gender, phone, notes)
                    st.toast(f"Pasien '{name}' ditambahkan.", icon="✅")
                    st.rerun()
                else:
                    st.warning("Nama pasien wajib diisi.")

    patients_df = get_patients(CURRENT_USER)
    if patients_df.empty:
        st.markdown("""<div class="mh-empty">👤 Belum ada pasien terdaftar.<br>
                     Gunakan formulir di atas untuk menambahkan pasien pertama Anda.</div>""",
                    unsafe_allow_html=True)
        return

    search = st.text_input("🔍 Cari pasien", placeholder="Ketik nama pasien...")
    view_df = patients_df[patients_df["name"].str.contains(search, case=False, na=False)] if search else patients_df

    for _, row in view_df.iterrows():
        logs_count = int((load_user_logs(CURRENT_USER)["patient_id"] == row["patient_id"]).sum())
        st.markdown(f"""
            <div class="frost-card" style="margin-bottom:14px;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div>
                        <h4 style="margin:0;">{row['name']} <span class="pill">{row['gender']} · {row['age']} th</span></h4>
                        <p style="color:{SLATE_500}; margin:4px 0 0 0; font-size:0.85rem;">
                            📞 {row['phone'] or '-'} &nbsp;|&nbsp; 🩺 {logs_count} pemeriksaan tercatat
                        </p>
                        <p style="color:{SLATE_500}; margin:4px 0 0 0; font-size:0.82rem;">{row['notes'] or ''}</p>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        ec1, ec2, ec3 = st.columns([1, 1, 4])
        with ec1:
            if st.button("✏️ Edit", key=f"editp_{row['patient_id']}"):
                st.session_state[f"editing_{row['patient_id']}"] = True
        with ec2:
            if st.button("🗑️ Hapus", key=f"delp_{row['patient_id']}"):
                st.session_state.confirm_delete_patient = row["patient_id"]

        if st.session_state.get(f"editing_{row['patient_id']}"):
            with st.form(f"edit_form_{row['patient_id']}"):
                ne1, ne2, ne3 = st.columns(3)
                new_name = ne1.text_input("Nama", value=row["name"])
                new_age = ne2.text_input("Usia", value=row["age"])
                new_gender = ne3.selectbox("Jenis Kelamin", ["L", "P"], index=0 if row["gender"] == "L" else 1)
                new_phone = st.text_input("Telepon", value=row["phone"] or "")
                new_notes = st.text_area("Catatan", value=row["notes"] or "")
                s1, s2 = st.columns(2)
                if s1.form_submit_button("Simpan Perubahan", use_container_width=True):
                    update_patient(row["patient_id"], new_name, new_age, new_gender, new_phone, new_notes)
                    st.session_state[f"editing_{row['patient_id']}"] = False
                    st.toast("Data pasien diperbarui.", icon="✅")
                    st.rerun()
                if s2.form_submit_button("Batal", use_container_width=True):
                    st.session_state[f"editing_{row['patient_id']}"] = False
                    st.rerun()

        if st.session_state.confirm_delete_patient == row["patient_id"]:
            st.warning(f"Hapus pasien **{row['name']}**? Riwayat EMR terkait tidak akan terhapus otomatis.")
            dc1, dc2 = st.columns(2)
            if dc1.button("Ya, hapus", key=f"confirmdel_{row['patient_id']}"):
                delete_patient(row["patient_id"], CURRENT_USER)
                st.session_state.confirm_delete_patient = None
                st.toast("Pasien dihapus.", icon="🗑️")
                st.rerun()
            if dc2.button("Batal", key=f"canceldel_{row['patient_id']}"):
                st.session_state.confirm_delete_patient = None
                st.rerun()


# ============================================================
# HALAMAN: RIWAYAT KLINIS (EMR)
# ============================================================
def render_emr_history():
    page_header("📚", "Riwayat Klinis (EMR)", "Telusuri, kelola, dan ekspor seluruh riwayat pemeriksaan Anda.")

    df = load_user_logs(CURRENT_USER)
    if df.empty:
        st.markdown("""<div class="mh-empty">📭 Belum ada riwayat pemeriksaan.<br>
                     Mulai skrining pertama Anda di halaman Dashboard.</div>""", unsafe_allow_html=True)
        return

    # ---------- Filter ----------
    st.markdown("<div class='frost-card'>", unsafe_allow_html=True)
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        q = st.text_input("🔍 Cari pasien / lesi")
    with f2:
        status_filter = st.multiselect("Status", STATUS_OPTIONS, default=STATUS_OPTIONS)
    with f3:
        date_from = st.date_input("Dari tanggal", value=None, format="YYYY-MM-DD")
    with f4:
        date_to = st.date_input("Sampai tanggal", value=None, format="YYYY-MM-DD")
    st.markdown("</div>", unsafe_allow_html=True)

    view = df.copy()
    if q:
        mask = view["patient_name"].str.contains(q, case=False, na=False) | \
               view["lesi_terdeteksi"].str.contains(q, case=False, na=False)
        view = view[mask]
    if status_filter:
        view = view[view["status"].isin(status_filter)]
    if date_from:
        view = view[view["tanggal"] >= str(date_from)]
    if date_to:
        view = view[view["tanggal"] <= str(date_to)]

    st.caption(f"Menampilkan {len(view)} dari {len(df)} total rekam.")

    # ---------- Ekspor ----------
    exp1, exp2, exp3 = st.columns(3)
    exp1.download_button("⬇️ Ekspor CSV", df_to_csv_bytes(view), "riwayat_emr.csv", "text/csv", use_container_width=True)
    xlsx_bytes = df_to_excel_bytes(view)
    exp2.download_button("⬇️ Ekspor Excel", xlsx_bytes, "riwayat_emr.xlsx",
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                          use_container_width=True, disabled=(len(xlsx_bytes) == 0))
    exp3.caption("PDF per-rekam tersedia di setiap kartu di bawah." if FPDF_OK else
                 "Ekspor PDF per-rekam nonaktif (paket `fpdf2` belum terpasang).")

    st.write("")

    for _, row in view.iterrows():
        info_matches = [v for k, v in LESION_INFO.items() if v["nama_klinis"] in str(row["lesi_terdeteksi"])]
        urgensi = max((v["urgensi"] for v in info_matches), key=lambda u: {"Rendah": 0, "Sedang": 1, "Sedang-Tinggi": 2, "Tinggi": 3}.get(u, 0)) if info_matches else "Rendah"
        st.markdown(f"""
            <div class="frost-card" style="margin-bottom:14px;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px;">
                    <div>
                        <h4 style="margin:0;">{row['patient_name']} <span class="badge {urgency_badge_class(urgensi)}">{urgensi}</span>
                        <span class="pill">{row['status']}</span></h4>
                        <p style="color:{SLATE_500}; margin:4px 0 0 0; font-size:0.85rem;">
                            📅 {row['tanggal']} · 🕐 {row['waktu']} · 🧠 {row['model_version']} · 🎯 {float(row['confidence'] or 0)*100:.0f}%
                        </p>
                        <p style="margin:8px 0 0 0; font-size:0.9rem;"><b>Lesi:</b> {row['lesi_terdeteksi']}</p>
                        <p style="margin:2px 0 0 0; font-size:0.87rem; color:{SLATE_500};"><b>Kesan klinis:</b> {row['suspek_diagnosis']}</p>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        rc1, rc2, rc3, rc4 = st.columns([1.3, 1, 1, 1])
        with rc1:
            new_status = st.selectbox("Ubah status", STATUS_OPTIONS,
                                       index=STATUS_OPTIONS.index(row["status"]) if row["status"] in STATUS_OPTIONS else 0,
                                       key=f"status_{row['log_id']}", label_visibility="collapsed")
            if new_status != row["status"]:
                update_log(row["log_id"], status=new_status)
                st.toast("Status diperbarui.", icon="🔄")
                st.rerun()
        with rc2:
            if FPDF_OK:
                pdf_bytes = build_pdf_report(export_row_to_dict(row), st.session_state.user_name)
                st.download_button("📄 PDF", pdf_bytes, f"laporan_{row['log_id']}.pdf", "application/pdf",
                                    key=f"pdf_{row['log_id']}", use_container_width=True)
        with rc3:
            with st.popover("📝 Catatan", use_container_width=True):
                new_note = st.text_area("Catatan tambahan", value=row["catatan_tambahan"] or "",
                                         key=f"noteedit_{row['log_id']}")
                if st.button("Simpan Catatan", key=f"savenote_{row['log_id']}"):
                    update_log(row["log_id"], catatan=new_note)
                    st.toast("Catatan disimpan.", icon="✅")
                    st.rerun()
        with rc4:
            if st.button("🗑️ Hapus", key=f"del_{row['log_id']}", use_container_width=True):
                st.session_state.confirm_delete_log = row["log_id"]

        if st.session_state.confirm_delete_log == row["log_id"]:
            st.warning("Hapus rekam ini secara permanen?")
            wc1, wc2 = st.columns(2)
            if wc1.button("Ya, hapus rekam", key=f"confirmdellog_{row['log_id']}"):
                delete_log(row["log_id"], CURRENT_USER)
                st.session_state.confirm_delete_log = None
                st.toast("Rekam dihapus.", icon="🗑️")
                st.rerun()
            if wc2.button("Batal", key=f"canceldellog_{row['log_id']}"):
                st.session_state.confirm_delete_log = None
                st.rerun()


# ============================================================
# HALAMAN: ANALITIK DATA
# ============================================================
def render_analytics():
    page_header("📊", "Analitik Data", "Ringkasan tren dan pola temuan klinis dari seluruh riwayat skrining Anda.")

    scope_admin = False
    if st.session_state.is_admin:
        scope_admin = st.toggle("Tampilkan data seluruh klinisi (mode Admin)", value=False)

    df = load_all_logs_admin() if scope_admin else load_user_logs(CURRENT_USER)
    if df.empty:
        st.markdown("""<div class="mh-empty">📈 Belum ada data untuk dianalisis.<br>
                     Data akan muncul di sini setelah Anda menyimpan hasil skrining.</div>""", unsafe_allow_html=True)
        return

    total = len(df)
    unique_patients = df["patient_name"].nunique()
    avg_conf = float(df["confidence"].fillna(0).mean() or 0) * 100
    followup = int((df["status"] == "Perlu Tindak Lanjut").sum())

    k1, k2, k3, k4 = st.columns(4)
    with k1: kpi_card("Total Pemeriksaan", total)
    with k2: kpi_card("Pasien Unik", unique_patients)
    with k3: kpi_card("Rata-rata Confidence", f"{avg_conf:.0f}%")
    with k4: kpi_card("Perlu Tindak Lanjut", followup, accent=(followup > 0))

    st.write("")
    col_a, col_b = st.columns(2, gap="large")

    with col_a:
        st.markdown("<div class='frost-card'>", unsafe_allow_html=True)
        st.markdown("<h4>🦷 Frekuensi Jenis Lesi</h4>", unsafe_allow_html=True)
        lesion_counts = {}
        for names in df["lesi_terdeteksi"].dropna():
            for n in str(names).split(","):
                n = n.strip()
                if n:
                    lesion_counts[n] = lesion_counts.get(n, 0) + 1
        if lesion_counts:
            lc_df = pd.DataFrame({"Jumlah": lesion_counts}).sort_values("Jumlah", ascending=False)
            st.bar_chart(lc_df, color=CORAL_500)
        else:
            st.caption("Belum ada data lesi.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_b:
        st.markdown("<div class='frost-card'>", unsafe_allow_html=True)
        st.markdown("<h4>📅 Tren Pemeriksaan Harian</h4>", unsafe_allow_html=True)
        trend = df.groupby("tanggal").size().rename("Jumlah").to_frame()
        trend.index.name = "Tanggal"
        st.line_chart(trend, color=NAVY_700)
        st.markdown("</div>", unsafe_allow_html=True)

    col_c, col_d = st.columns(2, gap="large")
    with col_c:
        st.markdown("<div class='frost-card'>", unsafe_allow_html=True)
        st.markdown("<h4>🚦 Distribusi Status Tindak Lanjut</h4>", unsafe_allow_html=True)
        status_counts = df["status"].value_counts()
        st.bar_chart(status_counts, color=NAVY_600)
        st.markdown("</div>", unsafe_allow_html=True)
    with col_d:
        st.markdown("<div class='frost-card'>", unsafe_allow_html=True)
        st.markdown("<h4>🧠 Penggunaan Model AI</h4>", unsafe_allow_html=True)
        model_counts = df["model_version"].value_counts()
        st.bar_chart(model_counts, color=CORAL_600)
        st.markdown("</div>", unsafe_allow_html=True)

    if scope_admin:
        st.markdown("<div class='frost-card'>", unsafe_allow_html=True)
        st.markdown("<h4>👥 Aktivitas per Klinisi</h4>", unsafe_allow_html=True)
        by_clin = df.groupby("clinician_name").size().rename("Jumlah Pemeriksaan").sort_values(ascending=False)
        st.dataframe(by_clin, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# HALAMAN: ENSIKLOPEDIA LESI
# ============================================================
def render_encyclopedia():
    page_header("📖", "Ensiklopedia Lesi", "Referensi klinis singkat untuk setiap jenis lesi yang dapat dikenali sistem.")

    search = st.text_input("🔍 Cari nama lesi atau kategori", placeholder="mis. karies, trauma, variasi anatomis")
    categories = sorted(set(v["kategori"] for v in LESION_INFO.values()))
    cat_filter = st.multiselect("Filter kategori", categories, default=categories)

    items = [(k, v) for k, v in LESION_INFO.items() if v["kategori"] in cat_filter]
    if search:
        s = search.lower()
        items = [(k, v) for k, v in items if s in k or s in v["nama_klinis"].lower() or s in v["kategori"].lower()]

    if not items:
        st.markdown("""<div class="mh-empty">🔎 Tidak ada lesi yang cocok dengan pencarian Anda.</div>""",
                    unsafe_allow_html=True)
        return

    cols = st.columns(3, gap="medium")
    for i, (key, info) in enumerate(items):
        with cols[i % 3]:
            st.markdown(f"""
                <div class="lesion-card">
                    <div class="lesion-icon">{info['ikon']}</div>
                    <h4>{info['nama_klinis']}</h4>
                    <div class="lesion-cat">{info['kategori']} · <span class="badge {urgency_badge_class(info['urgensi'])}">{info['urgensi']}</span></div>
                    <p><b>Deskripsi:</b> {info['deskripsi']}</p>
                    <p><b>Rekomendasi:</b> {info['rekomendasi']}</p>
                </div>
            """, unsafe_allow_html=True)
            st.write("")


# ============================================================
# HALAMAN: PENGATURAN SISTEM
# ============================================================
def render_settings():
    page_header("⚙️", "Pengaturan Sistem", "Kelola profil, preferensi AI, data, dan akses administrator.")

    tabs = ["👤 Profil", "🔐 Keamanan", "🎛️ Preferensi AI", "💾 Data"]
    if st.session_state.is_admin:
        tabs.append("🛡️ Admin")
    tab_objs = st.tabs(tabs)

    with tab_objs[0]:
        st.markdown("<div class='frost-card'>", unsafe_allow_html=True)
        with st.form("profile_form"):
            new_name = st.text_input("Nama Lengkap", value=st.session_state.user_name)
            new_role = st.text_input("Peran/Jabatan", value=st.session_state.user_role)
            if st.form_submit_button("Simpan Profil"):
                update_profile(CURRENT_USER, new_name, new_role)
                st.session_state.user_name = new_name
                st.session_state.user_role = new_role
                st.toast("Profil diperbarui.", icon="✅")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_objs[1]:
        st.markdown("<div class='frost-card'>", unsafe_allow_html=True)
        st.markdown("<h4>Ubah Password</h4>", unsafe_allow_html=True)
        with st.form("password_form"):
            old_pw = st.text_input("Password Saat Ini", type="password")
            new_pw = st.text_input("Password Baru", type="password")
            new_pw2 = st.text_input("Konfirmasi Password Baru", type="password")
            if st.form_submit_button("Perbarui Password"):
                if not verify_login(CURRENT_USER, old_pw):
                    st.error("Password saat ini salah.")
                elif len(new_pw) < 6:
                    st.warning("Password baru minimal 6 karakter.")
                elif new_pw != new_pw2:
                    st.warning("Konfirmasi password baru tidak cocok.")
                else:
                    update_password(CURRENT_USER, new_pw)
                    st.success("Password berhasil diperbarui.")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_objs[2]:
        st.markdown("<div class='frost-card'>", unsafe_allow_html=True)
        st.markdown("<h4>Threshold Default</h4>", unsafe_allow_html=True)
        st.caption("Nilai ini akan otomatis dimuat setiap kali Anda masuk.")
        pc1, pc2 = st.columns(2)
        pconf = pc1.slider("Confidence default", 0.05, 0.95, float(st.session_state.conf_threshold), 0.05)
        piou = pc2.slider("IoU default", 0.05, 0.95, float(st.session_state.iou_threshold), 0.05)
        if st.button("Simpan Preferensi AI"):
            save_prefs(CURRENT_USER, pconf, piou)
            st.session_state.conf_threshold = pconf
            st.session_state.iou_threshold = piou
            st.toast("Preferensi AI disimpan.", icon="✅")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_objs[3]:
        st.markdown("<div class='frost-card'>", unsafe_allow_html=True)
        st.markdown("<h4>Ekspor & Cadangan Data</h4>", unsafe_allow_html=True)
        my_df = load_user_logs(CURRENT_USER)
        dcol1, dcol2 = st.columns(2)
        dcol1.download_button("⬇️ Unduh Seluruh Riwayat (CSV)", df_to_csv_bytes(my_df),
                               "backup_riwayat_emr.csv", "text/csv", use_container_width=True,
                               disabled=my_df.empty)
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "rb") as fh:
                dcol2.download_button("⬇️ Cadangkan Basis Data (.db)", fh.read(), "mammouth_backup.db",
                                       "application/octet-stream", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='frost-card' style='border-color:#fecaca;'>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='color:{DANGER};'>⚠️ Zona Berbahaya</h4>", unsafe_allow_html=True)
        st.caption("Menghapus seluruh riwayat pemeriksaan milik akun Anda secara permanen. Tindakan ini tidak dapat dibatalkan.")
        if st.button("Hapus Semua Riwayat Saya", type="secondary"):
            st.session_state.confirm_wipe = True
        if st.session_state.confirm_wipe:
            st.warning("Anda yakin? Ketik konfirmasi di bawah untuk melanjutkan.")
            wipe_confirm_text = st.text_input("Ketik HAPUS untuk konfirmasi")
            if st.button("Konfirmasi Penghapusan Permanen"):
                if wipe_confirm_text.strip().upper() == "HAPUS":
                    conn = get_conn()
                    conn.execute("DELETE FROM emr_logs WHERE user_id=?", (CURRENT_USER,))
                    conn.commit()
                    conn.close()
                    st.session_state.confirm_wipe = False
                    st.toast("Seluruh riwayat berhasil dihapus.", icon="🗑️")
                    st.rerun()
                else:
                    st.error("Konfirmasi tidak sesuai. Ketik 'HAPUS' persis.")
        st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.is_admin:
        with tab_objs[4]:
            st.markdown("<div class='frost-card'>", unsafe_allow_html=True)
            st.markdown("<h4>🛡️ Panel Administrator</h4>", unsafe_allow_html=True)
            st.caption(f"Total {count_users()} akun klinisi terdaftar di sistem ini.")
            st.dataframe(load_all_users_admin(), use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(f"""
        <div style="text-align:center; color:{SLATE_500}; font-size:0.78rem; margin-top:10px;">
            {APP_NAME} · Versi {APP_VERSION} · Dibangun dengan Streamlit
        </div>
    """, unsafe_allow_html=True)


# ============================================================
# ROUTING UTAMA
# ============================================================
PAGES = {
    "Dashboard Skrining": render_dashboard,
    "Manajemen Pasien": render_patients,
    "Riwayat Klinis (EMR)": render_emr_history,
    "Analitik Data": render_analytics,
    "Ensiklopedia Lesi": render_encyclopedia,
    "Pengaturan Sistem": render_settings,
}

PAGES.get(menu, render_dashboard)()
