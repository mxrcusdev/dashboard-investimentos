# 💹 Dashboard de Investimentos Avançado

Este é um dashboard de investimentos completo, construído em Python com a biblioteca Streamlit. A ferramenta permite que o usuário adicione sua carteira de ativos de renda variável, analise estatísticas, projete dividendos e rendimentos, e simule o crescimento do patrimônio a longo prazo através de diferentes metodologias.

---

## Principais Funcionalidades

- **Visão Geral:** Dashboard principal com o valor total da carteira, lucro/prejuízo, e alocação por ativo e por setor.
- **Análise Histórica e Risco:** Compara o desempenho da carteira com o IBOV e calcula métricas de risco como Beta e Índice de Sharpe.
- **Análise de Dividendos:** Mostra o histórico de pagamentos e projeções de renda passiva com base nos dados mais recentes.
- **Projeção de Carteira:** Simulação determinística do crescimento do patrimônio com aportes mensais, comparando cenários com e sem reinvestimento de dividendos.
- **Simulação Monte Carlo:** Uma simulação probabilística avançada que projeta uma gama de resultados futuros possíveis para a carteira, considerando sua volatilidade histórica.
- **Calculadora de Renda Fixa:** Ferramenta para simular rendimentos de ativos atrelados ao CDI, com a opção de usar a Curva de Juros Futuros para projeções mais realistas.

## Tecnologias Utilizadas

- **Python**
- **Streamlit:** Para a criação da interface web interativa.
- **Pandas:** Para manipulação e análise de dados.
- **yfinance:** Para a busca de dados do mercado financeiro (cotações, dividendos).
- **Plotly:** Para a criação de gráficos interativos.
- **Requests:** Para chamadas de API (Taxa Selic/DI).
- **Numpy:** Para cálculos numéricos avançados (Simulação Monte Carlo).

---

## Como Executar Localmente

Siga os passos abaixo para rodar o projeto no seu computador.

1.  **Clone o repositório:**

    ```bash
    git clone https://github.com/Marcus-DevPython/dashboard-investimentos.git
    ```

2.  **Crie e ative um ambiente virtual:**

    ```bash
    python -m venv .venv
    # No Windows
    .venv\Scripts\activate
    # No macOS/Linux
    source .venv/bin/activate
    ```

3.  **Instale as dependências:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Execute o aplicativo Streamlit:**
    ```bash
    streamlit run Tela_Principal.py
    ```

O dashboard abrirá automaticamente no seu navegador.

## Criador
```DC: mxrcus._```


