import streamlit as st
import sqlite3
import datetime
import re
import pandas as pd

# Sayfa Ayarları (Mobil ve Geniş Ekran Uyumlu)
st.set_page_config(page_title="PÖH Ailesi - Haftalık Takip", page_icon="📊", layout="wide")

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
st.title("📊 PÖH Ailesi - Haftalık Veri Takip Sistemi")

# --- ÜST MENÜ: TAKVİMDEN HAFTA SEÇİMİ ---
col_week_1, col_week_2 = st.columns([2, 1])

with col_week_1:
    # Kullanıcı takvimden istediği günü seçer
    chosen_date = st.date_input("Takip Edilecek Tarihi/Haftayı Takvimden Seçin:", datetime.date.today())
    # Seçilen tarihin ait olduğu haftanın başlangıcı (Pazartesi) hesaplanır
    selected_week_start = get_monday_of_date(chosen_date)
    selected_label = format_week_label(selected_week_start)
    
    # Bilgilendirme etiketi
    st.info(f"📅 Şu an işlem yapılan hafta aralığı: **{selected_label}**")

with col_week_2:
    st.write("##") # Hizalama Boşluğu
    st.write("##")
    # Mevcut seçili haftayı veritabanı altyapısına hazır hale getirmek için boş kayıt tetikleyicisi
    if st.button("🔄 Seçili Haftayı Sisteme Tanımla", use_container_width=True):
        st.success(f"Hafta aktif edildi: {selected_label}")

st.markdown("---")

# --- ANA KISIM: 3 SEKMELİ YAPI (Veri Girişi, Toplu Yükleme, Tablo ve Çıktı Al) ---
tab1, tab2, tab3 = st.tabs(["✍️ Tekli Veri Girişi", "📋 Metinden Toplu Yükle", "📊 Haftalık Tablo ve Çıktılar"])

# --- SEKME 1: TEKLİ VERİ GİRİŞİ ---
with tab1:
    st.subheader("Kullanıcı Ekle veya Düzenle")
    with st.form("user_form", clear_on_submit=True):
        u_name = st.text_input("Kullanıcı Adı:").strip()
        u_status = st.selectbox("Durum:", ["Aktif", "İZİNLİ", "YENİ GELDİ"])
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1: t_val = st.number_input("Terfi:", min_value=0, value=0, step=1)
        with col2: e_val = st.number_input("Eğitim:", min_value=0, value=0, step=1)
        with col3: m_val = st.number_input("Maaş (Mr):", min_value=0, value=0, step=1)
        with col4: d_val = st.number_input("Destek:", min_value=0, value=0, step=1)
        with col5: r_val = st.number_input("Rozet:", min_value=0, value=0, step=1)
        
        submit_btn = st.form_submit_button("Kaydet / Güncelle", use_container_width=True)
        
        if submit_btn:
            if not u_name:
                st.error("Kullanıcı adı boş olamaz!")
            else:
                cursor.execute("INSERT OR IGNORE INTO users (username) VALUES (?)", (u_name,))
                cursor.execute("""
                    INSERT INTO weekly_data (username, week_start, terfi, egitim, maas, destek, rozet, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(username, week_start) DO UPDATE SET
                        terfi=excluded.terfi, egitim=excluded.egitim, maas=excluded.maas,
                        destek=excluded.destek, rozet=excluded.rozet, status=excluded.status
                """, (u_name, selected_week_start, t_val, e_val, m_val, d_val, r_val, u_status))
                conn.commit()
                st.success(f"{u_name} verisi başarıyla kaydedildi!")
                st.rerun()

# --- SEKME 2: METİNDEN TOPLU YÜKLE ---
with tab2:
    st.subheader("Discord / Metin Listesinden Toplu Veri Aktarımı")
    st.info("Aşağıdaki kutuya haftalık metin formatını olduğu gibi yapıştırıp yükleyebilirsiniz.")
    
    raw_text = st.text_area("Haftalık Rapor Metni:", height=250, placeholder="ArdaDkbs-   5 + 0 + 0 + 6 + 11 = 22\nBerkan1515         İZİNLİ")
    
    if st.button("🚀 Verileri Sisteme Çözümle ve Yükle", use_container_width=True):
        if raw_text:
            lines = raw_text.strip().split("\n")
            count = 0
            for line in lines:
                line = line.strip()
                if not line or line.startswith("**") or "HAFTALIK VERİ GİRİŞİ" in line.upper():
                    continue
                
                if "İZİNLİ" in line.upper():
                    parts = re.split(r'\s+', line)
                    username = parts[0].replace("-", "").strip()
                    status, t, e, m, d, r = "İZİNLİ", 0, 0, 0, 0, 0
                elif "YENİ GELDİ" in line.upper() or "YENİ" in line.upper():
                    parts = re.split(r'\s{2,}', line) if "  " in line else line.split()
                    username = parts[0].replace("-", "").strip()
                    status, t, e, m, d, r = "YENİ GELDİ", 0, 0, 0, 0, 0
                else:
                    if "-" in line and not line.startswith("-"):
                        username_part, math_part = line.split("-", 1)
                        username = username_part.strip()
                    else:
                        match_user = re.match(r'^([a-zA-Z0-9_\.]+)', line)
                        if match_user:
                            username = match_user.group(1)
                            math_part = line[len(username):]
                        else:
                            continue
                    
                    nums = re.findall(r'\d+', math_part)
                    if len(nums) >= 5:
                        t, e, m, d, r = int(nums[0]), int(nums[1]), int(nums[2]), int(nums[3]), int(nums[4])
                        status = "Aktif"
                    else:
                        continue
                
                if username:
                    cursor.execute("INSERT OR IGNORE INTO users (username) VALUES (?)", (username,))
                    cursor.execute("""
                        INSERT INTO weekly_data (username, week_start, terfi, egitim, maas, destek, rozet, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(username, week_start) DO UPDATE SET
                            terfi=excluded.terfi, egitim=excluded.egitim, maas=excluded.maas,
                            destek=excluded.destek, rozet=excluded.rozet, status=excluded.status
                    """, (username, selected_week_start, t, e, m, d, r, status))
                    count += 1
            conn.commit()
            st.success(f"Başarılı! Toplam {count} kişinin verisi yüklendi/güncellendi.")
            st.rerun()

# --- SEKME 3: HAFTALIK TABLO VE ÇIKTILAR ---
with tab3:
    st.subheader(f"📅 {selected_label} Veri Raporları")
    
    cursor.execute("""
        SELECT username, status, terfi, egitim, maas, destek, rozet 
        FROM weekly_data WHERE week_start = ? ORDER BY username ASC
    """, (selected_week_start,))
    rows = cursor.fetchall()
    
    if rows:
        data_list = []
        text_output = f"**{selected_label} Haftalık Veri Girişi**\nTerfi - Eğitim - Mr - Destek - Rozet Verme Sayıları\n\n"
        
        for row in rows:
            username, status, t, e, m, d, r = row
            if status in ["İZİNLİ", "YENİ GELDİ"]:
                toplam = status
                text_output += f"{username:<15} {status}\n"
            else:
                toplam = t + e + m + d + r
                text_output += f"{username:<15} {t} + {e} + {m} + {d} + {r} = {toplam}\n"
                
            data_list.append([username, status, t, e, m, d, r, toplam])
            
        df = pd.DataFrame(data_list, columns=["Kullanıcı Adı", "Durum", "Terfi", "Eğitim", "Maaş (Mr)", "Destek", "Rozet", "Toplam"])
        
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.markdown("### 🛠️ Seçili Kullanıcıyı Sil")
        del_user = st.selectbox("Silmek istediğiniz kullanıcıyı seçin:", ["---"] + [r[0] for r in rows])
        if del_user != "---":
            if st.button(f"❌ {del_user} Kişisinin Bu Haftaki Verisini Sil", type="primary"):
                cursor.execute("DELETE FROM weekly_data WHERE username=? AND week_start=?", (del_user, selected_week_start))
                conn.commit()
                st.success(f"{del_user} silindi.")
                st.rerun()
        
        st.markdown("---")
        
        col_out1, col_out2 = st.columns(2)
        
        with col_out1:
            st.markdown("#### 📋 Kopyalanabilir Metin Formatı")
            st.text_area("Aşağıdaki metni direkt kopyalayabilirsiniz:", text_output, height=250)
            
        with col_out2:
            st.markdown("#### 🍏 Excel Formatında İndir")
            csv_data = df.to_csv(index=False, sep=";").encode('utf-8-sig')
            st.download_button(
                label="📥 Excel (CSV) Dosyasını İndir",
                data=csv_data,
                file_name=f"poh_haftalik_{selected_week_start}.csv",
                mime="text/csv",
                use_container_width=True
            )
    else:
        st.warning("Seçtiğiniz bu haftaya ait henüz girilmiş bir veri bulunmuyor. Diğer sekmeleri kullanarak veri ekleyebilirsiniz.")
