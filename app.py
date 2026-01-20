import streamlit as st
import google.generativeai as genai

# --- CONFIGURAÇÃO DA IA ---
# Tenta pegar a chave secreta. Se não achar, avisa o usuário.
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("ERRO: Configure a GOOGLE_API_KEY nos 'Secrets' do Streamlit.")

st.set_page_config(page_title="NutriCalc AI", page_icon="🍎")

# --- FUNÇÃO QUE CONVERSA COM A IA ---
def analisar_alimento(texto):
    prompt = f"""
    Atue como nutricionista. Analise: '{texto}'.
    Retorne APENAS um formato JSON simples com: nome, calorias (inteiro), proteinas (g), carboidratos (g), gorduras (g).
    Se não for comida, retorne calorias 0.
    Exemplo: {{"nome": "Ovo", "calorias": 70, "proteinas": 6, "carboidratos": 0, "gorduras": 5}}
    """
    try:
        response = model.generate_content(prompt)
        # Limpeza básica para garantir que o JSON venha correto
        texto_limpo = response.text.replace("```json", "").replace("```", "")
        return eval(texto_limpo) # Converte texto em dicionário
    except:
        return None

# --- BARRA LATERAL (SEUS DADOS) ---
with st.sidebar:
    st.header("Suas Metas")
    # Simplifiquei os inputs para focar na IA, mas mantive a lógica
    peso = st.number_input("Peso (Kg):", value=101.0)
    meta_calorias = st.number_input("Sua Meta de Calorias:", value=2919)
    
    # Session State para guardar o que comeu (memória temporária)
    if 'diario' not in st.session_state:
        st.session_state.diario = []

# --- TELA PRINCIPAL ---
st.title("🍎 Diário Alimentar com IA")

# 1. Campo de Busca
st.subheader("O que você comeu?")
comida_input = st.text_input("Ex: 2 ovos fritos e 1 pão francês", key="input_comida")

if st.button("Registrar Alimento"):
    with st.spinner('Consultando nutricionista artificial...'):
        dados = analisar_alimento(comida_input)
        
        if dados and dados['calorias'] > 0:
            st.session_state.diario.append(dados)
            st.success(f"Adicionado: {dados['nome']} ({dados['calorias']} kcal)")
        else:
            st.error("Não entendi esse alimento. Tente ser mais específico.")

# 2. Resumo do Dia
st.divider()
st.subheader("Resumo do Dia")

total_cal = sum(item['calorias'] for item in st.session_state.diario)
total_prot = sum(item['proteinas'] for item in st.session_state.diario)
total_carb = sum(item['carboidratos'] for item in st.session_state.diario)
total_gord = sum(item['gorduras'] for item in st.session_state.diario)

# Barra de Progresso
progresso = min(total_cal / meta_calorias, 1.0)
st.progress(progresso)
st.caption(f"Você consumiu {total_cal} de {meta_calorias} Kcal")

# Colunas de Macros
col1, col2, col3 = st.columns(3)
col1.metric("Proteínas", f"{total_prot}g")
col2.metric("Carboidratos", f"{total_carb}g")
col3.metric("Gorduras", f"{total_gord}g")

# 3. Lista de Alimentos
if st.session_state.diario:
    st.write("---")
    st.write("📝 **Histórico de hoje:**")
    for i, item in enumerate(st.session_state.diario):
        st.text(f"{i+1}. {item['nome']} - {item['calorias']} kcal")
    
    if st.button("Limpar Diário"):
        st.session_state.diario = []
        st.rerun()
