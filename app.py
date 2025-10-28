# ====================================================================
# 🎓 DASHBOARD KESENJANGAN PENDIDIKAN KALIMANTAN SELATAN
# ====================================================================
# Dibuat oleh: Muhammad Rizki Ramadhan (Bubub)
# Untuk: UTS Visualisasi Data
# ====================================================================

# --- 1. Import Library ---
import streamlit as st
import pandas as pd
import plotly.express as px

# --- 2. Konfigurasi Halaman ---
st.set_page_config(
    page_title="Dashboard Kesenjangan Pendidikan Kalsel",
    page_icon="🎓",
    layout="wide"
)

# ====================================================================
# 🔹 BAGIAN 1 — LOAD & CLEANING DATA
# ====================================================================

# Fungsi untuk memuat data APM
@st.cache_data
def load_data_apm(path):
    df = pd.read_csv(path, delimiter=';')
    
    # Ganti nama kolom agar mudah digunakan
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
    df_long['Rasio_Murid_per_Guru'] = df_long['Rasio_Murid_per_Guru'].round(2)
    
    return df_long

# [FUNGSI DIPERBARUI untuk RLS - Lebih Robust]
# [FUNGSI RLS DIPERBARUI - Langsung pakai delimiter ';']
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

# --- Load kedua dataset ---
DATA_APM = 'Data_APM_Bersih.csv'
DATA_RASIO = 'Data_Rasio_Murid-per-Guru_Bersih.csv'
DATA_RLS = 'Data_RLS_Bersih.csv'

df_apm = load_data_apm(DATA_APM)
df_rasio = load_data_rasio(DATA_RASIO)
df_rls = load_data_rls(DATA_RLS)

# --- Gabungkan Data ---
DATA_LOADED_SUCCESS = False
if not df_apm.empty and not df_rasio.empty and not df_rls.empty:
    # Gabungkan APM + Rasio
    df_master = pd.merge(df_apm, df_rasio, on=['Wilayah', 'Jenjang'], how='left')
    # Gabungkan dengan RLS (hanya berdasarkan Wilayah)
    df_master = pd.merge(df_master, df_rls, on='Wilayah', how='left')
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

# ====================================================================
# 🔹 BAGIAN 3 — DATA FILTERING
# ====================================================================

df_filtered = df_apm[df_apm['Jenjang'] == pilih_jenjang].sort_values(by='Nilai_APM', ascending=False)
df_rasio_filtered = df_rasio[df_rasio['Jenjang'] == pilih_jenjang]
df_rls_unique = df_master[['Wilayah', 'Nilai_RLS']].drop_duplicates().sort_values('Nilai_RLS', ascending=False).dropna()

# ====================================================================
# 🔹 BAGIAN 4 — KONTEN UTAMA
# ====================================================================

st.title("🎓 Analisis Kesenjangan Pendidikan Kalimantan Selatan")
st.subheader(f"Menampilkan data: Angka Partisipasi Murni (APM), Rasio Murid per Guru — Jenjang {pilih_jenjang}, dan Rata-rata Lama Sekolah (RLS)")
st.markdown("Dashboard ini menganalisis partisipasi pendidikan murni (APM), hasil historis (RLS), dan faktor sumber daya guru.")
# --- Konteks Studi Kasus ---
with st.expander("📖 Konteks Studi Kasus & Pertanyaan Analitis"):
    st.markdown("""
    **Konteks:**
    Pemerataan akses pendidikan adalah fondasi pembangunan SDM di Kalimantan Selatan.
    Namun, data menunjukkan adanya perbedaan signifikan antar kabupaten/kota.
    Visualisasi ini bertujuan untuk mengubah data BPS menjadi **insight yang actionable**.

    **Pertanyaan Analitis:**
    1. Kabupaten/kota mana yang memiliki **partisipasi pendidikan tertinggi dan terendah**?
    2. Seberapa besar **kesenjangan gender** dalam partisipasi pendidikan?
    3. Bagaimana **rasio murid per guru** memengaruhi kesenjangan antar daerah?
    4. Bagaimana **hasil pendidikan historis (RLS)** di tiap wilayah, dan apakah konsisten dengan APM saat ini? 
    """)

# ====================================================================
# 🔹 VISUALISASI #1 — Peringkat APM per Kabupaten/Kota
# ====================================================================

st.subheader(f"📊 Visualisasi #1: Peringkat APM Jenjang {pilih_jenjang}")

fig1 = px.bar(
    df_filtered,
    x='Nilai_APM',
    y='Wilayah',
    orientation='h',
    title=f"Peringkat Angka Partisipasi Murni ({pilih_jenjang}) per Kabupaten/Kota",
    labels={'Nilai_APM': 'APM (%)', 'Wilayah': 'Kabupaten/Kota'},
    text='Nilai_APM'
)

fig1.update_layout(yaxis={'categoryorder': 'total ascending'})
st.plotly_chart(fig1, use_container_width=True)
st.markdown("---")

# ====================================================================
# 🔹 VISUALISASI #2 — Perbandingan APM antar Jenjang
# ====================================================================

st.subheader("📊 Visualisasi #2: Perbandingan APM Antar Jenjang per Wilayah")

df_vis2 = df_apm.copy()
if pilih_wilayah:
    df_vis2 = df_vis2[df_vis2['Wilayah'].isin(pilih_wilayah)]

fig2 = px.bar(
    df_vis2,
    x='Wilayah',
    y='Nilai_APM',
    color='Jenjang',
    barmode='group',
    title="Perbandingan APM SD, SMP, dan SMA per Wilayah",
    labels={'Nilai_APM': 'APM (%)', 'Wilayah': 'Kabupaten/Kota'},
    category_orders={"Jenjang": ["SD", "SMP", "SMA"]}
)

fig2.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig2, use_container_width=True)
st.markdown("---")

# ====================================================================
# 🔹 VISUALISASI #3 — Kesenjangan Gender
# ====================================================================

st.subheader(f"📊 Visualisasi #3: Analisis Kesenjangan Gender (Jenjang {pilih_jenjang})")

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
    color_continuous_scale='RdBu_r'
)

fig3.add_shape(
    type='line',
    x0=df_filtered['Nilai_Laki'].min()-5, y0=df_filtered['Nilai_Laki'].min()-5,
    x1=df_filtered['Nilai_Perempuan'].max()+5, y1=df_filtered['Nilai_Perempuan'].max()+5,
    line=dict(color='gray', dash='dash')
)

st.plotly_chart(fig3, use_container_width=True)
st.markdown("---")

# ====================================================================
# 🔹 VISUALISASI #4 — Rasio Murid per Guru
# ====================================================================

st.subheader("📊 Visualisasi #4: Rasio Murid per Guru per Kabupaten/Kota")
st.markdown("""
Rasio ini menunjukkan **jumlah murid rata-rata yang ditangani oleh satu guru** di setiap kabupaten/kota.
Nilai yang tinggi mengindikasikan potensi kekurangan guru dan dapat berdampak pada kualitas pembelajaran.
""")

fig4 = px.bar(
    df_rasio_filtered,
    x='Wilayah',
    y='Rasio_Murid_per_Guru',
    color='Jenjang',
    title=f"Rasio Murid per Guru — Jenjang {pilih_jenjang}",
    labels={'Rasio_Murid_per_Guru': 'Jumlah Murid per 1 Guru', 'Wilayah': 'Kabupaten/Kota'},
    text='Rasio_Murid_per_Guru'
)

fig4.update_traces(texttemplate='%{text:.1f}', textposition='outside')
fig4.update_layout(xaxis_tickangle=-45, showlegend=False)
st.plotly_chart(fig4, use_container_width=True)

rata2_rasio = df_rasio_filtered['Rasio_Murid_per_Guru'].mean().round(2)
max_row = df_rasio_filtered.loc[df_rasio_filtered['Rasio_Murid_per_Guru'].idxmax()]
min_row = df_rasio_filtered.loc[df_rasio_filtered['Rasio_Murid_per_Guru'].idxmin()]

st.info(f"""
**Rata-rata Rasio Murid per Guru (Jenjang {pilih_jenjang}):** {rata2_rasio}
- 🔺 Tertinggi: {max_row['Wilayah']} ({max_row['Rasio_Murid_per_Guru']:.1f} murid/guru)
- 🔻 Terendah: {min_row['Wilayah']} ({min_row['Rasio_Murid_per_Guru']:.1f} murid/guru)
""")
st.markdown("---")

# ====================================================================
# 🔹 VISUALISASI #5 — Peringkat Rata-rata Lama Sekolah (RLS)
# ====================================================================

st.subheader("📊 5. Peringkat Rata-rata Lama Sekolah (RLS) per Kabupaten/Kota")
st.markdown("RLS mengukur capaian pendidikan historis penduduk dewasa (25 tahun ke atas).")
if df_rls_unique.empty:
    st.warning("Data RLS tidak tersedia atau kosong.")
else:
    fig5 = px.bar(
        df_rls_unique,
        x='Nilai_RLS', y='Wilayah', orientation='h',
        title="Peringkat Rata-rata Lama Sekolah (RLS)",
        labels={'Nilai_RLS': 'RLS (Tahun)', 'Wilayah': 'Kabupaten/Kota'},
        text='Nilai_RLS'
    )
    fig5.update_traces(texttemplate='%{text:.2f}')
    fig5.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig5, use_container_width=True)
st.markdown("---")

# ====================================================================
# 🔹 VISUALISASI #6 — RLS vs. APM SMA
# ====================================================================

st.subheader("📊 6. Analisis Konsistensi Kesenjangan: RLS vs. APM SMA")
st.markdown("Membandingkan hasil pendidikan historis (RLS) dengan partisipasi SMA saat ini (APM SMA).")
df_vis6 = df_master[df_master['Jenjang'] == 'SMA'][['Wilayah', 'Nilai_RLS', 'Nilai_APM']].drop_duplicates().dropna()
if df_vis6.empty: st.warning("Data lengkap ('RLS' dan 'APM SMA') tidak tersedia.")
else:
    fig6 = px.scatter(
        df_vis6, x='Nilai_RLS', y='Nilai_APM', hover_name='Wilayah',
        title="Konsistensi Kesenjangan: RLS vs APM SMA",
        labels={'Nilai_RLS': 'RLS (Hasil Historis)', 'Nilai_APM': 'APM SMA (Partisipasi Saat Ini)'},
        size='Nilai_APM', color='Wilayah'
    )
    avg_rls_vis6 = df_vis6['Nilai_RLS'].mean(); avg_apm_sma_vis6 = df_vis6['Nilai_APM'].mean()
    fig6.add_vline(x=avg_rls_vis6, line=dict(color='grey', dash='dash'), annotation_text="Rata-rata RLS")
    fig6.add_hline(y=avg_apm_sma_vis6, line=dict(color='grey', dash='dash'), annotation_text="Rata-rata APM SMA")
    st.plotly_chart(fig6, use_container_width=True)
    st.markdown("""**Cara Membaca Grafik:** *(Kuadran Kiri Bawah: Masalah Persisten)*""")
st.markdown("---")

# ====================================================================
# 🔹 PENUTUP — INSIGHT & REKOMENDASI
# ====================================================================

st.subheader("🧠 Insight & Rekomendasi")

st.markdown("""
1. **Ketimpangan APM antar wilayah** cukup signifikan, terutama antara wilayah perkotaan dan pedesaan.
2. **Kesenjangan gender** umumnya kecil di jenjang SD, namun mulai meningkat di jenjang SMA.
3. **Rasio murid per guru yang tinggi** (terutama di daerah terpencil) berkorelasi dengan rendahnya APM — menandakan perlunya pemerataan distribusi tenaga pendidik.

**Rekomendasi:**
- Pemerintah daerah dapat memprioritaskan **rekrutmen dan redistribusi guru** di wilayah dengan rasio tinggi.
- Perlu adanya **program retensi siswa SMA** di kabupaten dengan penurunan partisipasi signifikan.
- Integrasikan data ini dengan data infrastruktur pendidikan (misal: jumlah sekolah & fasilitas) untuk analisis lanjutan.
""")

st.success("✅ Dashboard selesai! Anda telah memenuhi semua komponen UTS Visualisasi Data 🎉")