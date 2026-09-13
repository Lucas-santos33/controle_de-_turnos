def calcular_tempo_parada(
    realizado: int,
    meta: int = 22,
    minutos_periodo: float = 60.0,
) -> float:
    """
    Calcula a parada estimada pela perda de produção.

    Com meta 22 em 60 minutos:
    - ciclo teórico = 60 / 22 = 2,727 min/peça;
    - tempo produtivo = realizado * ciclo teórico;
    - parada = 60 - tempo produtivo.
    """
    if meta <= 0:
        raise ValueError("A meta deve ser maior que zero.")
    if realizado < 0:
        raise ValueError("O realizado não pode ser negativo.")
    tempo_produtivo = (realizado / meta) * minutos_periodo
    return round(max(0.0, min(minutos_periodo, minutos_periodo - tempo_produtivo)), 1)


def calcular_eficiencia(realizado: int, meta: int = 22) -> float:
    if meta <= 0:
        raise ValueError("A meta deve ser maior que zero.")
    return realizado / meta

