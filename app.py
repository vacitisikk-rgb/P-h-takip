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
            transfer INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Aktif',
            FOREIGN KEY(username) REFERENCES users(username),
            UNIQUE(username, week_start)
        )
    ''')
    conn.commit()
    return conn

conn = init_db()
cursor = conn.cursor()

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
tab1, tab2, tab3 = st.tabs(["✍️ Tekli Veri Girişi", "📋 Metinden Toplu Yükle", "📊 Haftalık Tablo ve Çıktılar"])

# --- SEKME 1: TEKLİ VERİ GİRİŞİ ---
with tab1:
    st.subheader("İşlem Bazlı Kullanıcı Girişi")
    
    with st.form("user_form", clear_on_submit=True):
        col_u1, col_u2 = st.columns([2, 1])
        with col_u1:
            u_name = st.text_input("Kullanıcı Adı:").strip()
        with col_u2:
            u_status = st.selectbox("Kullanıcı Genel Durumu:", ["Aktif", "İZİNLİ", "YENİ GELDİ"])
            
        st.markdown("##### Eklenecek İşlem Bilgileri")
        col_i1, col_i2 = st.columns(3)
        
        with col_i1:
            selected_activity = st.selectbox(
                "Yapılan İşlem Türünü Seçin:", 
                ["Terfi", "Eğitim", "Maaş (Mr)", "Destek", "Rozet", "Transfer"]
            )
        with col_i2:
            activity_value = st.number_input("Gireceğiniz Sayı / Miktar:", min_value=0, value=1, step=1)
            
        submit_btn = st.form_submit_button("İşlemi Kaydet / Listeye Ekle", use_container_width=True)
        
        if submit_btn:
            if not u_name:
                st.error("Kullanıcı adı boş olamaz!")
            else:
                cursor.execute("INSERT OR IGNORE INTO users (username) VALUES (?)", (u_name,))
                
                cursor.execute(
                    "SELECT terfi, egitim, maas, destek, rozet, transfer FROM weekly_data WHERE username=? AND week_start=?",
                    (u_name, selected_week_start)
                )
                existing_record = cursor.fetchone()
                
                t_val = activity_value if selected_activity == "Terfi" else 0
                e_val = activity_value if selected_activity == "Eğitim" else 0
                m_val = activity_value if selected_activity == "Maaş (Mr)" else 0
                d_val = activity_value if selected_activity == "Destek" else 0
                r_val = activity_value if selected_activity == "Rozet" else 0
                tr_val = activity_value if selected_activity == "Transfer" else 0
                
                if existing_record:
                    cursor.execute("UPDATE weekly_data SET terfi=terfi+?, egitim=egitim+?, maas=maas+?, destek=destek+?, rozet=rozet+?, transfer=transfer+?, status=? WHERE username=? AND week_start=?", (t_val, e_val, m_val, d_val, r_val, tr_val, u_status, u_name, selected_week_start))
                else:
                    cursor.execute("INSERT INTO weekly_data (username, week_start, terfi, egitim, maas, destek, rozet, transfer, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (u_name, selected_week_start, t_val, e_val, m_val, d_val, r_val, tr_val, u_status))
                    
                conn.commit()
                st.success(f"Başarılı! {u_name} kullanıcısına {activity_value} adet {selected_activity} eklendi.")
                st.rerun()

# --- SEKME 2: DİSCORD METİNLERİNİ AKILLI ÇÖZÜMLEYEN TOPLU YÜKLEME ---
with tab2:
    st.subheader("Discord / Metin Listesinden Akıllı Toplu Veri Aktarımı")
    st.info("Yapıştıracağınız listenin ana kategorisini seçin. Eğer girdiğiniz metin hem Rozet hem Transfer içeriyorsa, sistem ikisini de aynı anda ayıklar.")
    
    bulk_category = st.selectbox(
        "Yapıştıracağınız Metindeki Sayılar Hangi Haneye Eklensin?",
        ["Terfi", "Eğitim", "Maaş (Mr)", "Destek", "Rozet / Özel Ekip"]
    )
    
    raw_text = st.text_area(
        "Discord Listesini Buraya Yapıştırın:", 
        height=250, 
        placeholder="Kopyaladığınız listeyi direkt buraya yapıştırabilirsiniz."
    )
    
    if st.button("🚀 Verileri Ayrıştır ve Üzerine Ekle", use_container_width=True):
        if raw_text:
            lines = raw_text.strip().split("\n")
            count = 0
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith("**") or "VERİLERİ" in line.upper() or "GÜNCELDİR" in line.upper() or line.startswith("➔") or line.startswith("»") or "NICK :" in line.upper():
                    continue
                
                status = "Aktif"
                val = 0
                trans_val = 0
                username = ""
                
                if "İZİNLİ" in line.upper():
                    status = "İZİNLİ"
                    parts = line.split()
                    username = parts[0].replace("-", "").replace(":", "").strip()
                elif "YENİ GELDİ" in line.upper() or "YENİ" in line.upper():
                    status = "YENİ GELDİ"
                    parts = line.split()
                    username = parts[0].replace("-", "").replace(":", "").strip()
                else:
                    # Özel Ekip/Rozet formatı kontrolü: "2577-: Rozet: 1 Transfer: 1"
                    if "ROZET:" in line.upper() or "TRANSFER:" in line.upper():
                        clean_line = line.replace("-", " ").replace(":", " ").replace("=", " ")
                        parts = clean_line.split()
                        username = parts[0].strip()
                        nums = [int(s) for s in parts if s.isdigit()]
                        if len(nums) >= 2:
                            val = nums[0]        # İlk sayı Rozet
                            trans_val = nums[1]  # İkinci sayı Transfer
                        elif len(nums) == 1:
                            val = nums[0]
                    else:
                        clean_line = line.replace("➔", " ").replace("»", " ").replace(":", " ").replace("-", " ").replace(",", " ")
                        clean_line = re.sub(r'\b(Veri|veri|verisi|Mr|mr|Maaş|Maas)\b', ' ', clean_line)
                        
                        parts = clean_line.split()
                        if not parts:
                            continue
                        
                        username = parts[0].strip()
                        nums = [int(n) for n in parts if n.isdigit()]
                        if nums:
                            val = nums[0]
                        else:
                            continue
                
                if username and username != "---":
                    cursor.execute("INSERT OR IGNORE INTO users (username) VALUES (?)", (username,))
                    
                    cursor.execute(
                        "SELECT terfi, egitim, maas, destek, rozet, transfer FROM weekly_data WHERE username=? AND week_start=?",
                        (username, selected_week_start)
                    )
                    existing = cursor.fetchone()
                    
                    t_inc = val if bulk_category == "Terfi" else 0
                    e_inc = val if bulk_category == "Eğitim" else 0
                    m_inc = val if bulk_category == "Maaş (Mr)" else 0
                    d_inc = val if bulk_category == "Destek" else 0
                    r_inc = val if bulk_category == "Rozet / Özel Ekip" else 0
                    tr_inc = trans_val if bulk_category == "Rozet / Özel Ekip" else 0
                    
                    if existing:
                        cursor.execute("UPDATE weekly_data SET terfi=terfi+?, egitim=egitim+?, maas=maas+?, destek=destek+?, rozet=rozet+?, transfer=transfer+?, status=? WHERE username=? AND week_start=?", (t_inc, e_inc, m_inc, d_inc, r_inc, tr_inc, status, username, selected_week_start))
                    else:
                        cursor.execute("INSERT INTO weekly_data (username, week_start, terfi, egitim, maas, destek, rozet, transfer, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (username, selected_week_start, t_inc, e_inc, m_inc, d_inc, r_inc, tr_inc, status))
                        
                    count += 1
                    
            conn.commit()
            st.success(f"Başarılı! Listeden {count} kişi ayıklandı.")
            st.rerun()

# --- SEKME 3: HAFTALIK TABLO VE ÇIKTILAR ---
with tab3:
    st.subheader(f"📅 {selected_label} Veri Raporları")
    
    cursor.execute("""
        SELECT username, status, terfi, egitim, maas, destek, rozet, transfer 
        FROM weekly_data WHERE week_start = ? ORDER BY username ASC
    """, (selected_week_start,))
    rows = cursor.fetchall()
    
    if rows:
        data_list = []
        
        # Genel Tablo Metin Formatı
        text_output = f"**{selected_label} Haftalık Veri Girişi**\nTerfi - Eğitim - Mr - Destek - Rozet Verme Sayıları\n\n"
        
        # Rozet Ekibi Özel Çıktı Formatı (İstediğin `Rozet: X Transfer: Y = Z` düzeni)
        rozet_output = f"🏅 **Rozet Ekibi Listesi ve Format Çıktısı**\n\n{selected_label} Rozet Verme Sayısı\n\n"
        rozet_output += f"    Nick :       Rozet:  Transfer:\n\n"
        
        # Toplam Sayaçlar
        total_rozet_count = 0
        total_transfer_count = 0
        
        for row in rows:
            username, status, t, e, m, d, r, tr = row
            if status in ["İZİNLİ", "YENİ GELDİ"]:
                toplam = status
                text_output += f"{username:<15} {status}\n"
            else:
                toplam = t + e + m + d + r + tr
                text_output += f"{username:<15} {t} + {e} + {m} + {d} + {r} + {tr} = {toplam}\n"
                
                # Kişinin rozet veya transfer verisi varsa tam istediğin "= toplam" formatıyla ekle
                if r > 0 or tr > 0:
                    rozet_toplam = r + tr
                    rozet_output += f"{username:<12}-: Rozet: {r} Transfer: {tr} = {rozet_toplam}\n"
                    total_rozet_count += r
                    total_transfer_count += tr
                
            data_list.append([username, status, t, e, m, d, r, tr, toplam])
            
        rozet_output += f"\n➔ Toplam Dağıtılan Rozet: {total_rozet_count}\n➔ Toplam Yapılan Transfer: {total_transfer_count}"
            
        df = pd.DataFrame(data_list, columns=["Kullanıcı Adı", "Durum", "Terfi", "Eğitim", "Maaş (Mr)", "Destek", "Rozet", "Transfer", "Toplam"])
        
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
            st.markdown("#### 📋 Kopyalanabilir Genel Veri Formatı")
            st.text_area("Genel Tablo Metni:", text_output, height=220)
            
            st.markdown("#### 🏅 Rozet Ekibi Format Çıktısı")
            st.text_area("Rozet Özel Çıktı Metni:", rozet_output, height=220)
            
        with col_out2:
            st.markdown("#### 🍏 Excel Formatında İndir")
            csv_data = df.to_csv(index=False, sep=";").encode('utf-8-sig')
            st.download_button(label="📥 Excel (CSV) Dosyasını İndir", data=csv_data, file_name=f"poh_haftalik_{selected_week_start}.csv", mime="text/csv", use_container_width=True)
    else:
        st.warning("Seçtiğiniz bu haftaya ait henüz girilmiş bir veri bulunmuyor. Diğer sekmeleri kullanarak veri ekleyebilirsiniz.")
