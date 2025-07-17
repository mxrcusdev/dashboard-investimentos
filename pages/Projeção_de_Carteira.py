import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import plotly.graph_objects as go
from portfolio_manager import load_portfolio

st.set_page_config(page_title="Simulação Monte Carlo", page_icon="🎲", layout="wide")

st.title("🎲 Simulação de Monte Carlo para Projeção de Carteira")
st.markdown("Uma simulação probabilística que considera a volatilidade para estimar uma gama de resultados futuros possíveis.")

# --- Funções Auxiliares (sem alterações) ---

@st.cache_data(ttl=3600)
def get_portfolio_stats(p_df, period="5y"):
    if p_df.empty:
        return 0, 0, 0, 0

    tickers_sa = [t + '.SA' for t in p_df['Ativo'].tolist()]
    
    hist_data = yf.download(tickers_sa, period=period, auto_adjust=True, progress=False)['Close']
    if hist_data.empty:
        return 0, 0, 0, 0
    latest_prices = hist_data.iloc[-1]
    
    p_df['Preco Atual'] = p_df['Ativo'].apply(lambda x: latest_prices.get(x + '.SA'))
    p_df.dropna(subset=['Preco Atual'], inplace=True)
    p_df['Valor Atual'] = p_df['Quantidade'] * p_df['Preco Atual']
    
    initial_value = p_df['Valor Atual'].sum()
    if initial_value == 0: return 0, 0, 0, 0
    p_df['Peso'] = p_df['Valor Atual'] / initial_value
    weights = p_df['Valor Atual'] / initial_value
    weights.index = p_df['Ativo'] + '.SA'
    
    daily_returns = hist_data.pct_change().dropna()
    portfolio_daily_returns = (daily_returns * weights).sum(axis=1)
    
    drift = portfolio_daily_returns.mean()
    volatility = portfolio_daily_returns.std()
    
    total_yield = 0
    for ticker_sa in tickers_sa:
        try:
            info = yf.Ticker(ticker_sa).info
            dy = info.get('dividendYield', 0) or 0
            if dy > 1: dy /= 100
            ativo = ticker_sa.replace('.SA', '')
            peso_ativo = p_df.loc[p_df['Ativo'] == ativo, 'Peso'].iloc[0]
            total_yield += dy * peso_ativo
        except (KeyError, IndexError):
            continue

    return initial_value, drift, volatility, total_yield

# --- FUNÇÃO DE SIMULAÇÃO MODIFICADA ---
def run_monte_carlo_simulation(initial_value, drift, volatility, dividend_yield, years, monthly_contribution, num_simulations, reinvest_dividends=True):
    num_days = years * 252
    
    all_paths = np.zeros((num_days + 1, num_simulations))
    all_paths[0] = initial_value
    
    accumulated_dividends = np.zeros((num_days + 1, num_simulations))
    
    for i in range(num_simulations):
        current_value = initial_value
        current_dividends = 0
        
        for day in range(1, num_days + 1):
            random_shock = np.random.normal(0, 1)
            daily_return = drift + volatility * random_shock
            current_value *= (1 + daily_return)
            
            if day % 21 == 0:
                # Calcula os dividendos do mês ANTES de adicionar o aporte
                monthly_dividend_return = (1 + dividend_yield)**(1/12) - 1
                dividends_this_month = current_value * monthly_dividend_return
                current_dividends += dividends_this_month
                
                # Adiciona aporte
                current_value += monthly_contribution
                
                # Reinveste se a opção estiver marcada
                if reinvest_dividends:
                    current_value += dividends_this_month
            
            all_paths[day, i] = current_value
            accumulated_dividends[day, i] = current_dividends
            
    return all_paths, accumulated_dividends

# --- Interface do Usuário ---
portfolio_df = load_portfolio()

if portfolio_df.empty:
    st.warning("Sua carteira está vazia. Adicione ativos na página 'Visão Geral' para usar a simulação.")
    st.stop()

st.sidebar.header("Parâmetros da Simulação")
projection_years_option = st.sidebar.slider("Período de Projeção (Anos)", 1, 30, 10)
monthly_contribution_option = st.sidebar.number_input("Aporte Mensal (R$)", value=500, step=100)
num_simulations_option = st.sidebar.select_slider("Número de Simulações", options=[100, 500, 1000, 5000, 10000], value=1000)
reinvest_dividends_option = st.sidebar.checkbox("Reinvestir Dividendos", value=True)

if st.sidebar.button("Rodar Simulação de Monte Carlo"):
    with st.spinner(f"Rodando {num_simulations_option} simulações... Isso pode levar um momento."):
        initial_value, drift, volatility, dividend_yield = get_portfolio_stats(portfolio_df.copy())

        if initial_value == 0:
            st.error("Não foi possível calcular o valor inicial da sua carteira. Verifique os tickers.")
        else:
            st.header("Sumário da Carteira Atual")
            col_sumario1, col_sumario2 = st.columns(2)
            with col_sumario1:
                st.metric("Patrimônio Atual (Base da Simulação)", f"R$ {initial_value:,.2f}")
            with col_sumario2:
                fiis_df = portfolio_df[portfolio_df['Ativo'].str.endswith('11')]
                if not fiis_df.empty:
                    st.write("**FIIs na Carteira:**")
                    st.dataframe(fiis_df[['Ativo', 'Quantidade']], hide_index=True)
                else:
                    st.info("Nenhum Fundo Imobiliário (FII) encontrado na sua carteira.")
            st.divider()

            simulation_paths, dividend_paths = run_monte_carlo_simulation(
                initial_value, drift, volatility, dividend_yield, projection_years_option, 
                monthly_contribution_option, num_simulations_option, reinvest_dividends_option
            )
            
            final_results = simulation_paths[-1]
            final_dividends = dividend_paths[-1]

            st.header("Resultados da Simulação")
            
            p10 = np.percentile(final_results, 10)
            p50 = np.percentile(final_results, 50)
            p90 = np.percentile(final_results, 90)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Cenário Pessimista (10%)", f"R$ {p10:,.2f}")
            with col2:
                st.metric("Cenário Mediano (50%)", f"R$ {p50:,.2f}")
            with col3:
                st.metric("Cenário Otimista (90%)", f"R$ {p90:,.2f}")

            st.subheader("Projeção de Renda Passiva (Dividendos)")
            
            # Calcula a média dos dividendos totais recebidos em todas as simulações
            avg_total_dividends = np.mean(final_dividends)
            avg_annual_dividends = avg_total_dividends / projection_years_option
            avg_monthly_dividends = avg_annual_dividends / 12

            col_div1, col_div2, col_div3 = st.columns(3)
            with col_div1:
                st.metric("Total de Dividendos Acumulados (Média)", f"R$ {avg_total_dividends:,.2f}", help="Valor médio total que você teria recebido em dividendos ao final do período.")
            with col_div2:
                st.metric("Média Anual de Dividendos", f"R$ {avg_annual_dividends:,.2f}", help="A média de dividendos que você receberia por ano.")
            with col_div3:
                st.metric("Média Mensal de Dividendos", f"R$ {avg_monthly_dividends:,.2f}", help="A renda passiva mensal média projetada.")

            fig_hist = go.Figure(data=[go.Histogram(x=final_results, nbinsx=100, name="Distribuição")])
            fig_hist.add_vline(x=p10, line_width=2, line_dash="dash", line_color="red", annotation_text="P10")
            fig_hist.add_vline(x=p50, line_width=3, line_dash="dash", line_color="yellow", annotation_text="Mediana P50")
            fig_hist.add_vline(x=p90, line_width=2, line_dash="dash", line_color="green", annotation_text="P90")
            fig_hist.update_layout(title_text=f'Distribuição dos Resultados Finais Após {projection_years_option} Anos',
                                 xaxis_title='Patrimônio Final Projetado (R$)', yaxis_title='Frequência')
            st.plotly_chart(fig_hist, use_container_width=True)

            st.divider()
            st.header("Evolução do Patrimônio (Caminhos da Simulação)")

            p10_path = np.percentile(simulation_paths, 10, axis=1)
            p50_path = np.percentile(simulation_paths, 50, axis=1)
            p90_path = np.percentile(simulation_paths, 90, axis=1)
            
            time_axis = list(range(projection_years_option * 252 + 1))

            fig_paths = go.Figure()
            fig_paths.add_trace(go.Scatter(x=time_axis, y=p10_path, fill=None, mode='lines', line_color='rgba(255,0,0,0.2)', name='P10'))
            fig_paths.add_trace(go.Scatter(x=time_axis, y=p90_path, fill='tonexty', mode='lines', line_color='rgba(0,255,0,0.2)', name='P90 (Intervalo de Confiança)'))
            fig_paths.add_trace(go.Scatter(x=time_axis, y=p50_path, mode='lines', name='Caminho Mediano (P50)', line=dict(color='yellow', width=3)))

            fig_paths.update_layout(
                title_text='Projeção da Evolução do Patrimônio ao Longo do Tempo',
                xaxis_title='Dias de Investimento',
                yaxis_title='Patrimônio Projetado (R$)',
                legend_title='Cenários'
            )
            st.plotly_chart(fig_paths, use_container_width=True)
            st.info("Este gráfico mostra a evolução do caminho mediano (linha amarela) e a faixa de prováveis resultados (área sombreada entre os cenários pessimista e otimista) ao longo do tempo.")
            
            st.info(f"As premissas para a simulação foram um retorno médio diário de **{drift:.5f}** e uma volatilidade diária de **{volatility:.5f}**, calculados com base no histórico dos últimos 5 anos da sua carteira.")
else:
    st.info("Ajuste os parâmetros na barra lateral e clique em 'Rodar Simulação de Monte Carlo' para ver as projeções.")