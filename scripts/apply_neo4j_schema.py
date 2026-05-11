"""Apply Neo4j constraints and indexes. Run once after first boot."""

from pathlib import Path

from neo4j import GraphDatabase

from src.core.config import get_settings


def main():
    settings = get_settings()
    cypher = (Path(__file__).parent / "neo4j_schema.cypher").read_text()

    statements = [
        s.strip()
        for s in cypher.split(";")
        if s.strip() and not s.strip().startswith("//")
    ]

    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    with driver.session() as session:
        for stmt in statements:
            print(f"  Applying: {stmt[:70]}...")
            session.run(stmt)

    driver.close()
    print("✅ Neo4j schema applied")


if __name__ == "__main__":
    main()
