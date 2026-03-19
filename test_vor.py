from services.neo4j_service import driver

query = """
MATCH (n)
WHERE toLower(n.drug_name) CONTAINS 'vorinostat' OR toLower(n.name) CONTAINS 'vorinostat'
OPTIONAL MATCH (n)-[r]-(m)
RETURN labels(n) as l_n, n.drug_name as n_dn, n.name as n_name, type(r) as r_type, labels(m) as l_m
LIMIT 100
"""

with driver.session() as session:
    res = session.run(query)
    for row in res:
        print(row)
