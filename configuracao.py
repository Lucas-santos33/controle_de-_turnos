TURNOS = {
    "1º Turno": [
        "06:30-07:30", "07:30-08:30", "08:30-09:30", "09:30-10:30",
        "10:30-11:30", "11:30-12:30", "12:30-13:30", "13:30-14:30",
    ],
    "2º Turno": [
        "14:30-15:30", "15:30-16:30", "16:30-17:30", "17:30-18:30",
        "18:30-19:30", "19:30-20:30", "20:30-21:30", "21:30-22:30",
    ],
    "3º Turno": [
        "22:30-23:30", "23:30-00:30", "00:30-01:30", "01:30-02:30",
        "02:30-03:30", "03:30-04:30", "04:30-05:30", "05:30-06:30",
    ],
}

TODOS_PERIODOS = [
    (turno, periodo)
    for turno, periodos in TURNOS.items()
    for periodo in periodos
]

META_PADRAO = 22
MINUTOS_PERIODO = 60

MOTIVOS_PADRAO = [
    "Sem parada",
    "Falta de material",
    "Manutenção",
    "Qualidade",
    "Setup/Troca",
    "Falta de operador",
    "Logística",
    "Outro",
]
