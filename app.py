import streamlit as st
import google.generativeai as genai
import pandas as pd
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Dieta por Refeição", page_icon="🍽", layout="wide")

# --- CONFIGURAÇÃO DA IA ---
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
    else:
        st.error("Configure a GOOGLE_API_KEY nos Secrets.")
except:
    pass

# --- FUNÇÃO: IA CALCULA MACROS (GENÉRICA) ---
def calcular_alimentos_ia(lista_alimentos):
    # Recebe uma lista de strings e retorna os dados
    if not lista_alimentos: return []
    
    prompt = f"""
    Atue como nutricionista. Analise estes itens:
    {lista_alimentos}

    Retorne APENAS um JSON (lista de objetos) na mesma ordem:
    [
        {{"kcal": 100, "prot": 10, "carb": 20, "gord": 5}},
        ...
    ]
    """
    try:
        response = model.generate_content(prompt)
        texto_limpo = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(texto_limpo)
    except:
        return []

# --- ESTRUTURA INICIAL DOS DADOS ---
# Agora usamos um DICIONÁRIO onde cada chave é uma refeição
refeicoes_padrao = ["07:00 - Café da Manhã", "10:00 - Lanche da Manhã", "13:00 - Almoço", "16:00 - Lanche da Tarde", "20:00 - Jantar"]

if 'refeicoes' not in st.session_state:
    st.session_state.refeicoes = {}
    for ref in refeicoes_padrao:
        # Cria uma tabela vazia para cada horário
        st.session_state.refeicoes[ref] = pd.DataFrame(
            [{"Alimento": "", "Qtd": "", "Kcal": 0, "P(g)": 0, "C(g)": 0, "G(g)": 0}]
        )

# --- BARRA LATERAL (RESUMO GERAL) ---
with st.sidebar:
    st.header("🎯 Metas do Dia")
    meta_calorias = st.number_input("Meta Kcal", value=2900, step=100)
    meta_prot = st.number_input("Meta Proteína (g)", value=180, step=10)
    meta_carb = st.number_input("Meta Carbo (g)", value=300, step=10)
    meta_gord = st.number_input("Meta Gordura (g)", value=80, step=10)
    
    st.divider()
    
    # Botão Global de Cálculo
    if st.button("🤖 Calcular Tudo com IA", type="primary"):
        with st.spinner("Calculando todos os blocos..."):
            # Varre todas as refeições
            for ref_nome, df in st.session_state.refeicoes.items():
                # Busca itens sem Kcal mas com nome
                itens_pra_calc = []
                indices = []
                
                for i, row in df.iterrows():
                    if row["Alimento"] and row["Kcal"] == 0:
                        itens_pra_calc.append(f"{row['Qtd']} de {row['Alimento']}")
                        indices.append(i)
                
                if itens_pra_calc:
                    resultados = calcular_alimentos_ia(itens_pra_calc)
                    # Atualiza o DF
                    for j, dados in enumerate(resultados):
                        idx_real = indices[j]
                        df.at[idx_real, "Kcal"] = dados.get("kcal", 0)
                        df.at[idx_real, "P(g)"] = dados.get("prot", 0)
                        df.at[idx_real, "C(g)"] = dados.get("carb", 0)
                        df.at[idx_real, "G(g)"] = dados.get("gord", 0)
                    
                    st.session_state.refeicoes[ref_nome] = df # Salva
        st.rerun()

    if st.button("🗑️ Zerar Tudo"):
        for ref in refeicoes_padrao:
             st.session_state.refeicoes[ref] = pd.DataFrame([{"Alimento": "", "Qtd": "", "Kcal": 0, "P(g)": 0, "C(g)": 0, "G(g)": 0}])
        st.rerun()

# --- TELA PRINCIPAL (LAYOUT IGUAL À FOTO) ---
st.title("📋 Diário de Dieta")

total_dia_kcal = 0
total_dia_prot = 0
total_dia_carb = 0
total_dia_gord = 0

# Loop para desenhar cada bloco de refeição
for ref_nome in refeicoes_padrao:
    
    # Layout: Coluna Pequena (Horário) | Coluna Grande (Tabela)
    col_tempo, col_tabela = st.columns([1, 6])
    
    with col_tempo:
        st.write("") # Espaço vazio para alinhar
        st.write("") 
        # Pega só o horário do nome (ex: "07:00")
        horario = ref_nome.split("-")[0]
        st.markdown(f"### {horario}")
    
    with col_tabela:
        st.markdown(f"**{ref_nome.split('-')[1]}**")
        
        # O Editor de Dados
        df_editado = st.data_editor(
            st.session_state.refeicoes[ref_nome],
            num_rows="dynamic",
            use_container_width=True,
            key=f"editor_{ref_nome}", # Chave única para cada tabela
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
        
        # Salva o que você digitou de volta no estado
        st.session_state.refeicoes[ref_nome] = df_editado
        
        # --- CÁLCULO DOS TOTAIS DESTA REFEIÇÃO ---
        sub_kcal = df_editado["Kcal"].sum()
        sub_p = df_editado["P(g)"].sum()
        sub_c = df_editado["C(g)"].sum()
        sub_g = df_editado["G(g)"].sum()
        
        # Acumula para o total do dia
        total_dia_kcal += sub_kcal
        total_dia_prot += sub_p
        total_dia_carb += sub_c
        total_dia_gord += sub_g
        
        # --- BARRA DE TOTAL (VISUAL IGUAL À FOTO) ---
        # Criamos um HTML cinza para parecer o rodapé da tabela
        st.markdown(
            f"""
            <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; display: flex; justify-content: space-between; font-weight: bold;">
                <span>TOTAL</span>
                <span>🔥 {int(sub_kcal)} kcal | P: {int(sub_p)}g | C: {int(sub_c)}g | G: {int(sub_g)}g</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.divider()

# --- RODAPÉ FLUTUANTE OU FINAL COM TOTAL GERAL ---
st.subheader("📊 Resumo do Dia")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Calorias", f"{int(total_dia_kcal)}", f"{int(total_dia_kcal - meta_calorias)}")
c2.metric("Proteína", f"{int(total_dia_prot)}g", f"{int(total_dia_prot - meta_prot)}")
c3.metric("Carboidrato", f"{int(total_dia_carb)}g", f"{int(total_dia_carb - meta_carb)}")
c4.metric("Gordura", f"{int(total_dia_gord)}g", f"{int(total_dia_gord - meta_gord)}")

# Barras de Progresso
st.write(f"Progresso da Meta Calórica ({int(total_dia_kcal)}/{int(meta_calorias)})")
st.progress(min(total_dia_kcal/meta_calorias if meta_calorias > 0 else 0, 1.0))
