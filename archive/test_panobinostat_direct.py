import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from services.tox_predictor import predict_drug_toxicity

load_dotenv()

uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")
api_key = os.getenv("GEMINI_API_KEY")

driver = GraphDatabase.driver(uri, auth=(user, password))

def test_panobinostat():
    print("Testing toxicity prediction for Panobinostat...")
    try:
        result = predict_drug_toxicity("Panobinostat", driver, api_key)
        import json
        print(json.dumps(result, indent=4))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_panobinostat()
    driver.close()
