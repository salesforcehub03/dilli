from services.llm_service import llm_manager
from config import Config
import json
import traceback

llm_manager.update_gemini_key(Config.GEMINI_API_KEY)
drug_name = 'Vorinostat'
all_target_cats = ['PreclinicalData', 'Transcriptomics', 'ExperimentalDesign', 'Genotoxicity', 'Exposure', 'MicroscopicFindings', 'AdverseEvents', 'Hepatotoxicity Risk', 'Metabolism & CYP Profile', 'Preclinical Organ Toxicity', 'Clinical Safety Alerts', 'Physicochemical Risk Factors']

prompt = (f"Generate a strictly formatted, highly detailed clinical and pharmacological analysis for the drug {drug_name}. "
          f"Output EXACTLY a JSON dictionary featuring these '{len(all_target_cats)}' Categories as keys: {', '.join(all_target_cats)}. "
          f"The value for each key MUST be a JSON list containing EXACTLY ONE dictionary with 3 to 4 insightful key-value pairs representing the specific medical/toxicity properties for that exact category. "
          f"Do NOT include markdown formatting or blocks, your output will be parsed natively via json.loads().")

res = llm_manager.query_gemini(prompt)
print(f"STATUS: {res.get('status')}")
try:
    reply_text = res['reply'].strip()
    if reply_text.startswith("```json"): reply_text = reply_text[7:]
    elif reply_text.startswith("```"): reply_text = reply_text[3:]
    if reply_text.endswith("```"): reply_text = reply_text[:-3]
    ai_data = json.loads(reply_text.strip())
    print("KEYS GENERATED:", list(ai_data.keys()))
except Exception as e:
    print("PARSE ERROR:")
    traceback.print_exc()
    print("RAW REPLY:")
    print(res.get("reply"))
