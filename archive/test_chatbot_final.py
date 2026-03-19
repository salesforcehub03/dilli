import sys
import io
# Force stdout to handle UTF-8 for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from services.chatbot_agent import get_chatbot_response
import json

test_questions = [
    "What was highest SAD cohort for Belinostat?",
    "What were the most frequently reported AE's for Belinostat in GI SOC?",
    "What exposures were seen in pre-clinical toxicology studies for Belinostat?",
    "Rank most common AE for treated patients 1-10 for Belinostat"
]

print("=== CHATBOT VERIFICATION START ===")
for q in test_questions:
    try:
        print(f"\nQUERY: {q}")
        response = get_chatbot_response(q, "Belinostat")
        reply = response.get('reply', 'No reply')
        # Print only first 1000 chars to avoid overwhelming terminal
        print(f"REPLY:\n{reply[:1000]}...")
        if response.get('cypher'):
            print(f"CYPHER: {response.get('cypher')}")
        print("-" * 50)
    except Exception as e:
        print(f"ERROR on query '{q}': {e}")

print("=== CHATBOT VERIFICATION END ===")
