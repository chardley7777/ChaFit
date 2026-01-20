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
        {{"alimento": "Nome do Alimento 1", "qtd": "quantidade estimada", "kcal": 100, "prot": 10, "carb": 20, "gord": 5}},
        {{"alimento": "Nome do Alimento 2", "qtd": "quantidade estimada", "kcal": 50, "prot": 2, "carb": 5, "gord": 1}}
    ]
    Não use Markdown (```json). Retorne apenas o texto puro do JSON.
    """
    try:
        response = model.generate_content(prompt)
        texto_limpo = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(texto_limpo)
    except Exception as e:
        return None

# --- BARRA LATERAL (DADOS DO USUÁRIO) ---
with st.sidebar:
    st.header("👤 Seus Dados")
    sexo = st.radio("Sexo:", ["Masculino", "Feminino"])
    peso = st.number_input("Peso (Kg):", value=101.0)
    altura = st.number_input("Altura (cm):", value=177)
    idade = st.number_input("Idade:", value=19)
    
    atividade_opcoes = {
        "Sedentário (1.2)": 1.2,
        "Levemente ativo (1.375)": 1.375,
        "Moderadamente ativo (1.55)": 1.55,
        "Muito ativo (1.725)": 1.725,
        "Extremamente ativo (1.9)": 1.9
    }
    atividade_selecionada = st.selectbox("Nível de Atividade:", list(atividade_opcoes.keys()))
    fator = atividade_opcoes[atividade_selecionada]
    
    objetivo = st.selectbox("Objetivo:", ["Definição (-500kcal)", "Manutenção", "Hipertrofia (+500kcal)"])

    # Cálculos Basais
    if sexo == "Masculino":
        tmb = 66.5 + (13.75 * peso) + (5.003 * altura) - (6.75 * idade)
    else:
        tmb = 655.1 + (9.563 * peso) + (1.850 * altura) - (4.676 * idade)
    
    gasto_total = tmb * fator
    
    ajuste = -500 if "Definição" in objetivo else (500 if "Hipertrofia" in objetivo else 0)
    meta_calorias = int(gasto_total + ajuste)
    
    st.divider()
    st.metric("🎯 Sua Meta Diária", f"{meta_calorias} kcal")
    
    # Metas de Macros (40/40/20)
    meta_prot = int((meta_calorias * 0.40) / 4)
    meta_carb = int((meta_calorias * 0.40) / 4)
    meta_gord = int((meta_calorias * 0.20) / 9)
    
    st.caption(f"Metas: P: {meta_prot}g | C: {meta_carb}g | G: {meta_gord}g")

# --- TELA PRINCIPAL ---
st.title("🍽 Calculadora de Cardápio")
st.write("Cole seu planejamento alimentar completo abaixo (Café, Almoço, Janta...) e veja se bate com sua meta.")

cardapio_input = st.text_area("Digite o cardápio aqui:", height=150, placeholder="Exemplo:\nCafé: 3 ovos mexidos e café preto\nAlmoço: 200g de arroz, 100g de feijão e 150g de frango\nJantar: Iogurte com aveia")

if st.button("Calcular Cardápio Completo"):
    if not cardapio_input:
        st.warning("Por favor, digite algum alimento.")
    else:
        with st.spinner("A Nutri-IA está analisando cada item..."):
            dados_cardapio = analisar_cardapio(cardapio_input)
            
            if dados_cardapio:
                # Cálculos dos Totais
                total_kcal = sum(item['kcal'] for item in dados_cardapio)
                total_prot = sum(item['prot'] for item in dados_cardapio)
                total_carb = sum(item['carb'] for item in dados_cardapio)
                total_gord = sum(item['gord'] for item in dados_cardapio)

                # --- EXIBIÇÃO DOS RESULTADOS ---
                st.divider()
                st.subheader("📊 Resultado do Planejamento")
                
                # Colunas de comparação (Meta vs Realizado)
                c1, c2, c3, c4 = st.columns(4)
                
                # Helper para cor (Verde se estiver perto da meta, Vermelho se estourar muito)
                def check_meta(valor, meta):
                    delta = valor - meta
                    return f"{delta} (Acima)" if delta > 0 else f"{delta} (Abaixo)"

                c1.metric("Calorias", f"{total_kcal} kcal", f"Meta: {meta_calorias}")
                c2.metric("Proteínas", f"{total_prot} g", f"Meta: {meta_prot}")
                c3.metric("Carboidratos", f"{total_carb} g", f"Meta: {meta_carb}")
                c4.metric("Gorduras", f"{total_gord} g", f"Meta: {meta_gord}")

                # Gráficos de Barra
                st.write("### Progresso da Meta")
                st.caption("Calorias")
                st.progress(min(total_kcal / meta_calorias, 1.0))
                
                st.caption("Proteínas")
                st.progress(min(total_prot / meta_prot, 1.0))

                # Tabela Detalhada
                st.divider()
                st.subheader("📝 Detalhamento por Item")
                st.table(dados_cardapio)

            else:
                st.error("Não foi possível ler o cardápio. Tente simplificar o texto.")
