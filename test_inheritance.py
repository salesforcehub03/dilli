from services.neo4j_service import driver

query = """
MATCH p = (d:Drug)-[*1..4]-(n)
WHERE toLower(d.drug_name) = 'vorinostat'
WITH d, relationships(p) AS rels, n, 
     ALL(node IN nodes(p) WHERE NOT ('Drug' IN labels(node)) OR node = d) AS is_direct
RETURN labels(n)[0] as label, is_direct, count(n) as count
"""

print("=== INHERITANCE TEST FOR VORINOSTAT ===")
with driver.session() as session:
    res = session.run(query)
    for r in res:
        print(f"{r['label']} (Direct: {r['is_direct']}): {r['count']}")
