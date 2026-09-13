import csv
import sqlite3
import tkinter as tk
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from calculos import calcular_tempo_parada
from configuracao import META_PADRAO, TURNOS
from database_sqlite import BancoSQLite

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "hora_a_hora.db"


class SistemaSupervisao(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sistema de Gestão Hora a Hora")
        self.geometry("1420x860")
        self.minsize(1180, 720)
        self.configure(bg="#e9eef5")
        self.db = BancoSQLite(DB_PATH)
        self.registro_id = None
        self._estilos()
        self._interface()
        self._atualizar_cadastros()
        self._atualizar_supervisao()
        self._atualizar_historico()
        self.protocol("WM_DELETE_WINDOW", self._fechar)

    def _estilos(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TFrame", background="#e9eef5")
        s.configure("Card.TFrame", background="#ffffff")
        s.configure(
            "Header.TLabel", background="#12395b", foreground="white",
            font=("Segoe UI", 19, "bold"), padding=15,
        )
        s.configure(
            "Section.TLabel", background="#ffffff", foreground="#12395b",
            font=("Segoe UI", 11, "bold"),
        )
        s.configure(
            "Kpi.TLabel", background="#ffffff", foreground="#12395b",
            font=("Segoe UI", 21, "bold"),
        )
        s.configure(
            "Treeview", rowheight=27, font=("Segoe UI", 9),
            background="white", fieldbackground="white",
        )
        s.configure(
            "Treeview.Heading", background="#1d537d", foreground="white",
            font=("Segoe UI", 9, "bold"),
        )
        s.configure(
            "Primary.TButton", background="#1976d2", foreground="white",
            padding=8, font=("Segoe UI", 10, "bold"),
        )

    def _interface(self):
        ttk.Label(
            self,
            text="GESTÃO DE PRODUÇÃO — HORA A HORA",
            style="Header.TLabel",
        ).pack(fill="x")
        faixa = ttk.Frame(self, padding=(14, 5))
        faixa.pack(fill="x")
        ttk.Label(
            faixa,
            text="SQLite local • 24 horas • 3 turnos • início 06:30",
            foreground="#475467",
        ).pack(side="left")
        self.lbl_status = ttk.Label(
            faixa, text="● Sistema operacional", foreground="#14804a"
        )
        self.lbl_status.pack(side="right")

        self.abas = ttk.Notebook(self)
        self.abas.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.aba_supervisao = ttk.Frame(self.abas, padding=12)
        self.aba_apontamento = ttk.Frame(self.abas, padding=12)
        self.aba_historico = ttk.Frame(self.abas, padding=12)
        self.aba_analises = ttk.Frame(self.abas, padding=12)
        self.aba_cadastros = ttk.Frame(self.abas, padding=12)
        self.abas.add(self.aba_supervisao, text="Painel de supervisão")
        self.abas.add(self.aba_apontamento, text="Novo apontamento")
        self.abas.add(self.aba_historico, text="Histórico")
        self.abas.add(self.aba_analises, text="Análises gerenciais")
        self.abas.add(self.aba_cadastros, text="Cadastros")
        self._criar_supervisao()
        self._criar_apontamento()
        self._criar_historico()
        self._criar_analises()
        self._criar_cadastros()

    def _criar_supervisao(self):
        filtros = ttk.Frame(self.aba_supervisao)
        filtros.pack(fill="x", pady=(0, 8))
        self.data_painel = tk.StringVar(value=date.today().isoformat())
        self.turno_painel = tk.StringVar(value="Todos")
        ttk.Label(filtros, text="Data de produção").pack(side="left")
        ttk.Entry(filtros, textvariable=self.data_painel, width=13).pack(
            side="left", padx=(5, 15)
        )
        ttk.Label(filtros, text="Turno").pack(side="left")
        ttk.Combobox(
            filtros, textvariable=self.turno_painel,
            values=["Todos"] + list(TURNOS), state="readonly", width=13,
        ).pack(side="left", padx=5)
        ttk.Button(
            filtros, text="Atualizar painel", style="Primary.TButton",
            command=self._atualizar_supervisao,
        ).pack(side="left", padx=8)
        ttk.Button(
            filtros, text="Exportar resumo gerencial",
            command=self._exportar_resumo,
        ).pack(side="right")

        kpis = ttk.Frame(self.aba_supervisao)
        kpis.pack(fill="x", pady=6)
        self.kpis = {}
        titulos = [
            ("cobertura", "Períodos preenchidos"),
            ("pendentes", "Períodos pendentes"),
            ("meta", "Meta registrada"),
            ("real", "Produção realizada"),
            ("eficiencia", "Eficiência"),
            ("parada", "Parada estimada"),
        ]
        for i, (chave, titulo) in enumerate(titulos):
            card = ttk.Frame(kpis, style="Card.TFrame", padding=12)
            card.grid(row=0, column=i, sticky="ew", padx=4)
            kpis.columnconfigure(i, weight=1)
            ttk.Label(card, text=titulo, background="white").pack()
            self.kpis[chave] = ttk.Label(card, text="0", style="Kpi.TLabel")
            self.kpis[chave].pack()

        area = ttk.Panedwindow(self.aba_supervisao, orient="horizontal")
        area.pack(fill="both", expand=True, pady=8)
        esquerda = ttk.Frame(area, style="Card.TFrame", padding=8)
        direita = ttk.Frame(area, style="Card.TFrame", padding=8)
        area.add(esquerda, weight=3)
        area.add(direita, weight=2)

        ttk.Label(
            esquerda, text="Cobertura das 24 horas", style="Section.TLabel"
        ).pack(anchor="w", pady=(0, 6))
        self.tabela_cobertura = ttk.Treeview(
            esquerda,
            columns=("turno", "periodo", "status", "operador", "item", "real", "parada"),
            show="headings",
        )
        for c, t, w in [
            ("turno", "Turno", 90), ("periodo", "Período", 105),
            ("status", "Situação", 100), ("operador", "Operador", 130),
            ("item", "Item", 100), ("real", "Real", 60), ("parada", "Parada", 70),
        ]:
            self.tabela_cobertura.heading(c, text=t)
            self.tabela_cobertura.column(c, width=w, anchor="center")
        self.tabela_cobertura.tag_configure("ok", background="#dff3e4")
        self.tabela_cobertura.tag_configure("pendente", background="#fff2cc")
        self.tabela_cobertura.pack(fill="both", expand=True)

        ttk.Label(
            direita, text="Resumo por turno", style="Section.TLabel"
        ).pack(anchor="w", pady=(0, 6))
        self.tabela_turnos = ttk.Treeview(
            direita,
            columns=("turno", "cobertura", "meta", "real", "efic", "parada"),
            show="headings",
            height=5,
        )
        for c, t, w in [
            ("turno", "Turno", 85), ("cobertura", "Cobertura", 80),
            ("meta", "Meta", 65), ("real", "Real", 65),
            ("efic", "Eficiência", 75), ("parada", "Parada", 70),
        ]:
            self.tabela_turnos.heading(c, text=t)
            self.tabela_turnos.column(c, width=w, anchor="center")
        self.tabela_turnos.pack(fill="x")
        ttk.Label(
            direita, text="Principais perdas do dia", style="Section.TLabel"
        ).pack(anchor="w", pady=(18, 4))
        self.canvas_pareto_dia = tk.Canvas(
            direita, height=270, bg="white", highlightthickness=0
        )
        self.canvas_pareto_dia.pack(fill="both", expand=True)

    def _criar_apontamento(self):
        self.vars = {
            "data": tk.StringVar(value=date.today().isoformat()),
            "turno": tk.StringVar(value="1º Turno"),
            "periodo": tk.StringVar(value=TURNOS["1º Turno"][0]),
            "operador": tk.StringVar(),
            "item_primario": tk.StringVar(),
            "meta_primario": tk.StringVar(value=str(META_PADRAO)),
            "real_primario": tk.StringVar(value="0"),
            "item_secundario": tk.StringVar(),
            "meta_secundario": tk.StringVar(value="0"),
            "real_secundario": tk.StringVar(value="0"),
            "parada": tk.StringVar(value="60.0"),
            "motivo": tk.StringVar(),
            "observacoes": tk.StringVar(),
            "responsavel": tk.StringVar(),
        }
        quadro = ttk.Frame(self.aba_apontamento, style="Card.TFrame", padding=16)
        quadro.pack(fill="x")
        ttk.Label(
            quadro, text="Registro da produção", style="Section.TLabel"
        ).grid(row=0, column=0, columnspan=5, sticky="w", pady=(0, 12))
        campos = [
            ("Data de produção", "data", "entry"),
            ("Turno", "turno", "turno"),
            ("Período", "periodo", "periodo"),
            ("Operador", "operador", "operador"),
            ("Responsável pelo registro", "responsavel", "entry"),
            ("Item primário", "item_primario", "item1"),
            ("Meta primária", "meta_primario", "entry"),
            ("Real primário", "real_primario", "entry"),
            ("Item secundário (opcional)", "item_secundario", "item2"),
            ("Real secundário", "real_secundario", "entry"),
            ("Parada calculada (min)", "parada", "readonly"),
            ("Motivo da parada", "motivo", "motivo"),
        ]
        for i, (rotulo, chave, tipo) in enumerate(campos):
            r, c = 1 + (i // 4) * 2, i % 4
            ttk.Label(quadro, text=rotulo, background="white").grid(
                row=r, column=c, sticky="w", padx=5
            )
            if tipo == "turno":
                w = ttk.Combobox(
                    quadro, textvariable=self.vars[chave],
                    values=list(TURNOS), state="readonly",
                )
                w.bind("<<ComboboxSelected>>", self._mudar_turno)
            elif tipo == "periodo":
                self.cmb_periodo = ttk.Combobox(
                    quadro, textvariable=self.vars[chave],
                    values=TURNOS["1º Turno"], state="readonly",
                )
                w = self.cmb_periodo
            elif tipo == "operador":
                self.cmb_operador = ttk.Combobox(
                    quadro, textvariable=self.vars[chave], state="readonly"
                )
                w = self.cmb_operador
            elif tipo in ("item1", "item2"):
                w = ttk.Combobox(
                    quadro, textvariable=self.vars[chave], state="readonly"
                )
                if tipo == "item1":
                    self.cmb_item1 = w
                    w.bind(
                        "<<ComboboxSelected>>",
                        lambda _e: self._meta_item("primario"),
                    )
                else:
                    self.cmb_item2 = w
                    w.bind(
                        "<<ComboboxSelected>>",
                        lambda _e: self._meta_item("secundario"),
                    )
            elif tipo == "motivo":
                self.cmb_motivo = ttk.Combobox(
                    quadro, textvariable=self.vars[chave], state="readonly"
                )
                w = self.cmb_motivo
            else:
                w = ttk.Entry(
                    quadro, textvariable=self.vars[chave],
                    state="readonly" if tipo == "readonly" else "normal",
                )
            w.grid(row=r + 1, column=c, sticky="ew", padx=5, pady=(2, 10))
            quadro.columnconfigure(c, weight=1)
        self.vars["meta_primario"].trace_add("write", self._recalcular_parada)
        self.vars["real_primario"].trace_add("write", self._recalcular_parada)
        ttk.Label(quadro, text="Observações", background="white").grid(
            row=7, column=0, sticky="w", padx=5
        )
        ttk.Entry(
            quadro, textvariable=self.vars["observacoes"]
        ).grid(row=8, column=0, columnspan=4, sticky="ew", padx=5, pady=(2, 12))
        botoes = ttk.Frame(quadro, style="Card.TFrame")
        botoes.grid(row=9, column=0, columnspan=4, sticky="e")
        ttk.Button(
            botoes, text="Limpar", command=self._limpar_formulario
        ).pack(side="left", padx=4)
        ttk.Button(
            botoes, text="Salvar apontamento", style="Primary.TButton",
            command=self._salvar_apontamento,
        ).pack(side="left", padx=4)
        ttk.Label(
            self.aba_apontamento,
            text=(
                "O item secundário é opcional. A parada utiliza o realizado "
                "primário: 60 − (real ÷ meta × 60)."
            ),
            foreground="#475467",
        ).pack(anchor="w", pady=12)

    def _criar_historico(self):
        filtros = ttk.Frame(self.aba_historico)
        filtros.pack(fill="x", pady=(0, 8))
        hoje = date.today()
        self.filtro_inicio = tk.StringVar(value=(hoje - timedelta(days=30)).isoformat())
        self.filtro_fim = tk.StringVar(value=hoje.isoformat())
        self.filtro_turno = tk.StringVar(value="Todos")
        self.filtro_operador = tk.StringVar(value="Todos")
        self.filtro_item = tk.StringVar(value="Todos")
        for texto, var, tipo in [
            ("De", self.filtro_inicio, "entry"),
            ("Até", self.filtro_fim, "entry"),
            ("Turno", self.filtro_turno, "turno"),
            ("Operador", self.filtro_operador, "operador"),
            ("Item", self.filtro_item, "item"),
        ]:
            ttk.Label(filtros, text=texto).pack(side="left", padx=(8, 3))
            if tipo == "entry":
                w = ttk.Entry(filtros, textvariable=var, width=12)
            else:
                w = ttk.Combobox(filtros, textvariable=var, state="readonly", width=15)
                if tipo == "turno":
                    w.configure(values=["Todos"] + list(TURNOS))
                elif tipo == "operador":
                    self.cmb_filtro_operador = w
                else:
                    self.cmb_filtro_item = w
            w.pack(side="left")
        ttk.Button(
            filtros, text="Filtrar", command=self._atualizar_historico
        ).pack(side="left", padx=8)
        ttk.Button(
            filtros, text="Exportar CSV detalhado",
            command=self._exportar_detalhado,
        ).pack(side="right")

        card = ttk.Frame(self.aba_historico, style="Card.TFrame", padding=8)
        card.pack(fill="both", expand=True)
        cols = (
            "id", "data", "turno", "periodo", "operador", "item1", "meta",
            "real", "item2", "real2", "efic", "parada", "motivo", "resp", "obs",
        )
        self.tabela_historico = ttk.Treeview(card, columns=cols, show="headings")
        for c, t, w in [
            ("id", "ID", 45), ("data", "Data", 85), ("turno", "Turno", 80),
            ("periodo", "Período", 100), ("operador", "Operador", 120),
            ("item1", "Item 1", 90), ("meta", "Meta", 55), ("real", "Real", 55),
            ("item2", "Item 2", 90), ("real2", "Real 2", 55),
            ("efic", "Eficiência", 75), ("parada", "Parada", 65),
            ("motivo", "Motivo", 110), ("resp", "Responsável", 110),
            ("obs", "Observações", 200),
        ]:
            self.tabela_historico.heading(c, text=t)
            self.tabela_historico.column(c, width=w, anchor="center")
        self.tabela_historico.tag_configure("meta", background="#dff3e4")
        self.tabela_historico.tag_configure("abaixo", background="#fde2e2")
        sy = ttk.Scrollbar(card, orient="vertical", command=self.tabela_historico.yview)
        sx = ttk.Scrollbar(card, orient="horizontal", command=self.tabela_historico.xview)
        self.tabela_historico.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.tabela_historico.grid(row=0, column=0, sticky="nsew")
        sy.grid(row=0, column=1, sticky="ns")
        sx.grid(row=1, column=0, sticky="ew")
        card.rowconfigure(0, weight=1)
        card.columnconfigure(0, weight=1)
        comandos = ttk.Frame(self.aba_historico)
        comandos.pack(fill="x", pady=6)
        ttk.Button(
            comandos, text="Editar selecionado", command=self._editar_selecionado
        ).pack(side="left", padx=3)
        ttk.Button(
            comandos, text="Excluir selecionado", command=self._excluir_selecionado
        ).pack(side="left", padx=3)
        self.lbl_resultados = ttk.Label(comandos, text="0 registros")
        self.lbl_resultados.pack(side="right")

    def _criar_analises(self):
        filtros = ttk.Frame(self.aba_analises)
        filtros.pack(fill="x", pady=(0, 8))
        hoje = date.today()
        self.analise_inicio = tk.StringVar(value=(hoje - timedelta(days=30)).isoformat())
        self.analise_fim = tk.StringVar(value=hoje.isoformat())
        ttk.Label(filtros, text="Período de").pack(side="left")
        ttk.Entry(filtros, textvariable=self.analise_inicio, width=12).pack(
            side="left", padx=5
        )
        ttk.Label(filtros, text="até").pack(side="left")
        ttk.Entry(filtros, textvariable=self.analise_fim, width=12).pack(
            side="left", padx=5
        )
        ttk.Button(
            filtros, text="Gerar análises", style="Primary.TButton",
            command=self._atualizar_analises,
        ).pack(side="left", padx=8)
        area = ttk.Panedwindow(self.aba_analises, orient="horizontal")
        area.pack(fill="both", expand=True)
        p1 = ttk.Frame(area, style="Card.TFrame", padding=10)
        p2 = ttk.Frame(area, style="Card.TFrame", padding=10)
        area.add(p1, weight=1)
        area.add(p2, weight=1)
        ttk.Label(p1, text="Pareto de paradas", style="Section.TLabel").pack(anchor="w")
        self.canvas_pareto = tk.Canvas(p1, bg="white", highlightthickness=0)
        self.canvas_pareto.pack(fill="both", expand=True)
        ttk.Label(p2, text="Tendência diária", style="Section.TLabel").pack(anchor="w")
        self.tabela_tendencia = ttk.Treeview(
            p2, columns=("data", "meta", "real", "efic", "parada"), show="headings"
        )
        for c, t in [
            ("data", "Data"), ("meta", "Meta"), ("real", "Real"),
            ("efic", "Eficiência"), ("parada", "Parada"),
        ]:
            self.tabela_tendencia.heading(c, text=t)
            self.tabela_tendencia.column(c, width=100, anchor="center")
        self.tabela_tendencia.pack(fill="both", expand=True)

    def _criar_cadastros(self):
        self.op_nome = tk.StringVar()
        self.op_matricula = tk.StringVar()
        self.item_codigo = tk.StringVar()
        self.item_descricao = tk.StringVar()
        self.item_meta = tk.StringVar(value=str(META_PADRAO))
        self.motivo_nome = tk.StringVar()
        quadros = [
            ("Operadores", [("Nome", self.op_nome), ("Matrícula", self.op_matricula)],
             self._cadastrar_operador),
            ("Itens", [("Código", self.item_codigo), ("Descrição", self.item_descricao),
                       ("Meta padrão", self.item_meta)], self._cadastrar_item),
            ("Motivos de parada", [("Motivo", self.motivo_nome)], self._cadastrar_motivo),
        ]
        for titulo, campos, acao in quadros:
            q = ttk.LabelFrame(self.aba_cadastros, text=titulo, padding=12)
            q.pack(fill="x", pady=6)
            for i, (rotulo, var) in enumerate(campos):
                ttk.Label(q, text=rotulo).grid(row=0, column=i, sticky="w")
                ttk.Entry(q, textvariable=var, width=32).grid(
                    row=1, column=i, padx=(0, 8)
                )
            ttk.Button(q, text="Cadastrar", command=acao).grid(
                row=1, column=len(campos)
            )

    def _mudar_turno(self, _evento=None):
        periodos = TURNOS[self.vars["turno"].get()]
        self.cmb_periodo.configure(values=periodos)
        self.vars["periodo"].set(periodos[0])

    def _meta_item(self, tipo):
        codigo = self.vars[f"item_{tipo}"].get()
        item = next((x for x in self.db.listar_itens() if x["codigo"] == codigo), None)
        self.vars[f"meta_{tipo}"].set(str(item["meta_padrao"] if item else 0))

    def _recalcular_parada(self, *_):
        try:
            meta = int(self.vars["meta_primario"].get() or META_PADRAO)
            real = int(self.vars["real_primario"].get() or 0)
            self.vars["parada"].set(f"{calcular_tempo_parada(real, meta):.1f}")
        except ValueError:
            self.vars["parada"].set("")

    def _validar_data(self, valor):
        datetime.strptime(valor, "%Y-%m-%d")

    def _salvar_apontamento(self):
        try:
            self._validar_data(self.vars["data"].get())
            meta1 = int(self.vars["meta_primario"].get())
            real1 = int(self.vars["real_primario"].get())
            if meta1 <= 0 or real1 < 0:
                raise ValueError("Meta deve ser positiva e realizado não pode ser negativo.")
            if not self.vars["operador"].get() or not self.vars["item_primario"].get():
                raise ValueError("Operador e item primário são obrigatórios.")
            item2 = self.vars["item_secundario"].get()
            if item2 and item2 == self.vars["item_primario"].get():
                raise ValueError("O item secundário deve ser diferente do primário.")
            meta2 = int(self.vars["meta_secundario"].get() or 0) if item2 else 0
            real2 = int(self.vars["real_secundario"].get() or 0) if item2 else 0
            dados = {
                "data": self.vars["data"].get(),
                "turno": self.vars["turno"].get(),
                "periodo": self.vars["periodo"].get(),
                "operador": self.vars["operador"].get(),
                "item_primario": self.vars["item_primario"].get(),
                "meta_primario": meta1,
                "real_primario": real1,
                "item_secundario": item2,
                "meta_secundario": meta2,
                "real_secundario": real2,
                "parada": calcular_tempo_parada(real1, meta1),
                "motivo": self.vars["motivo"].get(),
                "observacoes": self.vars["observacoes"].get().strip(),
                "responsavel": self.vars["responsavel"].get().strip(),
            }
            self.db.salvar_apontamento(dados, self.registro_id)
            messagebox.showinfo("Apontamento", "Registro salvo com sucesso.")
            self.data_painel.set(dados["data"])
            self._limpar_formulario()
            self._atualizar_supervisao()
            self._atualizar_historico()
            self.abas.select(self.aba_supervisao)
        except sqlite3.IntegrityError:
            messagebox.showerror(
                "Duplicidade", "Já existe registro para essa data, turno e período."
            )
        except ValueError as exc:
            messagebox.showerror("Dados inválidos", str(exc))

    def _limpar_formulario(self):
        self.registro_id = None
        self.vars["data"].set(date.today().isoformat())
        self.vars["turno"].set("1º Turno")
        self._mudar_turno()
        for c in ("operador", "item_primario", "item_secundario", "observacoes"):
            self.vars[c].set("")
        self.vars["meta_primario"].set(str(META_PADRAO))
        self.vars["real_primario"].set("0")
        self.vars["meta_secundario"].set("0")
        self.vars["real_secundario"].set("0")
        self._recalcular_parada()

    def _atualizar_cadastros(self):
        operadores = self.db.listar_operadores()
        itens = self.db.listar_itens()
        motivos = self.db.listar_motivos()
        nomes = [x["nome"] for x in operadores]
        codigos = [x["codigo"] for x in itens]
        motivos_nomes = [x["nome"] for x in motivos]
        self.cmb_operador.configure(values=nomes)
        self.cmb_item1.configure(values=codigos)
        self.cmb_item2.configure(values=[""] + codigos)
        self.cmb_motivo.configure(values=motivos_nomes)
        self.cmb_filtro_operador.configure(values=["Todos"] + nomes)
        self.cmb_filtro_item.configure(values=["Todos"] + codigos)
        if motivos_nomes and not self.vars["motivo"].get():
            self.vars["motivo"].set(motivos_nomes[0])

    def _cadastrar_operador(self):
        try:
            if not self.op_nome.get().strip():
                raise ValueError("Informe o nome.")
            self.db.cadastrar_operador(
                self.op_nome.get(), self.op_matricula.get() or None
            )
            self.op_nome.set(""); self.op_matricula.set("")
            self._atualizar_cadastros()
        except (ValueError, sqlite3.IntegrityError) as exc:
            messagebox.showerror("Operador", f"Não foi possível cadastrar: {exc}")

    def _cadastrar_item(self):
        try:
            meta = int(self.item_meta.get())
            if not self.item_codigo.get().strip() or not self.item_descricao.get().strip():
                raise ValueError("Informe código e descrição.")
            if meta <= 0:
                raise ValueError("Meta deve ser maior que zero.")
            self.db.cadastrar_item(
                self.item_codigo.get(), self.item_descricao.get(), meta
            )
            self.item_codigo.set(""); self.item_descricao.set("")
            self.item_meta.set(str(META_PADRAO))
            self._atualizar_cadastros()
        except (ValueError, sqlite3.IntegrityError) as exc:
            messagebox.showerror("Item", f"Não foi possível cadastrar: {exc}")

    def _cadastrar_motivo(self):
        try:
            if not self.motivo_nome.get().strip():
                raise ValueError("Informe o motivo.")
            self.db.cadastrar_motivo(self.motivo_nome.get())
            self.motivo_nome.set("")
            self._atualizar_cadastros()
        except (ValueError, sqlite3.IntegrityError) as exc:
            messagebox.showerror("Motivo", f"Não foi possível cadastrar: {exc}")

    def _atualizar_supervisao(self):
        try:
            data_ref = self.data_painel.get()
            self._validar_data(data_ref)
            turno = self.turno_painel.get()
            ind = self.db.indicadores(data_ref, turno)
            self.kpis["cobertura"].config(
                text=f'{ind["periodos"]}/{ind["esperados"]}'
            )
            self.kpis["pendentes"].config(text=str(ind["pendentes"]))
            self.kpis["meta"].config(text=str(ind["meta"]))
            self.kpis["real"].config(text=str(ind["real"]))
            self.kpis["eficiencia"].config(text=f'{ind["eficiencia"]:.1%}')
            self.kpis["parada"].config(text=f'{ind["parada"]:.1f} min')
            for x in self.tabela_cobertura.get_children():
                self.tabela_cobertura.delete(x)
            for item in self.db.cobertura_dia(data_ref):
                if turno != "Todos" and item["turno"] != turno:
                    continue
                r = item["registro"]
                self.tabela_cobertura.insert(
                    "", "end",
                    values=(
                        item["turno"], item["periodo"], item["status"],
                        r["operador"] if r else "",
                        r["item_primario"] if r else "",
                        r["real_primario"] if r else "",
                        f'{r["parada"]:.1f}' if r else "",
                    ),
                    tags=("ok" if r else "pendente",),
                )
            for x in self.tabela_turnos.get_children():
                self.tabela_turnos.delete(x)
            for r in self.db.resumo_turnos(data_ref):
                self.tabela_turnos.insert(
                    "", "end",
                    values=(
                        r["turno"], f'{r["periodos"]}/8', r["meta"], r["real"],
                        f'{r["eficiencia"]:.1%}', f'{r["parada"]:.1f}',
                    ),
                )
            pareto = self.db.pareto_motivos(data_ref, data_ref)
            self._desenhar_barras(self.canvas_pareto_dia, pareto)
        except ValueError:
            messagebox.showerror("Data", "Use o formato AAAA-MM-DD.")

    def _desenhar_barras(self, canvas, dados):
        canvas.delete("all")
        canvas.update_idletasks()
        largura = max(canvas.winfo_width(), 420)
        if not dados:
            canvas.create_text(
                largura / 2, 120, text="Sem paradas registradas no período",
                fill="#667085", font=("Segoe UI", 11),
            )
            return
        maximo = max(float(x["minutos"]) for x in dados) or 1
        y = 28
        for linha in dados:
            valor = float(linha["minutos"])
            tamanho = (largura - 190) * valor / maximo
            canvas.create_text(
                8, y + 9, anchor="w", text=linha["motivo"],
                fill="#344054", font=("Segoe UI", 9),
            )
            canvas.create_rectangle(
                130, y, 130 + tamanho, y + 20, fill="#2878b5", outline=""
            )
            canvas.create_text(
                138 + tamanho, y + 10, anchor="w",
                text=f"{valor:.1f} min", fill="#344054",
            )
            y += 31

    def _linhas_historico(self):
        return self.db.historico(
            self.filtro_inicio.get(), self.filtro_fim.get(),
            self.filtro_turno.get(), self.filtro_operador.get(),
            self.filtro_item.get(),
        )

    def _atualizar_historico(self):
        try:
            self._validar_data(self.filtro_inicio.get())
            self._validar_data(self.filtro_fim.get())
            linhas = self._linhas_historico()
            for x in self.tabela_historico.get_children():
                self.tabela_historico.delete(x)
            for r in linhas:
                eficiencia = r["real_primario"] / r["meta_primario"]
                self.tabela_historico.insert(
                    "", "end",
                    values=(
                        r["id"], r["data"], r["turno"], r["periodo"],
                        r["operador"], r["item_primario"], r["meta_primario"],
                        r["real_primario"], r["item_secundario"],
                        r["real_secundario"], f"{eficiencia:.1%}",
                        f'{r["parada"]:.1f}', r["motivo"],
                        r["responsavel"] or "", r["observacoes"] or "",
                    ),
                    tags=("meta" if eficiencia >= 1 else "abaixo",),
                )
            self.lbl_resultados.config(text=f"{len(linhas)} registros")
        except ValueError:
            messagebox.showerror("Filtro", "Use datas no formato AAAA-MM-DD.")

    def _editar_selecionado(self):
        s = self.tabela_historico.selection()
        if not s:
            messagebox.showinfo("Editar", "Selecione um registro.")
            return
        registro_id = int(self.tabela_historico.item(s[0], "values")[0])
        r = self.db.obter_apontamento(registro_id)
        self.registro_id = registro_id
        for chave in self.vars:
            if chave in r.keys():
                self.vars[chave].set(r[chave] if r[chave] is not None else "")
        self.cmb_periodo.configure(values=TURNOS[r["turno"]])
        self.abas.select(self.aba_apontamento)

    def _excluir_selecionado(self):
        s = self.tabela_historico.selection()
        if not s:
            messagebox.showinfo("Excluir", "Selecione um registro.")
            return
        registro_id = int(self.tabela_historico.item(s[0], "values")[0])
        if messagebox.askyesno("Confirmação", "Excluir definitivamente este apontamento?"):
            self.db.excluir_apontamento(registro_id)
            self._atualizar_historico()
            self._atualizar_supervisao()

    def _atualizar_analises(self):
        try:
            inicio, fim = self.analise_inicio.get(), self.analise_fim.get()
            self._validar_data(inicio); self._validar_data(fim)
            self._desenhar_barras(
                self.canvas_pareto, self.db.pareto_motivos(inicio, fim)
            )
            for x in self.tabela_tendencia.get_children():
                self.tabela_tendencia.delete(x)
            for r in self.db.tendencia_diaria(inicio, fim):
                eficiencia = r["real"] / r["meta"] if r["meta"] else 0
                self.tabela_tendencia.insert(
                    "", "end",
                    values=(
                        r["data"], r["meta"], r["real"],
                        f"{eficiencia:.1%}", f'{r["parada"]:.1f}',
                    ),
                )
        except ValueError:
            messagebox.showerror("Análises", "Use datas no formato AAAA-MM-DD.")

    def _exportar_detalhado(self):
        linhas = self._linhas_historico()
        caminho = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            initialfile=f"apontamentos_{self.filtro_inicio.get()}_{self.filtro_fim.get()}.csv",
        )
        if not caminho:
            return
        with open(caminho, "w", newline="", encoding="utf-8-sig") as arq:
            w = csv.writer(arq, delimiter=";")
            w.writerow([
                "ID", "Data", "Turno", "Período", "Operador", "Item primário",
                "Meta", "Real", "Item secundário", "Meta secundária",
                "Real secundário", "Eficiência", "Parada (min)", "Motivo",
                "Observações", "Responsável", "Criado em", "Alterado em",
            ])
            for r in linhas:
                w.writerow([
                    r["id"], r["data"], r["turno"], r["periodo"], r["operador"],
                    r["item_primario"], r["meta_primario"], r["real_primario"],
                    r["item_secundario"], r["meta_secundario"],
                    r["real_secundario"],
                    round(r["real_primario"] / r["meta_primario"], 4),
                    r["parada"], r["motivo"], r["observacoes"],
                    r["responsavel"], r["criado_em"], r["alterado_em"],
                ])
        messagebox.showinfo("Relatório", "Relatório detalhado exportado.")

    def _exportar_resumo(self):
        data_ref = self.data_painel.get()
        caminho = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            initialfile=f"resumo_gerencial_{data_ref}.csv",
        )
        if not caminho:
            return
        with open(caminho, "w", newline="", encoding="utf-8-sig") as arq:
            w = csv.writer(arq, delimiter=";")
            w.writerow(["RESUMO GERENCIAL", data_ref])
            w.writerow(["Turno", "Períodos", "Pendentes", "Meta", "Real",
                        "Eficiência", "Parada (min)"])
            for r in self.db.resumo_turnos(data_ref):
                w.writerow([
                    r["turno"], r["periodos"], r["pendentes"], r["meta"],
                    r["real"], round(r["eficiencia"], 4), r["parada"],
                ])
            w.writerow([])
            w.writerow(["Motivo", "Minutos de parada", "Ocorrências"])
            for r in self.db.pareto_motivos(data_ref, data_ref):
                w.writerow([r["motivo"], r["minutos"], r["ocorrencias"]])
        messagebox.showinfo("Relatório", "Resumo gerencial exportado.")

    def _fechar(self):
        self.db.fechar()
        self.destroy()


if __name__ == "__main__":
    SistemaSupervisao().mainloop()
