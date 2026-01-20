import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import re
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Dieta Pro", page_icon="🥗", layout="wide")

# --- CONFIGURAÇÃO DA IA ---
api_key_status = "OK"
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        # VOLTAMOS PARA O PRO (Funciona em todas as versões)
        model = genai.GenerativeModel('gemini-pro')
    else:
        api_key_status = "FALTA_KEY"
except Exception as e:
    api_key_status = f"ERRO CONFIG: {e}"

# --- FUNÇÃO DA IA (COM LOG VISUAL) ---
def calcular_alimentos_ia(lista_alimentos):
    if not lista_alimentos: return []
    
    # Prompt simplificado para evitar erros
    prompt = f"""
    Nutricionista: analise {lista_alimentos}.
    Responda APENAS um JSON (lista de objetos). 
    Exemplo: [{{"kcal": 100, "prot": 10, "carb": 20, "gord": 5}}]
    """
    try:
        response = model.generate_content(prompt)
        texto = response.text
        
        # Limpeza robusta do texto
        limpo = texto.replace("```json", "").replace("```", "").strip()
        # Se tiver texto extra antes ou depois, tenta pegar só o que parece JSON
        if "[" in limpo and "]" in limpo:
            inicio = limpo.find("[")
            fim = limpo.rfind("]") + 1
            limpo = limpo[inicio:fim]
            
        return json.loads(limpo)
    except Exception as e:
        st.error(f"Erro ao ler resposta da IA: {e}")
        return []

# --- INICIALIZAÇÃO ---
refeicoes_padrao = ["07:00 - Café da Manhã", "10:00 - Lanche da Manhã", "13:00 - Almoço", "16:00 - Lanche da Tarde", "20:00 - Jantar"]

if 'refeicoes' not in st.session_state:
    st.session_state.refeicoes = {}
    for ref in refeicoes_padrao:
        st.session_state.refeicoes[ref] = pd.DataFrame(
            [{"Alimento": "", "Qtd": "", "Kcal": 0, "P(g)": 0, "C(g)": 0, "G(g)": 0}]
        )

# ==========================================
# BARRA LATERAL (DO JEITO QUE VOCÊ GOSTA)
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
    
    atividade_opcoes = {"Sedentário (1.2)": 1.2, "Leve (1.375)": 1.375, "Moderado (1.55)": 1.55, "Intenso (1.725)": 1.725}
    atv_sel = st.selectbox("Nível de Atividade:", list(atividade_opcoes.keys()), index=2)
    fator = atividade_opcoes[atv_sel]
    
    st.divider()
    
    st.header("🎯 Meta & Calorias")
    objetivo = st.selectbox("Objetivo:", ["Definição (Perder)", "Manutenção", "Hipertrofia (Ganhar)"])

    ajuste = 0
    if "Perder" in objetivo: ajuste = -st.number_input("Déficit (-):", value=500, step=50)
    elif "Ganhar" in objetivo: ajuste = st.number_input("Superávit (+):", value=300, step=50)

    st.subheader("Configurar Macros (g/kg)")
    c1, c2, c3 = st.columns(3)
    prot_g_kg = c1.number_input("Prot", value=2.0, step=0.1)
    carb_g_kg = c2.number_input("Carb", value=4.0, step=0.1)
    gord_g_kg = c3.number_input("Gord", value=0.8, step=0.1)

    tmb_val = 66.5 + (13.75 * peso) + (5.003 * altura) - (6.75 * idade) if sexo == "Masculino" else 655.1 + (9.563 * peso) + (1.850 * altura) - (4.676 * idade)
    meta_calorias = int((tmb_val * fator) + ajuste)
    meta_prot = int(peso * prot_g_kg)
    meta_carb = int(peso * carb_g_kg)
    meta_gord = int(peso * gord_g_kg)
    
    st.divider()
    st.metric("🔥 Meta Diária", f"{meta_calorias} kcal")
    
    st.divider()
    
    # --- BOTÃO DE CÁLCULO (LÓGICA BLINDADA) ---
    if st.button("🤖 Calcular Macros (IA)", type="primary"):
        if api_key_status != "OK":
            st.error("ERRO: Configure a API Key nos Secrets!")
        else:
            # STATUS AZUL NA TELA PARA VOCÊ VER O QUE ESTÁ ACONTECENDO
            status = st.status("Iniciando Nutricionista IA...", expanded=True)
            try:
                total_itens = 0
                for ref_nome, df in st.session_state.refeicoes.items():
                    itens_calc = []
                    indices = []
                    
                    # Varre a tabela procurando itens sem Kcal
                    for i, row in df.iterrows():
                        tem_nome = row["Alimento"] and str(row["Alimento"]).strip() != ""
                        # Verifica se Kcal é zero/vazio de forma segura
                        kcal = pd.to_numeric(row["Kcal"], errors='coerce')
                        if pd.isna(kcal): kcal = 0
                        
                        if tem_nome and kcal == 0:
                            qtd = row["Qtd"] if row["Qtd"] else "1 porção"
                            itens_calc.append(f"{qtd} de {row['Alimento']}")
                            indices.append(i)
                    
                    if itens_calc:
                        status.write(f"Refeição {ref_nome}: Enviando {len(itens_calc)} itens para IA...")
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
                            total_itens += len(res)
                        else:
                            status.warning(f"A IA não conseguiu ler os itens de {ref_nome}.")
                            
                if total_itens > 0:
                    status.update(label="✅ Sucesso! Cardápio calculado.", state="complete", expanded=False)
                    time.sleep(1) # Dá tempo de ver a mensagem antes de atualizar
                    st.rerun()
                else:
                    status.update(label="⚠️ Nenhum item novo encontrado para calcular.", state="error")
            except Exception as e:
                status.update(label="❌ Erro fatal no cálculo", state="error")
                st.error(f"Detalhe do erro: {e}")

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
        st.markdown(f"### {ref_nome.split('-')[0]}")
    with col_tabela:
        st.markdown(f"**{ref_nome.split('-')[1]}**")
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
        
        s_k = df_editado["Kcal"].sum(); s_p = df_editado["P(g)"].sum(); s_c = df_editado["C(g)"].sum(); s_g = df_editado["G(g)"].sum()
        total_dia_kcal += s_k; total_dia_prot += s_p; total_dia_carb += s_c; total_dia_gord += s_g
        
        st.caption(f"Total: 🔥 {int(s_k)} | P: {int(s_p)} | C: {int(s_c)} | G: {int(s_g)}")
        st.divider()

# Rodapé
st.subheader("📊 Resumo do Dia")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Kcal", f"{int(total_dia_kcal)}", f"{int(total_dia_kcal - meta_calorias)}")
c2.metric("Prot", f"{int(total_dia_prot)}g", f"{int(total_dia_prot - meta_prot)}")
c3.metric("Carb", f"{int(total_dia_carb)}g", f"{int(total_dia_carb - meta_carb)}")
c4.metric("Gord", f"{int(total_dia_gord)}g", f"{int(total_dia_gord - meta_gord)}")
