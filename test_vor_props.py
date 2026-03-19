from services.neo4j_service import driver

query = """
MATCH (n:Drug)
WHERE toLower(n.drug_name) = 'vorinostat' OR n.smiles CONTAINS 'vorinostat'
RETURN properties(n) as props
"""

with driver.session() as session:
    res = session.run(query)
    for row in res:
        print("Vorinostat Properties:")
        for k, v in row['props'].items():
            print(f"{k}: {v}")
