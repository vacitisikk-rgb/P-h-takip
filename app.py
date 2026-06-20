import streamlit as st
import sqlite3
import datetime
import re
import pandas as pd

# Sayfa Ayarları (Mobil ve Geniş Ekran Uyumlu)
st.set_page_config(page_title="PÖH Hak Sahipleri - Haftalık Veri Takip", page_icon="📊", layout="wide")

# Veri Tabanı Kurulumu
def init_db():
    conn = sqlite3.connect("haftalik_takip.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY)')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weekly_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            week_start TEXT,
            terfi INTEGER DEFAULT 0,
            egitim INTEGER DEFAULT 0,
            maas INTEGER DEFAULT 0,
            destek INTEGER DEFAULT 0,
            rozet INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Aktif',
            FOREIGN KEY(username) REFERENCES users(username),
            UNIQUE(username, week_start)
        )
    ''')
    conn.commit()
    return conn

conn = init_db()
cursor = conn.cursor()

# Herhangi bir tarihin ait olduğu Pazartesi gününü bulma fonksiyonu
def get_monday_of_date(target_date):
    monday = target_date - datetime.timedelta(days=target_date.weekday())
    return monday.strftime("%Y-%m-%d")

def format_week_label(date_str):
    start_dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    end_dt = start_dt + datetime.timedelta(days=6)
    return f"{start_dt.strftime('%d.%m.%Y')} - {end_dt.strftime('%d.%m.%Y')}"

# --- ARAYÜZ BAŞLIĞI ---
st.title("📊 PÖH Hak Sahipleri - Haftalık Takip")

# --- ÜST MENÜ: TAKVİMDEN HAFTA SEÇİMİ ---
col_week_1, col_week_2 = st.columns([2, 1])

with col_week_1:
    chosen_date = st.date_input("Takip Edilecek Tarihi/Haftayı Takvimden Seçin:", datetime.date.today())
    selected_week_start = get_monday_of_date(chosen_date)
    selected_label = format_week_label(selected_week_start)
    st.info(f"📅 Şu an işlem yapılan hafta aralığı: **{selected_label}**")

with col_week_2:
    st.write("##") 
    st.write("##")
    if st.button("🔄 Seçili Haftayı Sisteme Tanımla", use_container_width=True):
        st.success(f"Hafta aktif edildi: {selected_label}")

st.markdown("---")

# --- ANA KISIM: 3 SEKMELİ YAPI ---
tab1, tab2, tab3 = st.tabs(["✍️ Hak Sahipleri & Veri Girişi", "📋 Metinden Toplu Yükle", "📊 Haftalık Tablo ve Çıktılar"])

# --- SEKME 1: YENİLENEN LİSTELİ VERİ GİRİŞİ ---
with tab1:
    st.subheader("Hak Sahibi Seçimi ve İşlem Girişi")
    
    # Veritabanındaki tüm kullanıcıları çekelim
    cursor.execute("SELECT username FROM users ORDER BY username ASC")
    existing_users = [row[0] for row in cursor.fetchall()]
    
    # Seçim listesi oluşturuyoruz (En başına yeni ekleme seçeneği koyduk)
    user_options = ["+ Yeni Hak Sahibi Ekle"] + existing_users
    
    with st.form("user_form", clear_on_submit=True):
        col_u1, col_u2 = st.columns([2, 1])
        
        with col_u1:
            selected_user_option = st.selectbox("İşlem Yapılacak Hak Sahibini Seçin:", user_options)
            
            # Eğer yeni ekle seçildiyse altta bir metin kutusu açalım
            if selected_user_option == "+ Yeni Hak Sahibi Ekle":
                u_name = st.text_input("Yeni Hak Sahibinin Adı:").strip()
            else:
                u_name = selected_user_option
                
        with col_u2:
            u_status = st.selectbox("Kullanıcı Genel Durumu:", ["Aktif", "İZİNLİ", "YENİ GELDİ"])
            
        st.markdown("##### Eklenecek İşlem Bilgileri")
        col_i1, col_i2 = st.columns(2)
        
        with col_i1:
            selected_activity = st.selectbox(st.markdown("##### Eklenecek İşlem Bilgileri")
        col_i1, col_i2 = st.columns(2)
        
        with col_i1:
            selected_activity = st.selectbox(
                "Yapılan İşlem Türünü Seçin:", 
                ["Terfi", "Eğitim", "Maaş (Mr)", "Destek", "Rozet"] )
        with col_i2:
            activity_value = st.number_input("Gireceğiniz Sayı / Miktar:", min_value=0, value=1, step=1)
                
                "Yapılan İşlem Türünü Seçin:",
