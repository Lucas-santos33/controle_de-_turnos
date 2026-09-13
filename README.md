# Sistema profissional de gestão Hora a Hora — SQLite

Sistema local para apontamento, supervisão e análise da produção durante
24 horas, iniciando às 06:30. Não exige internet nem bibliotecas externas.

## Iniciar

No Windows, execute:

`iniciar_windows.bat`

Ou pelo terminal:

`python app.py`

O banco `hora_a_hora.db` será criado automaticamente.

## Turnos controlados

- 1º turno: 06:30–14:30;
- 2º turno: 14:30–22:30;
- 3º turno: 22:30–06:30.

O painel mostra todas as 24 faixas de uma hora. Cada faixa aparece como
`REGISTRADO` ou `PENDENTE`, facilitando a cobrança e o fechamento diário.

## Painel de supervisão

Para cada data e turno, o painel apresenta:

- períodos preenchidos e pendentes;
- meta registrada;
- produção realizada;
- eficiência;
- tempo total de parada;
- resumo individual dos três turnos;
- principais motivos de perda do dia;
- tabela completa das 24 horas.

## Apontamentos

Cada registro contém:

- data, turno e período;
- operador;
- responsável pelo registro;
- item primário, meta e realizado;
- item secundário opcional;
- parada calculada;
- motivo;
- observações;
- data/hora de criação e alteração.

Os registros podem ser incluídos, editados e excluídos. O banco impede dois
apontamentos para a mesma data, turno e período.

## Cálculo da parada

```text
tempo de parada = 60 − (realizado primário / meta primária × 60)
```

Com meta 22:

| Realizado | Parada |
|---:|---:|
| 22 | 0,0 min |
| 18 | 10,9 min |
| 11 | 30,0 min |
| 0 | 60,0 min |

O item secundário não é somado porque os dois itens são produzidos
simultaneamente.

## Histórico e análises

O histórico possui filtros por:

- período de datas;
- turno;
- operador;
- item.

A área gerencial contém:

- Pareto de minutos de parada por motivo;
- tendência diária de meta, realizado, eficiência e parada;
- relatório CSV detalhado;
- resumo CSV gerencial por turno.

## Cadastros

- operadores e matrículas;
- itens, descrições e metas;
- motivos de parada.

## Arquivos

- `app.py`: inicialização;
- `app_profissional.py`: interface de gestão;
- `database_sqlite.py`: banco e consultas;
- `configuracao.py`: turnos, horários e meta;
- `calculos.py`: cálculo da parada e eficiência;
- `hora_a_hora.db`: banco criado automaticamente.

Faça cópia de segurança periódica do arquivo `hora_a_hora.db`.
