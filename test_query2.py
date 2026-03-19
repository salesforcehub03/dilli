from services.neo4j_service import driver

query_with_parens = """
MATCH p = (d:Drug)-[*1..6]-(n)
WHERE (toLower(d.drug_name) = toLower($drug) OR d.smiles = $drug)
  AND ALL(node IN nodes(p) WHERE NOT ('Drug' IN labels(node)) OR node = d)
RETURN labels(n) AS labels, count(n) as count
"""

query_no_filter = """
MATCH p = (d:Drug)-[*1..6]-(n)
WHERE (toLower(d.drug_name) = toLower($drug))
RETURN labels(n) AS labels, count(n) as count
"""

drugs = ["Belinostat", "Vorinostat"]

print("=== WITH FILTER (app.py behavior) ===")
with driver.session() as session:
    for d in drugs:
        print(f"\n--- {d} ---")
        for r in session.run(query_with_parens, drug=d):
            print(f"{r['labels'][0]}: {r['count']}")
