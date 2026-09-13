from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from configuracao import MOTIVOS_PADRAO, TODOS_PERIODOS


class BancoSQLite:
    def __init__(self, caminho: Path):
        self.conn = sqlite3.connect(caminho)
        self.conn.row_factory = sqlite3.Row
        self._criar_estrutura()

    def _criar_estrutura(self):
        self.conn.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;

            CREATE TABLE IF NOT EXISTS operadores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                matricula TEXT UNIQUE,
                ativo INTEGER NOT NULL DEFAULT 1,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS itens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT NOT NULL UNIQUE,
                descricao TEXT NOT NULL,
                meta_padrao INTEGER NOT NULL DEFAULT 22,
                ativo INTEGER NOT NULL DEFAULT 1,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS motivos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                ativo INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS apontamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                turno TEXT NOT NULL,
                periodo TEXT NOT NULL,
                operador TEXT NOT NULL,
                item_primario TEXT NOT NULL,
                meta_primario INTEGER NOT NULL,
                real_primario INTEGER NOT NULL,
                item_secundario TEXT,
                meta_secundario INTEGER NOT NULL DEFAULT 0,
                real_secundario INTEGER NOT NULL DEFAULT 0,
                parada REAL NOT NULL,
                motivo TEXT NOT NULL,
                observacoes TEXT,
                criado_em TEXT NOT NULL,
                alterado_em TEXT,
                responsavel TEXT,
                UNIQUE(data, turno, periodo)
            );

            CREATE INDEX IF NOT EXISTS idx_apontamentos_data
            ON apontamentos(data);
            CREATE INDEX IF NOT EXISTS idx_apontamentos_turno
            ON apontamentos(data, turno);
            CREATE INDEX IF NOT EXISTS idx_apontamentos_operador
            ON apontamentos(operador);
            CREATE INDEX IF NOT EXISTS idx_apontamentos_item
            ON apontamentos(item_primario);
        """)
        self._migrar_colunas()
        for motivo in MOTIVOS_PADRAO:
            self.conn.execute(
                "INSERT OR IGNORE INTO motivos(nome) VALUES (?)",
                (motivo,),
            )
        self.conn.commit()

    def _migrar_colunas(self):
        existentes = {
            linha["name"]
            for linha in self.conn.execute("PRAGMA table_info(apontamentos)")
        }
        novas = {
            "alterado_em": "TEXT",
            "responsavel": "TEXT",
        }
        for nome, tipo in novas.items():
            if nome not in existentes:
                self.conn.execute(
                    f"ALTER TABLE apontamentos ADD COLUMN {nome} {tipo}"
                )

    def fechar(self):
        self.conn.close()

    def cadastrar_operador(self, nome: str, matricula: str | None):
        self.conn.execute(
            "INSERT INTO operadores(nome,matricula) VALUES (?,?)",
            (nome.strip(), matricula.strip() if matricula else None),
        )
        self.conn.commit()

    def listar_operadores(self):
        return self.conn.execute(
            "SELECT * FROM operadores WHERE ativo=1 ORDER BY nome"
        ).fetchall()

    def cadastrar_item(self, codigo: str, descricao: str, meta: int):
        self.conn.execute(
            "INSERT INTO itens(codigo,descricao,meta_padrao) VALUES (?,?,?)",
            (codigo.strip().upper(), descricao.strip(), meta),
        )
        self.conn.commit()

    def listar_itens(self):
        return self.conn.execute(
            "SELECT * FROM itens WHERE ativo=1 ORDER BY codigo"
        ).fetchall()

    def cadastrar_motivo(self, nome: str):
        self.conn.execute(
            "INSERT INTO motivos(nome) VALUES (?)",
            (nome.strip(),),
        )
        self.conn.commit()

    def listar_motivos(self):
        return self.conn.execute(
            "SELECT * FROM motivos WHERE ativo=1 ORDER BY nome"
        ).fetchall()

    def salvar_apontamento(self, dados: dict[str, Any], registro_id: int | None = None):
        agora = datetime.now().isoformat(timespec="seconds")
        campos = (
            dados["data"], dados["turno"], dados["periodo"], dados["operador"],
            dados["item_primario"], dados["meta_primario"], dados["real_primario"],
            dados.get("item_secundario") or "", dados.get("meta_secundario", 0),
            dados.get("real_secundario", 0), dados["parada"], dados["motivo"],
            dados.get("observacoes", ""), dados.get("responsavel", ""),
        )
        if registro_id:
            self.conn.execute("""
                UPDATE apontamentos SET
                data=?,turno=?,periodo=?,operador=?,item_primario=?,
                meta_primario=?,real_primario=?,item_secundario=?,
                meta_secundario=?,real_secundario=?,parada=?,motivo=?,
                observacoes=?,responsavel=?,alterado_em=?
                WHERE id=?
            """, campos + (agora, registro_id))
        else:
            self.conn.execute("""
                INSERT INTO apontamentos(
                    data,turno,periodo,operador,item_primario,meta_primario,
                    real_primario,item_secundario,meta_secundario,
                    real_secundario,parada,motivo,observacoes,responsavel,
                    criado_em
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, campos + (agora,))
        self.conn.commit()

    def obter_apontamento(self, registro_id: int):
        return self.conn.execute(
            "SELECT * FROM apontamentos WHERE id=?",
            (registro_id,),
        ).fetchone()

    def excluir_apontamento(self, registro_id: int):
        self.conn.execute("DELETE FROM apontamentos WHERE id=?", (registro_id,))
        self.conn.commit()

    def historico(
        self,
        data_inicio: str | None = None,
        data_fim: str | None = None,
        turno: str = "Todos",
        operador: str = "Todos",
        item: str = "Todos",
    ):
        filtros, valores = [], []
        if data_inicio:
            filtros.append("data>=?")
            valores.append(data_inicio)
        if data_fim:
            filtros.append("data<=?")
            valores.append(data_fim)
        if turno != "Todos":
            filtros.append("turno=?")
            valores.append(turno)
        if operador != "Todos":
            filtros.append("operador=?")
            valores.append(operador)
        if item != "Todos":
            filtros.append("(item_primario=? OR item_secundario=?)")
            valores.extend([item, item])
        where = " WHERE " + " AND ".join(filtros) if filtros else ""
        return self.conn.execute(
            "SELECT * FROM apontamentos" + where +
            " ORDER BY data DESC, criado_em DESC",
            valores,
        ).fetchall()

    def apontamentos_dia(self, data: str):
        return self.conn.execute(
            "SELECT * FROM apontamentos WHERE data=? ORDER BY id",
            (data,),
        ).fetchall()

    def cobertura_dia(self, data: str):
        registrados = {
            (r["turno"], r["periodo"]): r
            for r in self.apontamentos_dia(data)
        }
        return [
            {
                "turno": turno,
                "periodo": periodo,
                "status": "REGISTRADO" if (turno, periodo) in registrados else "PENDENTE",
                "registro": registrados.get((turno, periodo)),
            }
            for turno, periodo in TODOS_PERIODOS
        ]

    def indicadores(self, data: str, turno: str = "Todos"):
        filtro = "data=?"
        valores: list[Any] = [data]
        if turno != "Todos":
            filtro += " AND turno=?"
            valores.append(turno)
        row = self.conn.execute(f"""
            SELECT
                COUNT(*) AS periodos,
                COALESCE(SUM(meta_primario),0) AS meta,
                COALESCE(SUM(real_primario),0) AS real,
                COALESCE(SUM(parada),0) AS parada,
                COALESCE(AVG(CASE WHEN meta_primario>0
                    THEN CAST(real_primario AS REAL)/meta_primario END),0) AS eficiencia_media
            FROM apontamentos WHERE {filtro}
        """, valores).fetchone()
        esperados = 24 if turno == "Todos" else 8
        meta, real = row["meta"], row["real"]
        return {
            "periodos": row["periodos"],
            "esperados": esperados,
            "pendentes": max(0, esperados - row["periodos"]),
            "meta": meta,
            "real": real,
            "eficiencia": real / meta if meta else 0,
            "parada": round(row["parada"], 1),
        }

    def resumo_turnos(self, data: str):
        resultado = []
        for turno in ("1º Turno", "2º Turno", "3º Turno"):
            item = self.indicadores(data, turno)
            item["turno"] = turno
            resultado.append(item)
        return resultado

    def pareto_motivos(self, data_inicio: str, data_fim: str, limite: int = 8):
        return self.conn.execute("""
            SELECT motivo, ROUND(SUM(parada),1) AS minutos,
                   COUNT(*) AS ocorrencias
            FROM apontamentos
            WHERE data BETWEEN ? AND ? AND parada>0
            GROUP BY motivo
            ORDER BY minutos DESC
            LIMIT ?
        """, (data_inicio, data_fim, limite)).fetchall()

    def tendencia_diaria(self, data_inicio: str, data_fim: str):
        return self.conn.execute("""
            SELECT data,
                   SUM(meta_primario) AS meta,
                   SUM(real_primario) AS real,
                   ROUND(SUM(parada),1) AS parada
            FROM apontamentos
            WHERE data BETWEEN ? AND ?
            GROUP BY data
            ORDER BY data
        """, (data_inicio, data_fim)).fetchall()
