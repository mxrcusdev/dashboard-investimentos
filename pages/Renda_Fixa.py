import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

st.set_page_config(page_title="Calculadora de CDI", page_icon="🧮", layout="centered")

# --- FUNÇÃO DE API ---
@st.cache_data(ttl=86400) # Cache de 1 dia
def get_current_di_rate():
    """
    Busca a meta anual da Taxa Selic (que serve como proxy para o CDI) 
    diretamente da API do Banco Central.
    """
    try:
        # Série 432: Meta Selic definida pelo Copom (anual)
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        annual_rate_percent = float(data[0]['valor'])
        annual_rate_decimal = annual_rate_percent / 100
        return annual_rate_decimal
        
    except Exception as e:
        st.warning(f"Não foi possível buscar a taxa CDI atualizada ({e}). Usando um valor padrão.")
        # Usando um fallback que reflete a realidade atual (Julho/2025)
        return 0.1500

# --- Função de Cálculo (sem alterações) ---
def calculate_cdi_return(initial_value, period_months, cdi_rate_percent, investment_yield_percent):
    cdi_rate = cdi_rate_percent / 100
    investment_yield = investment_yield_percent / 100
    
    effective_annual_rate = cdi_rate * investment_yield
    
    if 1 + effective_annual_rate > 0:
        monthly_rate = (1 + effective_annual_rate)**(1/12) - 1
    else:
        monthly_rate = -1

    value_history = [initial_value]
    current_value = initial_value

    for month in range(period_months):
        current_value *= (1 + monthly_rate)
        value_history.append(current_value)
        
    final_value = value_history[-1]
    total_interest = final_value - initial_value
    
    return final_value, total_interest, value_history

# --- Interface do Usuário ---

st.image("https://storage.googleapis.com/clara-insider/2022/10/clara-logo-2-1024x284.png", width=200)
st.title("Calculadora de Rendimento CDI")
st.markdown("Simule e projete seus rendimentos com precisão usando nossa ferramenta de cálculo de CDI.")

st.divider()

current_di_rate_decimal = get_current_di_rate()
default_di_rate_percent = current_di_rate_decimal * 100

with st.form(key="cdi_calculator_form"):
    st.subheader("Valor Investido")
    initial_investment = st.number_input(
        "Insira o valor inicial do investimento", 
        label_visibility="collapsed",
        min_value=0.0, 
        value=7000.0, 
        step=100.0, 
        format="%.2f"
    )

    st.subheader("Período em meses")
    investment_period_months = st.number_input(
        "Insira o período do investimento em meses",
        label_visibility="collapsed",
        min_value=1,
        value=24,
        step=1
    )

    st.subheader("Taxa de CDI (% ao ano)")

    cdi_annual_rate = st.number_input(
        "Insira a taxa de CDI anual esperada",
        label_visibility="collapsed",
        min_value=0.0,
        value=default_di_rate_percent, # Usa o valor da API como padrão
        step=0.1,
        format="%.2f"
    )

    st.subheader("Rendimento do CDI (%)")
    percentage_of_cdi = st.number_input(
        "Insira o percentual do CDI que seu investimento rende",
        label_visibility="collapsed",
        min_value=0,
        value=102,
        step=1
    )
    
    submit_button = st.form_submit_button(label="Calcular Retorno")


# --- Exibição dos Resultados ---
if submit_button:
    final_value, total_interest, value_history = calculate_cdi_return(
        initial_investment, 
        investment_period_months, 
        cdi_annual_rate, 
        percentage_of_cdi
    )
    
    st.divider()
    st.header("Resultado do Cálculo")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Valor Investido", f"R$ {initial_investment:,.2f}")
    with col2:
        st.metric("Total em Juros (Bruto)", f"R$ {total_interest:,.2f}")
    with col3:
        st.metric("Valor Final (Bruto)", f"R$ {final_value:,.2f}")
        
    months_axis = list(range(investment_period_months + 1))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=months_axis, y=value_history, mode='lines+markers', name='Patrimônio'))
    fig.update_layout(title='Evolução do Investimento ao Longo do Tempo',
                      xaxis_title='Meses', yaxis_title='Valor (R$)')
    st.plotly_chart(fig, use_container_width=True)

    st.warning(
        "**Atenção:** O resultado exibido é o **valor bruto**, antes da dedução do Imposto de Renda (IR). "
        "A alíquota do IR sobre rendimentos de Renda Fixa é regressiva, variando de 22,5% (até 6 meses) a 15% (acima de 2 anos)."
    )