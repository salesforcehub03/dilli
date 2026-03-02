from flask import Blueprint, render_template, request, jsonify, make_response, session
from services.neo4j_service import driver, get_context_for_drug
from services.llm_service import llm_manager
from services.session_service import session_manager
from io import BytesIO
import json
import requests

main_bp = Blueprint('main', __name__)

# ===============================
# HOME & VISUALIZATION
# ===============================

@main_bp.route("/")
def home():
    session_manager.clear_session() # Start fresh
    return render_template("index.html")

@main_bp.route("/graph", methods=["POST"])
def graph():
    drug_input = request.form.get("drug")
    session_manager.add_visit(drug_input)
    return render_template("graph.html", drug=drug_input)

@main_bp.route("/get_graph_data")
def get_graph_data():
    drug_input = request.args.get("drug")
    
    if not driver:
        # Mock Data (Fallback)
        return jsonify({
            "nodes": [
                {"id": "1", "label": "Drug", "properties": {"name": drug_input or "TestDrug"}},
                {"id": "2", "label": "Drug Product Info", "properties": {"name": "Test Event"}}
            ],
            "edges": [
                {"id": "e1", "from": "1", "to": "2", "label": "HAS_EVENT", "properties": {}}
            ]
        })

    # Optimized Query
    query = """
    MATCH (d:Drug)
    WHERE toLower(d.drug_name) = toLower($drug) OR d.smiles = $drug
    MATCH (d)-[r*1..3]-(n)
    RETURN d, r, n
    LIMIT 100
    """

    try:
        with driver.session() as session:
            result = session.run(query, drug=drug_input)
            nodes = []
            edges = []
            processed_nodes = set()
            
            for record in result:
                d = record['d']
                if d.element_id not in processed_nodes:
                    nodes.append({"id": d.element_id, "label": list(d.labels)[0], "properties": dict(d)})
                    processed_nodes.add(d.element_id)
                
                n = record['n']
                if n.element_id not in processed_nodes:
                    nodes.append({"id": n.element_id, "label": list(n.labels)[0], "properties": dict(n)})
                    processed_nodes.add(n.element_id)

                path_rels = record['r']
                if isinstance(path_rels, list):
                    for rel in path_rels:
                         edges.append({
                            "id": rel.element_id,
                            "from": rel.start_node.element_id,
                            "to": rel.end_node.element_id,
                            "label": rel.type,
                            "properties": dict(rel)
                        })
                else:
                     edges.append({
                        "id": path_rels.element_id,
                        "from": path_rels.start_node.element_id,
                        "to": path_rels.end_node.element_id,
                        "label": path_rels.type,
                        "properties": dict(path_rels)
                    })
            
            # De-dupe edges
            unique_edges = list({e['id']: e for e in edges}.values())

    except Exception as e:
        print(f"Error executing query: {e}", flush=True)
        return jsonify({"error": str(e)}), 500

    # Enrich sparse Drug nodes from PubChem (outside Neo4j session)
    for node in nodes:
        if node['label'] == 'Drug' and node['properties'].get('drug_name') and not node['properties'].get('smiles'):
            try:
                pubchem = _fetch_pubchem_properties(node['properties']['drug_name'])
                if pubchem:
                    node['properties'].update(pubchem)
            except Exception as e:
                print(f"[PubChem] Error enriching {node['properties'].get('drug_name')}: {e}", flush=True)

    return jsonify({"nodes": nodes, "edges": unique_edges})

@main_bp.route("/get_similar_molecules")
def get_similar_molecules():
    drug_input = request.args.get("drug")

    if not driver:
        return jsonify({"molecules": []})

    query = """
    MATCH (d:Drug)
    WHERE toLower(d.drug_name) = toLower($drug) OR d.smiles = $drug
    MATCH (d)-[r:SIMILAR_TO]-(sm:Drug)
    WHERE sm.drug_name <> d.drug_name
    RETURN sm, r
    """

    try:
        with driver.session() as session:
            result = session.run(query, drug=drug_input)
            molecules = []
            seen = set()
            for record in result:
                sm = record['sm']
                sm_id = sm.element_id
                if sm_id in seen:
                    continue
                seen.add(sm_id)

                props = dict(sm)
                # Include relationship properties (e.g., similarity_score)
                rel = record.get('r')
                if rel:
                    rel_props = dict(rel) if hasattr(rel, '__iter__') else {}
                    for key in ['similarity_score', 'score', 'similarity']:
                        if key in rel_props:
                            props['similarity_score'] = rel_props[key]
                            break

                molecules.append(props)

        # Enrich sparse molecules from PubChem
        for mol in molecules:
            if not mol.get('smiles'):
                name = mol.get('drug_name') or mol.get('name')
                if name:
                    pubchem = _fetch_pubchem_properties(name)
                    if pubchem:
                        for k, v in pubchem.items():
                            if k not in mol or not mol[k]:
                                mol[k] = v

        return jsonify({"molecules": molecules})

    except Exception as e:
        print(f"Error fetching similar molecules: {e}")
        return jsonify({"molecules": [], "error": str(e)}), 500


@main_bp.route("/get_compare_data")
def get_compare_data():
    """Fetch subnode data for two drugs for side-by-side comparison."""
    drug1 = request.args.get("drug1")
    drug2 = request.args.get("drug2")

    if not driver or not drug1 or not drug2:
        return jsonify({"error": "Missing parameters or no database connection"}), 400

    query = """
    MATCH (d:Drug)
    WHERE toLower(d.drug_name) = toLower($drug) OR d.smiles = $drug
    MATCH (d)-[r*1..2]-(n)
    RETURN d, r, n
    LIMIT 100
    """

    def fetch_drug_data(drug_name):
        nodes = []
        edges = []
        drug_props = {}
        processed_nodes = set()

        try:
            with driver.session() as session:
                result = session.run(query, drug=drug_name)
                for record in result:
                    d = record['d']
                    if d.element_id not in processed_nodes:
                        drug_props = dict(d)
                        nodes.append({"id": d.element_id, "label": list(d.labels)[0], "properties": dict(d)})
                        processed_nodes.add(d.element_id)

                    n = record['n']
                    if n.element_id not in processed_nodes:
                        nodes.append({"id": n.element_id, "label": list(n.labels)[0], "properties": dict(n)})
                        processed_nodes.add(n.element_id)

                    path_rels = record['r']
                    if isinstance(path_rels, list):
                        for rel in path_rels:
                            edges.append({
                                "id": rel.element_id,
                                "from": rel.start_node.element_id,
                                "to": rel.end_node.element_id,
                                "label": rel.type,
                                "properties": dict(rel)
                            })
                    else:
                        edges.append({
                            "id": path_rels.element_id,
                            "from": path_rels.start_node.element_id,
                            "to": path_rels.end_node.element_id,
                            "label": path_rels.type,
                            "properties": dict(path_rels)
                        })
        except Exception as e:
            print(f"Error fetching compare data for {drug_name}: {e}", flush=True)

        # Group subnodes by label type (exclude the Drug node itself)
        subnodes = {}
        for node in nodes:
            lbl = node['label']
            if lbl == 'Drug':
                continue
            if lbl not in subnodes:
                subnodes[lbl] = []
            subnodes[lbl].append(node['properties'])

        unique_edges = list({e['id']: e for e in edges}.values())

        return {
            "name": drug_name,
            "drug_props": drug_props,
            "subnodes": subnodes,
            "nodes": nodes,
            "edges": unique_edges
        }

    result1 = fetch_drug_data(drug1)
    result2 = fetch_drug_data(drug2)

    return jsonify({"drug1": result1, "drug2": result2})

def _fetch_pubchem_properties(drug_name):
    """Fetch molecular properties from PubChem by drug name."""
    try:
        # Step 1: Resolve name to CID
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{requests.utils.quote(drug_name)}/cids/JSON"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        cids = resp.json().get("IdentifierList", {}).get("CID", [])
        if not cids:
            return None
        cid = cids[0]

        # Step 2: Fetch properties
        props_url = (
            f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/"
            "IsomericSMILES,CanonicalSMILES,MolecularWeight,XLogP,TPSA,HBondDonorCount,HBondAcceptorCount,IUPACName/JSON"
        )
        resp2 = requests.get(props_url, timeout=10)
        if resp2.status_code != 200:
            return None
        prop_list = resp2.json().get("PropertyTable", {}).get("Properties", [])
        if not prop_list:
            return None
        p = prop_list[0]

        # PubChem may return SMILES under different keys
        smiles = p.get("CanonicalSMILES") or p.get("IsomericSMILES") or p.get("SMILES") or ""

        return {
            "cid": cid,
            "smiles": smiles,
            "molecular_weight": p.get("MolecularWeight", ""),
            "logp": p.get("XLogP", ""),
            "tpsa": p.get("TPSA", ""),
            "h_donor": p.get("HBondDonorCount", ""),
            "h_acceptor": p.get("HBondAcceptorCount", ""),
            "iupac_name": p.get("IUPACName", ""),
        }
    except Exception as e:
        print(f"[PubChem] Lookup failed for {drug_name}: {e}", flush=True)
        return None

# ===============================
# CHATBOT ENDPOINTS
# ===============================

@main_bp.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message")
    drug_input = data.get("drug")
    
    # 1. Get Context
    context_text = get_context_for_drug(drug_input)

    # 2. Try Azure
    reply_data = llm_manager.query_azure(f"Context: {context_text}\nQuestion: {user_message}")
    
    # 3. Try Gemini
    if not reply_data:
        # Check if key is set
        if not llm_manager.gemini_key:
             return jsonify({"reply": "API Key not configured.", "error_code": "KEY_MISSING", "status": 401}), 401

        prompt = f"""
        You are a helpful assistant for a Drug-Induced Liver Injury (DILI) analysis platform.
        User Question: "{user_message}"
        Context from Knowledge Graph for drug '{drug_input}':
        {context_text}
        
        Answer based on the context. If unknown, say so.
        """
        reply_data = llm_manager.query_gemini(prompt)

    # 4. Fallback
    if not reply_data:
        reply_data = {"reply": "No AI backend configured.", "status": 200}

    # Store in history
    if reply_data.get("status") == 200:
        session_manager.add_chat(drug_input, user_message, reply_data.get("reply"))
    
    return jsonify(reply_data), reply_data.get("status", 200)

@main_bp.route("/set_key", methods=["POST"])
def set_key():
    data = request.get_json()
    new_key = data.get("key")
    if new_key:
        llm_manager.update_gemini_key(new_key)
        print(f"[INFO] Gemini API Key updated via UI.")
        return jsonify({"status": "success", "message": "API Key updated successfully."})
    return jsonify({"status": "error", "message": "Invalid key"}), 400

@main_bp.route("/track_node", methods=["POST"])
def track_node():
    data = request.get_json()
    node_type = data.get("type", "Unknown")
    label = data.get("label", "")
    properties = data.get("properties", {})
    session_manager.add_node_view(node_type, label, properties)
    return jsonify({"status": "ok"})

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import base64

@main_bp.route("/download_report", methods=["POST"])
def download_report():
    session_data = session_manager.get_session_data()
    data = request.get_json(silent=True) or {}
    graph_image_b64 = data.get("graph_image", "")
    
    # Create PDF buffer
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    heading_style = styles['Heading2']
    normal_style = styles['Normal']
    
    # Title
    elements.append(Paragraph("DILI Analysis Session Report", title_style))
    elements.append(Spacer(1, 12))
    
    # Metadata
    elements.append(Paragraph(f"Generated: {session_data['start_time']}", normal_style))
    elements.append(Paragraph(f"Total Drugs Analyzed: {session_data['total_visited']}", normal_style))
    elements.append(Spacer(1, 12))

    # --- GRAPH SNAPSHOT ---
    if graph_image_b64:
        try:
            # Remove header if present (data:image/png;base64,...)
            if "," in graph_image_b64:
                graph_image_b64 = graph_image_b64.split(",")[1]
            
            img_data = base64.b64decode(graph_image_b64)
            img_io = BytesIO(img_data)
            
            # Create Image for ReportLab
            # Constrain width to page width (approx 6 inches)
            img = RLImage(img_io, width=6*inch, height=4*inch, kind='proportional')
            elements.append(Paragraph("Current Visualization Snapshot", heading_style))
            elements.append(Spacer(1, 6))
            elements.append(img)
            elements.append(Spacer(1, 24))
        except Exception as e:
            print(f"Error processing graph image: {e}")
            elements.append(Paragraph(f"Error including graph image: {e}", normal_style))

    # --- DRUGS TABLE ---
    elements.append(Paragraph("Drugs Visited", heading_style))
    elements.append(Spacer(1, 6))

    data = [["Time", "Drug Name"]] # Header
    if session_data['drugs']:
        for item in session_data['drugs']:
            data.append([item['time'], item['name']])
    else:
        data.append(["-", "No drugs analyzed in this session."])

    t = Table(data, colWidths=[100, 400])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 24))

    # --- NODES EXPLORED ---
    viewed = session_data.get('viewed_nodes', [])
    if viewed:
        elements.append(Paragraph("Nodes Explored", heading_style))
        elements.append(Spacer(1, 6))

        for node in viewed:
            node_block = []
            ntype = node.get('type', 'Node')
            nlabel = node.get('label', '')
            ntime = node.get('time', '')
            node_block.append(Paragraph(f"<b>[{ntime}] {ntype}:</b> {nlabel}", normal_style))

            props = node.get('properties', {})
            if props:
                prop_data = [["Property", "Value"]]
                for k, v in props.items():
                    val_str = str(v) if v is not None else ""
                    if len(val_str) > 120:
                        val_str = val_str[:120] + "..."
                    prop_data.append([Paragraph(f"<b>{k}</b>", normal_style), Paragraph(val_str, normal_style)])

                pt = Table(prop_data, colWidths=[150, 350])
                pt.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#34495e")),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#ecf0f1")),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                node_block.append(Spacer(1, 4))
                node_block.append(pt)

            node_block.append(Spacer(1, 12))
            elements.append(KeepTogether(node_block))

    # --- CHAT HISTORY ---
    if session_data.get('chat'):
        elements.append(Paragraph("Chat History", heading_style))
        elements.append(Spacer(1, 12))
        
        for chat in session_data['chat']:
            # Use KeepTogether to ensure Q&A stay on same page if possible
            qa_block = []
            qa_block.append(Paragraph(f"<b>[{chat['time']}] Q:</b> {chat['question']}", normal_style))
            qa_block.append(Spacer(1, 4))
            qa_block.append(Paragraph(f"<b>A:</b> {chat['answer']}", normal_style))
            qa_block.append(Spacer(1, 12))
            elements.append(KeepTogether(qa_block))
    
    # Footer
    elements.append(Spacer(1, 24))
    elements.append(Paragraph("Generated by DILI Analysis Platform", normal_style))
    
    # Build PDF
    doc.build(elements)
    
    buffer.seek(0)
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=dili_session_report.pdf'
    return response
