def get_bureau_name(bureau_id: str) -> str:
    """Recherche automatique et intelligente du nom du bureau/direction à travers toutes les tables et colonnes possibles"""
    if not bureau_id:
        return "Non spécifié"
    
    clean_id = str(bureau_id).strip()
    
    try:
        # 1. Tadiavina ao amin'ny tabilao UO (Unité Opérationnelle)
        for id_col in ["ID_UO", "uo_id", "id_uo"]:
            for name_col in ["Libelle_UO", "uo", "libelle_uo", "libelle", "nom"]:
                try:
                    res = supabase.table("uo").select(name_col).eq(id_col, clean_id).execute()
                    if res.data and len(res.data) > 0:
                        val = res.data[0].get(name_col)
                        if val and str(val).strip():
                            return str(val).strip()
                except Exception:
                    continue
        
        # 2. Tadiavina ao amin'ny Direction Rattachée
        for id_col in ["direction_rattache_id", "id_direction_rattachee", "Direction_ratache_ID"]:
            for name_col in ["direction_ratache", "direction_rattachee", "libelle", "nom"]:
                try:
                    res = supabase.table("direction_rattachee").select(name_col).eq(id_col, clean_id).execute()
                    if res.data and len(res.data) > 0:
                        val = res.data[0].get(name_col)
                        if val and str(val).strip():
                            return str(val).strip()
                except Exception:
                    continue
                
        # 3. Tadiavina ao amin'ny tabilao Direction
        for id_col in ["direction_id", "id_direction"]:
            for name_col in ["direction", "libelle", "nom"]:
                try:
                    res = supabase.table("direction").select(name_col).eq(id_col, clean_id).execute()
                    if res.data and len(res.data) > 0:
                        val = res.data[0].get(name_col)
                        if val and str(val).strip():
                            return str(val).strip()
                except Exception:
                    continue

        # 4. Tadiavina ao amin'ny tabilao Ministère
        for id_col in ["ministere_id", "id_ministere"]:
            for name_col in ["ministere", "libelle", "nom"]:
                try:
                    res = supabase.table("ministere").select(name_col).eq(id_col, clean_id).execute()
                    if res.data and len(res.data) > 0:
                        val = res.data[0].get(name_col)
                        if val and str(val).strip():
                            return str(val).strip()
                except Exception:
                    continue
    except Exception:
        pass
        
    return clean_id
