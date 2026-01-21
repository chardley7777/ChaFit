import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Dieta Pro Flex", page_icon="🥗", layout="wide")

# --- CONFIGURAÇÃO DA IA ---
api_key_status = "OK"
model = None
nome_modelo_usado = "Nenhum"

try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        modelos_disponiveis = []
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    modelos_disponiveis.append(m.name)
        except: pass

        if modelos_disponiveis:
            preferidos = ["models/gemini-1.5-flash", "models/gemini-1.5-pro", "models/gemini-1.0-pro"]
            escolhido = modelos_disponiveis[0]
            for pref in preferidos:
                if pref in modelos_disponiveis:
                    escolhido = pref
                    break
            model = genai.GenerativeModel(escolhido)
            nome_modelo_usado = escolhido
        else:
            api_key_status = "Sem modelos." 
    else:
        api_key_status = "FALTA_KEY"
except Exception as e:
    api_key_status = f"ERRO: {e}"

# --- FUNÇÃO 1: CALCULAR LINHAS (JÁ EXISTIA) ---
def calcular_alimentos_ia(lista_alimentos):
    if not lista_alimentos or not model: return []
    prompt = f"""
    Nutricionista: analise {lista_alimentos}.
    Responda APENAS um JSON (lista de objetos). 
    Exemplo: [{{"kcal": 100, "prot": 10, "carb": 20, "gord": 5}}]
    """
    try:
        response = model.generate_content(prompt)
        texto = response.text.replace("```json", "").replace("```", "").strip()
        if "[" in texto: texto = texto[texto.find("["):texto.rfind("]")+1]
        return json.loads(texto)
    except: return []

# --- FUNÇÃO 2: GERAR DIETA COMPLETA (NOVA) ---
def gerar_dieta_automatica(preferencias, meta_kcal, meta_macros, refeicoes_lista):
    if not model: return None
    
    # Cria uma string com os horários para a IA entender a estrutura
    estrutura_refeicoes = [f"{r['Horário']} - {r['Nome']}" for r in refeicoes_lista]
    
    prompt = f"""
    Atue como nutricionista esportivo de elite.
    OBJETIVO: Criar uma dieta diária completa para atingir EXATAMENTE:
    - Calorias: {meta_kcal} kcal
    - Proteína: {meta_macros['p']}g
    - Carbo: {meta_macros['c']}g
    - Gordura: {meta_macros['g']}g
    
    ALIMENTOS PERMITIDOS (Use apenas estes ou variações simples deles):
    {preferencias}
    
    ESTRUTURA DE REFEIÇÕES (Distribua os alimentos nestes horários):
    {estrutura_refeicoes}
    
    REGRA: Calcule as quantidades (em gramas ou unidades) para que a soma total do dia bata as metas.
    
    SAÍDA OBRIGATÓRIA: Retorne APENAS um JSON onde as chaves são os nomes exatos das refeições (ex: "07:00 - Café") e o valor é uma lista de alimentos.
    Formato do JSON:
    {{
      "07:00 - Café da Manhã": [
        {{"Alimento": "Ovo cozido", "Qtd": "3 un", "Kcal": 210, "P(g)": 18, "C(g)": 2, "G(g)": 15}},
        {{"Alimento": "Pão integral", "Qtd": "2 fatias", "Kcal": 120, "P(g)": 4, "C(g)": 24, "G(g)": 1}}
      ],
      "13:00 - Almoço": [ ... ]
    }}
    """
    try:
        response = model.generate_content(prompt)
        texto = response.text.replace("```json", "").replace("```", "").strip()
        if "{" in texto: texto = texto[texto.find("{"):texto.rfind("}")+1]
        return json.loads(texto)
    except Exception as e:
        return {"erro": str(e)}

# --- INICIALIZAÇÃO ---
schedule_padrao = [
    {"Horário": "07:00", "Nome": "Café da Manhã"},
    {"Horário": "13:00", "Nome": "Almoço"},
    {"Horário": "20:00", "Nome": "Jantar"},
]

if 'meus_horarios' not in st.session_state: st.session_state.meus_horarios = schedule_padrao
if 'refeicoes' not in st.session_state: st.session_state.refeicoes = {}

# Garante tabelas
for item in st.session_state.meus_horarios:
    chave = f"{item['Horário']} - {item['Nome']}"
    if chave not in st.session_state.refeicoes:
        st.session_state.refeicoes[chave] = pd.DataFrame([{"Alimento": "", "Qtd": "", "Kcal": 0, "P(g)": 0, "C(g)": 0, "G(g)": 0}])

# ==========================================
# BARRA LATERAL
# ==========================================
with st.sidebar:
    st.header("👤 Seus Dados")
    if api_key_status != "OK": st.error(f"⚠️ {api_key_status}")

    with st.expander("⚙️ Configurar Horários", expanded=False):
        df_sch = pd.DataFrame(st.session_state.meus_horarios)
        df_sch_ed = st.data_editor(df_sch, num_rows="dynamic", use_container_width=True, hide_index=True)
        st.session_state.meus_horarios = df_sch_ed.to_dict('records')

    st.divider()
    sexo = st.radio("Sexo:", ["Masc", "Fem"], horizontal=True)
    c1,c2,c3 = st.columns(3)
    peso = c1.number_input("Peso", 70.0, format="%.1f")
    altura = c2.number_input("Alt", 175)
    idade = c3.number_input("Idade", 30)
    
    fator = st.selectbox("Atividade", [1.2, 1.375, 1.55, 1.725], format_func=lambda x: f"Fator {x}")
    objetivo = st.selectbox("Objetivo", ["Definição (-)", "Manutenção", "Hipertrofia (+)"])
    
    ajuste = 0
    if "Definição" in objetivo: ajuste = -st.number_input("Déficit", 500, step=50)
    elif "Hipertrofia" in objetivo: ajuste = st.number_input("Superávit", 300, step=50)

    st.caption("Macros (g/kg)")
    cc1, cc2, cc3 = st.columns(3)
    p_gkg = cc1.number_input("Prot", 2.0, step=0.1)
    c_gkg = cc2.number_input("Carb", 4.0, step=0.1)
    g_gkg = cc3.number_input("Gord", 0.8, step=0.1)

    tmb = (66.5 + (13.75*peso) + (5*altura) - (6.75*idade)) if sexo == "Masc" else (655 + (9.6*peso) + (1.8*altura) - (4.7*idade))
    meta_kcal = int((tmb * fator) + ajuste)
    meta_p = int(peso * p_gkg)
    meta_c = int(peso * c_gkg)
    meta_g = int(peso * g_gkg)
    
    st.divider()
    st.metric("Meta Diária", f"{meta_kcal} kcal")
    st.caption(f"P:{meta_p}g | C:{meta_c}g | G:{meta_g}g")

# ==========================================
# ÁREA PRINCIPAL
# ==========================================
st.title("🥗 Planejador Inteligente")

# ABAS: MANUAL vs AUTOMÁTICO
tab1, tab2 = st.tabs(["✏️ Modo Manual", "🤖 Gerador Automático"])

# --- ABA 1: MODO MANUAL (O QUE JÁ EXISTIA) ---
with tab1:
    st.caption("Preencha manualmente e use a IA apenas para calcular calorias.")
    forcar = st.checkbox("Recalcular valores já preenchidos", value=False)
    
    if st.button("Calcular Manualmente", type="secondary"):
        status = st.status("Calculando...", expanded=True)
        total_novos = 0
        for item in st.session_state.meus_horarios:
            ref = f"{item['Horário']} - {item['Nome']}"
            if ref not in st.session_state.refeicoes: continue
            
            df = st.session_state.refeicoes[ref]
            itens, idxs = [], []
            for i, row in df.iterrows():
                nome = str(row["Alimento"])
                kcal = float(row["Kcal"]) if row["Kcal"] else 0
                if nome and (kcal == 0 or forcar):
                    itens.append(f"{row['Qtd'] or '1'} de {nome}")
                    idxs.append(i)
            
            if itens:
                res = calcular_alimentos_ia(itens)
                for j, d in enumerate(res):
                    if j < len(idxs):
                        idx = idxs[j]
                        df.at[idx, "Kcal"] = d.get("kcal",0)
                        df.at[idx, "P(g)"] = d.get("prot",0)
                        df.at[idx, "C(g)"] = d.get("carb",0)
                        df.at[idx, "G(g)"] = d.get("gord",0)
                st.session_state.refeicoes[ref] = df
                total_novos += 1
        status.update(label="Pronto!", state="complete", expanded=False)
        if total_novos > 0: time.sleep(1); st.rerun()

# --- ABA 2: GERADOR AUTOMÁTICO (A NOVIDADE) ---
with tab2:
    st.info("Diga o que você gosta, e a IA monta a dieta completa distribuindo nos seus horários.")
    
    preferencias = st.text_area("O que você gosta de comer?", height=100, 
        placeholder="Ex: Arroz, feijão, frango, ovo, aveia, whey, banana, doce de leite...")
    
    if st.button("✨ Gerar Dieta Completa", type="primary"):
        if not preferencias:
            st.warning("Digite suas preferências primeiro.")
        else:
            with st.spinner("A IA está distribuindo seus alimentos para bater a meta..."):
                resultado = gerar_dieta_automatica(
                    preferencias, 
                    meta_kcal, 
                    {"p": meta_p, "c": meta_c, "g": meta_g},
                    st.session_state.meus_horarios
                )
                
                if resultado and "erro" not in resultado:
                    # Atualiza as tabelas com o resultado da IA
                    for ref_chave, lista_alimentos in resultado.items():
                        # Cria DataFrame novo com os dados da IA
                        novo_df = pd.DataFrame(lista_alimentos)
                        # Garante que as colunas existem
                        cols = ["Alimento", "Qtd", "Kcal", "P(g)", "C(g)", "G(g)"]
                        for c in cols: 
                            if c not in novo_df.columns: novo_df[c] = 0
                        
                        # Salva no estado
                        st.session_state.refeicoes[ref_chave] = novo_df
                    
                    st.success("Dieta gerada com sucesso! Veja o resultado abaixo.")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("Falha ao gerar. Tente novamente.")

# --- VISUALIZAÇÃO DAS TABELAS (COMUM ÀS DUAS ABAS) ---
st.divider()
total_k, total_p, total_c, total_g = 0,0,0,0

for item in st.session_state.meus_horarios:
    ref = f"{item['Horário']} - {item['Nome']}"
    if ref not in st.session_state.refeicoes:
        st.session_state.refeicoes[ref] = pd.DataFrame([{"Alimento": "", "Qtd": "", "Kcal": 0, "P(g)": 0, "C(g)": 0, "G(g)": 0}])

    c_time, c_tbl = st.columns([1, 6])
    with c_time: st.markdown(f"### {item['Horário']}")
    with c_tbl:
        st.markdown(f"**{item['Nome']}**")
        df = st.data_editor(st.session_state.refeicoes[ref], num_rows="dynamic", use_container_width=True, key=f"edit_{ref}", hide_index=True)
        st.session_state.refeicoes[ref] = df
        
        sk = df["Kcal"].sum(); sp = df["P(g)"].sum(); sc = df["C(g)"].sum(); sg = df["G(g)"].sum()
        total_k+=sk; total_p+=sp; total_c+=sc; total_g+=sg
        st.caption(f"Total: 🔥 {int(sk)} | P: {int(sp)} | C: {int(sc)} | G: {int(sg)}")
        st.divider()

# RODAPÉ
st.subheader("📊 Resumo vs Meta")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Kcal", int(total_k), int(total_k - meta_kcal))
c2.metric("Prot", int(total_p), int(total_p - meta_p))
c3.metric("Carb", int(total_c), int(total_c - meta_c))
c4.metric("Gord", int(total_g), int(total_g - meta_g))
