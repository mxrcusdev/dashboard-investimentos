import streamlit as st
import pandas as pd
import yfinance as yf
from portfolio_manager import load_portfolio
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Análise de Dividendos", page_icon="💰", layout="wide")

st.title("💰 Análise Avançada de Dividendos")

def format_currency(value):
    return f"R$ {value:,.2f}"

@st.cache_data(ttl=3600)
def get_advanced_dividend_info(ticker_symbol):
    if not ticker_symbol.endswith('.SA'):
        ticker_symbol += '.SA'
    ticker = yf.Ticker(ticker_symbol)
    info = ticker.info
    dividends_hist = ticker.dividends
    return info, dividends_hist

# --- Carregar Carteira ---
portfolio_df = load_portfolio()

if portfolio_df.empty:
    st.warning("Sua carteira está vazia. Adicione ativos na página 'Visão Geral' primeiro.")
    st.stop()

# --- Lógica de Cálculo de Dividendos ---
dividend_data = []
with st.spinner("Buscando dados avançados de dividendos..."):
    for index, row in portfolio_df.iterrows():
        ticker = row['Ativo']
        quantity = row['Quantidade']
        avg_price = row['Preço Médio']
        
        info, dividends_hist = get_advanced_dividend_info(ticker)
        
        forward_annual_dividend_rate = info.get('dividendRate')
        if forward_annual_dividend_rate:
            annual_projection = forward_annual_dividend_rate * quantity
        else:
            annual_projection = dividends_hist.last('365d').sum() * quantity

        current_yield = info.get('dividendYield', 0) or 0
        
        if current_yield > 1:
            current_yield = current_yield / 100
            
        cost_basis = quantity * avg_price
        yield_on_cost = (annual_projection / cost_basis) if cost_basis > 0 else 0
        
        ex_dividend_date_ts = info.get('exDividendDate')
        ex_dividend_date = pd.to_datetime(ex_dividend_date_ts, unit='s') if ex_dividend_date_ts else None
        
        dividend_data.append({
            'Ativo': ticker,
            'Projeção Anual (R$)': annual_projection,
            'Yield on Cost Projetado': yield_on_cost,
            'Dividend Yield (Atual)': current_yield,
            'Próxima Data Ex-Div': ex_dividend_date,
            'Histórico de Pagamentos': dividends_hist.tail(5).to_dict()
        })

div_df = pd.DataFrame(dividend_data)

# --- Exibição dos Resultados ---
total_projected_dividends = div_df['Projeção Anual (R$)'].sum()
total_invested = (portfolio_df['Quantidade'] * portfolio_df['Preço Médio']).sum()
overall_yoc = (total_projected_dividends / total_invested) if total_invested > 0 else 0

st.header("Projeções e Métricas Gerais")
col1, col2, col3 = st.columns(3)
col1.metric(
    "Projeção de Dividendos Anuais", 
    format_currency(total_projected_dividends), 
    help="Projeção baseada na taxa de dividendo futura anunciada ('dividendRate') ou, como alternativa, na soma dos últimos 12 meses."
)
col2.metric(
    "Yield on Cost Médio (YOC)", 
    f"{overall_yoc:.2%}", 
    help="Rendimento da projeção anual de dividendos sobre o seu custo total de aquisição."
)
temp_portfolio = portfolio_df.merge(div_df[['Ativo', 'Dividend Yield (Atual)']], on='Ativo')
temp_portfolio['Custo Total'] = temp_portfolio['Quantidade'] * temp_portfolio['Preço Médio']
if total_invested > 0:
    weighted_dy = (temp_portfolio['Dividend Yield (Atual)'] * temp_portfolio['Custo Total']).sum() / total_invested
else:
    weighted_dy = 0
col3.metric(
    "Dividend Yield Médio (Atual)",
    f"{weighted_dy:.2%}",
    help="Média ponderada do Dividend Yield de cada ativo, com base no valor investido."
)

st.divider()

st.header("Calendário de Dividendos (Próximas Datas Ex)")
upcoming_dividends = div_df[div_df['Próxima Data Ex-Div'].notna()].copy()
upcoming_dividends = upcoming_dividends[upcoming_dividends['Próxima Data Ex-Div'] >= datetime.now()]

if not upcoming_dividends.empty:
    upcoming_dividends['Próxima Data Ex-Div'] = upcoming_dividends['Próxima Data Ex-Div'].dt.strftime('%d/%m/%Y')
    st.dataframe(
        upcoming_dividends[['Ativo', 'Próxima Data Ex-Div']].sort_values(by='Próxima Data Ex-Div').reset_index(drop=True),
        width='stretch'
    )
else:
    st.info("Nenhum dividendo futuro anunciado encontrado para os ativos da sua carteira no momento.")

st.divider()

st.header("Análise Detalhada por Ativo")
fig = px.bar(
    div_df, x='Ativo', y='Projeção Anual (R$)', 
    title='Contribuição de Dividendos por Ativo (Projeção Anual)',
    labels={'Projeção Anual (R$)': 'Valor Projetado (R$)'},
    color='Ativo',
    text='Projeção Anual (R$)'
)
fig.update_traces(texttemplate='R$ %{text:.2f}', textposition='outside')
st.plotly_chart(fig, width='stretch')

for index, row in div_df.sort_values(by='Projeção Anual (R$)', ascending=False).iterrows():
    header = f"**{row['Ativo']}** | Projeção Anual: {format_currency(row['Projeção Anual (R$)'])} | YOC: {row['Yield on Cost Projetado']:.2%} | DY Atual: {row['Dividend Yield (Atual)']:.2%}"
    with st.expander(header):
        if not row['Histórico de Pagamentos']:
            st.write("Nenhum dividendo registrado no histórico recente para este ativo.")
        else:
            st.subheader("Histórico Recente de Pagamentos")
            hist_df = pd.DataFrame.from_dict(row['Histórico de Pagamentos'], orient='index', columns=['Valor por Ação (R$)'])
            
            # --- CORREÇÃO FINAL: Removida a linha que causava o erro ---
            # A linha abaixo foi removida, pois o índice já estava no formato correto de data
            # hist_df.index = pd.to_datetime(hist_df.index, dayfirst=True) 
            
            hist_df = hist_df.sort_index(ascending=False)
            hist_df.index = hist_df.index.strftime('%d/%m/%Y')
            hist_df.index.name = 'Data de Pagamento'
            st.table(hist_df.style.format({'Valor por Ação (R$)': '{:,.4f}'}))

st.info("**Nota:** As projeções são baseadas em dados de mercado e não constituem uma garantia de retornos futuros. 'Data Ex' é a data limite para possuir o ativo e ter direito ao provento.")