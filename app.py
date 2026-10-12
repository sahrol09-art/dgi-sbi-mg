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
    st.subheader("Veuillez saisir votre Matricule (IM) et votre mot de passe")

    with st.form("login_form"):
        im_input = st.number_input("Immatriculation (IM) :", value=277485, step=1)
        password_input = st.text_input("Mot de passe :", type="password")
        submit_button = st.form_submit_button("Se connecter")

        if submit_button:
            response = supabase.table("utilisateur").select("*").eq("im", im_input).execute()
            data = response.data

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
                st.error("Matricule (IM) introuvable dans la base de données !")

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

    st.sidebar.title("👤 Profil Connecté")
    st.sidebar.write(f"**Nom :** {user.get('nom', '')}")
    st.sidebar.write(f"**IM :** {user.get('im', '')}")
    st.sidebar.write(f"**Fonction :** {user_fonction}")
    st.sidebar.write(f"**ID Bureau / UO :** {user_bureau_id}")
    
    if is_admin:
        st.sidebar.success("🔑 Accès Administrateur Activé")

    if st.sidebar.button("Se déconnecter"):
        st.session_state["authenticated"] = False
        st.session_state["user_info"] = None
        st.session_state["import_pending"] = None
        st.rerun()

    st.title("📊 Projet SBI - Dashboard de Gestion")
    st.write(f"Bienvenue, **{user.get('nom', '')}** !")

    tab_btt, tab_uo, tab_user = st.tabs(["📄 Données BTT", "📁 Structure Organisationnelle", "👥 Gestion des Utilisateurs"])

    # --- TAB BTT ---
    with tab_btt:
        st.subheader("📄 Gestion des Bordereaux de Transfert (BTT)")

        sub_tab1, sub_tab2, sub_tab3 = st.tabs(["📊 Consulter les Données", "📤 Importer un fichier Excel", "✍️ Saisie Manuelle"])

        # 1. Consultation des données
        with sub_tab1:
            if is_admin:
                st.write("### Liste globale de tous les BTT (Vue Administrateur)")
                btt_res = supabase.table("btt").select("*").order("id", desc=True).execute()
            else:
                st.write(f"### Liste des BTT enregistrés pour le bureau {user_bureau_id}")
                btt_res = supabase.table("btt").select("*").eq("uo_id", user_bureau_id).order("id", desc=True).execute()

            df_btt = pd.DataFrame(btt_res.data)
            if not df_btt.empty:
                st.dataframe(df_btt, use_container_width=True)
            else:
                st.info("Aucune donnée BTT disponible pour le moment.")

        # 2. Importation Excel
        with sub_tab2:
            st.write("### 📤 Importation de fichier Excel (BTT)")
            st.caption(f"Seules les lignes correspondant au bureau **{user_bureau_id}** seront importées.")
            
            uploaded_file = st.file_uploader("Choisissez un fichier Excel (.xlsx) :", type=["xlsx", "xls"], key="excel_btt")
            
            if uploaded_file is not None:
                try:
                    df_upload = pd.read_excel(uploaded_file, sheet_name="BTT")
                    df_upload.columns = df_upload.columns.astype(str).str.strip()

                    col_mapping = {
                        "UO_ID": "uo_id",
                        "Agent": "agent",
                        "UO": "uo",
                        "Année": "annee",
                        "Mois": "mois",
                        "N°_BTT": "num_btt",
                        "Lieu_dégagement (TG/TP; BFM;BP)": "lieu_degagement",
                        "Date_période_début": "date_periode_debut",
                        "Date_période_Fin": "date_periode_fin",
                        "Date_Dégagement": "date_degagement",
                        "Numéraire=Espèce (**12)": "numeraire_espece",
                        "Chèque (**22)": "cheque",
                        "Virement (*3)": "virement",
                        "BTT_Total": "btt_total",
                        "BTT_Cumul": "btt_cumul",
                        "OBSERVATION": "observation"
                    }
                    
                    df_upload = df_upload.rename(columns=col_mapping)

                    if "uo_id" not in df_upload.columns:
                        st.error("La colonne 'UO_ID' est introuvable dans le fichier Excel.")
                    else:
                        df_upload["uo_id"] = df_upload["uo_id"].astype(str).str.strip()

                        if is_admin:
                            df_user_data = df_upload.copy()
                        else:
                            df_user_data = df_upload[df_upload["uo_id"] == user_bureau_id].copy()

                        if df_user_data.empty:
                            st.warning(f"⚠️ Aucune donnée correspondant à l'ID Bureau = {user_bureau_id} n'a été trouvée dans ce fichier.")
                        else:
                            st.success(f"{len(df_user_data)} ligne(s) trouvée(s) pour l'importation.")
                            st.dataframe(df_user_data.head(), use_container_width=True)

                            if st.button("🚀 Lancer l'importation", key="btn_check_import"):
                                for d_col in ["date_periode_debut", "date_periode_fin", "date_degagement"]:
                                    if d_col in df_user_data.columns:
                                        df_user_data[d_col] = pd.to_datetime(df_user_data[d_col], errors='coerce').dt.strftime('%Y-%m-%d')

                                raw_records = df_user_data.to_dict(orient="records")
                                records = [clean_record_for_json(r) for r in raw_records]

                                existing_criteria = []
                                conflicts_found = False

                                for r in records:
                                    annee_val = r.get("annee")
                                    mois_val = r.get("mois")
                                    target_uo = r.get("uo_id", user_bureau_id)

                                    if annee_val is not None and mois_val is not None:
                                        check_res = supabase.table("btt").select("id")\
                                            .eq("uo_id", target_uo)\
                                            .eq("annee", int(annee_val))\
                                            .eq("mois", str(mois_val))\
                                            .execute()
                                        
                                        if check_res.data and len(check_res.data) > 0:
                                            conflicts_found = True
                                            crit = {"annee": int(annee_val), "mois": str(mois_val)}
                                            if crit not in existing_criteria:
                                                existing_criteria.append(crit)

                                if conflicts_found:
                                    st.session_state["import_pending"] = {
                                        "records": records,
                                        "existing_criteria": existing_criteria
                                    }
                                    st.rerun()
                                else:
                                    execute_btt_insert(records, user_bureau_id, action="insert")

                except Exception as e:
                    st.error(f"Erreur lors de la lecture du fichier : {e}")

            if st.session_state.get("import_pending"):
                pending = st.session_state["import_pending"]
                st.write("---")
                st.warning("⚠️ **Des données existent déjà pour la même période (Année / Mois) :**")
                for c in pending["existing_criteria"]:
                    st.write(f"- **Année :** {c['annee']} | **Mois :** {c['mois']}")

                st.write("### Choisissez une action :")
                col_act1, col_act2 = st.columns(2)

                with col_act1:
                    if st.button("🔄 Mettre à jour (Remplacer)"):
                        execute_btt_insert(
                            pending["records"], 
                            user_bureau_id, 
                            action="update", 
                            existing_criteria=pending["existing_criteria"]
                        )

                with col_act2:
                    if st.button("🛡️ Conserver les données existantes (Annuler)"):
                        st.session_state["import_pending"] = None
                        st.info("Importation annulée. Les données existantes sont conservées.")
                        st.rerun()

        # 3. Saisie Manuelle
        with sub_tab3:
            st.write("### ✍️ Formulaire de saisie d'un nouveau BTT")
            with st.form("form_btt_saisie"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    uo_id_in = st.text_input("ID Bureau / UO", value=user_bureau_id, disabled=not is_admin)
                    agent_in = st.text_input("Nom de l'Agent", value=user.get('nom', ''))
                    uo_in = st.text_input("Libellé du Bureau / UO")
                    annee_in = st.number_input("Année", value=2026, step=1)
                    mois_in = st.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])

                with col2:
                    num_btt_in = st.text_input("N° BTT")
                    lieu_in = st.text_input("Lieu de dégagement")
                    date_debut_in = st.date_input("Date début période", value=date.today())
                    date_fin_in = st.date_input("Date fin période", value=date.today())
                    date_deg_in = st.date_input("Date de dégagement", value=date.today())

                with col3:
                    numeraire_in = st.number_input("Numéraire / Espèce", value=0.0)
                    cheque_in = st.number_input("Chèque", value=0.0)
                    virement_in = st.number_input("Virement", value=0.0)
                    observation_in = st.text_area("Observation")

                submit_btt = st.form_submit_button("Enregistrer le BTT")

                if submit_btt:
                    btt_total_val = numeraire_in + cheque_in + virement_in
                    new_btt = {
                        "uo_id": uo_id_in,
                        "agent": agent_in,
                        "uo": uo_in,
                        "annee": int(annee_in),
                        "mois": mois_in,
                        "num_btt": num_btt_in,
                        "lieu_degagement": lieu_in,
                        "date_periode_debut": str(date_debut_in),
                        "date_periode_fin": str(date_fin_in),
                        "date_degagement": str(date_deg_in),
                        "numeraire_espece": numeraire_in,
                        "cheque": cheque_in,
                        "virement": virement_in,
                        "btt_total": btt_total_val,
                        "observation": observation_in
                    }
                    supabase.table("btt").insert(new_btt).execute()
                    st.success("Nouveau BTT enregistré avec succès !")
                    st.rerun()

    # --- TAB STRUCTURE UO / DIRECTION ---
    with tab_uo:
        st.subheader("📁 Structure Organisationnelle de la DGI")
        
        tab_dir, tab_dir_rat, tab_uo_list = st.tabs(["Directions", "Directions Rattachées / DRI", "Unités Opérationnelles (UO)"])
        
        with tab_dir:
            res_dir = supabase.table("direction").select("*").execute()
            st.dataframe(pd.DataFrame(res_dir.data), use_container_width=True)
            
        with tab_dir_rat:
            res_dir_rat = supabase.table("direction_rattachee").select("*").execute()
            st.dataframe(pd.DataFrame(res_dir_rat.data), use_container_width=True)
            
        with tab_uo_list:
            res_uo = supabase.table("uo").select("*").execute()
            st.dataframe(pd.DataFrame(res_uo.data), use_container_width=True)

    # --- TAB UTILISATEUR ---
    with tab_user:
        st.subheader("👥 Liste des Utilisateurs")
        if is_admin:
            user_response = supabase.table("utilisateur").select("*").execute()
            df_user = pd.DataFrame(user_response.data)
            if "user_psw" in df_user.columns:
                df_user = df_user.drop(columns=["user_psw"])
            if "password" in df_user.columns:
                df_user = df_user.drop(columns=["password"])
            st.dataframe(df_user, use_container_width=True)
        else:
            user_response = supabase.table("utilisateur").select("*").eq("bureau_id", user_bureau_id).execute()
            df_user = pd.DataFrame(user_response.data)
            if "user_psw" in df_user.columns:
                df_user = df_user.drop(columns=["user_psw"])
            st.dataframe(df_user, use_container_width=True)

if not st.session_state["authenticated"]:
    login()
else:
    main_app()
