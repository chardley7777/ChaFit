import streamlit as st

# Configuração da página
st.set_page_config(page_title="NutriCalc Pro", page_icon="🍎")

st.title("🍎 TMB - Taxa Metabolica Basal")
st.write("Baseado no seu painel de referência.")

# --- BARRA LATERAL (ENTRADA DE DADOS) ---
with st.sidebar:
    st.header("Preencha seus dados")
    sexo = st.radio("Sexo:", ["Masculino", "Feminino"])
    altura = st.number_input("Altura (cm):", value=177)
    peso = st.number_input("Peso (Kg):", value=101.0)
    idade = st.number_input("Idade:", value=19)
    
    # Fatores de atividade idênticos à sua imagem
    atividade_opcoes = {
        "Sedentário (1.2)": 1.2,
        "Levemente ativo (1.375)": 1.375,
        "Moderadamente ativo (1.55)": 1.55,
        "Muito ativo (1.725)": 1.725,
        "Extremamente ativo (1.9)": 1.9
    }
    atividade_selecionada = st.selectbox("Atividade física*:", list(atividade_opcoes.keys()))
    fator_atividade = atividade_opcoes[atividade_selecionada]

    objetivo = st.selectbox("Objetivo:", ["Definição (-500kcal)", "Manutenção", "Hipertrofia (+500kcal)"])

# --- CÁLCULOS (LÓGICA DO BACKEND) ---
# 1. TMB (Fórmula de Harris-Benedict)
if sexo == "Masculino":
    tmb = 66.5 + (13.75 * peso) + (5.003 * altura) - (6.75 * idade)
else:
    tmb = 655.1 + (9.563 * peso) + (1.850 * altura) - (4.676 * idade)

# 2. Gasto Calórico Médio
gasto_total = tmb * fator_atividade

# 3. Calorias Recomendadas (Ajuste do Objetivo)
ajuste = 0
if "Definição" in objetivo:
    ajuste = -500
elif "Hipertrofia" in objetivo:
    ajuste = 500

calorias_finais = gasto_total + ajuste

# --- EXIBIÇÃO DOS RESULTADOS (DASHBOARD) ---
st.divider()

col1, col2, col3 = st.columns(3)
col1.metric("Taxa Metabólica Basal (TMB)", f"{int(tmb)} Kcal")
col2.metric("Gasto Calórico Médio", f"{int(gasto_total)} Kcal")
col3.metric("🔥 Calorias Recomendadas", f"{int(calorias_finais)} Kcal", delta=f"{ajuste} Kcal")

st.divider()

# --- DISTRIBUIÇÃO DE MACROS (INTELIGÊNCIA) ---
st.subheader("🍽 Sugestão de Distribuição (Macros)")

# Regra: 40% Proteína, 40% Carbo, 20% Gordura (Padrão para definição/fitness)
prot_cal = calorias_finais * 0.40
carb_cal = calorias_finais * 0.40
gord_cal = calorias_finais * 0.20

# Conversão kcal para gramas (Prot/Carb = 4kcal/g, Gord = 9kcal/g)
prot_g = prot_cal / 4
carb_g = carb_cal / 4
gord_g = gord_cal / 9

c1, c2, c3 = st.columns(3)
c1.info(f"**Proteína:** {int(prot_g)}g")
c2.warning(f"**Carboidrato:** {int(carb_g)}g")
c3.error(f"**Gordura:** {int(gord_g)}g")
