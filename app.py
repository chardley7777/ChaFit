import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import re

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Dieta Pro com IA", page_icon="💪", layout="wide")

# --- CONFIGURAÇÃO DA IA ---
api_key_status = "OK"
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        # MUDANÇA AQUI: Trocamos para 'gemini-pro' que é mais compatível
        model = genai.GenerativeModel('gemini-pro')
    else:
        api_key_status = "FALTA_KEY"
except Exception as e:
    api_key_status = f"ERRO: {e}"

# --- FUNÇÃO DA IA (MAIS ROBUSTA) ---
def calcular_alimentos_ia(lista_alimentos):
    if not lista_alimentos: return []
    
    prompt = f"""
    Atue como nutricionista. Analise: {lista_alimentos}
    
    Responda APENAS com um JSON (lista). Nada de texto extra.
    Formato:
    [
        {{"kcal": 100, "prot": 10, "carb": 20, "gord": 5}},
        {{"kcal": 50, "prot": 2, "carb": 5, "gord": 1}}
    ]
    """
    try:
        response = model.generate_content(prompt)
        texto = response.text
        
        # Limpeza avançada para garantir que pegamos só o JSON
        match = re.search(r'\[.*\]', texto, re.DOTALL)
        if match:
            texto_limpo = match.group(0)
            return json.loads(texto_limpo)
        else:
            # Fallback: tenta limpar crases de markdown
            texto_limpo = texto.replace("```json", "").replace("```", "").strip()
            # Se a IA respondeu texto puro, tentamos pegar o começo e fim da lista
            if "[" in texto_limpo and "]" in texto_limpo:
                start = texto_limpo.find("[")
                end = texto_limpo.rfind("]") + 1
                return json.loads(texto_limpo[start:end])
            return []
            
    except Exception as e:
        st.error(f"Erro na IA: {e}")
        return []

# --- INICIALIZAÇÃO DAS TABELAS ---
refeicoes_padrao = ["07:00 - Café da Manhã", "10:00 - Lanche da Manhã", "13:00 - Almoço", "16:00 - Lanche da Tarde", "20:00 - Jantar"]

if 'refeicoes' not in st.session_state:
    st.session_state.refeicoes = {}
    for ref in refeicoes_padrao:
        st.session_state.refeicoes[ref] = pd.DataFrame(
            [{"Alimento": "", "Qtd": "", "Kcal": 0, "P(g)": 0, "C(g)": 0, "G(g)": 0}]
        )

# ==========================================
# PAINEL LATERAL
# ==========================================
with st.sidebar:
    st.header("👤 Seus Dados")
    
    if api_key_status != "OK":
        st.error(f"⚠️ API Key: {api_key_status}")

    sexo = st.radio("Sexo:", ["Masculino", "Feminino"], horizontal=True)
    col_p, col_a, col_i = st.columns(3)
    peso = col_p.number_input("Peso (Kg):", value=70.0, format="%.1f")
    altura = col_a.number_input("Alt (cm):", value=175, step=1)
    idade = col_i.number_input("Idade:", value=30, step=1)
    
    atividade_opcoes = {
        "Sedentário (1.2)": 1.2,
        "Leve (1.375)": 1.375,
        "Moderado (1.55)": 1.55,
        "Intenso (1.725)": 1.725,
        "Extremo (1.9)": 1.9
    }
    atv_sel = st.selectbox("Nível de Atividade:", list(atividade_opcoes.keys()), index=2)
    fator = atividade_opcoes[atv_sel]
    
    st.divider()
    
    st.header("🎯 Meta & Calorias")
    objetivo = st.selectbox("Objetivo:", ["Definição (Perder)", "Manutenção", "Hipertrofia (Ganhar)"])

    ajuste_calorico = 0
    if "Perder" in objetivo:
        ajuste_input = st.number_input("Déficit Calórico (-):", value=500, step=50)
        ajuste_calorico = -ajuste_input
    elif "Ganhar" in objetivo:
        ajuste_calorico = st.number_input("Superávit Calórico (+):", value=300, step=50)

    st.subheader("Configurar Macros (g/kg)")
    c1, c2, c3 = st.columns(3)
    def_p, def_c, def_g = (2.0, 4.0, 0.8)
    if "Perder" in objetivo: def_p, def_c = 2.2, 2.5
    
    prot_g_kg = c1.number_input("Prot", value=def_p, step=0.1, format="%.1f")
    carb_g_kg = c2.number_input("Carb", value=def_c, step=0.1, format="%.1f")
    gord_g_kg = c3.number_input("Gord", value=def_g, step=0.1, format="%.1f")

    if sexo == "Masculino":
        tmb = 66.5 + (13.75 * peso) + (5.003 * altura) - (6.75 * idade)
    else:
        tmb = 655.1 + (9.563 * peso) + (1.850 * altura) - (4.676 * idade)
    
    gasto_total = tmb * fator
    meta_calorias = int(gasto_total + ajuste_calorico)
    
    meta_prot = int(peso * prot_g_kg)
    meta_carb = int(peso * carb_g_kg)
    meta_gord = int(peso * gord_g_kg)
    
    st.divider()
    st.metric("🔥 Meta Diária", f"{meta_calorias} kcal")
    st.caption(f"Macros: P:{meta_prot}g | C:{meta_carb}g | G:{meta_gord}g")
    
    st.divider()
    
    # --- BOTÃO DE CÁLCULO ---
    if st.button("🤖 Calcular Macros (IA)", type="primary"):
        if api_key_status != "OK":
            st.error("Configure sua API KEY nos Secrets primeiro!")
        else:
            with st.spinner("Analisando cardápio..."):
                for ref_nome, df in st.session_state.refeicoes.items():
                    itens_calc = []
                    indices = []
                    
                    for i, row in df.iterrows():
                        # Lógica segura para detectar campos vazios
                        tem_texto = row["Alimento"] and str(row["Alimento"]).strip() != ""
                        # Verifica se Kcal é zero, None, ou string vazia
                        try:
                            kcal_val = float(row["Kcal"])
                        except:
                            kcal_val = 0
                            
                        kcal_zerada = (kcal_val == 0)
                        
                        if tem_texto and kcal_zerada:
                            qtd = row["Qtd"] if row["Qtd"] else "1 porção"
                            itens_calc.append(f"{qtd} de {row['Alimento']}")
                            indices.append(i)
                    
                    if itens_calc:
                        res = calcular_alimentos_ia(itens_calc)
                        if res:
                            for j, dados in enumerate(res):
                                if j < len(indices):
                                    idx = indices[j]
                                    df.at[idx, "Kcal"] = dados.get("kcal", 0)
                                    df.at[idx, "P(g)"] = dados.get("prot", 0)
                                    df.at[idx, "C(g)"] = dados.get("carb", 0)
                                    df.at[idx, "G(g)"] = dados.get("gord", 0)
                            st.session_state.refeicoes[ref_nome] = df
                            
            st.success("Calculado!")
            st.rerun()

    if st.button("🗑️ Limpar Tudo"):
        for ref in refeicoes_padrao:
             st.session_state.refeicoes[ref] = pd.DataFrame([{"Alimento": "", "Qtd": "", "Kcal": 0, "P(g)": 0, "C(g)": 0, "G(g)": 0}])
        st.rerun()

# ==========================================
# ÁREA PRINCIPAL
# ==========================================
st.title("📋 Planejador de Dieta")

total_dia_kcal = 0
total_dia_prot = 0
total_dia_carb = 0
total_dia_gord = 0

for ref_nome in refeicoes_padrao:
    col_tempo, col_tabela = st.columns([1, 6])
    
    with col_tempo:
        st.write("")
        st.write("")
        horario = ref_nome.split("-")[0]
        st.markdown(f"### {horario}")
    
    with col_tabela:
        st.markdown(f"**{ref_nome.split('-')[1]}**")
        
        # Tabela sem placeholder nas colunas para evitar bug
        df_editado = st.data_editor(
            st.session_state.refeicoes[ref_nome],
            num_rows="dynamic",
            use_container_width=True,
            key=f"editor_{ref_nome}",
            column_config={
                "Alimento": st.column_config.TextColumn("Alimento", width="large"),
                "Qtd": st.column_config.TextColumn("Qtd", width="small"),
                "Kcal": st.column_config.NumberColumn("Kcal", format="%d"),
                "P(g)": st.column_config.NumberColumn("P(g)", format="%d"),
                "C(g)": st.column_config.NumberColumn("C(g)", format="%d"),
                "G(g)": st.column_config.NumberColumn("G(g)", format="%d"),
            },
            hide_index=True
        )
        
        st.session_state.refeicoes[ref_nome] = df_editado
        
        s_kcal = df_editado["Kcal"].sum()
        s_p = df_editado["P(g)"].sum()
        s_c = df_editado["C(g)"].sum()
        s_g = df_editado["G(g)"].sum()
        
        total_dia_kcal += s_kcal
        total_dia_prot += s_p
        total_dia_carb += s_c
        total_dia_gord += s_g
        
        st.markdown(
            f"""<div style="background-color: #f0f2f6; padding: 8px; border-radius: 5px; display: flex; justify-content: space-between; font-size: 14px;">
            <b>TOTAL REFEIÇÃO</b> <span>🔥 {int(s_kcal)} | P: {int(s_p)} | C: {int(s_c)} | G: {int(s_g)}</span></div>""", 
            unsafe_allow_html=True
        )
        st.divider()

# ==========================================
# RODAPÉ
# ==========================================
st.subheader("📊 Resultado do Dia vs Meta")

c1, c2, c3, c4 = st.columns(4)

def delta_str(real, meta, suf=""):
    d = int(real - meta)
    return f"{d}{suf}"

c1.metric("Calorias", f"{int(total_dia_kcal)}", delta_str(total_dia_kcal, meta_calorias))
c2.metric("Proteína", f"{int(total_dia_prot)}g", delta_str(total_dia_prot, meta_prot, "g"))
c3.metric("Carboidrato", f"{int(total_dia_carb)}g", delta_str(total_dia_carb, meta_carb, "g"))
c4.metric("Gordura", f"{int(total_dia_gord)}g", delta_str(total_dia_gord, meta_gord, "g"))

st.write("Aderência à Meta Calórica:")
progresso = total_dia_kcal / meta_calorias if meta_calorias > 0 else 0
st.progress(min(progresso, 1.0))
