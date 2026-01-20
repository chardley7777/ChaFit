import streamlit as st
import google.generativeai as genai
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="NutriCalc Pro", page_icon="💪", layout="wide")

# --- CONFIGURAÇÃO DA IA ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("ERRO: Configure a GOOGLE_API_KEY nos 'Secrets' do Streamlit.")

# --- FUNÇÃO QUE ANALISA O CARDÁPIO COMPLETO ---
def analisar_cardapio(texto_cardapio):
    prompt = f"""
    Atue como nutricionista esportivo. Analise o cardápio:
    '''
    {texto_cardapio}
    '''
    Retorne APENAS um JSON (sem markdown) com a lista:
    [
        {{"alimento": "Nome", "qtd": "estimada", "kcal": 0, "prot": 0, "carb": 0, "gord": 0}}
    ]
    """
    try:
        response = model.generate_content(prompt)
        texto_limpo = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(texto_limpo)
    except:
        return None

# --- BARRA LATERAL (DADOS DO USUÁRIO) ---
with st.sidebar:
    st.header("👤 Seus Dados")
    
    sexo = st.radio("Sexo:", ["Masculino", "Feminino"], horizontal=True)
    col_p, col_a, col_i = st.columns(3)
    peso = col_p.number_input("Peso (Kg):", value=None, placeholder="00.0")
    altura = col_a.number_input("Altura (cm):", value=None, placeholder="000", step=1)
    idade = col_i.number_input("Idade:", value=None, placeholder="00", step=1)
    
    atividade_opcoes = {
        "Sedentário (1.2)": 1.2,
        "Levemente ativo (1.375)": 1.375,
        "Moderadamente ativo (1.55)": 1.55,
        "Muito ativo (1.725)": 1.725,
        "Extremamente ativo (1.9)": 1.9
    }
    atividade_selecionada = st.selectbox("Nível de Atividade:", list(atividade_opcoes.keys()), index=None, placeholder="Selecione...")
    
    st.divider()
    
    # --- 1. CONFIGURAÇÃO DE OBJETIVO MANUAL ---
    st.header("🎯 Objetivo & Calorias")
    objetivo = st.selectbox("Fase Atual:", ["Manutenção", "Definição (Perder)", "Hipertrofia (Ganhar)"], index=None, placeholder="Selecione...")

    ajuste_calorico = 0
    if objetivo == "Definição (Perder)":
        ajuste_calorico = st.number_input("Déficit Calórico (Kcal):", value=500, step=50, help="Quanto você quer comer A MENOS que seu gasto?")
        ajuste_calorico = -ajuste_calorico # Torna negativo
    elif objetivo == "Hipertrofia (Ganhar)":
        ajuste_calorico = st.number_input("Superávit Calórico (Kcal):", value=300, step=50, help="Quanto você quer comer A MAIS que seu gasto?")

    st.divider()

    # --- 2. CONFIGURAÇÃO DE MACROS MANUAL ---
    st.header("⚙️ Configurar Macros")
    st.info("Defina seus macros em g/kg (gramas por quilo corporal).")
    
    # Valores padrão comuns na nutrição
    def_prot = 2.0
    def_gord = 0.8
    def_carb = 4.0
    
    # Se o objetivo for definição, sugere carbos mais baixos
    if objetivo == "Definição (Perder)":
        def_carb = 2.5
        def_prot = 2.2 # Proteína mais alta no cutting

    col_m1, col_m2, col_m3 = st.columns(3)
    prot_g_kg = col_m1.number_input("Prot (g/kg)", value=def_prot, step=0.1, format="%.1f")
    carb_g_kg = col_m2.number_input("Carb (g/kg)", value=def_carb, step=0.1, format="%.1f")
    gord_g_kg = col_m3.number_input("Gord (g/kg)", value=def_gord, step=0.1, format="%.1f")


# --- LÓGICA PRINCIPAL ---
if peso and altura and idade and atividade_selecionada and objetivo:
    
    # 1. Cálculos Basais
    fator = atividade_opcoes[atividade_selecionada]
    if sexo == "Masculino":
        tmb = 66.5 + (13.75 * peso) + (5.003 * altura) - (6.75 * idade)
    else:
        tmb = 655.1 + (9.563 * peso) + (1.850 * altura) - (4.676 * idade)
    
    gasto_total = tmb * fator
    meta_calorias_calculada = int(gasto_total + ajuste_calorico)
    
    # 2. Cálculo dos Macros Manuais (O que o usuário configurou)
    meta_prot = int(peso * prot_g_kg)
    meta_carb = int(peso * carb_g_kg)
    meta_gord = int(peso * gord_g_kg)
    
    # Calorias geradas pelos macros configurados
    calorias_dos_macros = (meta_prot * 4) + (meta_carb * 4) + (meta_gord * 9)

    # --- Exibição na Barra Lateral (Resumo) ---
    st.sidebar.divider()
    st.sidebar.write(f"**TMB:** {int(tmb)} kcal")
    st.sidebar.write(f"**Gasto Total:** {int(gasto_total)} kcal")
    
    # Aviso se houver discrepância grande entre a Meta de Calorias e os Macros
    diff = calorias_dos_macros - meta_calorias_calculada
    
    st.sidebar.metric("🔥 Meta pelos Macros", f"{calorias_dos_macros} kcal", delta=f"{diff} vs Estimativa")
    st.sidebar.caption(f"P: {meta_prot}g | C: {meta_carb}g | G: {meta_gord}g")


    # --- TELA PRINCIPAL ---
    st.title("💪 Calculadora Pro")
    
    # Input do Cardápio
    st.write("Cole seu planejamento alimentar completo abaixo:")
    cardapio_input = st.text_area("", height=150, placeholder="Ex: Café: 3 ovos e 1 banana...")

    if st.button("Calcular Cardápio"):
        if not cardapio_input:
            st.warning("Digite seu cardápio primeiro.")
        else:
            with st.spinner("Analisando macros..."):
                dados = analisar_cardapio(cardapio_input)
                
                if dados:
                    total_kcal = sum(i['kcal'] for i in dados)
                    total_prot = sum(i['prot'] for i in dados)
                    total_carb = sum(i['carb'] for i in dados)
                    total_gord = sum(i['gord'] for i in dados)

                    st.divider()
                    
                    # --- DASHBOARD COMPARATIVO ---
                    # Vamos comparar o Cardápio (Real) vs A Configuração Manual (Meta)
                    
                    c1, c2, c3, c4 = st.columns(4)
                    
                    def delta_metric(real, meta, suffix=""):
                        diff = real - meta
                        return f"{diff}{suffix}"

                    c1.metric("Calorias", f"{total_kcal}", delta_metric(total_kcal, calorias_dos_macros))
                    c2.metric("Proteínas", f"{total_prot}g", delta_metric(total_prot, meta_prot, "g"))
                    c3.metric("Carboidratos", f"{total_carb}g", delta_metric(total_carb, meta_carb, "g"))
                    c4.metric("Gorduras", f"{total_gord}g", delta_metric(total_gord, meta_gord, "g"))

                    st.write("### 📊 Aderência à Dieta")
                    
                    # Barras de Progresso
                    st.caption(f"Proteína ({total_prot}/{meta_prot}g)")
                    st.progress(min(total_prot / meta_prot if meta_prot > 0 else 0, 1.0))
                    
                    st.caption(f"Carboidrato ({total_carb}/{meta_carb}g)")
                    st.progress(min(total_carb / meta_carb if meta_carb > 0 else 0, 1.0))
                    
                    st.caption(f"Gordura ({total_gord}/{meta_gord}g)")
                    st.progress(min(total_gord / meta_gord if meta_gord > 0 else 0, 1.0))
                    
                    st.caption(f"Calorias Totais ({total_kcal}/{calorias_dos_macros} kcal)")
                    if total_kcal > calorias_dos_macros:
                        st.warning("⚠️ Você ultrapassou as calorias planejadas!")
                    else:
                        st.success("✅ Dentro do planejado.")

                    st.divider()
                    st.table(dados)

else:
    st.info("👈 Preencha seus dados e configure seus macros na barra lateral para começar.")
