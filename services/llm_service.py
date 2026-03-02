import requests
import json
from config import Config

class LLMService:
    def __init__(self):
        self.gemini_key = None # Must be set via UI
        self.gemini_models = ["gemini-1.5-flash", "gemini-2.0-flash"]
        self.azure_config = {
            "endpoint": Config.AZURE_OPENAI_ENDPOINT,
            "key": Config.AZURE_OPENAI_API_KEY,
            "deployment": Config.AZURE_OPENAI_DEPLOYMENT,
            "version": Config.AZURE_OPENAI_VERSION
        }

    def update_gemini_key(self, new_key):
        """Update API key at runtime."""
        self.gemini_key = new_key

    def query_azure(self, prompt):
        cfg = self.azure_config
        if not cfg["endpoint"] or not cfg["key"]:
            return None
        
        base_url = cfg["endpoint"].rstrip('/')
        url = f"{base_url}/openai/deployments/{cfg['deployment']}/chat/completions?api-version={cfg['version']}"
        
        headers = {
            "Content-Type": "application/json",
            "api-key": cfg["key"]
        }
        
        payload = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant for drug safety analysis."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 800
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                try:
                    return {"reply": data["choices"][0]["message"]["content"], "status": 200}
                except (KeyError, IndexError):
                    return {"reply": "Error parsing Azure response.", "status": 500}
            else:
                return {"reply": f"Azure OpenAI Error ({response.status_code}): {response.text}", "status": response.status_code}
        except Exception as e:
            return {"reply": f"Azure Connection Error: {e}", "status": 500}

    def query_gemini(self, prompt):
        if not self.gemini_key:
            return None

        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }

        errors = []
        
        # Try models in sequence (Fallback Logic)
        for model_name in self.gemini_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.gemini_key}"
            try:
                masked_key = self.gemini_key[:5] + "..." if self.gemini_key else "None"
                print(f"[DEBUG] querying {model_name} with key: {masked_key}")
                
                response = requests.post(url, json=payload, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    try:
                        text = data["candidates"][0]["content"]["parts"][0]["text"]
                        return {"reply": text, "status": 200}
                    except (KeyError, IndexError):
                        print(f"[ERROR] Parse failed. Raw: {response.text}")
                        return {"reply": "Error parsing Gemini response.", "status": 500}
                else:
                    print(f"[FAIL] {model_name} Error: {response.status_code} - {response.text}")
                    error_msg = f"Model {model_name} failed: {response.text}"
                    errors.append(error_msg)
            except Exception as e:
                print(f"[ERROR] Connection failed for {model_name}: {e}")
                errors.append(str(e))
        
        # All failed
        full_error = "; ".join(errors)
        is_quota = "quota" in full_error.lower() or "429" in full_error
        is_invalid = "API_KEY_INVALID" in full_error or "API key not valid" in full_error
        
        status_code = 500
        error_code = None
        
        if is_quota:
            status_code = 503
            error_code = "QUOTA_EXCEEDED"
        elif is_invalid:
            status_code = 401
            error_code = "INVALID_KEY"

        return {
            "reply": f"Gemini Error: {full_error}",
            "status": status_code,
            "error_code": error_code
        }

# Global Instance
llm_manager = LLMService()
