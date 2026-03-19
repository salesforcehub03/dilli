from services.neo4j_service import driver

query = """
MATCH (d:Drug)
WHERE toLower(d.drug_name) = 'romidepsin'
OPTIONAL MATCH (d)-[r]-(n)
RETURN d.drug_name as name, labels(n) as n_labels, type(r) as rel_type, count(n) as count
"""

print("--- Romidepsin Check ---")
try:
    with driver.session() as session:
        records = list(session.run(query))
        if not records:
            print("Drug node not found at all.")
        for r in records:
            print(f"Name: {r['name']}, n_labels: {r['n_labels']}, rel_type: {r['rel_type']}, count: {r['count']}")
except Exception as e:
    print(e)
