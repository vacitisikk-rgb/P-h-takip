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
            rozet_transfer INTEGER DEFAULT 0,
            rozet_rozet INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Aktif',
            FOREIGN KEY(username) REFERENCES users(username),
            UNIQUE(username, week_start)
        )
    ''')
    
    # Eski veritabanı olanlar için yeni sütunları kontrol edip ekliyoruz
    cursor.execute("PRAGMA table_info(weekly_data)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'rozet_transfer' not in columns:
        cursor.execute('ALTER TABLE weekly_data ADD COLUMN rozet_transfer INTEGER DEFAULT 0')
    if 'rozet_rozet' not in columns:
        cursor.execute('ALTER TABLE weekly_data ADD COLUMN rozet_rozet INTEGER DEFAULT 0')
        
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

# --- ANA KISIM: 4 SEKMELİ YAPI ---
tab1, tab2, tab3, tab4 = st.tabs([
    "✍️ Hak Sahipleri & Veri Girişi", 
    "🏅 Rozet Ekibi Girişi",
    "📋 Metinden Toplu Yükle", 
    "📊 Haftalık Tablo ve Çıktılar"
])

# --- SEKME 1: GENEL HAK SAHİPLERİ ---
with tab1:
    cursor.execute("SELECT username FROM users ORDER BY username ASC")
    existing_users = [row[0] for row in cursor.fetchall()]
    
    col_left, col_right = st.columns([5, 3])
    
    with col_left:
        st.subheader("👥 Seçili Haftanın Hak Sahipleri ve Güncel Verileri")
        cursor.execute("""
            SELECT u.username, COALESCE(w.status, 'Aktif') as status,
                   COALESCE(w.terfi, 0) as terfi, COALESCE(w.egitim, 0) as egitim, 
                   COALESCE(w.maas, 0) as maas, COALESCE(w.destek, 0) as destek, COALESCE(w.rozet, 0) as rozet
            FROM users u
            LEFT JOIN weekly_data w ON u.username = w.username AND w.week_start = ?
            ORDER BY u.username ASC
        """, (selected_week_start,))
        current_week_rows = cursor.fetchall()
        
        if current_week_rows:
            table_data = []
            for row in current_week_rows:
                uname, status, t, e, m, d, r = row
                toplam = status if status in ["İZİNLİ", "YENİ GELDİ"] else (t + e + m + d + r)
                table_data.append([uname, status, t, e, m, d, r, toplam])
                
            df_display = pd.DataFrame(table_data, columns=["Kullanıcı Adı", "Durum", "Terfi", "Eğitim", "Maaş (Mr)", "Destek", "Rozet", "Toplam"])
            st.dataframe(df_display, use_container_width=True, hide_index=True, height=280)
        else:
            st.warning("Sistemde henüz kayıtlı hiçbir Hak Sahibi bulunmuyor.")
            
    with col_right:
        st.subheader("🛠️ Hak Sahibi Yönetimi")
        with st.form("add_user_form", clear_on_submit=True):
            new_user_input = st.text_input("Yeni Hak Sahibi Ekle:", placeholder="Kullanıcı adını yazın...").strip()
            add_btn = st.form_submit_button("➕ Listeye Yeni İsim Ekle", use_container_width=True)
            if add_btn and new_user_input:
                cursor.execute("INSERT OR IGNORE INTO users (username) VALUES (?)", (new_user_input,))
                conn.commit()
                st.success(f"**{new_user_input}** listeye eklendi!")
                st.rerun()
                
        st.write("##")
        with st.form("delete_user_form", clear_on_submit=True):
            user_to_delete = st.selectbox("Sistemden Tamamen Silinecek Kişi:", ["---"] + existing_users)
            delete_btn = st.form_submit_button("❌ Seçili İsmi Tamamen Sil", use_container_width=True)
            if delete_btn and user_to_delete != "---":
                cursor.execute("DELETE FROM weekly_data WHERE username=?", (user_to_delete,))
                cursor.execute("DELETE FROM users WHERE username=?", (user_to_delete,))
                conn.commit()
                st.success(f"**{user_to_delete}** sistemden tamamen silindi.")
                st.rerun()

    st.markdown("---")
    st.subheader("🎯 Hak Sahibi Seçimi ve İşlem Girişi")
    if existing_users:
        with st.form("data_entry_form", clear_on_submit=True):
            col_u1, col_u2 = st.columns([2, 1])
            with col_u1:
                u_name = st.selectbox("İşlem Yapılacak Hak Sahibini Seçin:", existing_users)
            with col_u2:
                u_status = st.selectbox("Kullanıcı Genel Durumu:", ["Aktif", "İZİNLİ", "YENİ GELDİ"])
                
            col_i1, col_i2 = st.columns(2)
            with col_i1:
                selected_activity = st.selectbox("Yapılan İşlem Türünü Seçin:", ["Terfi", "Eğitim", "Maaş (Mr)", "Destek", "Rozet"])
            with col_i2:
                activity_value = st.number_input("Gireceğiniz Sayı / Miktar:", min_value=0, value=1, step=1)
                
            submit_btn = st.form_submit_button("💾 İşlemi Kaydet / Veriyi İşle", use_container_width=True)
            if submit_btn:
                cursor.execute("SELECT terfi, egitim, maas, destek, rozet FROM weekly_data WHERE username=? AND week_start=?", (u_name, selected_week_start))
                existing_record = cursor.fetchone()
                
                t_val = activity_value if selected_activity == "Terfi" else 0
                e_val = activity_value if selected_activity == "Eğitim" else 0
                m_val = activity_value if selected_activity == "Maaş (Mr)" else 0
                d_val = activity_value if selected_activity == "Destek" else 0
                r_val = activity_value if selected_activity == "Rozet" else 0
                
                if existing_record:
                    cursor.execute("""
                        UPDATE weekly_data SET terfi=terfi+?, egitim=egitim+?, maas=maas+?, destek=destek+?, rozet=rozet+?, status=?
                        WHERE username=? AND week_start=?
                    """, (t_val, e_val, m_val, d_val, r_val, u_status, u_name, selected_week_start))
                else:
                    cursor.execute("""
                        INSERT INTO weekly_data (username, week_start, terfi, egitim, maas, destek, rozet, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (u_name, selected_week_start, t_val, e_val, m_val, d_val, r_val, u_status))
                conn.commit()
                st.success(f"Başarılı! **{u_name}** kullanıcısına {activity_value} adet '{selected_activity}' işlendi.")
                st.rerun()

# --- SEKME 2: ROZET EKİBİ GİRİŞİ ---
with tab2:
    st.subheader("🏅 Rozet Ekibi Özel Takip Alanı")
    cursor.execute("SELECT username FROM users ORDER BY username ASC")
    rozet_users = [row[0] for row in cursor.fetchall()]
    
    col_r_left, col_r_right = st.columns([5, 3])
    
    with col_r_left:
        st.markdown("##### 👥 Rozet Ekibi Haftalık Durumu")
        cursor.execute("""
            SELECT u.username, COALESCE(w.rozet_transfer, 0), COALESCE(w.rozet_rozet, 0)
            FROM users u
            LEFT JOIN weekly_data w ON u.username = w.username AND w.week_start = ?
            WHERE (w.rozet_transfer > 0 OR w.rozet_rozet > 0)
            ORDER BY u.username ASC
        """, (selected_week_start,))
        rozet_rows = cursor.fetchall()
        
        if rozet_rows:
            rozet_table_data = []
            for r_row in rozet_rows:
                r_uname, r_trans, r_roz = r_row
                r_total = r_trans + r_roz
                rozet_table_data.append([r_uname, r_trans, r_roz, r_total])
                
            df_rozet = pd.DataFrame(rozet_table_data, columns=["Kullanıcı Adı (Nick)", "Transfer", "Rozet", "Toplam"])
            st.dataframe(df_rozet, use_container_width=True, hide_index=True, height=250)
        else:
            st.info("Bu hafta henüz Rozet Ekibi için girilmiş bir veri yok.")
            
    with col_r_right:
        st.markdown("##### 🛠️ Ekip Üyesi Yönetimi")
        with st.form("add_rozet_user_form", clear_on_submit=True):
            r_user_input = st.text_input("Yeni Rozet Ekip Üyesi Ekle:", placeholder="Nick yazın...").strip()
            if st.form_submit_button("➕ Listeye Ekle", use_container_width=True) and r_user_input:
                cursor.execute("INSERT OR IGNORE INTO users (username) VALUES (?)", (r_user_input,))
                conn.commit()
                st.success(f"**{r_user_input}** sisteme eklendi.")
                st.rerun()

    st.markdown("---")
    st.markdown("##### 🎯 Rozet ve Transfer Sayısı İşleme")
    if rozet_users:
        with st.form("rozet_entry_form", clear_on_submit=True):
            col_ro1, col_ro2, col_ro3 = st.columns([2, 2, 1])
            with col_ro1:
                r_select_name = st.selectbox("Rozet Görevlisi Seçin:", rozet_users, key="r_sel_name")
            with col_ro2:
                rozet_action_type = st.selectbox("İşlem Türü Seçin:", ["Transfer", "Rozet"], key="r_act_type")
            with col_ro3:
                rozet_count_input = st.number_input("Miktar:", min_value=0, value=1, step=1, key="r_cnt_in")
                
            if st.form_submit_button("💾 Rozet Verisini Kaydet", use_container_width=True):
                cursor.execute("SELECT rozet_transfer, rozet_rozet FROM weekly_data WHERE username=? AND week_start=?", (r_select_name, selected_week_start))
                r_exists = cursor.fetchone()
                
                trans_add = rozet_count_input if rozet_action_type == "Transfer" else 0
                rozet_add = rozet_count_input if rozet_action_type == "Rozet" else 0
                
                if r_exists:
                    cursor.execute("""
                        UPDATE weekly_data SET rozet_transfer=rozet_transfer+?, rozet_rozet=rozet_rozet+?
                        WHERE username=? AND week_start=?
                    """, (trans_add, rozet_add, r_select_name, selected_week_start))
                else:
                    cursor.execute("""
                        INSERT INTO weekly_data (username, week_start, rozet_transfer, rozet_rozet)
                        VALUES (?, ?, ?, ?)
                    """, (r_select_name, selected_week_start, trans_add, rozet_add))
                conn.commit()
                st.success(f"Başarıyla eklendi: **{r_select_name}** -> {rozet_action_type}: {rozet_count_input}")
                st.rerun()

# --- SEKME 3: METİNDEN TOPLU YÜKLE ---
with tab3:
    st.subheader("Discord / Metin Listesinden Toplu Veri Aktarımı")
    raw_text = st.text_area("Haftalık Rapor Metni:", height=250, placeholder="ArdaDkbs-   5 + 0 + 0 + 6 + 11 = 22")
    
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
            st.success(f"Toplam {count} kişinin verisi yüklendi.")
            st.rerun()

# --- SEKME 4: HAFTALIK TABLO VE ÇIKTILAR ---
with tab4:
    st.subheader(f"📅 {selected_label} Veri Raporları")
    
    # 1. BÖLÜM: GENEL HAK SAHİPLERİ TABLOSU VE ÇIKTILARI
    st.markdown("### 📋 Genel Hak Sahipleri Listesi")
    cursor.execute("""
        SELECT username, status, terfi, egitim, maas, destek, rozet 
        FROM weekly_data WHERE week_start = ? AND (terfi>0 OR egitim>0 OR maas>0 OR destek>0 OR rozet>0 OR status != 'Aktif')
        ORDER BY username ASC
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
        st.text_area("Genel Liste Metin Çıktısı (Kopyala):", text_output, height=180)
    else:
        st.info("Bu haftaya ait girilmiş Genel Hak Sahibi verisi bulunamadı.")

    # 2. BÖLÜM: ALT TOPLAMLARI HESAPLAYAN ROZET EKİBİ ÇIKTISI
    st.markdown("---")
    st.markdown("### 🏅 Rozet Ekibi Listesi ve Format Çıktısı")
    cursor.execute("""
        SELECT username, rozet_transfer, rozet_rozet 
        FROM weekly_data WHERE week_start = ? AND (rozet_transfer > 0 OR rozet_rozet > 0)
        ORDER BY username ASC
    """, (selected_week_start,))
    r_output_rows = cursor.fetchall()
    
    if r_output_rows:
        rozet_text_output = f"{selected_label} Rozet Verme Sayısı \n\n"
        rozet_text_output += f"       Nick :             Rozet:      Transfer:\n\n"
        
        # Toplamları biriktirmek için değişkenler kuruyoruz
        total_week_rozet = 0
        total_week_transfer = 0
        
        for r_out in r_output_rows:
            r_name, r_trans, r_roz = r_out
            rozet_text_output += f"{r_name}-: Rozet: {r_roz} Transfer: {r_trans}\n"
            total_week_rozet += r_roz
            total_week_transfer += r_trans
            
        # İstediğin o alt toplam satırını buraya ekliyoruz
        rozet_text_output += f"\nHaftalık Toplam -> Rozet: {total_week_rozet} | Transfer: {total_week_transfer}\n"
            
        st.text_area("Rozet Ekibi Özel Metin Çıktısı (Kopyala):", rozet_text_output, height=240)
    else:
        st.info("Bu haftaya ait girilmiş Rozet Ekibi çıktısı bulunamadı.")

    # 3. BÖLÜM: SIFIRLAMA VE YÖNETİM İŞLEMLERİ
    st.markdown("---")
    st.markdown("### 🛠️ Veri Temizleme ve Yönetim İşlemleri")
    col_action_left, col_action_right = st.columns(2)
    
    with col_action_left:
        st.markdown("#### 👤 Seçili Kullanıcıyı Sil")
        cursor.execute("SELECT username FROM weekly_data WHERE week_start=? ORDER BY username ASC", (selected_week_start,))
        all_week_users = [r[0] for r in cursor.fetchall()]
        del_user = st.selectbox("Bu haftaki kaydı silinecek kullanıcıyı seçin:", ["---"] + all_week_users, key="tab3_del_user")
        if del_user != "---":
            if st.button(f"❌ {del_user} Kişisinin Bu Haftaki Verisini Sil", type="primary", use_container_width=True):
                cursor.execute("DELETE FROM weekly_data WHERE username=? AND week_start=?", (del_user, selected_week_start))
                conn.commit()
                st.success(f"**{del_user}** verileri silindi.")
                st.rerun()
                
    with col_action_right:
        st.markdown("#### 🚨 Tüm Listeyi Sıfırla")
        confirm_reset = st.checkbox("Evet, bu haftanın tüm listesini sıfırlamak istediğime eminim.", key="confirm_mass_reset")
        if st.button("🗑️ Bu Haftanın Tüm Verilerini Sıfırla", type="primary", disabled=not confirm_reset, use_container_width=True):
            cursor.execute("DELETE FROM weekly_data WHERE week_start=?", (selected_week_start,))
            conn.commit()
            st.success("Seçili haftaya ait tüm veriler tamamen sıfırlandı!")
            st.rerun()
