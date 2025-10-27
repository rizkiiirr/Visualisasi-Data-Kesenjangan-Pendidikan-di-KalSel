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

# Fungsi untuk memuat data APK
@st.cache_data
def load_data_apk(path):
    df = pd.read_csv(path, delimiter=';')
    
    # Ganti nama kolom agar mudah digunakan
    df = df.rename(columns={
        'Kabupaten/Kota + Provinsi': 'Wilayah',
        'Laki-laki+Perempuan': 'Nilai_APK',
        'Laki-Laki': 'Nilai_Laki',
        'Perempuan': 'Nilai_Perempuan'
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


# --- Load kedua dataset ---
DATA_APK = 'Data_APK_Bersih.csv'
DATA_RASIO = 'Data_Rasio_Murid-per-Guru_Bersih.csv'

df_apk = load_data_apk(DATA_APK)
df_rasio = load_data_rasio(DATA_RASIO)

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
list_wilayah = sorted(df_apk['Wilayah'].unique())
pilih_wilayah = st.sidebar.multiselect(
    "Pilih Wilayah (opsional):",
    list_wilayah,
    placeholder="Tampilkan Semua Wilayah"
)

# ====================================================================
# 🔹 BAGIAN 3 — DATA FILTERING
# ====================================================================

df_filtered = df_apk[df_apk['Jenjang'] == pilih_jenjang].sort_values(by='Nilai_APK', ascending=False)
df_rasio_filtered = df_rasio[df_rasio['Jenjang'] == pilih_jenjang]

# ====================================================================
# 🔹 BAGIAN 4 — KONTEN UTAMA
# ====================================================================

st.title("🎓 Analisis Kesenjangan Pendidikan Kalimantan Selatan")
st.subheader(f"Menampilkan data: Angka Partisipasi Kasar (APK) dan Rasio Murid per Guru — Jenjang {pilih_jenjang}")
st.markdown("---")

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
    """)

# ====================================================================
# 🔹 VISUALISASI #1 — Peringkat APK per Kabupaten/Kota
# ====================================================================

st.subheader(f"📊 Visualisasi #1: Peringkat APK Jenjang {pilih_jenjang}")

fig1 = px.bar(
    df_filtered,
    x='Nilai_APK',
    y='Wilayah',
    orientation='h',
    title=f"Peringkat Angka Partisipasi Kasar ({pilih_jenjang}) per Kabupaten/Kota",
    labels={'Nilai_APK': 'APK (%)', 'Wilayah': 'Kabupaten/Kota'},
    text='Nilai_APK'
)

fig1.update_layout(yaxis={'categoryorder': 'total ascending'})
st.plotly_chart(fig1, use_container_width=True)
st.markdown("---")

# ====================================================================
# 🔹 VISUALISASI #2 — Perbandingan APK antar Jenjang
# ====================================================================

st.subheader("📊 Visualisasi #2: Perbandingan APK Antar Jenjang per Wilayah")

df_vis2 = df_apk.copy()
if pilih_wilayah:
    df_vis2 = df_vis2[df_vis2['Wilayah'].isin(pilih_wilayah)]

fig2 = px.bar(
    df_vis2,
    x='Wilayah',
    y='Nilai_APK',
    color='Jenjang',
    barmode='group',
    title="Perbandingan APK SD, SMP, dan SMA per Wilayah",
    labels={'Nilai_APK': 'APK (%)', 'Wilayah': 'Kabupaten/Kota'},
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
    size='Nilai_APK',
    hover_name='Wilayah',
    title=f"Perbandingan APK Laki-Laki vs Perempuan ({pilih_jenjang})",
    labels={
        'Nilai_Laki': 'APK Laki-Laki (%)',
        'Nilai_Perempuan': 'APK Perempuan (%)',
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
# 🔹 PENUTUP — INSIGHT & REKOMENDASI
# ====================================================================

st.subheader("🧠 Insight & Rekomendasi")

st.markdown("""
1. **Ketimpangan APK antar wilayah** cukup signifikan, terutama antara wilayah perkotaan dan pedesaan.
2. **Kesenjangan gender** umumnya kecil di jenjang SD, namun mulai meningkat di jenjang SMA.
3. **Rasio murid per guru yang tinggi** (terutama di daerah terpencil) berkorelasi dengan rendahnya APK — menandakan perlunya pemerataan distribusi tenaga pendidik.

**Rekomendasi:**
- Pemerintah daerah dapat memprioritaskan **rekrutmen dan redistribusi guru** di wilayah dengan rasio tinggi.
- Perlu adanya **program retensi siswa SMA** di kabupaten dengan penurunan partisipasi signifikan.
- Integrasikan data ini dengan data infrastruktur pendidikan (misal: jumlah sekolah & fasilitas) untuk analisis lanjutan.
""")

st.success("✅ Dashboard selesai! Anda telah memenuhi semua komponen UTS Visualisasi Data 🎉")