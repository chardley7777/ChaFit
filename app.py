import streamlit as st
import google.generativeai as genai
import pandas as pd
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="NutriCalc Planilha", page_icon="📅", layout="wide")

# --- CONFIGURAÇÃO DA IA ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("ERRO: Configure a GOOGLE_API_KEY nos 'Secrets' do Streamlit.")

# --- FUNÇÃO: IA CALCULA MACROS DA TABELA ---
def preencher_macros_tabela(df_dict):
    # Filtra apenas linhas que têm alimento mas estão com calorias zeradas
    itens_para_calcular = []
    indices_para_atualizar = []

    for i, row in enumerate(df_dict):
        if row["Alimento"] and row["Alimento"] != "" and row["Kcal"] == 0:
            itens_para_calcular.append(f"Item {i}: {row['Quantidade']} de {row['Alimento']}")
            indices_para_atualizar.append(i)
    
    if not itens_para_calcular:
        return df_dict # Nada para calcular

    lista_texto = "\n".join(itens_para_calcular)
    
    prompt = f"""
    Atue como tabela nutricional precisa. Tenho estes itens:
    {lista_texto}

    Retorne APENAS um JSON (sem markdown) no formato de lista de objetos, na mesma ordem:
    [
        {{"kcal": 100, "prot": 10, "carb": 20, "gord": 5}},
        ...
    ]
    Considere valores padrão para alimentos cozidos/grelhados se não especificado.
    """
    
    try:
        response = model.generate_content(prompt)
        texto_limpo = response.text.strip().replace("```json", "").replace("```", "")
        dados_novos = json.loads(texto_limpo)

        # Atualiza a lista original com os dados da IA
        for idx_lista, idx_df in enumerate(indices_para_atualizar):
            try:
                dados = dados_novos[idx_lista]
                df_dict[idx_df]["Kcal"] = int(dados["kcal"])
                df_dict[idx_df]["Prot (g)"] = int(dados["prot"])
                df_dict[idx_df]["Carb (g)"] = int(dados["carb"])
                df_dict[idx_df]["Gord (g)"] = int(dados["gord"])
            except:
                pass # Se der erro num item, pula
                
        return df_dict
    except:
        return df_dict

# --- INICIALIZAÇÃO DOS DADOS (SESSION STATE) ---
if 'dieta_df' not in st.session_state:
    # Cria uma estrutura inicial vazia igual ao print que você mandou
    st.session_state.dieta_df = pd.DataFrame(
        [
            {"Horário": "07:00", "Alimento": "Ovo cozido", "Quantidade": "2 un", "Kcal": 0, "Prot (g)": 0, "Carb (g)": 0, "Gord (g)": 0},
            {"Horário": "07:00", "Alimento": "Pão francês", "Quantidade": "1 un", "Kcal": 0, "Prot (g)": 0, "Carb (g)": 0, "Gord (g)": 0},
            {"Horário": "10:00", "Alimento": "Arroz branco", "Quantidade": "100g", "Kcal": 0, "Prot (g)": 0, "Carb (g)": 0, "Gord (g)": 0},
            {"Horário": "13:00", "Alimento": "", "Quantidade": "", "Kcal": 0, "Prot (g)": 0, "Carb (g)": 0, "Gord (g)": 0},
        ]
    )

# --- BARRA LATERAL (CONFIGURAÇÃO) ---
with st.sidebar:
    st.header("⚙️ Configuração")
    
    sexo = st.radio("Sexo", ["Masculino", "Feminino"], horizontal=True)
    col1, col2 = st.columns(2)
    peso = col1.number_input("Peso (kg)", value=70.0, format="%.1f")
    altura = col2.number_input("Alt (cm)", value=175, step=1)
    idade = st.number_input("Idade", value=30, step=1)
    
    fator_atv = st.selectbox("Atividade", ["Sedentário (1.2)", "Leve (1.375)", "Moderado (1.55)", "Intenso (1.725)"])
    fator_valor = float(fator_atv.split("(")[1].replace(")", ""))
    
    st.divider()
    st.subheader("🎯 Metas")
    objetivo = st.selectbox("Objetivo", ["Definição", "Manutenção", "Hipertrofia"])
    
    ajuste = 0
    if objetivo == "Definição":
        ajuste = st.number_input("Déficit Calórico (-)", value=500, step=50) * -1
    elif objetivo == "Hipertrofia":
        ajuste = st.number_input("Superávit Calórico (+)", value=300, step=50)
        
    # Macros Manuais
    st.caption("Macros (g/kg)")
    c1, c2, c3 = st.columns(3)
    p_gkg = c1.number_input("Prot", value=2.0, step=0.1)
    c_gkg = c2.number_input("Carb", value=4.0, step=0.1)
    g_gkg = c3.number_input("Gord", value=0.8, step=0.1)

    # Cálculos
    if sexo == "Masculino":
        tmb = 66.5 + (13.75 * peso) + (5.003 * altura) - (6.75 * idade)
    else:
        tmb = 655.1 + (9.563 * peso) + (1.850 * altura) - (4.676 * idade)
        
    gasto_total = (tmb * fator_valor) + ajuste
    meta_calorias = int(gasto_total)
    
    meta_prot = int(peso * p_gkg)
    meta_carb = int(peso * c_gkg)
    meta_gord = int(peso * g_gkg)
    calorias_macros = (meta_prot*4) + (meta_carb*4) + (meta_gord*9)

    st.divider()
    st.metric("Meta Calórica", f"{meta_calorias} kcal")
    st.caption(f"Calculado pelos macros: {int(calorias_macros)} kcal")

# --- TELA PRINCIPAL ---
st.title("📋 Montador de Dieta")
st.write("Edite a tabela abaixo como se fosse um Excel. Adicione horários, alimentos e quantidades.")

# 1. O EDITOR DE TABELA (A ESTRELA DO SHOW)
# num_rows="dynamic" permite adicionar linhas clicando no "+"
dados_editados = st.data_editor(
    st.session_state.dieta_df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Horário": st.column_config.TextColumn("Horário", help="Ex: 07:00", width="small"),
        "Alimento": st.column_config.TextColumn("Alimento", help="Nome do alimento", width="large"),
        "Quantidade": st.column_config.TextColumn("Qtd", help="Ex: 100g, 1 colher", width="medium"),
        "Kcal": st.column_config.NumberColumn("Kcal", format="%d"),
        "Prot (g)": st.column_config.NumberColumn("Prot", format="%d"),
        "Carb (g)": st.column_config.NumberColumn("Carb", format="%d"),
        "Gord (g)": st.column_config.NumberColumn("Gord", format="%d"),
    },
    hide_index=True
)

# Atualiza o session_state com o que o usuário digitou
st.session_state.dieta_df = dados_editados

# 2. BOTÕES DE AÇÃO
col_btn1, col_btn2, col_space = st.columns([1, 1, 2])

if col_btn1.button("🤖 Calcular Vazios com IA", type="primary"):
    with st.spinner("Consultando tabela nutricional..."):
        # Converte para dicionario para manipular
        dados_dict = st.session_state.dieta_df.to_dict('records')
        # Chama a IA
        dados_preenchidos = preencher_macros_tabela(dados_dict)
        # Salva de volta
        st.session_state.dieta_df = pd.DataFrame(dados_preenchidos)
        st.rerun()

if col_btn2.button("🗑️ Limpar Tabela"):
    st.session_state.dieta_df = pd.DataFrame(
        [{"Horário": "", "Alimento": "", "Quantidade": "", "Kcal": 0, "Prot (g)": 0, "Carb (g)": 0, "Gord (g)": 0}]
    )
    st.rerun()

# 3. PAINEL DE TOTAIS (RODAPÉ)
st.divider()

# Soma os totais da tabela atual
total_kcal = dados_editados["Kcal"].sum()
total_prot = dados_editados["Prot (g)"].sum()
total_carb = dados_editados["Carb (g)"].sum()
total_gord = dados_editados["Gord (g)"].sum()

st.subheader("📊 Resumo do Planejamento")

c1, c2, c3, c4 = st.columns(4)

def estilo_metrica(label, valor, meta, suffix=""):
    delta = valor - meta
    cor = "normal"
    if valor > meta: cor = "inverse" # Indica que passou
    st.metric(label, f"{int(valor)}{suffix}", f"{int(delta)}{suffix}", delta_color=cor)

with c1: estilo_metrica("Calorias", total_kcal, meta_calorias)
with c2: estilo_metrica("Proteínas", total_prot, meta_prot, "g")
with c3: estilo_metrica("Carboidratos", total_carb, meta_carb, "g")
with c4: estilo_metrica("Gorduras", total_gord, meta_gord, "g")

# Barras de Progresso Visuais
st.write("")
st.caption(f"Progresso Proteína ({int(total_prot)}/{meta_prot}g)")
st.progress(min(total_prot/meta_prot if meta_prot > 0 else 0, 1.0))

st.caption(f"Progresso Calorias ({int(total_kcal)}/{meta_calorias} kcal)")
st.progress(min(total_kcal/meta_calorias if meta_calorias > 0 else 0, 1.0))
