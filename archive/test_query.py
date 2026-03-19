from services.neo4j_service import driver
import json

def test_graph_query():
    query = """
    MATCH (d:Drug {drug_name: 'Belinostat'})
    MATCH p=(d)-[r*1..2]-(n)
    WITH d, r, n,
         CASE WHEN ANY(rel in r WHERE type(rel) = 'SIMILAR_TO') THEN 1 ELSE 0 END as is_sim
    ORDER BY is_sim ASC
    LIMIT 200
    RETURN type(r[0]) as rel, labels(n)[0] as lbl, is_sim
    """
    
    with driver.session() as session:
        result = session.run(query)
        sim_count = 0
        non_sim_count = 0
        for record in result:
            if record["is_sim"] == 1:
                sim_count += 1
            else:
                non_sim_count += 1
        print(f"Non-SIMILAR_TO edges: {non_sim_count}")
        print(f"SIMILAR_TO edges: {sim_count}")

if __name__ == "__main__":
    test_graph_query()
