import streamlit as st
import google.generativeai as genai
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Calculadora de Cardápio", page_icon="🍽", layout="wide")

# --- CONFIGURAÇÃO DA IA ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("ERRO: Configure a GOOGLE_API_KEY nos 'Secrets' do Streamlit.")

# --- FUNÇÃO QUE ANALISA O CARDÁPIO COMPLETO ---
def analisar_cardapio(texto_cardapio):
    prompt = f"""
    Atue como nutricionista. Analise o seguinte cardápio completo:
    '''
    {texto_cardapio}
    '''
    Identifique cada alimento mencionado. Para cada um, estime: calorias (kcal), proteínas (g), carboidratos (g) e gorduras (g).
    Retorne a resposta APENAS em formato JSON, seguindo estritamente este padrão de lista:
    [
        {{"alimento": "Nome do Alimento", "qtd": "quantidade", "kcal": 100, "prot": 10, "carb": 20, "gord": 5}}
    ]
    Não use Markdown. Retorne apenas o texto puro do JSON.
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
    st.info("Preencha os campos abaixo para começar.")
    
    sexo = st.radio("Sexo:", ["Masculino", "Feminino"], index=None)
    
    # value=None deixa o campo em branco inicialmente
    peso = st.number_input("Peso (Kg):", value=None, placeholder="Ex: 70.5")
    altura = st.number_input("Altura (cm):", value=None, placeholder="Ex: 175", step=1)
    idade = st.number_input("Idade:", value=None, placeholder="Ex: 25", step=1)
    
    atividade_opcoes = {
        "Sedentário (1.2)": 1.2,
        "Levemente ativo (1.375)": 1.375,
        "Moderadamente ativo (1.55)": 1.55,
        "Muito ativo (1.725)": 1.725,
        "Extremamente ativo (1.9)": 1.9
    }
    # index=None deixa a caixa de seleção vazia
    atividade_selecionada = st.selectbox("Nível de Atividade:", list(atividade_opcoes.keys()), index=None, placeholder="Selecione...")
    
    objetivo = st.selectbox("Objetivo:", ["Definição (-500kcal)", "Manutenção", "Hipertrofia (+500kcal)"], index=None, placeholder="Selecione...")

# --- VERIFICAÇÃO SE DADOS FORAM PREENCHIDOS ---
# O app só mostra a calculadora se todas as variáveis tiverem valor
if peso and altura and idade and atividade_selecionada and objetivo and sexo:
    
    # Cálculos Basais
    fator = atividade_opcoes[atividade_selecionada]
    
    if sexo == "Masculino":
        tmb = 66.5 + (13.75 * peso) + (5.003 * altura) - (6.75 * idade)
    else:
        tmb = 655.1 + (9.563 * peso) + (1.850 * altura) - (4.676 * idade)
    
    gasto_total = tmb * fator
    
    ajuste = -500 if "Definição" in objetivo else (500 if "Hipertrofia" in objetivo else 0)
    meta_calorias = int(gasto_total + ajuste)
    
    # Exibe a meta na barra lateral
    st.sidebar.divider()
    st.sidebar.metric("🎯 Meta Diária", f"{meta_calorias} kcal")
    
    meta_prot = int((meta_calorias * 0.40) / 4)
    meta_carb = int((meta_calorias * 0.40) / 4)
    meta_gord = int((meta_calorias * 0.20) / 9)
    st.sidebar.caption(f"Metas: P: {meta_prot}g | C: {meta_carb}g | G: {meta_gord}g")

    # --- TELA PRINCIPAL (SÓ APARECE COM DADOS PREENCHIDOS) ---
    st.title("🍽 Calculadora de Cardápio")
    st.write("Cole seu planejamento alimentar completo abaixo.")

    cardapio_input = st.text_area("Digite o cardápio aqui:", height=150, placeholder="Exemplo:\nCafé: 2 ovos\nAlmoço: Arroz e feijão")

    if st.button("Calcular Cardápio Completo"):
        if not cardapio_input:
            st.warning("Por favor, digite algum alimento.")
        else:
            with st.spinner("Analisando..."):
                dados_cardapio = analisar_cardapio(cardapio_input)
                
                if dados_cardapio:
                    total_kcal = sum(item['kcal'] for item in dados_cardapio)
                    total_prot = sum(item['prot'] for item in dados_cardapio)
                    total_carb = sum(item['carb'] for item in dados_cardapio)
                    total_gord = sum(item['gord'] for item in dados_cardapio)

                    st.divider()
                    st.subheader("📊 Resultado do Planejamento")
                    
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Calorias", f"{total_kcal}", f"{total_kcal - meta_calorias} da meta")
                    c2.metric("Proteínas", f"{total_prot}g", f"{total_prot - meta_prot}g")
                    c3.metric("Carboidratos", f"{total_carb}g", f"{total_carb - meta_carb}g")
                    c4.metric("Gorduras", f"{total_gord}g", f"{total_gord - meta_gord}g")

                    st.write("### Progresso da Meta")
                    st.progress(min(total_kcal / meta_calorias, 1.0) if meta_calorias > 0 else 0)
                    
                    st.divider()
                    st.subheader("📝 Detalhamento")
                    st.table(dados_cardapio)
                else:
                    st.error("Erro ao ler o cardápio. Tente simplificar.")

else:
    # TELA DE BOAS-VINDAS (QUANDO TUDO ESTÁ EM BRANCO)
    st.title("👋 Bem-vindo ao NutriCalc")
    st.info("👈 Por favor, preencha seus dados na barra lateral (ao lado esquerdo) para gerarmos sua meta calórica personalizada.")
    st.write("Assim que preencher, a calculadora aparecerá aqui automaticamente.")
