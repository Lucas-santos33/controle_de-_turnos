from __future__ import annotations

from datetime import datetime
from typing import Any

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError


class BancoIndisponivel(RuntimeError):
    pass


class RegistroDuplicado(ValueError):
    pass


class MongoRepository:
    """Centraliza toda a comunicação do programa com o MongoDB."""

    def __init__(
        self,
        uri: str = "mongodb://localhost:27017/",
        database: str = "hora_a_hora",
        timeout_ms: int = 3000,
    ):
        try:
            self.client = MongoClient(
                uri,
                serverSelectionTimeoutMS=timeout_ms,
                connectTimeoutMS=timeout_ms,
                socketTimeoutMS=timeout_ms,
            )
            self.client.admin.command("ping")
        except PyMongoError as exc:
            raise BancoIndisponivel(
                f"Não foi possível conectar ao MongoDB em {uri}. "
                "Confirme se o serviço mongod está iniciado e se a porta 27017 está disponível."
            ) from exc

        self.db = self.client[database]
        self.operadores = self.db["operadores"]
        self.itens = self.db["itens"]
        self.motivos = self.db["motivos_parada"]
        self.apontamentos = self.db["apontamentos"]
        self.configuracoes = self.db["configuracoes"]
        self._criar_indices()
        self._criar_dados_iniciais()

    def _criar_indices(self) -> None:
        self.operadores.create_index([("nome", ASCENDING)], unique=True)
        self.operadores.create_index(
            [("matricula", ASCENDING)],
            unique=True,
            sparse=True,
        )
        self.itens.create_index([("codigo", ASCENDING)], unique=True)
        self.motivos.create_index([("nome", ASCENDING)], unique=True)
        self.apontamentos.create_index(
            [("data", ASCENDING), ("turno", ASCENDING), ("periodo", ASCENDING)],
            unique=True,
        )
        self.apontamentos.create_index([("criado_em", DESCENDING)])

    def _criar_dados_iniciais(self) -> None:
        self.configuracoes.update_one(
            {"_id": "producao"},
            {"$setOnInsert": {"meta_padrao": 22, "minutos_periodo": 60}},
            upsert=True,
        )
        nomes = [
            "Sem parada",
            "Falta de material",
            "Manutenção",
            "Qualidade",
            "Setup/Troca",
            "Falta de operador",
            "Logística",
            "Outro",
        ]
        for nome in nomes:
            self.motivos.update_one(
                {"nome": nome},
                {"$setOnInsert": {"nome": nome, "ativo": True}},
                upsert=True,
            )

    def testar_conexao(self) -> bool:
        self.client.admin.command("ping")
        return True

    def fechar(self) -> None:
        self.client.close()

    def cadastrar_operador(self, nome: str, matricula: str | None) -> str:
        doc = {
            "nome": nome.strip(),
            "matricula": matricula.strip() if matricula else None,
            "ativo": True,
            "criado_em": datetime.now(),
        }
        if not doc["nome"]:
            raise ValueError("Informe o nome do operador.")
        if doc["matricula"] is None:
            doc.pop("matricula")
        try:
            return str(self.operadores.insert_one(doc).inserted_id)
        except DuplicateKeyError as exc:
            raise RegistroDuplicado("Nome ou matrícula já cadastrado.") from exc

    def listar_operadores(self) -> list[dict[str, Any]]:
        return list(
            self.operadores.find({"ativo": True}).sort("nome", ASCENDING)
        )

    def cadastrar_item(
        self,
        codigo: str,
        descricao: str,
        meta_padrao: int = 22,
    ) -> str:
        if not codigo.strip() or not descricao.strip():
            raise ValueError("Informe o código e a descrição do item.")
        if meta_padrao <= 0:
            raise ValueError("A meta deve ser maior que zero.")
        try:
            result = self.itens.insert_one(
                {
                    "codigo": codigo.strip().upper(),
                    "descricao": descricao.strip(),
                    "meta_padrao": meta_padrao,
                    "ativo": True,
                    "criado_em": datetime.now(),
                }
            )
            return str(result.inserted_id)
        except DuplicateKeyError as exc:
            raise RegistroDuplicado("Código de item já cadastrado.") from exc

    def listar_itens(self) -> list[dict[str, Any]]:
        return list(self.itens.find({"ativo": True}).sort("codigo", ASCENDING))

    def cadastrar_motivo(self, nome: str) -> str:
        if not nome.strip():
            raise ValueError("Informe o motivo.")
        try:
            result = self.motivos.insert_one(
                {"nome": nome.strip(), "ativo": True, "criado_em": datetime.now()}
            )
            return str(result.inserted_id)
        except DuplicateKeyError as exc:
            raise RegistroDuplicado("Motivo já cadastrado.") from exc

    def listar_motivos(self) -> list[dict[str, Any]]:
        return list(self.motivos.find({"ativo": True}).sort("nome", ASCENDING))

    def salvar_apontamento(self, documento: dict[str, Any]) -> str:
        obrigatorios = (
            "data",
            "turno",
            "periodo",
            "operador",
            "item_primario",
            "meta_primario",
            "real_primario",
        )
        faltando = [campo for campo in obrigatorios if documento.get(campo) in (None, "")]
        if faltando:
            raise ValueError("Campos obrigatórios: " + ", ".join(faltando))
        documento = dict(documento)
        documento["criado_em"] = datetime.now()
        try:
            return str(self.apontamentos.insert_one(documento).inserted_id)
        except DuplicateKeyError as exc:
            raise RegistroDuplicado(
                "Já existe apontamento para essa data, turno e período."
            ) from exc

    def listar_apontamentos(
        self,
        data: str | None = None,
        limite: int = 500,
    ) -> list[dict[str, Any]]:
        filtro = {"data": data} if data else {}
        return list(
            self.apontamentos.find(filtro)
            .sort([("data", DESCENDING), ("criado_em", DESCENDING)])
            .limit(limite)
        )

    def excluir_apontamento(self, object_id) -> int:
        from bson import ObjectId

        return self.apontamentos.delete_one({"_id": ObjectId(str(object_id))}).deleted_count

