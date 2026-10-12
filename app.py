import streamlit as st
import pandas as pd
import numpy as np
import math
from supabase import create_client, Client
from datetime import date

# Configuration de la page Streamlit
st.set_page_config(page_title="Projet SBI - DGI Madagascar", page_icon="🔐", layout="wide")

# Connexion à Supabase
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# Variables de session
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "user_info" not in st.session_state:
    st.session_state["user_info"] = None
if "import_pending" not in st.session_state:
    st.session_state["import_pending"] = None

def get_bureau_name(bureau_id: str) -> str:
    """Récupère le nom du bureau / UO à partir de son ID"""
    if not bureau_id:
        return "Non spécifié"
    
    # 1. Chercher d'abord dans la table UO
    res_uo = supabase.table("uo").select("uo").eq("uo_id", bureau_id).execute()
    if res_uo.data and len(res_uo.data) > 0:
        return res_uo.data[0].get("uo", bureau_id)
    
    # 2. Chercher dans direction_rattachee si non trouvé dans UO
    res_dr = supabase.table("direction_rattachee").select("direction_ratache").eq("direction_rattache_id", bureau_id).execute()
    if res_dr.data and len(res_dr.data) > 0:
        return res_dr.data[0].get("direction_ratache", bureau_id)
        
    return bureau_id

def clean_record_for_json(record):
    """Nettoie les valeurs NaN, float invalides et adapte les types pour Supabase"""
    cleaned = {}
    int_cols = ["annee", "num_btt"]
    
    for k, v in record.items():
        if pd.isna(v) or v is None:
            cleaned[k] = None
        elif k in int_cols:
            try:
                cleaned[k] = int(float(v))
            except (ValueError, TypeError):
                cleaned[k] = None
        elif k == "mois":
            if isinstance(v, (float, int, np.number)):
                try:
                    cleaned[k] = str(int(float(v)))
                except (ValueError, TypeError):
                    cleaned[k] = str(v)
            else:
                cleaned[k] = str(v).strip()
        elif isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            cleaned[k] = None
        elif isinstance(v, (int, np.integer)):
            cleaned[k] = int(v)
        elif isinstance(v, (float, np.floating)):
            cleaned[k] = float(v)
        else:
            cleaned[k] = str(v).strip()
            
    return cleaned

def login():
    st.title("🔐 Projet SBI - Page de Connexion")
    st.subheader("Veuillez saisir votre Identifiant (Login ou IM) et votre mot de passe")

    with st.form("login_form"):
        login_input = st.text_input("Identifiant (Login ou IM) :", value="277485")
        password_input = st.text_input("Mot de passe :", type="password")
        submit_button = st.form_submit_button("Se connecter")

        if submit_button:
            clean_input = login_input.strip()
            data = []
            
            # 1. Recherche par user_login
            resp_login = supabase.table("utilisateur").select("*").eq("user_login", clean_input).execute()
            if resp_login.data and len(resp_login.data) > 0:
                data = resp_login.data
            else:
                # 2. Recherche par IM s'il s'agit d'un nombre
                try:
                    im_val = int(clean_input)
                    resp_im = supabase.table("utilisateur").select("*").eq("im", im_val).execute()
                    if resp_im.data and len(resp_im.data) > 0:
                        data = resp_im.data
                except ValueError:
                    pass

            if data and len(data) > 0:
                user = data[0]
                if user.get("user_psw") == password_input or user.get("password") == password_input:
                    st.session_state["authenticated"] = True
                    st.session_state["user_info"] = user
                    st.success("Connexion réussie !")
                    st.rerun()
                else:
                    st.error("Mot de passe incorrect !")
            else:
                st.error("Identifiant introuvable dans la base de données !")

def execute_btt_insert(records_to_insert, user_bureau, action="insert", existing_criteria=None):
    try:
        if action == "update" and existing_criteria:
            for crit in existing_criteria:
                supabase.table("btt").delete()\
                    .eq("uo_id", user_bureau)\
                    .eq("annee", crit["annee"])\
                    .eq("mois", crit["mois"])\
                    .execute()

        supabase.table("btt").insert(records_to_insert).execute()
        st.success(f"✅ Importation réussie pour le bureau {user_bureau} !")
        st.session_state["import_pending"] = None
        st.rerun()
    except Exception as e:
        st.error(f"Une erreur est survenue lors de l'enregistrement : {e}")

def main_app():
    user = st.session_state["user_info"]
    user_bureau_id = str(user.get('bureau_id', user.get('id_uo', ''))).strip()
    user_fonction = str(user.get('fonction', '')).strip()
    is_admin = (user_fonction.lower() == 'admin')

    # Récupération automatique du nom du bureau
    bureau_name = get_bureau_name(user_bureau_id)

    # --- MENU LATÉRAL (PROFIL CONNECTÉ) ---
    st.sidebar.title("👤 Profil Connecté")
    st.sidebar.write(f"**Nom :** {user.get('nom', '')}")
    st.sidebar.write(f"**Bureau / UO :** {bureau_name}")
    st.sidebar.write(f"**Code Bureau :** {user_bureau_id}")
    st.sidebar.write(f"**Fonction :** {user_fonction}")
    
    if is_admin:
        st.sidebar.success("🔑 Accès Administrateur Activé")

    if st.sidebar.button("Se déconnecter"):
        st.session_state["authenticated"] = False
