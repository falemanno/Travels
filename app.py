from pymongo import MongoClient
import os
import pandas as pd
import streamlit as st

def normalize_priority(p):
    if not p:
        return "⭐"

    # converte ★ in ⭐
    p = p.replace("★", "⭐")

    # riduce a max 5 stelle
    n = len(p)
    n = max(1, min(n, 5))

    return "⭐" * n

'''
MONGO_URI = "mongodb+srv://travel_user:travel_password@cluster0.xfuukvm.mongodb.net/?appName=Cluster0"

@st.cache_resource
def get_collection():
    MONGO_URI = os.environ.get("MONGO_URI")
    client = MongoClient(MONGO_URI)
    #    "mongodb+srv://falemanno_db_user:rRNEUas0X4OdJRcE@cluster0.xfuukvm.mongodb.net/"
    #)
    db = client['Travel_Plans']
    return db['Trips']

collection = get_collection()
'''
os.environ["MONGO_URI"] = "mongodb+srv://travel_user:travel_password@cluster0.xfuukvm.mongodb.net/?appName=Cluster0"
# -------------------------------
# Legge la variabile d'ambiente MONGO_URI
# -------------------------------
MONGO_URI = os.environ.get("MONGO_URI")

if not MONGO_URI:
    st.error(
        "La variabile d'ambiente MONGO_URI non è impostata!\n"
        "Assicurati di configurarla su Streamlit Cloud o nel tuo PC."
    )
    st.stop()  # ferma l'app se non trova la connessione

# -------------------------------
# Connessione al cluster MongoDB Atlas
# -------------------------------
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    # prova a pingare il server per verificare la connessione
    client.admin.command("ping")
except Exception as e:
    st.error(f"Connessione a MongoDB fallita:\n{e}")
    st.stop()

# -------------------------------
# Selezione database e collezione
# -------------------------------
db = client["Travel_Plans"]     # nome del database
collection = db["Trips"]        # nome della collezione

docs = list(collection.find())

def normalize(doc):

    durata = doc.get("durata_media_giorni")

    if durata in ("", None):
        durata = None
    else:
        try:
            durata = int(durata)
        except ValueError:
            durata = None

    return {
        "_id": doc["_id"],
        "Destinazione": doc.get("destinazione", ""),
        "Durata (giorni)": durata,
        "Periodo": doc.get("periodo", ""),
        "Budget (€)": doc.get("budget", "€"),
        #"Budget (€)": f"{doc.get('budget', {}).get('min','')} – {doc.get('budget', {}).get('max','')}",
        "Tipologia": doc.get("tipo_viaggio",""),
        "Stato": doc.get("stato",""),
        "Priorità": doc.get("priorità_vis", ""),
        "Note": doc.get("note", "")
    }


data = [normalize(d) for d in docs]
df = pd.DataFrame(data)

st.title("🌍 Travel Planner")
#st.dataframe(df, use_container_width=True)
st.data_editor(
    df.drop(columns=["_id"]),
    use_container_width=True,
    disabled=True
)


st.divider()
st.header("➕ Aggiungi un nuovo viaggio")

with st.form("add_trip"):
    destinazione = st.text_input("Destinazione *")

    col1, col2 = st.columns(2)
    with col1:
        durata = st.number_input(
            "Durata media (giorni)",
            min_value=1,
            step=1,
        )

    with col2:
        priorità_vis = st.selectbox(
            "Priorità",
            options=[1, 2, 3, 4, 5],
            format_func=lambda x: "⭐" * x
        )

    periodo = st.text_input(
        "Periodo migliore (separato da virgole)",
        placeholder="Marzo, Aprile oppure 30/12/2025, 05/01/2026"
    )

    budget = st.selectbox(
        "Budget",
        options=["€", "€€", "€€€"],       
        )

    note = st.text_area("Note")

    submitted = st.form_submit_button("Salva viaggio")

if submitted:
    if not destinazione:
        st.error("La destinazione è obbligatoria")
    else:
        periodo = [
            p.strip() for p in periodo.split(",") if p.strip()
        ]

        doc = {
            "destinazione": destinazione,
            "durata_media_giorni": int(durata) if durata else None,
            "periodo_migliore": periodo,
            "budget": budget,
            "priorità": int(priorità_vis),
            "note": note,
        }

        collection.insert_one(doc)
        st.success("Viaggio aggiunto correttamente ✅")
        st.rerun()

st.divider()
st.header("🗑️ Elimina un viaggio")

trip_labels = df.apply(
    lambda r: f"{r['Destinazione']} ({r['Periodo']})",
    axis=1
)

selected_label = st.selectbox(
    "Seleziona il viaggio da eliminare",
    options=trip_labels,
)

selected_id = df.loc[
    trip_labels == selected_label, "_id"
].values[0]

confirm = st.checkbox("Confermo di voler eliminare questo viaggio")

if st.button("❌ Elimina viaggio", disabled=not confirm):
    collection.delete_one({"_id": selected_id})
    st.success("Viaggio eliminato correttamente 🗑️")
    st.rerun()

st.divider()
st.header("✏️ Modifica un viaggio")

edit_labels = df.apply(
    lambda r: f"{r['Destinazione']} ({r['Periodo']})",
    axis=1
)

selected_edit = st.selectbox(
    "Seleziona il viaggio da modificare",
    options=edit_labels,
    key="edit_select"
)
row = df.loc[edit_labels == selected_edit].iloc[0]

priority_options = ["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"]
current_priority = normalize_priority(row["Priorità"])

budget_options = ["€", "€€", "€€€"]
current_budget = row.get("Budget", "€")

with st.form("edit_trip"):
    destinazione = st.text_input(
        "Destinazione *",
        value=row["Destinazione"]
    )

    col1, col2 = st.columns(2)
    with col1:
        durata = st.number_input(
            "Durata media (giorni)",
            min_value=1,
            step=1,
            value=int(row["Durata (giorni)"]) if pd.notna(row["Durata (giorni)"]) else 1
        )

    with col2:
        priorità_vis = st.selectbox(
            "Priorità",
            options=priority_options,
            index=priority_options.index(current_priority)
        )

    periodo = st.text_input(
        "Periodo migliore (separato da virgole)",
        value=row["Periodo"]
    )

    budget = st.selectbox(
        "Budget (€)",
        options=budget_options,
        index=budget_options.index(current_budget)
    )

    note = st.text_area(
        "Note",
        value=row["Note"]
    )

    submitted_edit = st.form_submit_button("💾 Salva modifiche")

if submitted_edit:
    periodo = [
        p.strip() for p in periodo.split(",") if p.strip()
    ]

    update = {
        "destinazione": destinazione,
        "durata_media_giorni": int(durata),
        "periodo_migliore": periodo,
        "budget": budget,
        "priorità": priorità_vis,
        "note": note,
    }

    collection.update_one(
        {"_id": row["_id"]},
        {"$set": update}
    )

    st.success("Viaggio aggiornato correttamente ✨")
    st.rerun()

