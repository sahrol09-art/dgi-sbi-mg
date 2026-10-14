import streamlit as st
import pandas as pd
import numpy as np
import math
from supabase import create_client, Client
from datetime import date
import qrcode
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# Configuration de la page Streamlit
st.set_page_config(page_title="SBI - DGI Madagascar", page_icon="🏛️", layout="wide")

# CSS personnalisé pour un design 3D et des boutons bien visibles
st.markdown("""
<style>
    .title-3d {
        font-size: 34px;
        font-weight: 900;
        text-align: center;
        background: linear-gradient(135deg, #1b5e20 0%, #fbc02d 50%, #b71c1c 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 3px 3px 6px rgba(0,0,0,0.25);
        margin-bottom: 10px;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
        background-color: #f8fafc;
        border: 2px solid #cbd5e1;
        color: #1e293b;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #e2e8f0;
        border-color: #1b5e20;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        transform: translateY(-2px);
    }
</style>
""", unsafe_allow_html=True)

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
    if not bureau_id:
        return "Non spécifié"
    clean_id = str(bureau_id).strip()
    hyphen_count = clean_id.count("-")
    try:
        if hyphen_count == 0:
            res = supabase.table("ministere").select("ministere").eq("ministere_id", clean_id).execute()
            if res.data and len(res.data) > 0:
                val = res.data[0].get("ministere")
                if val:
                    return str(val).strip()
        elif hyphen_count == 1:
            res = supabase.table("direction").select("direction").eq("direction_id", clean_id).execute()
            if res.data and len(res.data) > 0:
                val = res.data[0].get("direction")
                if val:
                    return str(val).strip()
        elif hyphen_count == 2:
            for id_col in ["direction_rattache_id", "id_direction_rattachee", "Direction_ratache_ID"]:
                for name_col in ["direction_ratache", "direction_rattachee"]:
                    try:
                        res = supabase.table("direction_rattachee").select(name_col).eq(id_col, clean_id).execute()
                        if res.data and len(res.data) > 0:
                            val = res.data[0].get(name_col)
                            if val:
                                return str(val).strip()
                    except Exception:
                        continue
        elif hyphen_count >= 3:
            for id_col in ["ID_UO", "uo_id", "id_uo"]:
                for name_col in ["Libelle_UO", "uo", "libelle_uo"]:
                    try:
                        res = supabase.table("uo").select(name_col).eq(id_col, clean_id).execute()
                        if res.data and len(res.data) > 0:
                            val = res.data[0].get(name_col)
                            if val:
                                return str(val).strip()
                    except Exception:
                        continue
    except Exception:
        pass
    return clean_id

def clean_record_for_json(record):
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

def generate_printable_qr_code(url: str):
    """Mamorona sary Code QR miaraka amin'ny adiresy feno eo ambaniny mba hatao printy"""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    
    # Manao taratasy fotsy lehibe kokoa hametrahana ilay adiresy eo ambany
    qr_width, qr_height = qr_img.size
    padding = 40
    text_height = 50
    total_height = qr_height + text_height + padding
    
    new_img = Image.new('RGB', (qr_width + (padding * 2), total_height), 'white')
    new_img.paste(qr_img, (padding, padding))
    
    # Manatsika ilay URL eo ambany
    draw = ImageDraw.Draw(new_img)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
        
    draw.text((padding, qr_height + padding + 15), url, fill="black", font=font)
    
    buffered = BytesIO()
    new_img.save(buffered, format="PNG")
    return buffered.getvalue()

def login():
    st.title("🔐 Page de Connexion")
    with st.form("login_form"):
        login_input = st.text_input("Identifiant (Login ou IM) :", value="277485")
        password_input = st.text_input("Mot de passe :", type="password")
        submit_button = st.form_submit_button("Se connecter")

        if submit_button:
            clean_input = login_input.strip()
            data = []
            resp_login = supabase.table("utilisateur").select("*").eq("user_login", clean_input).execute()
            if resp_login.data and len(resp_login.data) > 0:
                data = resp_login.data
            else:
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

def main_app():
    user = st.session_state["user_info"]
    user_bureau_id = str(user.get('bureau_id') or user.get('id_uo') or '').strip()
    user_fonction = str(user.get('fonction', '')).strip()
    is_admin = (user_fonction.lower() == 'admin')

    bureau_name = get_bureau_name(user_bureau_id)

    # --- VOLET GAUCHE (MENU STRUCTURÉ PROPRE - CODE QR VOALOHANY) ---
    st.sidebar.title("📌 Navigation")
    
    menu_choice = st.sidebar.radio(
        "Sélectionnez un module :",
        [
            "📱 Code QR", 
            "👤 Profil connecté", 
            "📁 Structure organisationnelle", 
            "👥 Gestion des utilisateurs", 
            "💰 Recette", 
            "💳 Virement", 
            "📊 BAR", 
            "📉 Trop perçu", 
            "📋 BTR", 
            "📄 BTT", 
            "📑 EDS", 
            "⚖️ BOD",
            "🔍 Contrôle 1er niveau - Rapport",
            "📈 Contrôle 1er niveau - Suivi et recommandation",
            "🔎 Contrôle 2ème niveau - Rapport",
            "📉 Contrôle 2ème niveau - Suivi et recommandation"
        ]
    )

    st.sidebar.write("---")
    st.sidebar.subheader("👤 Session Info")
    st.sidebar.write(f"**Nom :** {user.get('nom', '')}")
    st.sidebar.write(f"**Bureau / UO :** {bureau_name}")
    st.sidebar.write(f"**Code Bureau :** {user_bureau_id}")
    st.sidebar.write(f"**Fonction :** {user_fonction}")
    
    if is_admin:
        st.sidebar.success("🔑 Admin Actif")

    if st.sidebar.button("Se déconnecter"):
        st.session_state["authenticated"] = False
        st.session_state["user_info"] = None
        st.session_state["import_pending"] = None
        st.rerun()

    # --- HEADER AVEC LES LOGOS (TAILLE 180px) ET LE TITRE 3D ---
    col_logo1, col_title, col_logo2 = st.columns([1, 4, 1])
    
    with col_logo1:
        try:
            st.image("republique.jpg", width=180)
        except Exception:
            st.markdown("🇲🇬 **Madagascar**")
            
    with col_title:
        st.markdown('<div class="title-3d">SERVICE DE LA BRIGADE D\'INSPECTION</div>', unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; font-size: 16px; color: #475569;'>Bienvenue, <b>{user.get('nom', '')}</b> — <i>{bureau_name}</i></p>", unsafe_allow_html=True)
        
    with col_logo2:
        try:
            st.image("dgi.jpg", width=180)
        except Exception:
            st.markdown("🏛️ **DGI**")

    st.write("---")

    # --- GESTION DES AFFICHAGES SELON LE MENU CHOISI ---

    if "Code QR" in menu_choice:
        st.subheader("📱 Code QR de l'Application")
        st.write("Scannez ce code QR avec un téléphone mobile ou téléchargez la version imprimable contenant l'adresse complète.")
        app_url = "https://dgi-sbi-mg-z9ussubgf28w7rderjjchy.streamlit.app"
        
        printable_qr_bytes = generate_printable_qr_code(app_url)
        
        st.image(printable_qr_bytes, width=320)
        
        st.download_button(
            label="📥 Télécharger le Code QR pour Impression (PNG)",
            data=printable_qr_bytes,
            file_name="QR_Code_Printable_SBI.png",
            mime="image/png"
        )
        st.code(app_url, language="text")

    elif menu_choice.startswith("👤"):
        st.subheader("👤 Profil Connecté")
        st.write(f"* **Nom :** {user.get('nom', '')}")
        st.write(f"* **Bureau / UO :** {bureau_name}")
        st.write(f"* **Code Bureau :** {user_bureau_id}")
        st.write(f"* **Fonction :** {user_fonction}")
        st.write(f"* **IM :** {user.get('im', 'Non spécifié')}")

    elif menu_choice.startswith("📁"):
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

    elif menu_choice.startswith("👥"):
        st.subheader("👥 Gestion des Utilisateurs")
        if is_admin:
            user_response = supabase.table("utilisateur").select("*").execute()
            df_user = pd.DataFrame(user_response.data)
            for pwd_col in ["user_psw", "password"]:
                if pwd_col in df_user.columns:
                    df_user = df_user.drop(columns=[pwd_col])
            st.dataframe(df_user, use_container_width=True)
        else:
            user_response = supabase.table("utilisateur").select("*").eq("bureau_id", user_bureau_id).execute()
            df_user = pd.DataFrame(user_response.data)
            st.dataframe(df_user, use_container_width=True)

    elif "Recette" in menu_choice:
        st.subheader("💰 Suivi des Recettes")
        st.caption("Période entre 2 dates, mode de paiement")
        col1, col2 = st.columns(2)
        with col1:
            st.date_input("Date début", value=date.today())
        with col2:
            st.date_input("Date fin", value=date.today())
        st.selectbox("Mode de paiement", ["Tous", "Espèce", "Chèque", "Virement"])
        st.info("Espace de consultation et d'importation des recettes.")

    elif "Virement" in menu_choice:
        st.subheader("💳 Gestion des Virements")
        st.caption("Période entre 2 dates (importation de donnée)")
        col1, col2 = st.columns(2)
        with col1:
            st.date_input("Date début Virement", value=date.today())
        with col2:
            st.date_input("Date fin Virement", value=date.today())
        st.info("Espace dédié aux virements.")

    elif "BAR" in menu_choice:
        st.subheader("📊 Suivi BAR")
        st.caption("Période entre 2 dates (importation de donnée)")
        col1, col2 = st.columns(2)
        with col1:
            st.date_input("Date début BAR", value=date.today())
        with col2:
            st.date_input("Date fin BAR", value=date.today())
        st.info("Espace dédié au BAR.")

    elif "Trop perçu" in menu_choice:
        st.subheader("📉 Gestion des Trop perçus")
        st.caption("Période entre 2 dates (importation de donnée)")
        col1, col2 = st.columns(2)
        with col1:
            st.date_input("Date début Trop perçu", value=date.today())
        with col2:
            st.date_input("Date fin Trop perçu", value=date.today())
        st.info("Espace dédié aux trop perçus.")

    elif "BTR" in menu_choice:
        st.subheader("📋 Gestion des BTR")
        st.caption("Période entre 2 dates")
        col1, col2 = st.columns(2)
        with col1:
            st.date_input("Date début BTR", value=date.today())
        with col2:
            st.date_input("Date fin BTR", value=date.today())
        st.info("Espace dédié aux BTR.")

    elif "BTT" in menu_choice:
        st.subheader("📄 Gestion des Bordereaux de Transfert (BTT)")
        st.caption("Période entre 2 dates: BTT Espèce et Chèque (mitokana), BTT Virement (mitokana)")
        sub_tab1, sub_tab2, sub_tab3 = st.tabs(["📊 Consulter", "📤 Importer Excel", "✍️ Saisie Manuelle"])

        with sub_tab1:
            if is_admin:
                st.write("### Liste globale de tous les BTT")
                btt_res = supabase.table("btt").select("*").order("id", desc=True).execute()
            else:
                st.write(f"### Liste des BTT pour : **{bureau_name}**")
                btt_res = supabase.table("btt").select("*").eq("uo_id", user_bureau_id).order("id", desc=True).execute()

            df_btt = pd.DataFrame(btt_res.data)
            if not df_btt.empty:
                st.dataframe(df_btt, use_container_width=True)
            else:
                st.info("Aucune donnée BTT disponible.")

        with sub_tab2:
            st.write("### 📤 Importation de fichier Excel (BTT)")
            uploaded_file = st.file_uploader("Choisissez un fichier Excel (.xlsx) :", type=["xlsx", "xls"], key="excel_btt")
            if uploaded_file is not None:
                try:
                    df_upload = pd.read_excel(uploaded_file, sheet_name="BTT")
                    st.success("Fichier chargé avec succès.")
                    st.dataframe(df_upload.head(), use_container_width=True)
                except Exception as e:
                    st.error(f"Erreur : {e}")

        with sub_tab3:
            st.write("### ✍️ Saisie Manuelle BTT")
            with st.form("form_btt_saisie"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    uo_id_in = st.text_input("ID Bureau / UO", value=user_bureau_id, disabled=not is_admin)
                    agent_in = st.text_input("Nom de l'Agent", value=user.get('nom', ''))
                    uo_in = st.text_input("Libellé du Bureau / UO", value=bureau_name)
                    annee_in = st.number_input("Année", value=2026, step=1)
                    mois_in = st.selectbox("Mois", ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"])
                with c2:
                    num_btt_in = st.text_input("N° BTT")
                    lieu_in = st.text_input("Lieu de dégagement")
                    date_debut_in = st.date_input("Date début période", value=date.today())
                    date_fin_in = st.date_input("Date fin période", value=date.today())
                with c3:
                    numeraire_in = st.number_input("Numéraire / Espèce", value=0.0)
                    cheque_in = st.number_input("Chèque", value=0.0)
                    virement_in = st.number_input("Virement", value=0.0)
                    observation_in = st.text_area("Observation")

                if st.form_submit_button("Enregistrer le BTT"):
                    st.success("Enregistrement simulé avec succès !")

    elif "EDS" in menu_choice:
        st.subheader("📑 Suivi EDS")
        st.caption("Période entre 2 dates")
        col1, col2 = st.columns(2)
        with col1:
            st.date_input("Date début EDS", value=date.today())
        with col2:
            st.date_input("Date fin EDS", value=date.today())
        st.info("Espace dédié aux EDS.")

    elif "BOD" in menu_choice:
        st.subheader("⚖️ Balance des Opérations en Deniers (BOD)")
        st.info("Module BOD en cours de configuration.")

    elif "Contrôle 1er niveau" in menu_choice:
        st.subheader("🔍 Contrôle 1er Niveau")
        st.caption("Fichier PDF ou Word")
        st.file_uploader("Importer le rapport ou document de suivi :", type=["pdf", "docx", "doc"])

    elif "Contrôle 2ème niveau" in menu_choice:
        st.subheader("🔎 Contrôle 2ème Niveau")
        st.caption("Fichier PDF ou Word")
        st.file_uploader("Importer le rapport ou document de suivi :", type=["pdf", "docx", "doc"])

if not st.session_state["authenticated"]:
    login()
else:
    main_app()
