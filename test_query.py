from services.neo4j_service import driver

drugs = ["Belinostat", "Vorinostat", "Panobinostat", "Romidepsin", "Valproic Acid", "Chidamide"]

query = """
MATCH p = (d:Drug)-[*1..6]-(n)
WHERE toLower(d.drug_name) = toLower($drug) OR d.smiles = $drug
  AND ALL(node IN nodes(p) WHERE NOT ('Drug' IN labels(node)) OR node = d)
RETURN labels(n) AS labels, count(n) as count
"""

def test_drug(drug_name):
    print(f"\n--- Testing {drug_name} ---")
    with driver.session() as session:
        result = session.run(query, drug=drug_name)
        records = list(result)
        if not records:
            print("No subnodes found.")
        for r in records:
            print(f"{r['labels'][0]}: {r['count']}")

if driver:
    for d in drugs:
        test_drug(d)
else:
    print("No driver")
