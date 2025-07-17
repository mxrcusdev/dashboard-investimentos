import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import plotly.graph_objects as go
from portfolio_manager import load_portfolio
import requests

st.set_page_config(page_title="Análise Histórica e Risco", page_icon="📈", layout="wide")

st.title("📈 Análise Histórica e Métricas de Risco")

# --- FUNÇÃO get_selic_rate TOTALMENTE ATUALIZADA ---
@st.cache_data(ttl=86400)
def get_selic_rate():
    """
    Busca a meta anual da Taxa Selic diretamente da API do Banco Central.
    Série 432: Meta Selic definida pelo Copom (anual). Esta abordagem é mais robusta.
    """
    try:
        # URL para a meta anual da Selic
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # O valor já vem como uma taxa anual (ex: 8.75 para 8.75%)
        annual_rate_percent = float(data[0]['valor'])
        
        # Apenas convertemos para decimal
        annual_rate_decimal = annual_rate_percent / 100
        
        st.success(f"Taxa Selic atualizada com sucesso: {annual_rate_decimal:.2%}")
        return annual_rate_decimal
        
    except (requests.exceptions.RequestException, IndexError, ValueError, KeyError) as e:
        st.error(f"Erro ao buscar a taxa Selic atualizada: {e}")
        st.warning("Usando uma taxa Selic padrão de 8.75% a.a. como fallback.")
        return 0.0875 # Usando um fallback mais recente

@st.cache_data(ttl=3600)
def get_historical_data(tickers, period):
    data = yf.download(tickers, period=period, auto_adjust=True, progress=False)
    return data['Close'] if not data.empty else pd.DataFrame()

@st.cache_data(ttl=3600)
def get_benchmark_data(benchmark_ticker, period):
    data = yf.download(benchmark_ticker, period=period, auto_adjust=True, progress=False)
    return data['Close'] if not data.empty else pd.Series()

# --- Lógica Principal ---
portfolio_df = load_portfolio()

if portfolio_df.empty:
    st.warning("Sua carteira está vazia. Adicione ativos na página 'Visão Geral' primeiro.")
    st.stop()

selic_anual = get_selic_rate()
periodo = st.selectbox("Selecione o Período de Análise:", ['3mo', '6mo', '1y', '2y', '5y', 'max'], index=0)

with st.spinner("Calculando desempenho histórico e métricas de risco..."):
    tickers_sa = [t + '.SA' for t in portfolio_df['Ativo'].tolist()]
    
    try:
        latest_prices_df = yf.download(tickers_sa, period='2d', auto_adjust=True, progress=False)
        
        if latest_prices_df.empty:
            st.error("Não foi possível obter cotações recentes para calcular os pesos. Verifique a conexão ou os tickers.")
            st.stop()

        latest_prices = latest_prices_df['Close'].iloc[-1]
        
        calc_df = portfolio_df.copy()
        calc_df['Ticker.SA'] = calc_df['Ativo'] + '.SA'
        calc_df['Preco Atual'] = calc_df['Ticker.SA'].map(latest_prices)
        calc_df.dropna(subset=['Preco Atual'], inplace=True)
        
        if calc_df.empty:
            st.error("Não foi possível encontrar a cotação atual para nenhum dos ativos da carteira.")
            st.stop()

        calc_df['Valor Atual'] = calc_df['Quantidade'] * calc_df['Preco Atual']
        total_value = calc_df['Valor Atual'].sum()

        if total_value == 0:
            st.error("O valor total da carteira é zero. Não é possível calcular os pesos.")
            st.stop()

        pesos = calc_df['Valor Atual'] / total_value
        pesos.index = calc_df['Ticker.SA']

    except Exception as e:
        st.error(f"Ocorreu um erro ao calcular os pesos da carteira: {e}")
        st.stop()

    ativos_hist = get_historical_data(tickers_sa, periodo)
    ibov_hist = get_benchmark_data('^BVSP', periodo)

    if ativos_hist.empty or ibov_hist.empty:
        st.error("Não foi possível obter dados históricos para os ativos ou para o IBOV.")
        st.stop()
        
    retornos_ativos = ativos_hist.pct_change().dropna()
    retornos_ibov = ibov_hist.pct_change().dropna()
    
    pesos_alinhados = pesos.reindex(retornos_ativos.columns).fillna(0)
    
    if pesos_alinhados.sum() == 0:
        st.error("Todos os pesos da carteira são zero após o alinhamento. A análise não pode continuar.")
        st.stop()

    retorno_carteira = (retornos_ativos * pesos_alinhados).sum(axis=1)

    df_comparativo = pd.DataFrame({
        'Carteira': retorno_carteira.squeeze(),
        'IBOV': retornos_ibov.squeeze()
    }).dropna()

    desempenho_acumulado = (1 + df_comparativo).cumprod()
    desempenho_acumulado = desempenho_acumulado / desempenho_acumulado.iloc[0]

    # Cálculo de Métricas
    retorno_medio_diario = df_comparativo['Carteira'].mean()
    retorno_anualizado = ((1 + retorno_medio_diario) ** 252) - 1
    volatilidade_diaria = df_comparativo['Carteira'].std()
    volatilidade_anualizada = volatilidade_diaria * np.sqrt(252)
    
    covariancia = df_comparativo['Carteira'].cov(df_comparativo['IBOV'])
    variancia_ibov = df_comparativo['IBOV'].var()
    beta = covariancia / variancia_ibov

    taxa_livre_risco_diaria = (1 + selic_anual) ** (1/252) - 1
    if volatilidade_diaria == 0:
        sharpe_ratio = 0
    else:
        sharpe_ratio = (retorno_medio_diario - taxa_livre_risco_diaria) / volatilidade_diaria * np.sqrt(252)

# --- Exibição dos Resultados ---
st.header("Métricas de Risco e Retorno")
st.markdown(f"Análise para o período de **{periodo}**.")
st.caption(f"Taxa Selic anualizada (livre de risco) utilizada nos cálculos: **{selic_anual:.2%}** (Fonte: BCB)")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Retorno Anualizado", f"{retorno_anualizado:.2%}")
col2.metric("Volatilidade Anualizada", f"{volatilidade_anualizada:.2%}")
col3.metric("Índice de Sharpe", f"{sharpe_ratio:.2f}")
col4.metric("Beta (β) da Carteira", f"{beta:.2f}")

st.header("Desempenho Histórico vs. IBOV")
fig = go.Figure()
if not df_comparativo['Carteira'].eq(0).all():
    fig.add_trace(go.Scatter(x=desempenho_acumulado.index, y=desempenho_acumulado['Carteira'], mode='lines', name='Minha Carteira'))
fig.add_trace(go.Scatter(x=desempenho_acumulado.index, y=desempenho_acumulado['IBOV'], mode='lines', name='IBOV', line=dict(dash='dot')))
fig.update_layout(title='Desempenho Acumulado Normalizado', yaxis_title='Desempenho (Base 1)', xaxis_title='Data')
st.plotly_chart(fig, use_container_width=True)