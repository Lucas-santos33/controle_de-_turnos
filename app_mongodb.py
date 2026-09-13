import json
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import messagebox, ttk

from calculos import calcular_eficiencia, calcular_tempo_parada
from mongo_repository import (
    BancoIndisponivel,
    MongoRepository,
    RegistroDuplicado,
)

APP_DIR = Path(__file__).resolve().parent
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


def carregar_configuracao():
    caminho = APP_DIR / "config.json"
    return json.loads(caminho.read_text(encoding="utf-8"))


class MongoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Hora a Hora — MongoDB")
        self.geometry("1280x780")
        self.minsize(1080, 680)
        self.configuracao = carregar_configuracao()
        self.meta_padrao = int(self.configuracao.get("meta_padrao", 22))
        self.minutos_periodo = float(self.configuracao.get("minutos_periodo", 60))
        try:
            self.repo = MongoRepository(
                self.configuracao["mongo_uri"],
                self.configuracao["database"],
            )
        except BancoIndisponivel as exc:
            messagebox.showerror(
                "MongoDB desconectado",
                f"{exc}\n\nExecute primeiro: python testar_mongodb.py",
            )
            self.destroy()
            return
        self._criar_estilo()
        self._criar_interface()
        self._atualizar_cadastros()
        self._atualizar_historico()
        self.protocol("WM_DELETE_WINDOW", self._fechar)

    def _criar_estilo(self):
        estilo = ttk.Style(self)
        estilo.theme_use("clam")
        estilo.configure(
            "Titulo.TLabel",
            background="#15375b",
            foreground="white",
            font=("Segoe UI", 18, "bold"),
            padding=14,
        )
        estilo.configure(
            "Destaque.TButton",
            background="#1976d2",
            foreground="white",
            padding=7,
        )
        estilo.configure("Treeview", rowheight=27)
        estilo.configure(
            "Treeview.Heading",
            background="#15375b",
            foreground="white",
            font=("Segoe UI", 9, "bold"),
        )

    def _criar_interface(self):
        ttk.Label(
            self,
            text="PRODUÇÃO HORA A HORA — MONGODB",
            style="Titulo.TLabel",
        ).pack(fill="x")
        topo = ttk.Frame(self, padding=(12, 6))
        topo.pack(fill="x")
        self.lbl_conexao = ttk.Label(
            topo,
            text=f'● Conectado: {self.configuracao["database"]}',
            foreground="#14804a",
        )
        self.lbl_conexao.pack(side="left")
        ttk.Button(
            topo,
            text="Testar conexão",
            command=self._testar_conexao,
        ).pack(side="right")

        self.abas = ttk.Notebook(self)
        self.abas.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.aba_apontar = ttk.Frame(self.abas, padding=14)
        self.aba_historico = ttk.Frame(self.abas, padding=14)
        self.aba_cadastro = ttk.Frame(self.abas, padding=14)
        self.abas.add(self.aba_apontar, text="Apontamento")
        self.abas.add(self.aba_historico, text="Histórico")
        self.abas.add(self.aba_cadastro, text="Cadastros")
        self._criar_formulario()
        self._criar_historico()
        self._criar_cadastros()

    def _criar_formulario(self):
        self.vars = {
            "data": tk.StringVar(value=date.today().isoformat()),
            "turno": tk.StringVar(value="1º Turno"),
            "periodo": tk.StringVar(value=TURNOS["1º Turno"][0]),
            "operador": tk.StringVar(),
            "item_primario": tk.StringVar(),
            "meta_primario": tk.StringVar(value=str(self.meta_padrao)),
            "real_primario": tk.StringVar(value="0"),
            "item_secundario": tk.StringVar(),
            "meta_secundario": tk.StringVar(value=str(self.meta_padrao)),
            "real_secundario": tk.StringVar(value="0"),
            "parada_calculada": tk.StringVar(value="60.0"),
            "motivo": tk.StringVar(),
            "observacoes": tk.StringVar(),
        }
        quadro = ttk.LabelFrame(
            self.aba_apontar,
            text="Dados da produção",
            padding=14,
        )
        quadro.pack(fill="x")
        campos = [
            ("Data", "data", "entrada"),
            ("Turno", "turno", "turno"),
            ("Período", "periodo", "periodo"),
            ("Operador", "operador", "operador"),
            ("Item primário", "item_primario", "item1"),
            ("Meta primário", "meta_primario", "entrada"),
            ("Real primário", "real_primario", "entrada"),
            ("Item secundário", "item_secundario", "item2"),
            ("Meta secundário", "meta_secundario", "entrada"),
            ("Real secundário", "real_secundario", "entrada"),
            ("Parada calculada", "parada_calculada", "somente"),
            ("Motivo", "motivo", "motivo"),
        ]
        for indice, (rotulo, chave, tipo) in enumerate(campos):
            linha = (indice // 4) * 2
            coluna = indice % 4
            ttk.Label(quadro, text=rotulo).grid(
                row=linha,
                column=coluna,
                sticky="w",
                padx=6,
            )
            if tipo == "turno":
                componente = ttk.Combobox(
                    quadro,
                    textvariable=self.vars[chave],
                    values=list(TURNOS),
                    state="readonly",
                )
                componente.bind("<<ComboboxSelected>>", self._mudar_turno)
            elif tipo == "periodo":
                self.cmb_periodo = ttk.Combobox(
                    quadro,
                    textvariable=self.vars[chave],
                    values=TURNOS["1º Turno"],
                    state="readonly",
                )
                componente = self.cmb_periodo
            elif tipo == "operador":
                self.cmb_operador = ttk.Combobox(
                    quadro,
                    textvariable=self.vars[chave],
                    state="readonly",
                )
                componente = self.cmb_operador
            elif tipo in ("item1", "item2"):
                componente = ttk.Combobox(
                    quadro,
                    textvariable=self.vars[chave],
                    state="readonly",
                )
                if tipo == "item1":
                    self.cmb_item1 = componente
                    componente.bind(
                        "<<ComboboxSelected>>",
                        lambda _e: self._preencher_meta("primario"),
                    )
                else:
                    self.cmb_item2 = componente
                    componente.bind(
                        "<<ComboboxSelected>>",
                        lambda _e: self._preencher_meta("secundario"),
                    )
            elif tipo == "motivo":
                self.cmb_motivo = ttk.Combobox(
                    quadro,
                    textvariable=self.vars[chave],
                    state="readonly",
                )
                componente = self.cmb_motivo
            else:
                componente = ttk.Entry(
                    quadro,
                    textvariable=self.vars[chave],
                    state="readonly" if tipo == "somente" else "normal",
                )
            componente.grid(
                row=linha + 1,
                column=coluna,
                sticky="ew",
                padx=6,
                pady=(2, 10),
            )
            quadro.columnconfigure(coluna, weight=1)

        self.vars["real_primario"].trace_add("write", self._recalcular_parada)
        ttk.Label(quadro, text="Observações").grid(
            row=6, column=0, sticky="w", padx=6
        )
        ttk.Entry(
            quadro,
            textvariable=self.vars["observacoes"],
        ).grid(row=7, column=0, columnspan=4, sticky="ew", padx=6, pady=(2, 12))
        ttk.Button(
            quadro,
            text="Salvar no MongoDB",
            style="Destaque.TButton",
            command=self._salvar,
        ).grid(row=8, column=3, sticky="e", padx=6)

        explicacao = (
            "Cálculo: 60 − (realizado do item primário ÷ meta × 60). "
            "Os dois itens são simultâneos, portanto suas quantidades não são somadas."
        )
        ttk.Label(
            self.aba_apontar,
            text=explicacao,
            foreground="#475467",
        ).pack(anchor="w", pady=12)

    def _criar_historico(self):
        colunas = (
            "data", "turno", "periodo", "operador", "item1", "meta",
            "real", "item2", "real2", "parada", "motivo", "observacoes",
        )
        self.tabela = ttk.Treeview(
            self.aba_historico,
            columns=colunas,
            show="headings",
        )
        titulos = (
            "Data", "Turno", "Período", "Operador", "Item 1", "Meta",
            "Real", "Item 2", "Real 2", "Parada", "Motivo", "Observações",
        )
        for coluna, titulo in zip(colunas, titulos):
            self.tabela.heading(coluna, text=titulo)
            self.tabela.column(
                coluna,
                width=105 if coluna != "observacoes" else 220,
                anchor="center",
            )
        barra_y = ttk.Scrollbar(
            self.aba_historico,
            orient="vertical",
            command=self.tabela.yview,
        )
        barra_x = ttk.Scrollbar(
            self.aba_historico,
            orient="horizontal",
            command=self.tabela.xview,
        )
        self.tabela.configure(
            yscrollcommand=barra_y.set,
            xscrollcommand=barra_x.set,
        )
        self.tabela.grid(row=0, column=0, sticky="nsew")
        barra_y.grid(row=0, column=1, sticky="ns")
        barra_x.grid(row=1, column=0, sticky="ew")
        self.aba_historico.rowconfigure(0, weight=1)
        self.aba_historico.columnconfigure(0, weight=1)
        ttk.Button(
            self.aba_historico,
            text="Atualizar",
            command=self._atualizar_historico,
        ).grid(row=2, column=0, sticky="e", pady=8)

    def _criar_cadastros(self):
        self.op_nome = tk.StringVar()
        self.op_matricula = tk.StringVar()
        self.item_codigo = tk.StringVar()
        self.item_descricao = tk.StringVar()
        self.item_meta = tk.StringVar(value=str(self.meta_padrao))
        self.motivo_nome = tk.StringVar()

        quadros = [
            ("Operadores", [
                ("Nome", self.op_nome),
                ("Matrícula", self.op_matricula),
            ], self._cadastrar_operador),
            ("Itens", [
                ("Código", self.item_codigo),
                ("Descrição", self.item_descricao),
                ("Meta", self.item_meta),
            ], self._cadastrar_item),
            ("Motivos de parada", [
                ("Motivo", self.motivo_nome),
            ], self._cadastrar_motivo),
        ]
        for titulo, campos, comando in quadros:
            quadro = ttk.LabelFrame(
                self.aba_cadastro,
                text=titulo,
                padding=12,
            )
            quadro.pack(fill="x", pady=6)
            for coluna, (rotulo, variavel) in enumerate(campos):
                ttk.Label(quadro, text=rotulo).grid(row=0, column=coluna, sticky="w")
                ttk.Entry(
                    quadro,
                    textvariable=variavel,
                    width=32,
                ).grid(row=1, column=coluna, padx=(0, 8))
            ttk.Button(
                quadro,
                text="Cadastrar",
                command=comando,
            ).grid(row=1, column=len(campos))

    def _testar_conexao(self):
        try:
            self.repo.testar_conexao()
            messagebox.showinfo("MongoDB", "Conexão ativa.")
        except Exception as exc:
            messagebox.showerror("MongoDB", str(exc))

    def _mudar_turno(self, _evento=None):
        periodos = TURNOS[self.vars["turno"].get()]
        self.cmb_periodo.configure(values=periodos)
        self.vars["periodo"].set(periodos[0])

    def _preencher_meta(self, tipo):
        codigo = self.vars[f"item_{tipo}"].get()
        item = next(
            (x for x in self.repo.listar_itens() if x["codigo"] == codigo),
            None,
        )
        self.vars[f"meta_{tipo}"].set(
            str(item["meta_padrao"] if item else self.meta_padrao)
        )

    def _recalcular_parada(self, *_):
        try:
            real = int(self.vars["real_primario"].get() or 0)
            meta = int(self.vars["meta_primario"].get() or self.meta_padrao)
            parada = calcular_tempo_parada(real, meta, self.minutos_periodo)
            self.vars["parada_calculada"].set(f"{parada:.1f}")
        except ValueError:
            self.vars["parada_calculada"].set("")

    def _salvar(self):
        try:
            meta1 = int(self.vars["meta_primario"].get())
            real1 = int(self.vars["real_primario"].get())
            item2 = self.vars["item_secundario"].get()
            meta2 = int(self.vars["meta_secundario"].get()) if item2 else 0
            real2 = int(self.vars["real_secundario"].get()) if item2 else 0
            parada = calcular_tempo_parada(
                real1,
                meta1,
                self.minutos_periodo,
            )
            documento = {
                "data": self.vars["data"].get().strip(),
                "turno": self.vars["turno"].get(),
                "periodo": self.vars["periodo"].get(),
                "operador": self.vars["operador"].get(),
                "item_primario": self.vars["item_primario"].get(),
                "meta_primario": meta1,
                "real_primario": real1,
                "item_secundario": item2 or None,
                "meta_secundario": meta2,
                "real_secundario": real2,
                "eficiencia": round(calcular_eficiencia(real1, meta1), 4),
                "tempo_parada_calculado": parada,
                "motivo": self.vars["motivo"].get(),
                "observacoes": self.vars["observacoes"].get().strip(),
                "regra_calculo": "60-(real_primario/meta_primario*60)",
            }
            if not documento["operador"] or not documento["item_primario"]:
                raise ValueError("Selecione operador e item primário.")
            if item2 and item2 == documento["item_primario"]:
                raise ValueError("O item secundário deve ser diferente do primário.")
            self.repo.salvar_apontamento(documento)
            messagebox.showinfo("MongoDB", "Apontamento salvo com sucesso.")
            self._limpar_apontamento()
            self._atualizar_historico()
            self.abas.select(self.aba_historico)
        except (ValueError, RegistroDuplicado) as exc:
            messagebox.showerror("Apontamento", str(exc))
        except Exception as exc:
            messagebox.showerror("MongoDB", f"Falha ao gravar: {exc}")

    def _cadastrar_operador(self):
        try:
            self.repo.cadastrar_operador(
                self.op_nome.get(),
                self.op_matricula.get() or None,
            )
            self.op_nome.set("")
            self.op_matricula.set("")
            self._atualizar_cadastros()
        except (ValueError, RegistroDuplicado) as exc:
            messagebox.showerror("Operador", str(exc))

    def _cadastrar_item(self):
        try:
            self.repo.cadastrar_item(
                self.item_codigo.get(),
                self.item_descricao.get(),
                int(self.item_meta.get()),
            )
            self.item_codigo.set("")
            self.item_descricao.set("")
            self.item_meta.set(str(self.meta_padrao))
            self._atualizar_cadastros()
        except (ValueError, RegistroDuplicado) as exc:
            messagebox.showerror("Item", str(exc))

    def _cadastrar_motivo(self):
        try:
            self.repo.cadastrar_motivo(self.motivo_nome.get())
            self.motivo_nome.set("")
            self._atualizar_cadastros()
        except (ValueError, RegistroDuplicado) as exc:
            messagebox.showerror("Motivo", str(exc))

    def _atualizar_cadastros(self):
        operadores = [x["nome"] for x in self.repo.listar_operadores()]
        itens = [x["codigo"] for x in self.repo.listar_itens()]
        motivos = [x["nome"] for x in self.repo.listar_motivos()]
        self.cmb_operador.configure(values=operadores)
        self.cmb_item1.configure(values=itens)
        self.cmb_item2.configure(values=[""] + itens)
        self.cmb_motivo.configure(values=motivos)
        if motivos and not self.vars["motivo"].get():
            self.vars["motivo"].set(motivos[0])

    def _atualizar_historico(self):
        for item in self.tabela.get_children():
            self.tabela.delete(item)
        for doc in self.repo.listar_apontamentos():
            self.tabela.insert(
                "",
                "end",
                values=(
                    doc.get("data"),
                    doc.get("turno"),
                    doc.get("periodo"),
                    doc.get("operador"),
                    doc.get("item_primario"),
                    doc.get("meta_primario"),
                    doc.get("real_primario"),
                    doc.get("item_secundario") or "",
                    doc.get("real_secundario", 0),
                    f'{doc.get("tempo_parada_calculado", 0):.1f}',
                    doc.get("motivo"),
                    doc.get("observacoes", ""),
                ),
            )

    def _limpar_apontamento(self):
        self.vars["real_primario"].set("0")
        self.vars["real_secundario"].set("0")
        self.vars["observacoes"].set("")
        self._recalcular_parada()

    def _fechar(self):
        self.repo.fechar()
        self.destroy()


if __name__ == "__main__":
    MongoApp().mainloop()

