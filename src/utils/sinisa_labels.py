"""
Dicionário de rótulos amigáveis para os códigos de indicadores do SINISA.

Os códigos originais (ex: IAG0001) são preservados na camada Gold para
rastreabilidade com a fonte oficial. Este arquivo faz a tradução para
exibição no dashboard e relatórios.
"""

SINISA_AGUA_LABELS: dict[str, str] = {
    # Atendimento
    "iag0001": "Atendimento da população total com rede de abastecimento de água",
    "iag0002": "Atendimento da população urbana com rede de abastecimento de água",
    "iag0003": "Atendimento da população rural com rede de abastecimento de água",
    "iag0004": "Atendimento dos domicílios totais com rede de abastecimento de água",
    "iag0005": "Atendimento dos domicílios urbanos com rede de abastecimento de água",
    "iag0006": "Atendimento dos domicílios rurais com rede de abastecimento de água",
    # Infraestrutura
    "iag1001": "Extensão de rede de distribuição de água por ligação",
    "iag1002": "Densidade de economias de água por ligação",
    "iag1003": "Incidência de hidrometração de água",
    "iag1004": "Incidência de economias residenciais ativas de água",
    # Volume e consumo
    "iag2001": "Micromedição de água em relação ao volume disponibilizado para distribuição",
    "iag2002": "Micromedição do volume de água consumido",
    "iag2003": "Macromedição do volume de água na entrada do sistema de distribuição",
    "iag2004": "Consumo micromedido de água por economia",
    "iag2005": "Consumo de água faturado por economia",
    "iag2006": "Consumo total médio per capita de água",
    "iag2007": "Consumo residencial médio per capita de água",
    "iag2008": "Volume de água disponibilizado para distribuição por economia",
    "iag2009": "Consumo total médio de água por economia",
    "iag2010": "Consumo de água em relação ao volume disponibilizado para distribuição",
    "iag2011": "Volume faturado de água em relação ao volume de entrada no sistema de distribuição",
    "iag2012": "Perdas de faturamento de água",
    "iag2013": "Perdas totais de água na distribuição",
    "iag2014": "Perdas totais lineares de água na rede de distribuição",
    "iag2015": "Perdas totais de água por ligação",
    "iag2016": "Incidência de ligações de água setorizadas",
    "iag2023": "Consumo médio de energia elétrica no serviço de abastecimento de água",
    # Qualidade do serviço
    "iag3001": "Economias ativas de água atingidas por paralisações",
    "iag3002": "Economias ativas de água atingidas por interrupções sistemáticas",
    "iag3003": "Tempo médio de reparo de vazamentos de água",
    "iag3004": "Duração média das paralisações",
    "iag3005": "Duração média das interrupções sistemáticas",
    "iag3006": "Incidência de pedidos de ligações de água executados",
    "iag3007": "Incidência de economias atingidas por intermitências",
    "iag3008": "Reclamações de falta de água e vazamentos por economia",
    # Indicadores financeiros e administrativos
    "ifa0001": "Produtividade do pessoal total no serviço de abastecimento de água",
    "ifa0002": "Participação do pessoal próprio no serviço de abastecimento de água",
    "ifa1001": "Receita operacional direta média de usuários de água",
    "ifa1002": "Receita operacional direta total média de água",
    "ifa1003": "Participação da receita operacional indireta na receita operacional total de água",
    "ifa1004": "Evasão de receitas do serviço de água",
    "ifa1005": "Dias de faturamento comprometidos com contas a receber de água",
    "ifa2001": "Desempenho financeiro do serviço de abastecimento de água",
    "ifa2002": "Despesa total média de água incluindo tributos",
    "ifa2003": "Despesa total média de água não incluindo tributos",
    "ifa2004": "Despesa de exploração média de água",
    "ifa2005": "Despesa de exploração média de água por economia ativa",
    "ifa2006": "Despesa média com pessoal próprio do serviço de abastecimento de água",
    "ifa2007": "Despesa média de energia elétrica do serviço de abastecimento de água",
    "ifa2008": "Incidência da despesa de pessoal próprio nas despesas de exploração de água",
    "ifa2009": "Incidência da despesa de pessoal total nas despesas de exploração de água",
    "ifa2010": "Incidência da despesa de energia elétrica nas despesas de exploração de água",
    "ifa2011": "Margem da despesa de exploração de água",
    "ifa2012": "Margem da despesa com pessoal próprio do serviço de abastecimento de água",
    "ifa2013": "Margem da despesa com pessoal total do serviço de abastecimento de água",
    "ifa2014": "Margem da despesa com serviço da dívida de água",
    "ifa2016": "Suficiência de caixa do serviço de abastecimento de água",
}
