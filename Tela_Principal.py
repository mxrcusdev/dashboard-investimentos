import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from portfolio_manager import load_portfolio, save_portfolio

# --- Configuração da Página ---
st.set_page_config(
    page_title="Dashboard de Investimentos - Visão Geral",
    page_icon="💹",
    layout="wide"
)

# --- Funções ---
@st.cache_data(ttl=300)
def get_ticker_data(ticker_symbol):
    if not ticker_symbol.endswith('.SA'):
        ticker_symbol += '.SA'
    ticker = yf.Ticker(ticker_symbol)
    try:
        info = ticker.info
        hist = ticker.history(period="1d")
        if hist.empty:
            return None, None
        last_price = hist['Close'].iloc[0]
        return info, last_price
    except Exception:
        return None, None

def format_currency(value):
    return f"R$ {value:,.2f}"

# --- Carregar Carteira ---
st.session_state.portfolio = load_portfolio()

# --- Barra Lateral (Sidebar) ---
st.sidebar.header("Gerenciar Carteira")

# Formulário para adicionar ativo
with st.sidebar.form(key='add_asset_form', clear_on_submit=True):
    st.subheader("Adicionar Ativo")
    ticker_input = st.text_input("Ticker do Ativo (ex: PETR4)", help="Use o ticker da B3, sem o .SA").upper()
    quantity_input = st.number_input("Quantidade", min_value=1, step=1)
    price_input = st.number_input("Preço Médio de Compra (R$)", min_value=0.01, format="%.2f")
    add_button = st.form_submit_button(label='Adicionar/Atualizar Ativo')

    if add_button and ticker_input and quantity_input and price_input:
        portfolio = st.session_state.portfolio
        if ticker_input in portfolio['Ativo'].values:
            portfolio.loc[portfolio['Ativo'] == ticker_input, ['Quantidade', 'Preço Médio']] = [quantity_input, price_input]
            st.sidebar.success(f"Ativo {ticker_input} atualizado!")
        else:
            new_asset = pd.DataFrame([{'Ativo': ticker_input, 'Quantidade': quantity_input, 'Preço Médio': price_input}])
            portfolio = pd.concat([portfolio, new_asset], ignore_index=True)
            st.sidebar.success(f"Ativo {ticker_input} adicionado!")
        st.session_state.portfolio = portfolio
        save_portfolio(st.session_state.portfolio)

# Seção para remover ativo
st.sidebar.subheader("Remover Ativo")
if not st.session_state.portfolio.empty:
    asset_to_remove = st.sidebar.selectbox("Selecione o Ativo para Remover", options=st.session_state.portfolio['Ativo'])
    if st.sidebar.button("Remover Ativo"):
        portfolio = st.session_state.portfolio
        portfolio = portfolio[portfolio['Ativo'] != asset_to_remove]
        st.session_state.portfolio = portfolio
        save_portfolio(st.session_state.portfolio)
        st.sidebar.success(f"Ativo {asset_to_remove} removido!")
        st.rerun()

# --- Dashboard Principal ---
st.title("💹 Dashboard de Investimentos")
st.markdown("Bem-vindo! Adicione ativos na barra lateral para começar a análise.")

if not st.session_state.portfolio.empty:
    portfolio_df = st.session_state.portfolio.copy()
    
    # Processamento dos dados da carteira
    data_rows = []
    progress_bar = st.progress(0, text="Buscando dados dos ativos...")
    for i, row in enumerate(portfolio_df.iterrows()):
        asset = row[1]
        info, last_price = get_ticker_data(asset['Ativo'])
        
        if info and last_price:
            data_rows.append({
                'Ativo': asset['Ativo'],
                'Nome': info.get('longName', 'N/A'),
                'Setor': info.get('sector', 'Não Classificado'),
                'Quantidade': asset['Quantidade'],
                'Preço Médio': asset['Preço Médio'],
                'Cotação Atual': last_price
            })
        else:
            st.warning(f"Não foi possível obter dados para {asset['Ativo']}.")
        
        progress_bar.progress((i + 1) / len(portfolio_df), text=f"Buscando dados de {asset['Ativo']}...")
    
    progress_bar.empty()

    if data_rows:
        processed_df = pd.DataFrame(data_rows)
        processed_df['Custo Total'] = processed_df['Quantidade'] * processed_df['Preço Médio']
        processed_df['Valor Atual'] = processed_df['Quantidade'] * processed_df['Cotação Atual']
        processed_df['Lucro/Prejuízo'] = processed_df['Valor Atual'] - processed_df['Custo Total']
        processed_df['L/P %'] = (processed_df['Lucro/Prejuízo'] / processed_df['Custo Total'])
        
        # --- Métricas Gerais ---
        total_investido = processed_df['Custo Total'].sum()
        patrimonio_total = processed_df['Valor Atual'].sum()
        lucro_prejuizo_total = processed_df['Lucro/Prejuízo'].sum()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Patrimônio Total", format_currency(patrimonio_total))
        with col2:
            st.metric("Total Investido", format_currency(total_investido))
        with col3:
            delta = f"{lucro_prejuizo_total/total_investido:.2%}" if total_investido > 0 else "0.00%"
            st.metric("Lucro/Prejuízo Total", format_currency(lucro_prejuizo_total), delta)
        
        st.divider()

        # --- Tabela Detalhada ---
        st.header("Detalhes da Carteira")
        display_df = processed_df.copy()
        display_df['L/P %'] = display_df['L/P %'].apply(lambda x: f"{x:.2%}")
        st.dataframe(display_df.style.format({
            'Preço Médio': format_currency,
            'Cotação Atual': format_currency,
            'Custo Total': format_currency,
            'Valor Atual': format_currency,
            'Lucro/Prejuízo': format_currency,
        }), width='stretch')

        # --- Gráficos de Alocação ---
        st.header("Alocação da Carteira")
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            fig_pie_asset = px.pie(processed_df, values='Valor Atual', names='Ativo', title='Distribuição por Ativo', hole=.3)
            st.plotly_chart(fig_pie_asset, width='stretch')
        with col_chart2:
            sector_agg = processed_df.groupby('Setor')['Valor Atual'].sum().reset_index()
            fig_pie_sector = px.pie(sector_agg, values='Valor Atual', names='Setor', title='Distribuição por Setor', hole=.3)
            st.plotly_chart(fig_pie_sector, width='stretch')
else:
    st.info("Sua carteira está vazia. Adicione um ativo na barra lateral para começar.")