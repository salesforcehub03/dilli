from services.neo4j_service import driver

query = """
MATCH (d:Drug)
RETURN d.drug_name as drug_name, d.name as name
LIMIT 50
"""

with driver.session() as session:
    records = list(session.run(query))
    print(f"Found {len(records)} drugs")
    for r in records:
        print(f"drug_name: {r['drug_name']} | name: {r['name']}")
