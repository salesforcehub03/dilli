from datetime import datetime

class SessionService:
    def __init__(self):
        # In-memory storage for simplicity. 
        # In production, use Flask-Session or Redis.
        self.visited_drugs = []
        self.chat_history = []
        self.viewed_nodes = []
        self.session_start = datetime.now()

    def add_visit(self, drug_name):
        if not drug_name:
            return
            
        # Avoid duplicates in immediate succession
        if self.visited_drugs and self.visited_drugs[-1]["name"] == drug_name:
            return

        self.visited_drugs.append({
            "name": drug_name,
            "time": datetime.now().strftime("%H:%M:%S")
        })

    def add_node_view(self, node_type, label, properties):
        self.viewed_nodes.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "type": node_type,
            "label": label,
            "properties": properties
        })

    def add_chat(self, drug, question, answer):
        self.chat_history.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "drug": drug,
            "question": question,
            "answer": answer
        })

    def get_session_data(self):
        return {
            "start_time": self.session_start.strftime("%Y-%m-%d %H:%M:%S"),
            "drugs": self.visited_drugs,
            "chat": self.chat_history,
            "viewed_nodes": self.viewed_nodes,
            "total_visited": len(self.visited_drugs)
        }

    def clear_session(self):
        self.visited_drugs = []
        self.chat_history = []
        self.viewed_nodes = []
        self.session_start = datetime.now()

# Global Instance
session_manager = SessionService()
