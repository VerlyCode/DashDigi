import streamlit as st
import pandas as pd
from sklearn.cluster import KMeans
import plotly.express as px

# ===============================
# CONFIG PAGE
# ===============================
st.set_page_config(
    page_title="DigiPay | Profilage Clients",
    page_icon="📊",
    layout="wide"
)

# ===============================
# 🔐 MOT DE PASSE
# ===============================
PASSWORD = "DIGIPAY2026"

if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    pwd = st.text_input("🔐 Mot de passe", type="password")
    if pwd == PASSWORD:
        st.session_state.auth = True
        st.rerun()
    elif pwd:
        st.error("Mot de passe incorrect")
    st.stop()

# ===============================
# 📊 DONNÉES – GOOGLE SHEETS
# ===============================

DATA_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSnZAx_1R_KYMsasRquY0Ryue3j-vGERgij_3cHbdbPHdzR4X-gh77WQ69y2P0I_Q/pub?output=csv"

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_URL)

    # conversion date
    df["TxnDate"] = pd.to_datetime(df["TxnDate"], errors="coerce")

    return df

df = load_data()

# création colonne mois
df["YearMonth"] = df["TxnDate"].dt.to_period("M")

# ===============================
# EXCLUSION EMPLOYÉS DIGIPAY
# ===============================
clients_internes = [
    "KIHOULOU Mesmin omer",
    "NGASSAKI-ZONI Gachlem zepharos"
]

df = df[~df["Sender Name"].isin(clients_internes)]

# ===============================
# SIDEBAR – FILTRES
# ===============================
st.sidebar.header("🔎 Filtres")

# filtre année
annees = sorted(df["TxnDate"].dt.year.dropna().unique())

annee_sel = st.sidebar.multiselect(
    "Année",
    annees,
    default=annees
)

df = df[df["TxnDate"].dt.year.isin(annee_sel)]

# filtre agence
agences = sorted(df["Agence"].dropna().unique())

agence_sel = st.sidebar.multiselect(
    "Agence",
    agences,
    default=agences
)

df = df[df["Agence"].isin(agence_sel)]

# ===============================
# HEADER
# ===============================
col1, col2 = st.columns([1,6])

with col1:
    st.image("Logo.png", width=90)

with col2:
    st.markdown("""
        <h1 style='margin-bottom:0;'>📊 Profilage Clients</h1>
        <h4 style='color:#9CA3AF;margin-top:0;'>
        DigiPay – Analyse & Segmentation Clients
        </h4>
    """, unsafe_allow_html=True)

st.divider()

# ===============================
# KPI
# ===============================
date_max = df["TxnDate"].max()

def clients_actifs(jours):
    return df[df["TxnDate"] >= date_max - pd.Timedelta(days=jours)]["Sender Name"].nunique()

k1, k2, k3, k4 = st.columns(4)

k1.metric("CLIENTS", df["Sender Name"].nunique())
k2.metric("ACTIFS 30J", clients_actifs(30))
k3.metric("ACTIFS 60J", clients_actifs(60))
k4.metric("ACTIFS 90J", clients_actifs(90))

st.divider()

# ===============================
# TABLE CLIENTS
# ===============================
def table_clients(df, date_min=None):

    if date_min is not None:
        df = df[df["TxnDate"] >= date_min]

    table = (
        df.groupby(["Sender Name","Agence"])
        .agg(
            Telephone=("Tél. Expéditeur", "first"),
            Nombre_Envois=("TxnDate","count"),
            Mois_Actifs=("YearMonth","nunique")
        )
        .reset_index()
    )

    table["Frequence"] = (
        table["Nombre_Envois"] / table["Mois_Actifs"]
    ).round(2)

    return table.sort_values("Nombre_Envois", ascending=False)
# ===============================
# LISTES CLIENTS
# ===============================
st.subheader("🟢 Clients actifs – 30 jours")
st.dataframe(table_clients(df, date_max - pd.Timedelta(days=30)), use_container_width=True)

st.subheader("🟡 Clients actifs – 60 jours")
st.dataframe(table_clients(df, date_max - pd.Timedelta(days=60)), use_container_width=True)

st.subheader("🔵 Clients actifs – 90 jours")
st.dataframe(table_clients(df, date_max - pd.Timedelta(days=90)), use_container_width=True)

st.subheader("🏆 Top clients")
st.dataframe(table_clients(df).head(50), use_container_width=True)

# ===============================
# CLIENTS ACTIFS CHAQUE MOIS + FREQUENCE
# ===============================

df["YearMonth"] = df["TxnDate"].dt.to_period("M")

st.subheader("📆 Clients actifs chaque mois")

clients_12_mois = (
    df.groupby(["Sender Name","Agence"])
    .agg(
        Telephone=("Tél. Expéditeur","first"),
        Transactions=("TxnDate","count"),
        Mois_Actifs=("YearMonth","nunique")
    )
    .reset_index()
)

# fréquence moyenne des transactions par mois actif
clients_12_mois["Frequence_Mensuelle"] = (
    clients_12_mois["Transactions"] /
    clients_12_mois["Mois_Actifs"]
).round(2)

# clients présents tous les mois
clients_12_mois = clients_12_mois[clients_12_mois["Mois_Actifs"] >= 12]

st.dataframe(clients_12_mois, use_container_width=True)



# ===============================
# 🔁 CLIENTS RÉCURRENTS IMPORTANTS
# ===============================

st.subheader("🔁 Clients fort volume")

clients_gros = (
    df.groupby("Sender Name")
    .agg(
        Telephone=("Tél. Expéditeur","first"),
        Transactions=("TxnDate","count"),
        Derniere_Transaction=("TxnDate","max"),
        Mois_Actifs=("YearMonth","nunique")
    )
    .reset_index()
)

# fréquence moyenne mensuelle
clients_gros["Frequence_Mensuelle"] = (
    clients_gros["Transactions"] /
    clients_gros["Mois_Actifs"]
).round(2)

# estimation prochaine transaction
clients_gros["Prochaine_Transaction_Possible"] = (
    clients_gros["Derniere_Transaction"] +
    pd.Timedelta(days=30)
)

# trier par nombre de transactions
clients_gros = clients_gros.sort_values(
    "Transactions",
    ascending=False
)

# garder les 30 clients les plus actifs
clients_gros = clients_gros.head(30)

st.dataframe(clients_gros, use_container_width=True)


# ===============================
# CLIENTS 1 TRANSACTION
# ===============================
st.subheader("⚠️ Clients avec une seule transaction")

one_tx = table_clients(df)

st.dataframe(
    one_tx[one_tx["Nombre_Envois"] == 1],
    use_container_width=True
)

# ===============================
# PROJECTION CLIENTS
# ===============================

st.subheader("🔮 Projection clients probables")

clients_90 = df[df["TxnDate"] >= date_max - pd.Timedelta(days=90)]

projection = (
    clients_90.groupby("Sender Name")
    .agg(
        Telephone=("Tél. Expéditeur","first"),
        Transactions_90j=("TxnDate","count"),
        Derniere_Transaction=("TxnDate","max"),
        Mois_Actifs=("YearMonth","nunique")
    )
    .reset_index()
)

# fréquence moyenne
projection["Frequence_Mensuelle"] = (
    projection["Transactions_90j"] /
    projection["Mois_Actifs"]
).round(2)

# estimation transactions mois prochain
projection["Transactions_Prevues_Mars"] = (
    projection["Frequence_Mensuelle"]
).round()

# estimation date retour
projection["Retour_Potentiel"] = (
    projection["Derniere_Transaction"] +
    pd.Timedelta(days=30)
)

projection = projection.sort_values(
    "Frequence_Mensuelle",
    ascending=False
)

st.dataframe(projection, use_container_width=True)

# ===============================
# MOTIFS ENVOI
# ===============================
st.subheader("🥧 Répartition des transactions par motif d’envoi")

df_motif = df.copy()

df_motif["Reason Sending"] = (
    df_motif["Reason Sending"]
    .fillna("AUTRE")
    .str.upper()
    .str.strip()
)

motifs = (
    df_motif.groupby("Reason Sending")
    .size()
    .reset_index(name="Nombre_Transactions")
)

fig_motif = px.pie(
    motifs,
    names="Reason Sending",
    values="Nombre_Transactions",
    hole=0.4,
    template="plotly_dark"
)

fig_motif.update_layout(title_x=0.5)

st.plotly_chart(fig_motif, use_container_width=True)

# ===============================
# CLUSTERING KMEANS
# ===============================
st.subheader("🧠 Segmentation clients – Clustering K-Means")

# données clustering
cluster_df = table_clients(df)

# variables utilisées pour le ML
X = cluster_df[["Nombre_Envois","Mois_Actifs"]].fillna(0)

# modèle KMeans
kmeans = KMeans(
    n_clusters=3,
    random_state=42,
    n_init=10
)

cluster_df["Cluster"] = kmeans.fit_predict(X)

# graphique
fig = px.scatter(
    cluster_df,
    x="Nombre_Envois",
    y="Mois_Actifs",
    color=cluster_df["Cluster"].astype(str),
    hover_data=["Sender Name","Agence"],
    template="plotly_dark"
)

st.plotly_chart(fig, use_container_width=True)


# ===============================
# ÉVOLUTION MENSUELLE
# ===============================
st.subheader("📈 Évolution mensuelle des clients")

clients_actifs = (
    df.groupby("YearMonth")["Sender Name"]
    .nunique()
    .reset_index(name="Clients_Actifs")
)

clients_actifs["YearMonth"] = clients_actifs["YearMonth"].astype(str)

fig = px.line(
    clients_actifs,
    x="YearMonth",
    y="Clients_Actifs",
    markers=True,
    template="plotly_dark"
)

fig.update_layout(title_x=0.5)

st.plotly_chart(fig, use_container_width=True)


# ===============================
# 🔻 FUNNEL CLIENT DIGIPAY
# ===============================
st.subheader("🔻 Funnel Clients DigiPay")

# Nombre de transactions par client
tx_par_client = (
    df.groupby("Sender Name")
    .size()
    .reset_index(name="Nombre_Envois")
)

# Construction du funnel
funnel_data = pd.DataFrame({
    "Étape": [
        "Clients acquis",
        "Clients actifs",
        "Clients fidèles",
        "Clients très fidèles"
    ],
    "Clients": [
        tx_par_client["Sender Name"].nunique(),                 # ≥1 transaction
        tx_par_client[tx_par_client["Nombre_Envois"] >= 2].shape[0],
        tx_par_client[tx_par_client["Nombre_Envois"] >= 4].shape[0],
        tx_par_client[tx_par_client["Nombre_Envois"] >= 12].shape[0],
    ]
})

# ===============================
# KPI FUNNEL GLOBAL
# ===============================
c1, c2, c3 = st.columns(3)

c1.metric("👥 Clients acquis", funnel_data.loc[0, "Clients"])
c2.metric("🔥 Clients actifs", funnel_data.loc[1, "Clients"])
c3.metric("🔁 Clients fidèles", funnel_data.loc[2, "Clients"])


# ===============================
# 📊 ANALYSE MOIS DE FEVRIER 2026
# ===============================
st.markdown("## 📊 Analyse commerciale – Février 2026")
st.divider()

# -------------------------------
# FILTRE JANVIER / FEVRIER
# -------------------------------

df_jan = df[
    (df["TxnDate"].dt.year == 2026) &
    (df["TxnDate"].dt.month == 1)
]

df_fev = df[
    (df["TxnDate"].dt.year == 2026) &
    (df["TxnDate"].dt.month == 2)
]

# -------------------------------
# CLIENTS JANVIER / FEVRIER
# -------------------------------

clients_janvier = set(df_jan["Sender Name"])
clients_fevrier = set(df_fev["Sender Name"])

clients_retenus = clients_janvier.intersection(clients_fevrier)
clients_perdus = clients_janvier - clients_fevrier

# -------------------------------
# NOUVEAUX CLIENTS FEVRIER
# -------------------------------

first_tx = df.groupby("Sender Name")["TxnDate"].min()

nouveaux_clients_list = first_tx[
    (first_tx.dt.year == 2026) &
    (first_tx.dt.month == 2)
].index.tolist()

nouveaux_clients = len(nouveaux_clients_list)

# -------------------------------
# TRANSACTIONS PAR CLIENT FEVRIER
# -------------------------------

tx_fev = (
    df_fev.groupby("Sender Name")
    .size()
    .reset_index(name="Nombre_Envois")
)

clients_1_tx = tx_fev[tx_fev["Nombre_Envois"] == 1].shape[0]
clients_fideles = tx_fev[tx_fev["Nombre_Envois"] >= 2].shape[0]

# -------------------------------
# RETENTION / CHURN
# -------------------------------

retention = (len(clients_retenus) / len(clients_janvier)) * 100
churn = (len(clients_perdus) / len(clients_janvier)) * 100

# -------------------------------
# KPI
# -------------------------------

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric("🆕 Nouveaux clients", nouveaux_clients)
k2.metric("🔥 Clients fidèles", clients_fideles)
k3.metric("⚠️ 1 transaction", clients_1_tx)
k4.metric("📈 Rétention Jan → Fév", f"{retention:.1f}%")
k5.metric("📉 Churn", f"{churn:.1f}%")

st.divider()

# ===============================
# 🔻 FUNNEL FEVRIER
# ===============================

st.markdown("### 🔻 Funnel clients – Février 2026")

# transactions des nouveaux clients
tx_new_clients = (
    df_fev[df_fev["Sender Name"].isin(nouveaux_clients_list)]
    .groupby("Sender Name")
    .agg(
        Telephone=("Tél. Expéditeur","first"),
        Nombre_Envois=("TxnDate","count")
    )
    .reset_index()
)

# nouveaux clients actifs (>=2 transactions)
nouveaux_actifs = tx_new_clients[
    tx_new_clients["Nombre_Envois"] >= 2
]["Sender Name"]

# construction funnel
funnel_fev = pd.DataFrame({
    "Étape":[
        "Clients Janvier",
        "Revenus en Février",
        "Nouveaux clients acquis",
        "Nouveaux clients actifs (≥2 tx)"
    ],
    "Clients":[
        len(clients_janvier),
        len(clients_retenus),
        nouveaux_clients,
        len(nouveaux_actifs)
    ]
})

fig_funnel = px.bar(
    funnel_fev,
    x="Clients",
    y="Étape",
    orientation="h",
    text="Clients",
    color="Étape",
    template="plotly_dark"
)

fig_funnel.update_layout(title_x=0.5)

st.plotly_chart(fig_funnel, use_container_width=True)

# -------------------------------
# TAUX ACTIVATION NOUVEAUX CLIENTS
# -------------------------------

if nouveaux_clients > 0:
    activation_rate = (len(nouveaux_actifs) / nouveaux_clients) * 100
else:
    activation_rate = 0

st.metric("🔥 Activation nouveaux clients (≥2 transactions)", f"{activation_rate:.1f}%")

st.divider()

# ===============================
# LISTE NOUVEAUX CLIENTS
# ===============================

col1, col2 = st.columns(2)

with col1:

    st.markdown("### 🆕 Nouveaux clients acquis – Février 2026")

    tx_new_clients = (
        df_fev[df_fev["Sender Name"].isin(nouveaux_clients_list)]
        .groupby("Sender Name")
        .agg(
            Telephone=("Tél. Expéditeur","first"),
            Nombre_Envois=("TxnDate","count")
        )
        .reset_index()
        .sort_values("Nombre_Envois", ascending=False)
    )

    st.dataframe(tx_new_clients, use_container_width=True)


with col2:

    st.markdown("### 🔁 Nouveaux clients restés actifs")

    df_new_active = (
        df[df["Sender Name"].isin(nouveaux_actifs)]
        .groupby("Sender Name")
        .agg(
            Telephone=("Tél. Expéditeur","first")
        )
        .reset_index()
    )

    st.dataframe(df_new_active, use_container_width=True)

st.divider()

# ===============================
# DESTINATIONS + VOLUME
# ===============================

col1, col2 = st.columns(2)

with col1:

    st.markdown("### 🌍 Destinations principales – Février 2026")

    destinations = (
        df_fev.groupby("Destination Country")
        .size()
        .reset_index(name="Transactions")
        .sort_values("Transactions", ascending=False)
    )

    fig_dest = px.bar(
        destinations.head(10),
        x="Destination Country",
        y="Transactions",
        text="Transactions",
        template="plotly_dark"
    )

    st.plotly_chart(fig_dest, use_container_width=True)


with col2:

    st.markdown("### 💰 Répartition du volume envoyé")

    volume_pays = (
        df_fev.groupby("Destination Country")["Src Amount"]
        .sum()
        .reset_index()
        .sort_values("Src Amount", ascending=False)
    )

    fig_volume = px.pie(
        volume_pays.head(8),
        names="Destination Country",
        values="Src Amount",
        hole=0.4,
        template="plotly_dark"
    )

    fig_volume.update_traces(textinfo="percent+label")

    st.plotly_chart(fig_volume, use_container_width=True)

# ===============================
# TOP CLIENTS
# ===============================

st.markdown("### 🏆 Top clients – Février 2026")

top_clients = (
    df_fev.groupby("Sender Name")
    .agg(
        Telephone=("Tél. Expéditeur","first"),
        Transactions=("TxnDate","count")
    )
    .reset_index()
    .sort_values("Transactions", ascending=False)
)

st.dataframe(top_clients.head(20), use_container_width=True)

# ===============================
# SEGMENTATION FIDELITE CLIENTS
# ===============================

st.subheader("🎯 Segmentation fidélité des clients")

freq_clients = (
    df.groupby("Sender Name")
    .agg(
        Transactions=("TxnDate","count"),
        Mois_Actifs=("YearMonth","nunique")
    )
    .reset_index()
)

freq_clients["Frequence_Mensuelle"] = (
    freq_clients["Transactions"] /
    freq_clients["Mois_Actifs"]
).round(2)

# segmentation fidélité
freq_clients["Segment"] = pd.cut(
    freq_clients["Mois_Actifs"],
    bins=[0,3,9,12],
    labels=["Occasionnel","Fidèle","Très fidèle"]
)

segments = (
    freq_clients.groupby("Segment")
    .size()
    .reset_index(name="Clients")
)

fig_seg = px.pie(
    segments,
    names="Segment",
    values="Clients",
    hole=0.4,
    template="plotly_dark",
    title="Segmentation fidélité clients"
)

fig_seg.update_layout(title_x=0.5)

st.plotly_chart(fig_seg, use_container_width=True)




# ===============================
# 📈 ACQUISITION & RETENTION JAN → FEV
# ===============================

st.markdown("### 📈 Acquisition & rétention – Janvier → Février 2026")

# première transaction de chaque client
first_tx = df.groupby("Sender Name")["TxnDate"].min()

# clients acquis en janvier ou février
clients_acquis_jan_fev = first_tx[
    (first_tx.dt.year == 2026) &
    (first_tx.dt.month.isin([1,2]))
].index

# clients actifs en février
clients_fevrier = set(df_fev["Sender Name"])

# nouveaux clients revenus en février
clients_revenus = set(clients_acquis_jan_fev).intersection(clients_fevrier)

# nouveaux clients perdus
clients_non_revenus = set(clients_acquis_jan_fev) - clients_revenus

# taux retention
if len(clients_acquis_jan_fev) > 0:
    retention_acquisition = (len(clients_revenus) / len(clients_acquis_jan_fev)) * 100
else:
    retention_acquisition = 0

# KPI
k1, k2, k3 = st.columns(3)

k1.metric("👥 Clients acquis (Jan-Fév)", len(clients_acquis_jan_fev))
k2.metric("🔥 Revenus en Février", len(clients_revenus))
k3.metric("📉 Non revenus", len(clients_non_revenus))

st.metric("📊 Taux de rétention des nouveaux clients", f"{retention_acquisition:.1f}%")





# ===============================
# 🔻 FUNNEL ACQUISITION
# ===============================

funnel_acquisition = pd.DataFrame({
    "Étape":[
        "Clients acquis Jan-Fév",
        "Revenus en Février",
        "Clients perdus"
    ],
    "Clients":[
        len(clients_acquis_jan_fev),
        len(clients_revenus),
        len(clients_non_revenus)
    ]
})

fig_acq = px.bar(
    funnel_acquisition,
    x="Clients",
    y="Étape",
    orientation="h",
    text="Clients",
    color="Étape",
    template="plotly_dark",
    title="Conversion des nouveaux clients – Janvier → Février"
)

fig_acq.update_layout(title_x=0.5)

st.plotly_chart(fig_acq, use_container_width=True)


# ===============================
# 📊 SOLDE NET D’ACQUISITION CLIENTS
# ===============================

st.markdown("## 📊 Solde net d’acquisition clients")
st.caption("Évolution mensuelle de la base clients DigiPay")

# créer colonne mois
df["YearMonth"] = df["TxnDate"].dt.to_period("M")

# -------------------------------
# CLIENTS ACTIFS PAR MOIS
# -------------------------------

clients_mois = (
    df.groupby("YearMonth")["Sender Name"]
    .nunique()
    .reset_index(name="Clients_Actifs")
)

# -------------------------------
# NOUVEAUX CLIENTS PAR MOIS
# -------------------------------

first_tx = (
    df.groupby("Sender Name")["YearMonth"]
    .min()
    .reset_index()
)

nouveaux_clients = (
    first_tx.groupby("YearMonth")["Sender Name"]
    .nunique()
    .reset_index(name="Nouveaux_Clients")
)

# -------------------------------
# CLIENTS PERDUS PAR MOIS
# -------------------------------

months = sorted(df["YearMonth"].unique())
clients_perdus = []

for i in range(1, len(months)):

    prev_clients = set(
        df[df["YearMonth"] == months[i-1]]["Sender Name"]
    )

    curr_clients = set(
        df[df["YearMonth"] == months[i]]["Sender Name"]
    )

    clients_perdus.append([
        months[i],
        len(prev_clients - curr_clients)
    ])

clients_perdus = pd.DataFrame(
    clients_perdus,
    columns=["YearMonth","Clients_Perdus"]
)

# -------------------------------
# FUSION TABLEAU
# -------------------------------

solde_clients = (
    clients_mois
    .merge(nouveaux_clients, on="YearMonth", how="left")
    .merge(clients_perdus, on="YearMonth", how="left")
    .fillna(0)
)

# calcul solde net
solde_clients["Solde_Net"] = (
    solde_clients["Nouveaux_Clients"] -
    solde_clients["Clients_Perdus"]
)

# format mois
solde_clients["YearMonth"] = solde_clients["YearMonth"].astype(str)

# afficher tableau
st.dataframe(solde_clients, use_container_width=True)

# ===============================
# FOOTER
# ===============================
st.markdown("""
<hr>
<p style='text-align:center;color:#6B7280;'>
© 2026 DigiPay – Direction Commerciale<br>
Verly BOUMBOU KIMBATSA – Responsable des Opérations Commerciales
</p>
""", unsafe_allow_html=True)

