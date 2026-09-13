import json
from pathlib import Path

from mongo_repository import BancoIndisponivel, MongoRepository


def main():
    config = json.loads((Path(__file__).parent / "config.json").read_text(encoding="utf-8"))
    try:
        repo = MongoRepository(config["mongo_uri"], config["database"])
        repo.testar_conexao()
        print("Conexão com MongoDB realizada com sucesso.")
        print("Banco:", config["database"])
        print("Coleções:", ", ".join(repo.db.list_collection_names()))
        repo.fechar()
    except BancoIndisponivel as exc:
        print(exc)
        print("\nVerifique no PowerShell:")
        print("  Get-Service MongoDB")
        print("  Test-NetConnection localhost -Port 27017")


if __name__ == "__main__":
    main()
