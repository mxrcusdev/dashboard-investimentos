import pandas as pd
import os

PORTFOLIO_FILE = "portfolio.csv"

def load_portfolio():
    """Carrega a carteira de um arquivo CSV. Se não existir, cria um DataFrame vazio."""
    if os.path.exists(PORTFOLIO_FILE):
        return pd.read_csv(PORTFOLIO_FILE)
    else:
        return pd.DataFrame(columns=['Ativo', 'Quantidade', 'Preço Médio'])

def save_portfolio(df):
    """Salva o DataFrame da carteira em um arquivo CSV."""
    df.to_csv(PORTFOLIO_FILE, index=False)