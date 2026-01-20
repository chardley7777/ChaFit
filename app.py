import streamlit as st
import pandas as pd
import json
import requests
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Dieta Pro", page_icon="🥗", layout="wide")

# --- FUNÇÃO DE CONEXÃO UNIVERSAL (TENTA VÁRIOS MODELOS) ---
def chamar_gemini_direto(prompt, api_key):
    # Lista de modelos para tentar (do mais novo para o mais antigo)
    modelos_para_tentar = [
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-1.0-pro",
        "gemini-pro"
    ]
    
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    erros_log = []

    for modelo in modelos_para_tentar:
        # Tenta conectar neste modelo específico
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            
            # Se funcionou (Código 200), para de tentar e retorna o resultado
            if response.status_code == 200:
                dados = response.json()
                texto_resposta = dados["candidates"][0]["content"]["parts"][0]["text"]
                
                # Limpa o JSON
                limpo = texto_resposta.replace("```json", "").replace("```", "").strip()
                if "[" in limpo and "]" in limpo:
                    inicio = limpo.find("[")
                    fim = limpo.rfind("]") + 1
                    limpo = limpo[inicio:fim]
                
                return {"sucesso": True, "dados": json.loads(limpo), "modelo_usado": modelo}
            else:
                # Se deu erro, guarda o motivo e tenta o próximo
                erros_log.append(f"{modelo}: {response.status_code}")
                continue
                
        except Exception as e:
            erros_log.append(f"{modelo}: Erro de conexão")
            continue

    # Se chegou aqui, todos falharam
    return {"sucesso": False, "erro": " | ".join(erros_log)}

# --- INICIALIZAÇÃO ---
refeicoes_padrao = ["07:00 - Café da Manhã", "10:00 - Lanche da Manhã", "13:00 - Almoço", "16:00 - Lanche da Tarde", "20:00 - Jantar"]

if 'refeicoes' not in st.session_state:
    st.session_state.refeicoes = {}
    for ref in refeicoes_padrao:
        st.session_state.refeicoes[ref] = pd.DataFrame(
            [{"Alimento": "", "Qtd": "", "Kcal": 0, "P(g)": 0, "C(g)": 0, "G(g)": 0}]
        )

# ==========================================
# BARRA LATERAL
# ==========================================
with st.sidebar:
    st.header("👤 Seus Dados")
    
    tem_chave = "GOOGLE_API_KEY" in st.secrets
    if not tem_chave:
        st.error("⚠️ Configure a API Key!")

    sexo = st.radio("Sexo:", ["Masculino", "Feminino"], horizontal=True)
    col_p, col_a, col_i = st.columns(3)
    peso = col_p.number_input("Peso (Kg):", value=70.0, format="%.1f")
    altura = col_a.number_input("Alt (cm):", value=175, step=1)
    idade = col_i.number_input("Idade:", value=30, step=1)
    
    atividade_opcoes = {"Sedentário (1.2)": 1.2, "Leve (1.375)": 1.375, "Moderado (1.55)": 1.55, "Intenso (1.725)": 1.725}
    atv_sel = st.selectbox("Nível de Atividade:", list(atividade_opcoes.keys()), index=2)
    fator = atividade_opcoes[atv_sel]
    
    st.divider()
    
    st.header("🎯 Metas")
    objetivo = st.selectbox("Objetivo:", ["Definição (-)", "Manutenção", "Hipertrofia (+)"])
    ajuste = 0
    if "Definição" in objetivo: ajuste = -st.number_input("Déficit:", value=500, step=50)
    elif "Hipertrofia" in objetivo: ajuste = st.number_input("Superávit:", value=300, step=50)

    st.subheader("Macros (g/kg)")
    c1, c2, c3 = st.columns(3)
    prot_g_kg = c1.number_input("Prot", value=2.0, step=0.1)
    carb_g_kg = c2.number_input("Carb", value=4.0, step=0.1)
    gord_g_kg = c3.number_input("Gord", value=0.8, step=0.1)

    tmb_val = 66.5 + (13.75 * peso) + (5.003 * altura) - (6.75 * idade) if sexo == "Masculino" else 655.1 + (9.563 * peso) + (1.850 * altura) - (4.676 * idade)
    meta_calorias = int((tmb_val * fator) + ajuste)
    
    st.divider()
    st.metric("🔥 Meta Diária", f"{meta_calorias} kcal")
    
    st.divider()
    
    # --- BOTÃO DE CÁLCULO ---
    if st.button("🤖 Calcular Macros (IA)", type="primary"):
        if not tem_chave:
            st.error("Sem chave configurada.")
        else:
            api_key = st.secrets["GOOGLE_API_KEY"]
            status = st.status("Conectando ao Nutricionista IA...", expanded=True)
            try:
                total_novos = 0
                for ref_nome, df in st.session_state.refeicoes.items():
                    itens_calc = []
                    indices = []
                    
                    for i, row in df.iterrows():
                        tem_nome = row["Alimento"] and str(row["Alimento"]).strip() != ""
                        try: k = float(row["Kcal"])
                        except: k = 0
                        if tem_nome and k == 0:
                            q = row["Qtd"] if row["Qtd"] else "1 porção"
                            itens_calc.append(f"{q} de {row['Alimento']}")
                            indices.append(i)
                    
                    if itens_calc:
                        status.write(f"Analisando {ref_nome}...")
                        
                        prompt = f"""
                        Atue como nutricionista. Analise: {itens_calc}.
                        Retorne APENAS um JSON (lista de objetos) com valores numéricos.
                        Exemplo: [{{"kcal": 100, "prot": 10, "carb": 20, "gord": 5}}]
                        """
                        
                        # CHAMA A FUNÇÃO QUE TENTA VÁRIOS MODELOS
                        resultado = chamar_gemini_direto(prompt, api_key)
                        
                        if resultado["sucesso"]:
                            res_lista = resultado["dados"]
                            status.write(f"✅ Sucesso usando modelo: {resultado['modelo_usado']}")
                            for j, dados in enumerate(res_lista):
                                if j < len(indices):
                                    idx = indices[j]
                                    df.at[idx, "Kcal"] = dados.get("kcal", 0)
                                    df.at[idx, "P(g)"] = dados.get("prot", 0)
                                    df.at[idx, "C(g)"] = dados.get("carb", 0)
                                    df.at[idx, "G(g)"] = dados.get("gord", 0)
                            st.session_state.refeicoes[ref_nome] = df
                            total_novos += len(res_lista)
                        else:
                            status.error(f"Falha em todos os modelos: {resultado['erro']}")
                            st.stop()
                
                if total_novos > 0:
                    status.update(label="Cálculo Concluído!", state="complete", expanded=False)
                    time.sleep(1)
                    st.rerun()
                else:
                    status.update(label="Nada novo para calcular.", state="complete")
                    
            except Exception as e:
                status.update(label="Erro Crítico", state="error")
                st.error(f"Erro: {e}")

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
meta_prot = int(peso * prot_g_kg)
meta_carb = int(peso * carb_g_kg)
meta_gord = int(peso * gord_g_kg)

st.subheader("📊 Resumo do Dia")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Kcal", f"{int(total_dia_kcal)}", f"{int(total_dia_kcal - meta_calorias)}")
c2.metric("Prot", f"{int(total_dia_prot)}g", f"{int(total_dia_prot - meta_prot)}")
c3.metric("Carb", f"{int(total_dia_carb)}g", f"{int(total_dia_carb - meta_carb)}")
c4.metric("Gord", f"{int(total_dia_gord)}g", f"{int(total_dia_gord - meta_gord)}")
