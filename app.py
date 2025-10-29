
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Dashboard Kesenjangan Partisipasi Pendidikan per Kabupaten di Kalimantan Selatan",
    layout="wide"
)

st.markdown("""
<style>
html, body, [class*="css"] {
   font-size: 1.1rem !important; 
}
/* Anda juga bisa spesifik perbesar judul */
.stTitle {
    font-size: 2.8rem !important;
}
.stSubheader {
    font-size: 2.0rem !important;
}
</style>
""", unsafe_allow_html=True)

# ====================================================================
# BAGIAN 1 — LOAD & CLEANING DATA
# ====================================================================

# Memuat Data APM dan Membersihkannya
@st.cache_data
def load_data_apm(path):
    df = pd.read_csv(path, delimiter=';')
    
    # Mengganti Nama Kolom agar Konsisten
    df = df.rename(columns={
        'Wilayah': 'Wilayah',
        'Nilai_APM': 'Nilai_APM',
        'Nilai_Laki': 'Nilai_Laki',
        'Nilai_Perempuan': 'Nilai_Perempuan'
    })
    
    # Bersihkan data dan ubah nama jenjang agar seragam
    df['Jenjang'] = df['Jenjang'].replace({
        'SD/MI': 'SD',
        'SMP/MTs': 'SMP',
        'SMA/SMK/MA': 'SMA'
    })
    
    # Hapus baris ringkasan (misalnya 'KALIMANTAN SELATAN')
    df = df[~df['Wilayah'].str.contains('SELATAN', case=False, na=False)]
    
    # --- METRIK BARU #1 ---
    df['Kesenjangan_Gender'] = (df['Nilai_Perempuan'] - df['Nilai_Laki']).round(2)
    
    return df


# Fungsi untuk memuat dan menghitung rasio murid per guru
@st.cache_data
def load_data_rasio(path):
    df_r = pd.read_csv(path, delimiter=';')
    df_r.columns = df_r.columns.str.strip().str.lower()
    
    # Hapus baris kosong dan total provinsi
    df_r = df_r.dropna(subset=['kabupaten_kota'])
    df_r = df_r[~df_r['kabupaten_kota'].astype(str).str.contains('selatan', case=False, na=False)]
    
    # Hitung rasio murid per guru
    df_r['rasio_sd'] = df_r['jumlah_murid_sd_negeriswasta'] / df_r['jumlah_guru_sd_negeriswasta']
    df_r['rasio_smp'] = df_r['jumlah_murid_smp_negeriswasta'] / df_r['jumlah_guru_smp_negeriswasta']
    df_r['rasio_sma'] = df_r['jumlah_murid_sma_negeriswasta'] / df_r['jumlah_guru_sma_negeriswasta']
    
    # Ubah ke format long (1 baris = 1 wilayah + jenjang)
    df_long = pd.melt(
        df_r,
        id_vars=['kabupaten_kota'],
        value_vars=['rasio_sd', 'rasio_smp', 'rasio_sma'],
        var_name='Jenjang',
        value_name='Rasio_Murid_per_Guru'
    )
    
    # Bersihkan nama jenjang
    df_long['Jenjang'] = df_long['Jenjang'].replace({
        'rasio_sd': 'SD',
        'rasio_smp': 'SMP',
        'rasio_sma': 'SMA'
    })
    
    # Ganti nama kolom agar seragam
    df_long = df_long.rename(columns={'kabupaten_kota': 'Wilayah'})
    df_long['Wilayah'] = df_long['Wilayah'].str.upper().str.strip()
    df_long['Rasio_Murid_per_Guru'] = df_long['Rasio_Murid_per_Guru'].round(2)
    
    return df_long

# Fungsi untuk memuat dan membersihkan data RLS
@st.cache_data
def load_data_rls(url):
    """Memuat data Rata-rata Lama Sekolah (RLS) langsung dengan delimiter ';'"""
    try:
        # Langsung baca dengan delimiter semicolon (;)
        df = pd.read_csv(url, delimiter=';')
        # Cek apakah kolom penting ada
        # Asumsi nama kolom di CSV adalah 'Wilayah' dan 'Nilai_RLS'
        # Jika nama kolom di file Anda berbeda, ubah di sini
        required_cols = ['Wilayah', 'Nilai_RLS']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
             # Coba cek nama kolom alternatif (misal dari hasil cleaning sebelumnya)
             alt_wilayah = None
             alt_rls = None
             if 'kabupaten_kota' in df.columns: alt_wilayah = 'kabupaten_kota'
             elif 'Kabupaten/Kota + Provinsi' in df.columns: alt_wilayah = 'Kabupaten/Kota + Provinsi'

             # Cari kolom tahun (misal '2024') sebagai nilai RLS
             for col in df.columns:
                 if isinstance(col, (int, float)) or (isinstance(col, str) and col.isdigit() and len(col) == 4):
                     alt_rls = col
                     break
             if alt_rls is None and len(df.columns) > 1: alt_rls = df.columns[1] # Coba kolom kedua

             if alt_wilayah and alt_rls:
                 st.info(f"Mengganti nama kolom: '{alt_wilayah}' -> 'Wilayah', '{alt_rls}' -> 'Nilai_RLS'")
                 df = df.rename(columns={alt_wilayah: 'Wilayah', alt_rls: 'Nilai_RLS'})
                 # Cek ulang setelah rename
                 missing_cols = [col for col in required_cols if col not in df.columns]
                 if missing_cols: # Jika masih hilang, error
                      st.error(f"FATAL ERROR: Kolom '{missing_cols}' tidak ditemukan di '{url}' setelah rename.")
                      return pd.DataFrame()
             else: # Jika alternatif tidak ditemukan
                 st.error(f"FATAL ERROR: Kolom '{missing_cols}' tidak ditemukan di '{url}'.")
                 st.error(f"Kolom yang ditemukan: {df.columns.to_list()}")
                 return pd.DataFrame() # Kembalikan DF kosong

        # Pastikan tipe data benar
        df['Wilayah'] = df['Wilayah'].astype(str).str.strip()
        # Coba konversi RLS, ganti koma jika perlu
        if df['Nilai_RLS'].dtype == 'object':
             df['Nilai_RLS'] = df['Nilai_RLS'].astype(str).str.replace(',', '.', regex=False)
        df['Nilai_RLS'] = pd.to_numeric(df['Nilai_RLS'], errors='coerce')

        # Hapus baris ringkasan & NaN
        df = df[~df['Wilayah'].str.contains('SELATAN', case=False, na=False)]
        df = df.dropna(subset=['Wilayah', 'Nilai_RLS'])

        return df

    except FileNotFoundError:
        st.error(f"FATAL ERROR: File '{url}' tidak ditemukan. Pastikan file ini ada di folder proyek.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error saat memuat Data RLS ('{url}'): {e}")
        st.exception(e) # Tampilkan traceback lengkap
        return pd.DataFrame()
    
    # --- (Letakkan ini di BAGIAN 1, setelah fungsi 'load_data_rls') ---

# Fungsi untuk memuat data jumlah sekolah
@st.cache_data
def load_data_sekolah(path):
    """Memuat data jumlah sekolah dari file Rasio Guru"""
    df_s = pd.read_csv(path, delimiter=';')
    df_s.columns = df_s.columns.str.strip().str.lower()
    
    # Hapus baris kosong dan total provinsi
    df_s = df_s.dropna(subset=['kabupaten_kota'])
    df_s = df_s[~df_s['kabupaten_kota'].astype(str).str.contains('selatan', case=False, na=False)]
    
    # Pilih kolom yang relevan
    cols_to_keep = [
        'kabupaten_kota', 
        'jumlah_sekolah_sd_negeriswasta', 
        'jumlah_sekolah_smp_negeriswasta', 
        'jumlah_sekolah_sma_negeriswasta'
    ]
    df_s = df_s[cols_to_keep]
    
    # Ganti nama kolom agar lebih mudah dibaca
    df_s = df_s.rename(columns={
        'kabupaten_kota': 'Wilayah',
        'jumlah_sekolah_sd_negeriswasta': 'Jumlah SD',
        'jumlah_sekolah_smp_negeriswasta': 'Jumlah SMP',
        'jumlah_sekolah_sma_negeriswasta': 'Jumlah SMA'
    })
    
    # STANDARISASI: Ubah Wilayah ke UPPERCASE agar filter berfungsi
    df_s['Wilayah'] = df_s['Wilayah'].str.upper().str.strip()
    
    # Ubah ke format long (ideal untuk grouped bar chart)
    df_long_sekolah = pd.melt(
        df_s,
        id_vars=['Wilayah'],
        value_vars=['Jumlah SD', 'Jumlah SMP', 'Jumlah SMA'],
        var_name='Jenjang',
        value_name='Jumlah_Sekolah'
    )
    
    # Konversi tipe data untuk memastikan
    df_long_sekolah['Jumlah_Sekolah'] = pd.to_numeric(df_long_sekolah['Jumlah_Sekolah'], errors='coerce')

    df_long_sekolah = df_long_sekolah.dropna(subset=['Jumlah_Sekolah'])

    df_long_sekolah['Jumlah_Sekolah'] = df_long_sekolah['Jumlah_Sekolah'].fillna(0).astype(int)
    
    return df_long_sekolah

# --- (Akhir dari blok 1) ---

# --- Load kedua dataset ---
DATA_APM = 'Data_APM_Bersih.csv'
DATA_RASIO = 'Data_Rasio_Murid-per-Guru_Bersih.csv'
DATA_RLS = 'Data_RLS_Bersih.csv'

df_apm = load_data_apm(DATA_APM)
df_rasio = load_data_rasio(DATA_RASIO)
df_rls = load_data_rls(DATA_RLS)
df_sekolah = load_data_sekolah(DATA_RASIO)

# --- Gabungkan Data ---
DATA_LOADED_SUCCESS = False
if not df_apm.empty and not df_rasio.empty and not df_rls.empty and not df_sekolah.empty:
    # Gabungkan APM + Rasio
    df_master = pd.merge(df_apm, df_rasio, on=['Wilayah', 'Jenjang'], how='left')
    # Gabungkan dengan RLS (hanya berdasarkan Wilayah)
    df_master = pd.merge(df_master, df_rls, on='Wilayah', how='left')
    # Gabungkan dengan Sekolah (hanya berdasarkan Wilayah dan Jenjang)
    df_master = pd.merge(df_master, df_sekolah, on=['Wilayah', 'Jenjang'], how='left')
    DATA_LOADED_SUCCESS = True

    # Validasi setelah merge
    required_master_cols = ['Wilayah', 'Jenjang', 'Nilai_APM', 'Rasio Murid-per-Guru', 'Nilai_RLS']
    missing_master_cols = [col for col in required_master_cols if col not in df_master.columns]
  
# ====================================================================
# 🔹 BAGIAN 2 — SIDEBAR (FILTER)
# ====================================================================

st.sidebar.header("🎛️ Filter Dashboard")

# Filter 1: Jenjang
pilih_jenjang = st.sidebar.selectbox(
    "Pilih Jenjang:",
    ('SD', 'SMP', 'SMA'),
    index=1
)

# Filter 2: Wilayah (opsional)
list_wilayah = sorted(df_apm['Wilayah'].unique())
pilih_wilayah = st.sidebar.multiselect(
    "Pilih Wilayah (opsional):",
    list_wilayah,
    placeholder="Tampilkan Semua Wilayah"
)

# Tambahkan baris-baris ini di akhir sidebar
st.sidebar.markdown("---")
st.sidebar.header("Sumber Data")
st.sidebar.info(
    """
    Semua data yang digunakan bersumber dari Badan Pusat Statistik (BPS) Kalimantan Selatan.

    1. [Link Data APM Jenjang SD/Sederajat 2024](https://kalsel.bps.go.id/id/statistics-table/2/NzkjMg==/angka-partisipasi-murni--apm--sd-mi-sederajat-menurut-jenis-kelamin-dan-kabupaten-kota-di-provinsi-kalimantan-selatan--persen-.html)
    2. [Link Data APM Jenjang SMP/Sederajat 2024](https://kalsel.bps.go.id/id/statistics-table/2/ODEjMg==/angka-partisipasi-murni--apm--smp-mts-sederajat-menurut-jenis-kelamin-dan-kabupaten-kota-di-provinsi-kalimantan-selatan--persen-.html)
    3. [Link Data APM Jenjang SMA/Sederajat 2024](https://kalsel.bps.go.id/id/statistics-table/2/ODIjMg==/angka-partisipasi-murni--apm--sma-smk-ma-sederajat-menurut-jenis-kelamin-dan-kabupaten-kota-di-provinsi-kalimantan-selatan--persen-.html)
    4. [Link Data Jumlah Guru dan Murid SD 2024/2025](https://kalsel.bps.go.id/id/statistics-table/3/VWtKTmFFbDZaSFJWWVhOYU16WmhaRzlCYlM5Wlp6MDkjMyM2MzAw/jumlah-sekolah--guru--dan-murid-sekolah-dasar--sd--di-bawah-kementerian-pendidikan--kebudayaan--riset--dan-teknologi-menurut-kabupaten-kota-di-provinsi-kalimantan-selatan.html?year=2024)
    5. [Link Data Jumlah Guru dan Murid SMP 2024/2025](https://kalsel.bps.go.id/id/statistics-table/3/ZHpkb1ZtcDNZV2RHTlUweVdFZ3JhVkl3Ym1ScVp6MDkjMyM2MzAw/jumlah-sekolah--guru--dan-murid-sekolah-menengah-pertama--smp--di-bawah-kementerian-pendidikan--kebudayaan--riset--dan-teknologi-menurut-kabupaten-kota-di-provinsi-kalimantan-selatan.html?year=2024)
    6. [Link Data Jumlah Guru dan Murid SMA 2024/2025](https://kalsel.bps.go.id/id/statistics-table/3/YTFsRmNubEhOWE5ZTUZsdWVHOHhMMFpPWm5VMFp6MDkjMyM2MzAw/jumlah-sekolah--guru--dan-murid-sekolah-menengah-atas--sma--di-bawah-kementerian-pendidikan--kebudayaan--riset--dan-teknologi-menurut-kabupaten-kota-di-provinsi-kalimantan-selatan.html?year=2024)
    7. [Link Data Jumlah SD 2024/2025](https://kalsel.bps.go.id/id/statistics-table/3/VWtKTmFFbDZaSFJWWVhOYU16WmhaRzlCYlM5Wlp6MDkjMyM2MzAw/jumlah-sekolah--guru--dan-murid-sekolah-dasar--sd--di-bawah-kementerian-pendidikan--kebudayaan--riset--dan-teknologi-menurut-kabupaten-kota-di-provinsi-kalimantan-selatan.html?year=2024)
    8. [Link Data Jumlah SMP 2024/2025](https://kalsel.bps.go.id/id/statistics-table/3/ZHpkb1ZtcDNZV2RHTlUweVdFZ3JhVkl3Ym1ScVp6MDkjMyM2MzAw/jumlah-sekolah--guru--dan-murid-sekolah-menengah-pertama--smp--di-bawah-kementerian-pendidikan--kebudayaan--riset--dan-teknologi-menurut-kabupaten-kota-di-provinsi-kalimantan-selatan.html?year=2024)
    9. [Link Data Jumlah SMA 2024/2025](https://kalsel.bps.go.id/id/statistics-table/3/YTFsRmNubEhOWE5ZTUZsdWVHOHhMMFpPWm5VMFp6MDkjMyM2MzAw/jumlah-sekolah--guru--dan-murid-sekolah-menengah-atas--sma--di-bawah-kementerian-pendidikan--kebudayaan--riset--dan-teknologi-menurut-kabupaten-kota-di-provinsi-kalimantan-selatan.html?year=2024)
    10. [Link Data Rata-rata Lama Sekolah (RLS) 2024](https://kalsel.bps.go.id/id/statistics-table/2/MzYzIzI=/rata-rata-lama-sekolah--rls--menurut-jenis-kelamin--tahun-.html)
    """
)

# ====================================================================
# 🔹 BAGIAN 3 — DATA FILTERING
# ====================================================================

df_filtered = df_apm[df_apm['Jenjang'] == pilih_jenjang]
df_rasio_filtered = df_rasio[df_rasio['Jenjang'] == pilih_jenjang]
df_rls_unique = df_master[['Wilayah', 'Nilai_RLS']].drop_duplicates().dropna()
jenjang_sekolah_map = {
    'SD': 'Jumlah SD',
    'SMP': 'Jumlah SMP',
    'SMA': 'Jumlah SMA'
}
jenjang_terpilih_sekolah = jenjang_sekolah_map.get(pilih_jenjang)

if jenjang_terpilih_sekolah:
    df_sekolah_filtered = df_sekolah[df_sekolah['Jenjang'] == jenjang_terpilih_sekolah]
else:
    # Jika karena alasan tertentu jenjang tidak ditemukan, ambil SD sebagai default
    df_sekolah_filtered = df_sekolah[df_sekolah['Jenjang'] == 'Jumlah SD']

if pilih_wilayah:
    df_filtered = df_filtered[df_filtered['Wilayah'].isin(pilih_wilayah)]
    df_rasio_filtered = df_rasio_filtered[df_rasio_filtered['Wilayah'].isin(pilih_wilayah)]
    df_rls_unique = df_rls_unique[df_rls_unique['Wilayah'].isin(pilih_wilayah)]
    df_sekolah_filtered = df_sekolah_filtered[df_sekolah_filtered['Wilayah'].isin(pilih_wilayah)]

df_filtered = df_filtered.sort_values(by = 'Nilai_APM', ascending=False)
df_rls_unique = df_rls_unique.sort_values('Nilai_RLS', ascending=False) 
   
# ====================================================================
# 🔹 BAGIAN 4 — KONTEN UTAMA
# ====================================================================

st.title("Analisis Kesenjangan Partisipasi Pendidikan per Kabupaten di Kalimantan Selatan")
st.markdown("Dashboard ini menganalisis partisipasi pendidikan murni, faktor sumber daya guru, dan hasil historis rata-rata lama sekolah per Kabupaten di Kalimantan Selatan.")
# --- Konteks Studi Kasus ---
with st.expander("Studi Kasus"):
    st.markdown("""
    **Konteks:**
    Pemerataan akses pendidikan adalah fondasi pembangunan SDM di Kalimantan Selatan.
    Namun, data menunjukkan adanya perbedaan signifikan antar kabupaten/kota.
    Visualisasi ini bertujuan untuk mengubah data BPS menjadi **insight yang actionable**.

    **Pertanyaan Analitis:**
    1. Kabupaten/kota mana yang memiliki **partisipasi pendidikan tertinggi dan terendah**?
    2. Seberapa besar **kesenjangan gender** dalam partisipasi pendidikan?
    3. Bagaimana **rasio murid per guru** memengaruhi kesenjangan antar daerah?
    4. Bagaimana **hasil pendidikan historis (RLS)** di tiap wilayah dan apakah konsisten dengan APM saat ini? 
    5. Apa langkah strategis yang dapat diambil untuk mengurangi kesenjangan ini?            
    """)
st.markdown("---")
# ====================================================================
# 🔹 VISUALISASI #1 — Peringkat APM per Kabupaten/Kota
# ====================================================================

st.subheader(f"1. Peringkat Angka Partisipasi Murni Jenjang {pilih_jenjang}")

fig1 = px.bar(
    df_filtered,
    x='Nilai_APM',
    y='Wilayah',
    orientation='h',
    title=f"Peringkat Angka Partisipasi Murni ({pilih_jenjang}) per Kabupaten/Kota",
    labels={'Nilai_APM': 'APM (%)', 'Wilayah': 'Kabupaten/Kota'},
    text='Nilai_APM',
    color='Nilai_APM'
)

avg_apm = df_filtered['Nilai_APM'].mean()

fig1.add_vline(
    x=avg_apm,
    line_dash="dash",
    line_color="gray",
    annotation_text=f"Rata-rata Provinsi ({avg_apm:.1f}%)",
    annotation_position="top",
    annotation_font_color="white"
)

# --- PERUBAHAN DI SINI ---
# Tambahkan baris ini untuk memindahkan teks ke LUAR batang
# dan memformatnya menjadi 2 angka desimal (misal: 83.80)
fig1.update_traces(texttemplate='%{text:.1f}%',
    textfont=dict(color="white", size=11),
    textposition='outside',
    cliponaxis=False
)
# --- AKHIR PERUBAHAN ---

fig1.update_layout(yaxis={'categoryorder': 'total ascending'})
st.plotly_chart(fig1, use_container_width=True)

st.info(f"""
Kabupaten dengan partisipasi tertinggi: **{df_filtered.iloc[0]['Wilayah']} ({df_filtered.iloc[0]['Nilai_APM']:.1f}%)**  
Terendah: **{df_filtered.iloc[-1]['Wilayah']} ({df_filtered.iloc[-1]['Nilai_APM']:.1f}%)**  
Rata-rata Provinsi: **{avg_apm:.1f}%**
""")
st.markdown("---")

# ====================================================================
# 🔹 VISUALISASI #2 — Perbandingan APM antar Jenjang (Small Multiples)
# ====================================================================

# --- PERUBAHAN DIMULAI DI SINI ---

st.subheader("2. Perbandingan APM Antar Jenjang (Analisis Penurunan)")
st.markdown("""
Grafik ini menunjukkan **penurunan (drop-off)** partisipasi per wilayah. 
Setiap kotak mewakili satu kabupaten/kota, menunjukkan dengan jelas tren dari SD ke SMP, dan ke SMA.
""")

df_vis2 = df_apm.copy()
if pilih_wilayah:
    df_vis2 = df_vis2[df_vis2['Wilayah'].isin(pilih_wilayah)]

# Menggunakan px.line dengan FACET_COL untuk membuat "Small Multiples"
fig2 = px.line(
    df_vis2,
    x='Jenjang',
    y='Nilai_APM',
    facet_col='Wilayah',        # Buat 1 chart per Wilayah
    facet_col_wrap=6,         # Tampilkan 6 chart per baris
    facet_col_spacing=0.03,  # <── jarak antar kolom (opsional)
    title="Perbandingan APM SD, SMP, dan SMA per Wilayah",
    labels={'Nilai_APM': 'APM (%)', 'Jenjang': 'Jenjang Pendidikan'},
    category_orders={"Jenjang": ["SD", "SMP", "SMA"]},  # Memastikan urutan
    markers=True,             # Tambahkan titik
    text='Nilai_APM'            # Tambahkan label nilai
)

# Hitung batas atas Y agar label 99+ tidak terpotong
max_apm = df_vis2['Nilai_APM'].max()
fig2.update_yaxes(matches=None)  # biarkan tiap subplot punya sumbu Y independen
fig2.for_each_yaxis(lambda axis: axis.update(range=[0, max_apm * 1.1]))  # tambahkan 10% ruang di atas

# Mengatur format teks agar tidak tumpang tindih
fig2.update_traces(texttemplate='%{text:.1f}', textposition='top center', line_width=3, marker_color='#38bdf8', marker=dict(size=6, color="#bae6fd", line=dict(width=1, color="white")))

# Mengatur judul subplot (Wilayah) agar lebih rapi
# (Menghapus "Wilayah=" dari setiap judul)
fig2.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))

# Mengatur tinggi chart agar tidak terlalu sempit
fig2.update_layout(height=650) 

st.plotly_chart(fig2, use_container_width=True)

# Hitung rata-rata APM per jenjang
rata_sd = df_apm[df_apm['Jenjang'] == 'SD']['Nilai_APM'].mean().round(2)
rata_smp = df_apm[df_apm['Jenjang'] == 'SMP']['Nilai_APM'].mean().round(2)
rata_sma = df_apm[df_apm['Jenjang'] == 'SMA']['Nilai_APM'].mean().round(2)

# Hitung rata-rata penurunan antar jenjang
penurunan_sd_smp = (rata_sd - rata_smp).round(2)
penurunan_smp_sma = (rata_smp - rata_sma).round(2)

# Tampilkan insight dalam bentuk teks deskriptif
# GANTI st.info yang ada di bawah Visualisasi #2 dengan ini:

st.info(f"""
**📊 Insight Analitis: Tren Penurunan APM Antar Jenjang**

- Rata-rata APM jenjang **SD** di Kalimantan Selatan: **{rata_sd}%**
- Rata-rata APM jenjang **SMP**: **{rata_smp}%**
- Rata-rata APM jenjang **SMA**: **{rata_sma}%**

Terjadi penurunan partisipasi pendidikan sebesar:
- 🔻 **{penurunan_sd_smp}%** dari SD ke SMP  
- 🔻 **{penurunan_smp_sma}%** dari SMP ke SMA

💡 *Interpretasi:*  
Semakin tinggi jenjang pendidikan, partisipasi murid cenderung menurun.  
Penurunan paling signifikan terjadi pada transisi ke jenjang **SMA**,  
yang dapat menunjukkan tantangan ekonomi, akses sekolah menengah atas,  
atau motivasi belajar setelah jenjang wajib belajar selesai.
""")

st.markdown("---")

# --- PERUBAHAN BERAKHIR DI SINI ---

# ====================================================================
# 🔹 VISUALISASI #3 — Kesenjangan Gender
# ====================================================================

st.subheader(f"3. Analisis Kesenjangan Gender (Jenjang {pilih_jenjang})")

fig3 = px.scatter(
    df_filtered,
    x='Nilai_Laki',
    y='Nilai_Perempuan',
    color='Kesenjangan_Gender',
    size='Nilai_APM',
    hover_name='Wilayah',
    title=f"Perbandingan APM Laki-Laki vs Perempuan ({pilih_jenjang})",
    labels={
        'Nilai_Laki': 'APM Laki-Laki (%)',
        'Nilai_Perempuan': 'APM Perempuan (%)',
        'Kesenjangan_Gender': 'Kesenjangan (Perempuan - Laki-laki)'
    },
    color_continuous_scale=[
    (0.0, "#3b82f6"),   # soft blue
    (0.5, "#e2e8f0"),   # light gray
    (1.0, "#f472b6")    # soft pink
]
)

fig3.add_shape(
    type='line',
    x0=df_filtered['Nilai_Laki'].min()-5, y0=df_filtered['Nilai_Laki'].min()-5,
    x1=df_filtered['Nilai_Perempuan'].max()+5, y1=df_filtered['Nilai_Perempuan'].max()+5,
    line=dict(color='gray', dash='dash')
)

st.plotly_chart(fig3, use_container_width=True)

# Tambahkan kode ini di bawah Visualisasi #3
if not df_filtered.empty:
    avg_gap = df_filtered['Kesenjangan_Gender'].mean().round(2)
    max_gap_row = df_filtered.loc[df_filtered['Kesenjangan_Gender'].idxmax()]
    min_gap_row = df_filtered.loc[df_filtered['Kesenjangan_Gender'].idxmin()]

    st.info(f"""
    **Analisis Kesenjangan Gender (Jenjang {pilih_jenjang})**
    - 📈 **Rata-rata Kesenjangan:** {avg_gap} (Positif = Perempuan Unggul)
    - 🔺 **Partisipasi Perempuan Tertinggi:** {max_gap_row['Wilayah']} (Kesenjangan: +{max_gap_row['Kesenjangan_Gender']})
    - 🔻 **Partisipasi Laki-laki Tertinggi:** {min_gap_row['Wilayah']} (Kesenjangan: {min_gap_row['Kesenjangan_Gender']})

    *Kesenjangan gender bervariasi; tidak ada pola konsisten di mana satu gender selalu tertinggal di semua wilayah.*
    """)
else:
    st.warning(f"Tidak ada data Kesenjangan Gender untuk filter yang dipilih.")

st.markdown("---")

# ====================================================================
# 🔹 VISUALISASI #4 — Rasio Murid per Guru
# ====================================================================

st.subheader("4. Rasio Murid per Guru per Kabupaten/Kota")
st.markdown("""
Rasio ini menunjukkan **jumlah murid rata-rata yang ditangani oleh satu guru** di setiap kabupaten/kota.
Nilai yang tinggi mengindikasikan potensi kekurangan guru dan dapat berdampak pada kualitas pembelajaran.
""")
if not df_rasio_filtered.empty:
    # --- Data ---
    df_sorted = df_rasio_filtered.sort_values(by='Rasio_Murid_per_Guru', ascending=True)
    x_vals = df_sorted['Rasio_Murid_per_Guru']
    y_vals = df_sorted['Wilayah']

    # --- Skala warna serupa dengan visualisasi nomor 1 ---
    # (Gradasi biru → hijau → kuning seperti pada color_continuous_scale di visualisasi #1)
    color_scale = [
        (0.0, "#335eec"),  # biru (rendah)
        (0.5, "#2bbdee"),  # hijau (sedang)
        (1.0, "#ffffff")   # kuning (tinggi)
    ]

    # --- Buat figure manual dengan skema warna serupa ---
    fig4 = go.Figure()

    fig4.add_trace(go.Bar(
        x=x_vals,
        y=y_vals,
        orientation='h',
        text=x_vals,
        textposition='outside',
        texttemplate='%{text:.1f}',
        cliponaxis=False,
        marker=dict(
        color=x_vals,
        colorscale=color_scale,
        cmin=x_vals.min(),
        cmax=x_vals.max(),
        colorbar=dict(
            title=dict(
                text="Rasio Murid/Guru",         # teks judul colorbar
                font=dict(color="white")         # warna font judul
            ),
            tickfont=dict(color="white"),        # warna angka/tick label
            bgcolor="rgba(0,0,0,0)",             # latar transparan
            outlinecolor="rgba(255,255,255,0.2)",# garis tipis pinggir
            outlinewidth=1
        )
    )
    ))

    # --- Tambahkan garis rata-rata ---
    rata2_rasio = df_rasio_filtered['Rasio_Murid_per_Guru'].mean().round(2)
    fig4.add_vline(
        x=rata2_rasio,
        line_dash="dash",
        line_color="gray",
        annotation_text=f"Rata-rata: {rata2_rasio}",
        annotation_position="top",
        annotation_font_color="white"
    )

    # --- Layout ---
    x_max = x_vals.max()
    fig4.update_layout(
        title=f"Rasio Murid per Guru — Jenjang {pilih_jenjang}",
        xaxis=dict(
            title='Jumlah Murid per 1 Guru',
            range=[0, x_max * 1.15],
            color="white",
            gridcolor='rgba(255,255,255,0.1)'
        ),
        yaxis=dict(
            title='Kabupaten/Kota',
            categoryorder='total ascending',
            color="white"
        ),
        margin=dict(l=120, r=160, t=70, b=40),
        showlegend=False,
        height=520,
        bargap=0.3,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color="white")
    )

    fig4.update_traces(
        texttemplate='%{text:.1f}',
        textfont=dict(size=12, color="white"),
        textposition='outside',
        cliponaxis=False
    )

    st.plotly_chart(fig4, use_container_width=True)

    # --- Statistik tambahan ---
    max_row = df_rasio_filtered.loc[df_rasio_filtered['Rasio_Murid_per_Guru'].idxmax()]
    min_row = df_rasio_filtered.loc[df_rasio_filtered['Rasio_Murid_per_Guru'].idxmin()]

    st.info(f"""
    **Rata-rata Rasio Murid per Guru (Jenjang {pilih_jenjang}):** {rata2_rasio}
    - 🔺 **Tertinggi:** {max_row['Wilayah']} ({max_row['Rasio_Murid_per_Guru']:.1f} murid/guru)
    - 🔻 **Terendah:** {min_row['Wilayah']} ({min_row['Rasio_Murid_per_Guru']:.1f} murid/guru)
    """) 

    # Tampilkan pesan jika tidak ada data

    st.markdown("---")

# --- (Letakkan ini di BAGIAN 4, misalnya setelah Viz #4 dan sebelum Viz #5) ---

# ====================================================================
# 🔹 VISUALISASI #5 — Perbandingan Jumlah Sekolah (Infrastruktur)
# ====================================================================

st.subheader("5. Perbandingan Jumlah Infrastruktur Sekolah")
st.markdown(f"""
Visualisasi ini menunjukkan ketersediaan infrastruktur fisik (jumlah sekolah) 
untuk jenjang **{pilih_jenjang}** di tiap kabupaten/kota.
""")

if df_sekolah_filtered.empty:
    st.warning(f"Tidak ada data jumlah sekolah untuk jenjang {pilih_jenjang} (atau filter wilayah) yang dipilih.")
else:
    # Jika tidak ada wilayah dipilih, tampilkan semua
    df_sekolah_sorted = df_sekolah_filtered.sort_values(by='Jumlah_Sekolah', ascending=False)
    # Buat grouped bar chart
    fig5_sekolah = px.bar(
        df_sekolah_sorted,
        x='Jumlah_Sekolah',
        y='Wilayah',
        orientation='h',
        barmode='group',           # <-- Ini membuat bar berdampingan
        title=f'Peringkat Jumlah Sekolah (Jenjang {pilih_jenjang}) per Wilayah',
        labels={
            'Jumlah_Sekolah': f'Jumlah Sekolah ({pilih_jenjang})',
            'Wilayah': 'Kabupaten/Kota',
        },
        text='Jumlah_Sekolah',
        color='Jumlah_Sekolah', # Requirement: Gradasi warna berdasarkan nilai
    )

    # Hitung rata-rata
    avg_sekolah = df_sekolah_sorted['Jumlah_Sekolah'].mean()

    # Tambahkan garis rata-rata
    fig5_sekolah.add_vline(
        x=avg_sekolah,
        line_dash="dash",
        line_color="gray",
        annotation_text=f"Rata-rata ({avg_sekolah:.0f})", # Format .0f (tanpa desimal)
        annotation_position="top",
        annotation_font_color="white"
    )
    
    fig5_sekolah.update_traces(
        texttemplate='%{text:.0f}', # Format .0f (angka bulat)
        textfont=dict(color="white", size=12),
        textposition='outside',
        cliponaxis=False
    )

    fig5_sekolah.update_layout(
        yaxis={'categoryorder': 'total ascending'} 
    )
    
    st.plotly_chart(fig5_sekolah, use_container_width=True)

    # --- Insight Otomatis ---
    if not df_sekolah_sorted.empty:
        # Cari nilai Max dan Min
        max_val = df_sekolah_sorted['Jumlah_Sekolah'].max()
        min_val = df_sekolah_sorted['Jumlah_Sekolah'].min()
        
        # Dapatkan SEMUA wilayah yang cocok dengan nilai Max
        max_rows = df_sekolah_sorted[df_sekolah_sorted['Jumlah_Sekolah'] == max_val]
        max_wilayah_list = max_rows['Wilayah'].tolist()
        max_wilayah_str = ', '.join(max_wilayah_list)
        
        # Dapatkan SEMUA wilayah yang cocok dengan nilai Min
        min_rows = df_sekolah_sorted[df_sekolah_sorted['Jumlah_Sekolah'] == min_val]
        min_wilayah_list = min_rows['Wilayah'].tolist()
        min_wilayah_str = ', '.join(min_wilayah_list)

        st.info(f"""
        **Analisis Ketersediaan Infrastruktur (Jenjang {pilih_jenjang})**
        - 📈 **Rata-rata:** {avg_sekolah:.0f} sekolah
        - 🔺 **Tertinggi:** {max_wilayah_str} ({max_val} sekolah)
        - 🔻 **Terendah:** {min_wilayah_str} ({min_val} sekolah)

        *Insight: Analisis ini sekarang menunjukkan peringkat ketersediaan sekolah untuk jenjang yang Anda pilih.*
        """)
    # --- AKHIR PERBAIKAN ---

st.markdown("---")

# --- (Akhir dari blok 3) ---

# ====================================================================
# 🔹 VISUALISASI #6 — Peringkat Rata-rata Lama Sekolah (RLS)
# ====================================================================

st.subheader("6. Peringkat Rata-rata Lama Sekolah (RLS) per Kabupaten/Kota")
st.markdown("RLS mengukur capaian pendidikan historis penduduk dewasa (25 tahun ke atas).")
if df_rls_unique.empty:
    st.warning("Data RLS tidak tersedia atau kosong.")
else:
    fig5 = px.bar(
        df_rls_unique,
        x='Nilai_RLS', 
        y='Wilayah', 
        orientation='h',
        title="Peringkat Rata-rata Lama Sekolah (RLS)",
        labels={'Nilai_RLS': 'RLS (Tahun)', 'Wilayah': 'Kabupaten/Kota'},
        text='Nilai_RLS',
        color='Nilai_RLS',
    )

    avg_rls = df_rls_unique['Nilai_RLS'].mean().round(2)
    fig5.add_vline(
        x=avg_rls,
        line_dash="dash",
        line_color="gray",
        annotation_text=f"Rata-rata: {avg_rls}",
        annotation_position="top",
        annotation_font_color="white"
    )

    fig5.update_traces(texttemplate='%{text:.2f}', textposition='outside')
    fig5.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig5, use_container_width=True)

    # ... (kode st.plotly_chart(fig5) sudah ada)
    
    # Tambahkan perhitungan ini di dalam blok 'else' Viz #5
    avg_rls = df_rls_unique['Nilai_RLS'].mean().round(2)
    max_rls_row = df_rls_unique.loc[df_rls_unique['Nilai_RLS'].idxmax()]
    min_rls_row = df_rls_unique.loc[df_rls_unique['Nilai_RLS'].idxmin()]

    st.info(f"""
    **Analisis Rata-rata Lama Sekolah (RLS) per Wilayah**
    - 📈 **Rata-rata RLS Se-Kalsel:** {avg_rls} tahun
    - 🔺 **RLS Tertinggi:** {max_rls_row['Wilayah']} ({max_rls_row['Nilai_RLS']:.2f} tahun)
    - 🔻 **RLS Terendah:** {min_rls_row['Wilayah']} ({min_rls_row['Nilai_RLS']:.2f} tahun)

    *RLS menunjukkan capaian pendidikan historis penduduk 25+ tahun. Angka ~8-9 tahun berarti rata-rata lulusan SMP, ~11-12 tahun lulusan SMA.*
    """)

st.markdown("---")

# ====================================================================
# 🔹 VISUALISASI #7 — RLS vs. APM SMA
# ====================================================================

st.subheader("7. Analisis Konsistensi Kesenjangan: RLS vs. APM SMA")
st.markdown("Membandingkan hasil pendidikan historis (RLS) dengan partisipasi SMA saat ini (APM SMA).")
df_vis6 = df_master[df_master['Jenjang'] == 'SMA'][['Wilayah', 'Nilai_RLS', 'Nilai_APM']].drop_duplicates().dropna()
if df_vis6.empty: st.warning("Data lengkap ('RLS' dan 'APM SMA') tidak tersedia.")
else:
    fig6 = px.scatter(
        df_vis6, x='Nilai_RLS', y='Nilai_APM', hover_name='Wilayah',
        title="Konsistensi Kesenjangan: RLS vs APM SMA",
        labels={'Nilai_RLS': 'RLS (Hasil Historis)', 'Nilai_APM': 'APM SMA (Partisipasi Saat Ini)'},
        size='Nilai_APM', color='Wilayah',
        color_continuous_scale='Viridis'
    )
    avg_rls_vis6 = df_vis6['Nilai_RLS'].mean(); avg_apm_sma_vis6 = df_vis6['Nilai_APM'].mean()
    fig6.add_vline(x=avg_rls_vis6, line=dict(color='grey', dash='dash'), annotation_text="Rata-rata RLS")
    fig6.add_hline(y=avg_apm_sma_vis6, line=dict(color='grey', dash='dash'), annotation_text="Rata-rata APM SMA")
    # ... (kode fig6)

    st.plotly_chart(fig6, use_container_width=True)
    
    # --- UBAH BLOK INI UNTUK MEMPERJELAS ANOMALI ---
    st.subheader("Cara Membaca Grafik (Analisis Kuadran)")
    st.markdown("""
    Garis rata-rata membagi grafik menjadi empat kuadran yang menunjukkan konsistensi (atau anomali) antara capaian historis (RLS) dan partisipasi saat ini (APM SMA):

    -   **Kuadran Kanan Atas (Ideal):** RLS tinggi & APM SMA tinggi.
        Wilayah ini memiliki capaian historis yang baik dan partisipasi saat ini yang juga tinggi.

    -   **Kuadran Kiri Bawah (Masalah Persisten):** RLS rendah & APM SMA rendah.
        Wilayah ini memiliki tantangan ganda: capaian historis rendah dan partisipasi saat ini juga masih rendah.

    -   **Kuadran Kiri Atas (Anomali Positif):** RLS rendah & APM SMA tinggi.
        *Wilayah ini berhasil mendorong partisipasi sekolah (APM) saat ini meskipun capaian pendidikan historis (RLS) penduduknya rendah.*
        
    -   **Kuadran Kanan Bawah (Anomali Negatif / Peringatan):** RLS tinggi & APM SMA rendah.
        *Wilayah ini memiliki capaian pendidikan historis yang baik, namun partisipasi SMA saat ini justru rendah. Ini adalah anomali yang perlu investigasi.*
    """)
    # --- AKHIR PERUBAHAN ---

    # ... (kode st.plotly_chart(fig6) sudah ada)
    
    # Tambahkan ini di dalam blok 'else' Viz #6
    st.info(f"""
    **Analisis Konsistensi (RLS vs. APM SMA)**
    - 📈 **Rata-rata RLS (Garis Vertikal):** {avg_rls_vis6:.2f} tahun
    - 📈 **Rata-rata APM SMA (Garis Horizontal):** {avg_apm_sma_vis6:.2f}%

    *Insight utama adalah anomali: Wilayah di kuadran **kanan bawah** (RLS tinggi, APM rendah) seperti KOTA BANJARMASIN menunjukkan ketidakselarasan antara capaian historis yang baik dan partisipasi SMA saat ini yang rendah.*
    """)

st.markdown("---")

# ====================================================================
# 🔹 PENUTUP — INSIGHT & REKOMENDASI
# ====================================================================

st.subheader("Insight & Rekomendasi")

st.markdown("""
1. **Ketimpangan APM antar wilayah** cukup signifikan, terutama antara wilayah perkotaan dan pedesaan.
2. **Kesenjangan gender** umumnya kecil di jenjang SD, namun mulai meningkat di jenjang SMA.
3. **Rasio murid per guru yang tinggi** (terutama di daerah terpencil) berkorelasi dengan rendahnya APM — menandakan perlunya pemerataan distribusi tenaga pendidik.

**Rekomendasi:**
- Pemerintah daerah dapat memprioritaskan **rekrutmen dan redistribusi guru** di wilayah dengan rasio tinggi.
- Perlu adanya **program retensi siswa SMA** di kabupaten dengan penurunan partisipasi signifikan.
- Integrasikan data ini dengan data infrastruktur pendidikan (misal: jumlah sekolah & fasilitas) untuk analisis lanjutan.
""")