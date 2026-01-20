import streamlit as st
import google.generativeai as genai
import pandas as pd
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Dieta Pro com IA", page_icon="💪", layout="wide")

# --- CONFIGURAÇÃO DA IA COM DEBUG ---
# Tenta configurar. Se der erro, avisa na tela lateral.
api_key_status = "OK"
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
    else:
        api_key_status = "FALTA_KEY"
except Exception as e:
    api_key_status = f"ERRO: {e}"

# --- FUNÇÃO DA IA (COM RELATÓRIO DE ERRO) ---
def calcular_alimentos_ia(lista_alimentos):
    if not lista_alimentos: return []
    
    # Prompt reforçado para garantir JSON correto
    prompt = f"""
    Atue como nutricionista preciso. Analise estes itens:
    {lista_alimentos}

    Retorne APENAS um JSON puro (sem ```json ou markdown) com este formato de lista:
    [
        {{"kcal": 100, "prot": 10, "carb": 20, "gord": 5}},
        {{"kcal": 50, "prot": 2, "carb": 5, "gord": 1}}
    ]
    Se não souber exatamente, estime com média de mercado.
    """
    try:
        response = model.generate_content(prompt)
        # Limpeza agressiva para evitar erros de formatação
        texto_limpo = response.text.strip()
        texto_limpo = texto_limpo.replace("```json", "").replace("```", "").replace("\n", "")
        return json.loads(texto_limpo)
    except Exception as e:
        st.error(f"Erro ao processar IA: {e}")
        st.write(f"Resposta bruta da IA (para debug): {response.text if 'response' in locals() else 'Sem resposta'}")
        return []

# --- INICIALIZAÇÃO DAS TABELAS ---
refeicoes_padrao = ["07:00 - Café da Manhã", "10:00 - Lanche da Manhã", "13:00 - Almoço", "16:00 - Lanche da Tarde", "20:00 - Jantar"]

if 'refeicoes' not in st.session_state:
    st.session_state.refeicoes = {}
    for ref in refeicoes_padrao:
        # Tabela inicial padrão
        st.session_state.refeicoes[ref] = pd.DataFrame(
            [{"Alimento": "", "Qtd": "", "Kcal": 0, "P(g)": 0, "C(g)": 0, "G(g)": 0}]
        )

# ==========================================
# PAINEL LATERAL (RESTAURADO DA VERSÃO PRO)
# ==========================================
with st.sidebar:
    st.header("👤 Seus Dados")
    
    # Check de API Key
    if api_key_status != "OK":
        st.error(f"⚠️ Problema na API Key: {api_key_status}")
        st.info("Verifique os 'Secrets' no painel do Streamlit.")

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
    
    # --- OBJETIVOS ---
    st.header("🎯 Meta & Calorias")
    objetivo = st.selectbox("Objetivo:", ["Definição (Perder)", "Manutenção", "Hipertrofia (Ganhar)"])

    ajuste_calorico = 0
    if "Perder" in objetivo:
        ajuste_input = st.number_input("Déficit Calórico (-):", value=500, step=50)
        ajuste_calorico = -ajuste_input
    elif "Ganhar" in objetivo:
        ajuste_calorico = st.number_input("Superávit Calórico (+):", value=300, step=50)

    # --- MACROS G/KG ---
    st.subheader("Configurar Macros (g/kg)")
    c1, c2, c3 = st.columns(3)
    # Valores padrão inteligentes baseados no objetivo
    def_p, def_c, def_g = (2.0, 4.0, 0.8)
    if "Perder" in objetivo: def_p, def_c = 2.2, 2.5
    
    prot_g_kg = c1.number_input("Prot", value=def_p, step=0.1, format="%.1f")
    carb_g_kg = c2.number_input("Carb", value=def_c, step=0.1, format="%.1f")
    gord_g_kg = c3.number_input("Gord", value=def_g, step=0.1, format="%.1f")

    # --- CÁLCULOS TOTAIS ---
    if sexo == "Masculino":
        tmb = 66.5 + (13.75 * peso) + (5.003 * altura) - (6.75 * idade)
    else:
        tmb = 655.1 + (9.563 * peso) + (1.850 * altura) - (4.676 * idade)
    
    gasto_total = tmb * fator
    meta_calorias = int(gasto_total + ajuste_calorico)
    
    # Metas em gramas
    meta_prot = int(peso * prot_g_kg)
    meta_carb = int(peso * carb_g_kg)
    meta_gord = int(peso * gord_g_kg)
    
    # Mostra Resumo na Lateral
    st.divider()
    st.metric("🔥 Meta Diária", f"{meta_calorias} kcal")
    st.caption(f"Macros: P:{meta_prot}g | C:{meta_carb}g | G:{meta_gord}g")
    
    # Botões de Ação
    st.divider()
    if st.button("🤖 Calcular Macros (IA)", type="primary"):
        with st.spinner("Analisando todas as refeições..."):
            for ref_nome, df in st.session_state.refeicoes.items():
                # Busca itens para calcular
                itens_calc = []
                indices = []
                for i, row in df.iterrows():
                    # Só calcula se tiver nome e Kcal for 0
                    if row["Alimento"] and str(row["Alimento"]).strip() != "" and (row["Kcal"] == 0 or pd.isna(row["Kcal"])):
                        qtd = row["Qtd"] if row["Qtd"] else "1 porção"
                        itens_calc.append(f"{qtd} de {row['Alimento']}")
                        indices.append(i)
                
                # Se achou itens, manda pra IA
                if itens_calc:
                    res = calcular_alimentos_ia(itens_calc)
                    # Preenche de volta
                    if res:
                        for j, dados in enumerate(res):
                            if j < len(indices): # Segurança
                                idx = indices[j]
                                df.at[idx, "Kcal"] = dados.get("kcal", 0)
                                df.at[idx, "P(g)"] = dados.get("prot", 0)
                                df.at[idx, "C(g)"] = dados.get("carb", 0)
                                df.at[idx, "G(g)"] = dados.get("gord", 0)
                        st.session_state.refeicoes[ref_nome] = df
        st.rerun()

    if st.button("🗑️ Limpar Tudo"):
        for ref in refeicoes_padrao:
             st.session_state.refeicoes[ref] = pd.DataFrame([{"Alimento": "", "Qtd": "", "Kcal": 0, "P(g)": 0, "C(g)": 0, "G(g)": 0}])
        st.rerun()

# ==========================================
# ÁREA PRINCIPAL (TABELAS DE REFEIÇÃO)
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
        
        # Tabela Editável
        df_editado = st.data_editor(
            st.session_state.refeicoes[ref_nome],
            num_rows="dynamic",
            use_container_width=True,
            key=f"editor_{ref_nome}",
            column_config={
                "Alimento": st.column_config.TextColumn("Alimento", width="large", placeholder="Ex: 2 Ovos"),
                "Qtd": st.column_config.TextColumn("Qtd", width="small", placeholder="Ex: 100g"),
                "Kcal": st.column_config.NumberColumn("Kcal", format="%d"),
                "P(g)": st.column_config.NumberColumn("P(g)", format="%d"),
                "C(g)": st.column_config.NumberColumn("C(g)", format="%d"),
                "G(g)": st.column_config.NumberColumn("G(g)", format="%d"),
            },
            hide_index=True
        )
        
        # Atualiza Session State
        st.session_state.refeicoes[ref_nome] = df_editado
        
        # Subtotais
        s_kcal = df_editado["Kcal"].sum()
        s_p = df_editado["P(g)"].sum()
        s_c = df_editado["C(g)"].sum()
        s_g = df_editado["G(g)"].sum()
        
        # Acumula Totais Gerais
        total_dia_kcal += s_kcal
        total_dia_prot += s_p
        total_dia_carb += s_c
        total_dia_gord += s_g
        
        # Barra de Total da Refeição (Cinza)
        st.markdown(
            f"""<div style="background-color: #f0f2f6; padding: 8px; border-radius: 5px; display: flex; justify-content: space-between; font-size: 14px;">
            <b>TOTAL REFEIÇÃO</b> <span>🔥 {int(s_kcal)} | P: {int(s_p)} | C: {int(s_c)} | G: {int(s_g)}</span></div>""", 
            unsafe_allow_html=True
        )
        st.divider()

# ==========================================
# RODAPÉ (COMPARATIVO COM A META DA BARRA LATERAL)
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
