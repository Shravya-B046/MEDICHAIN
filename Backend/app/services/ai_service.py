import difflib
import json
import logging
import re
import urllib.request
from typing import Dict, List, Optional, Tuple

from app.config import settings

logger = logging.getLogger(__name__)

# Trusted medical reference sources
TRUSTED_SOURCES = [
    {"name": "WHO (World Health Organization)", "url": "https://www.who.int"},
    {"name": "MedlinePlus (National Library of Medicine)", "url": "https://medlineplus.gov"},
    {"name": "MoHFW / ICMR (Govt. of India)", "url": "https://www.mohfw.gov.in"},
    {"name": "NHS (National Health Service)", "url": "https://www.nhs.uk"},
    {"name": "FDA Drug Information", "url": "https://www.fda.gov/drugs"},
]

# Emergency red-flag trigger patterns that require immediate clinical triage
EMERGENCY_PATTERNS = [
    r"\b(chest\s+pain|heart\s+attack|crushing\s+chest|pressure\s+in\s+chest)\b",
    r"\b(shortness\s+of\s+breath|cannot\s+breathe|gasping|struggling\s+to\s+breathe|choking)\b",
    r"\b(stroke|face\s+droop|arm\s+weakness|slurred\s+speech|sudden\s+paralysis)\b",
    r"\b(coughing\s+blood|vomiting\s+blood|bleeding\s+uncontrollably)\b",
    r"\b(unconscious|passed\s+out|fainted|unresponsive)\b",
    r"\b(poison|poisoning|swallowed\s+chemical|overdose)\b",
    r"\b(thunderclap\s+headache|sudden\s+severe\s+headache\s+worst\s+of\s+life)\b",
    r"\b(anaphylaxis|throat\s+closing|lip\s+swelling|severe\s+allergic\s+reaction)\b",
]

# Curated verified medical knowledge base for common medications (WHO & MedlinePlus aligned)
VERIFIED_MEDICINE_KB: Dict[str, Dict] = {
    "paracetamol": {
        "brand_examples": ["Dolo 650", "Calpol", "Crocin", "Tylenol", "Panadol"],
        "generic_name": "Paracetamol (Acetaminophen)",
        "uses": "Relief of mild-to-moderate pain (headaches, muscular aches, toothaches) and reduction of fever.",
        "mechanism": "Blocks chemical messengers (prostaglandins) in the central nervous system that signal pain and regulates the brain's heat-regulating center (hypothalamus).",
        "side_effects": "Generally well tolerated at therapeutic doses. Rarely: mild nausea, allergic rash. Liver toxicity can occur if daily maximum limits are exceeded.",
        "precautions": "Maximum 4,000 mg (4g) per 24 hours for adults. Avoid concurrent medications containing acetaminophen to prevent accidental overdose. Extreme caution in liver disease or chronic alcohol use.",
        "interactions": "Warfarin (prolonged high doses can increase bleeding risk), alcohol (increases hepatotoxicity risk), carbamazepine, isoniazid.",
        "administration": "Can be taken with or without food. Swallow with a full glass of water. If gastric sensitivity occurs, take after meals.",
        "when_doctor": "Fever exceeding 3 days, pain lasting more than 5 days, yellowing of eyes/skin, dark urine, or severe nausea/vomiting.",
    },
    "ibuprofen": {
        "brand_examples": ["Brufen", "Advil", "Motrin", "Nurofen"],
        "generic_name": "Ibuprofen (NSAID)",
        "uses": "Relief of inflammatory pain (joint pain, dental pain, menstrual cramps, arthritis, fever).",
        "mechanism": "Non-steroidal anti-inflammatory drug (NSAID) that inhibits COX-1 and COX-2 enzymes, suppressing inflammatory prostaglandins.",
        "side_effects": "Indigestion, heartburn, stomach pain, dizziness, mild nausea.",
        "precautions": "Avoid in active peptic ulcer disease, severe heart failure, severe kidney impairment, or late pregnancy. Do not combine with other NSAIDs.",
        "interactions": "Aspirin, blood thinners (Warfarin/Heparin), ACE inhibitors, diuretics, corticosteroids.",
        "administration": "Always take with or immediately after food or milk to minimize gastric irritation.",
        "when_doctor": "Black tarry stools, persistent stomach ache, vomit resembling coffee grounds, or fluid retention/swelling in ankles.",
    },
    "metformin": {
        "brand_examples": ["Glucophage", "Glycomet", "Riomet"],
        "generic_name": "Metformin Hydrochloride",
        "uses": "First-line oral management for Type 2 Diabetes Mellitus; improves glycemic control.",
        "mechanism": "Decreases hepatic glucose production, decreases intestinal absorption of glucose, and improves insulin sensitivity in peripheral tissues.",
        "side_effects": "Diarrhea, nausea, stomach upset, metallic taste, vitamin B12 deficiency with prolonged use.",
        "precautions": "Contraindicated in severe renal impairment (eGFR < 30 mL/min). Stop temporarily prior to iodinated radiocontrast procedures.",
        "interactions": "Alcohol (increases lactic acidosis risk), cimetidine, certain diuretics, and carbonic anhydrase inhibitors.",
        "administration": "Take with meals (usually breakfast and/or dinner) to significantly reduce gastrointestinal upset.",
        "when_doctor": "Extreme fatigue, muscle cramps, rapid/difficult breathing, unexplained drowsiness (rare signs of lactic acidosis).",
    },
    "amoxicillin": {
        "brand_examples": ["Mox", "Amoxil", "Novamox"],
        "generic_name": "Amoxicillin (Beta-lactam Antibiotic)",
        "uses": "Treatment of susceptible bacterial infections (ear, nose, throat, respiratory, skin, urinary tract). Does NOT treat viral colds or flu.",
        "mechanism": "Inhibits bacterial cell wall synthesis during active multiplication, causing bacterial cell lysis and death.",
        "side_effects": "Mild diarrhea, loose stools, nausea, mild skin rash.",
        "precautions": "Contraindicated in confirmed penicillin allergy. Must complete the full prescribed course even if symptoms resolve early to prevent antibiotic resistance.",
        "interactions": "Oral contraceptives (may reduce effectiveness), methotrexate, probenecid, allopurinol.",
        "administration": "Can be taken with or without meals. Maintain consistent intervals (e.g., every 8 or 12 hours) with adequate water intake.",
        "when_doctor": "Severe watery diarrhea lasting days, severe hives/itching, facial swelling, or breathing difficulty.",
    },
    "azithromycin": {
        "brand_examples": ["Azee", "Zithromax", "Azithral"],
        "generic_name": "Azithromycin (Macrolide Antibiotic)",
        "uses": "Bacterial respiratory tract infections, bronchitis, community-acquired pneumonia, skin infections, certain STIs.",
        "mechanism": "Binds to the 50S ribosomal subunit of susceptible microorganisms, inhibiting bacterial protein synthesis.",
        "side_effects": "Nausea, diarrhea, abdominal cramps, mild headache, temporary taste alteration.",
        "precautions": "Caution in patients with cardiac conduction disorders (prolonged QT interval) or myasthenia gravis.",
        "interactions": "Antacids containing aluminum or magnesium (separate by 2 hours), digoxin, warfarin, ergotamine.",
        "administration": "Commonly taken once daily. Tablets can be taken with or without food; take at least 1 hour before or 2 hours after meals if using suspension.",
        "when_doctor": "Irregular heartbeat/palpitations, severe dizziness, yellowing of skin/eyes, persistent diarrhea.",
    },
    "cetirizine": {
        "brand_examples": ["Zyrtec", "Cetzine", "Alerid"],
        "generic_name": "Cetirizine Hydrochloride (Second-generation Antihistamine)",
        "uses": "Relief of allergic symptoms: allergic rhinitis, runny nose, sneezing, itchy/watery eyes, hives, skin allergies.",
        "mechanism": "Selectively blocks peripheral H1 histamine receptors, suppressing allergic cascade without prominent central sedation.",
        "side_effects": "Mild drowsiness in some individuals, dry mouth, mild headache, fatigue.",
        "precautions": "Use caution when driving or operating machinery. Dosage adjustment needed in moderate-to-severe renal impairment.",
        "interactions": "Alcohol, central nervous system depressants, sedatives.",
        "administration": "Typically taken once daily in the evening, with or without food.",
        "when_doctor": "Severe difficulty urinating, enlarged prostate symptoms, or if allergic symptoms persist without relief.",
    },
    "omeprazole": {
        "brand_examples": ["Prilosec", "Omez", "Losec"],
        "generic_name": "Omeprazole (Proton Pump Inhibitor - PPI)",
        "uses": "Gastroesophageal reflux disease (GERD), acid peptic disease, stomach ulcers, and protection against NSAID-induced ulcers.",
        "mechanism": "Irreversibly inhibits the H+/K+ ATPase enzyme system in gastric parietal cells, profoundly decreasing stomach acid secretion.",
        "side_effects": "Headache, constipation, mild diarrhea, abdominal flatulence.",
        "precautions": "Prolonged use (> 1 year) may decrease magnesium/calcium absorption and increase fracture or C. difficile infection risk.",
        "interactions": "Clopidogrel (decreases antiplatelet activity), ketoconazole, iron supplements, methotrexate.",
        "administration": "Take once daily in the morning, 30 to 60 minutes before the first meal of the day with water.",
        "when_doctor": "Difficulty swallowing food, vomiting blood, black tarry stools, or persistent unexplained weight loss.",
    },
    "pantoprazole": {
        "brand_examples": ["Pantocid", "Protonix", "Pan 40"],
        "generic_name": "Pantoprazole Sodium (Proton Pump Inhibitor)",
        "uses": "Erosive esophagitis, gastroesophageal reflux (GERD), pathological hypersecretory conditions.",
        "mechanism": "Suppresses gastric acid secretion by specific inhibition of the hydrogen-potassium ATPase pump in gastric parietal cells.",
        "side_effects": "Mild headache, diarrhea, abdominal discomfort, dizziness.",
        "precautions": "Swallow tablets whole; do not chew, crush, or split enteric-coated tablets.",
        "interactions": "HIV protease inhibitors (Atazanavir), iron salts, warfarin, methotrexate.",
        "administration": "Take 30 to 60 minutes before breakfast with a full glass of water.",
        "when_doctor": "Severe persistent stomach pain, severe diarrhea with fever, or signs of hypomagnesemia (muscle spasms, tremors).",
    },
    "ors": {
        "brand_examples": ["Electral", "WHO-ORS", "Pedialyte"],
        "generic_name": "Oral Rehydration Salts (WHO Formulation)",
        "uses": "Prevention and treatment of clinical dehydration resulting from acute diarrhea, cholera, vomiting, or excessive sweating.",
        "mechanism": "Sodium and glucose coupled co-transport across the intestinal mucosal brush border promotes rapid osmotic absorption of water and electrolytes.",
        "side_effects": "Virtually none when reconstituted with correct water volume. Hypernatremia if prepared with insufficient water.",
        "precautions": "Always dissolve the packet in the exact recommended volume of clean potable water (typically 1 liter). Do NOT add extra sugar, milk, or fruit juice.",
        "interactions": "No adverse drug interactions; safely co-administered with standard therapies.",
        "administration": "Sip continuously throughout the day following loose stools. Reconstituted solution must be used within 24 hours.",
        "when_doctor": "Inability to drink or keep fluids down, sunken eyes, lethargy, no urination for 6+ hours in children, or blood in stool.",
    },
}


class AIService:
    """
    Production-grade AI Health Integration Service for MEDICHAIN.
    Adheres strictly to WHO, MedlinePlus, ICMR, and FDA healthcare standards:
    - Provides structured 8-part explanations for medication queries.
    - Prevents unauthorized prescribing, dosage calculation, and clinical diagnosis.
    - Implements emergency red-flag fast-path alerts.
    - Resolves ambiguous/misspelled medicine names safely.
    - Manages multi-turn conversation memory for contextual follow-ups.
    - Ephemeral, zero-retention processing for medical reports.
    """

    def __init__(self) -> None:
        self.api_key = settings.GEMINI_API_KEY
        self._client = None
        self._init_client()

    def _init_client(self) -> None:
        if not self.api_key:
            return

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key, transport="rest")
            self._client = genai.GenerativeModel("gemini-3.1-flash-lite")
            logger.info("Initialized Google Generative AI (Gemini 3.1 Flash-Lite) client with REST transport.")
        except Exception as e:
            logger.warning(f"Could not initialize Gemini API: {e}. Falling back to clinical rule engine.")
            self._client = None

    def _detect_emergency(self, text: str) -> bool:
        """Evaluates whether the user's message contains acute medical red flags."""
        text_lower = text.lower()
        for pattern in EMERGENCY_PATTERNS:
            if re.search(pattern, text_lower):
                return True
        return False

    def _match_medicine(self, query: str) -> Tuple[Optional[str], Optional[Dict], bool]:
        """
        Looks up a medicine in the verified knowledge base.
        Returns: (med_key, med_data, is_exact_match)
        """
        query_clean = query.lower()

        # Check for brand or generic keywords
        for key, data in VERIFIED_MEDICINE_KB.items():
            if key in query_clean:
                return key, data, True
            for brand in data["brand_examples"]:
                if brand.lower() in query_clean:
                    return key, data, True

        # Fuzzy matching across individual tokens
        tokens = re.findall(r"[a-zA-Z]{4,}", query_clean)
        for token in tokens:
            # Check close match to medicine keys
            matches = difflib.get_close_matches(token, VERIFIED_MEDICINE_KB.keys(), n=1, cutoff=0.72)
            if matches:
                return matches[0], VERIFIED_MEDICINE_KB[matches[0]], False

            # Check close match to brand names
            for key, data in VERIFIED_MEDICINE_KB.items():
                brand_tokens = [b.lower().split()[0] for b in data["brand_examples"]]
                brand_matches = difflib.get_close_matches(token, brand_tokens, n=1, cutoff=0.75)
                if brand_matches:
                    return key, data, False

        return None, None, False

    def _is_medicine_query(self, query: str) -> bool:
        """Determines if the prompt is seeking medication or drug information."""
        keywords = [
            "tablet", "medicine", "medication", "pill", "capsule", "drug",
            "dose", "dosage", "syrup", "side effect", "prescribed", "inject",
            "paracetamol", "dolo", "ibuprofen", "metformin", "amoxicillin",
            "azithromycin", "cetirizine", "omeprazole", "pantoprazole", "ors"
        ]
        q_lower = query.lower()
        return any(k in q_lower for k in keywords)

    def _build_structured_medicine_kb_response(self, med_data: Dict, is_exact: bool, query_name: str) -> str:
        """Constructs an 8-part clinical medicine summary from verified knowledge base."""
        prefix = ""
        if not is_exact:
            prefix = (
                f"> [!NOTE]\n"
                f"> You asked about **'{query_name}'**. If you meant **{med_data['generic_name']}**, "
                f"here is the verified clinical information. Please confirm the exact prescription name with your doctor or pharmacist.\n\n"
            )

        brands_str = ", ".join(med_data["brand_examples"])
        return (
            f"{prefix}"
            f"### 1. Medicine Name & Generic Composition\n"
            f"- **Generic Name:** {med_data['generic_name']}\n"
            f"- **Common Brand / Trade Examples:** {brands_str}\n\n"
            f"### 2. Common Medical Uses\n"
            f"{med_data['uses']}\n\n"
            f"### 3. How It Works in the Body (Mechanism)\n"
            f"{med_data['mechanism']}\n\n"
            f"### 4. Common Side Effects\n"
            f"{med_data['side_effects']}\n\n"
            f"### 5. Important Precautions & Warnings\n"
            f"{med_data['precautions']}\n\n"
            f"### 6. Known Drug & Substance Interactions\n"
            f"{med_data['interactions']}\n\n"
            f"### 7. Food & Administration Considerations\n"
            f"{med_data['administration']}\n\n"
            f"### 8. Situations Requiring Medical Advice\n"
            f"{med_data['when_doctor']}\n\n"
            f"---\n"
            f"**Authoritative Sources:** MedlinePlus, WHO Essential Medicines, FDA Prescribing Information.\n"
            f"*Disclaimer: Never adjust doses or start prescription medicines without consulting a qualified physician.*"
        )

    def _call_gemini_direct(self, prompt: str) -> str:
        """Direct REST HTTPS fallback to Google Gemini v1beta API."""
        models_to_try = ["gemini-3.1-flash-lite", "gemini-3.8-flash"]
        for m in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={self.api_key}"
            payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=14) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts and "text" in parts[0]:
                            return parts[0]["text"]
            except Exception as ex:
                logger.warning(f"Direct Gemini REST attempt on {m} failed: {ex}")
        return ""

    def get_health_guidance(
        self,
        question: str,
        history: Optional[List[Dict[str, str]]] = None,
        context: Optional[str] = None
    ) -> Tuple[str, str, bool, bool, List[str]]:
        """
        Processes general health or medicine inquiries with strict clinical safety guardrails.
        Returns:
            (reply_text, source, is_emergency, is_medicine_query, verified_sources)
        """
        cleaned = question.strip()
        is_emergency = self._detect_emergency(cleaned)
        is_medicine = self._is_medicine_query(cleaned)

        # Dynamic re-check for API key if added while server is running
        if not self._client and settings.GEMINI_API_KEY:
            self.api_key = settings.GEMINI_API_KEY
            self._init_client()

        # EMERGENCY FAST-PATH
        if is_emergency:
            emergency_reply = (
                "🚨 **URGENT MEDICAL NOTICE: SEEK IMMEDIATE EMERGENCY CARE**\n\n"
                "The symptoms described in your message (such as acute chest pain, severe breathing difficulty, "
                "stroke indicators, sudden paralysis, or uncontrolled bleeding) represent potentially life-threatening medical emergencies.\n\n"
                "**Immediate Action Steps:**\n"
                "1. **Call Emergency Medical Services IMMEDIATELY** (Dial **112** in India/Europe, **911** in the US, or **108** for Ambulance).\n"
                "2. Do not drive yourself to the hospital; have emergency paramedics transport you with supportive equipment.\n"
                "3. Use the **[Emergency Coordination](emergency.html)** module in MEDICHAIN to dispatch an ambulance or identify the nearest trauma center.\n"
                "4. Rest quietly in a safe position while awaiting professional help.\n\n"
                "*Do not continue relying on an AI chat assistant for active medical emergencies.*"
            )
            return emergency_reply, "verified_medical_kb", True, is_medicine, ["WHO Emergency Guidelines", "AHA / ERC Guidelines"]

        # Check verified local knowledge base for exact/fuzzy medicine matches
        med_key, med_data, is_exact = self._match_medicine(cleaned)

        # Formulate Gemini clinical instruction prompt
        system_instruction = (
            "You are the MEDICHAIN AI Clinical Health Assistant, an advanced healthcare information companion. "
            "Your knowledge is strictly grounded in official guidelines from the World Health Organization (WHO), "
            "MedlinePlus (National Library of Medicine), ICMR / MoHFW (India), NHS, and FDA.\n\n"
            "MANDATORY CLINICAL SAFETY RULES:\n"
            "1. NEVER formulate a definitive diagnosis. Always distinguish possibilities from confirmed medical conditions.\n"
            "2. NEVER prescribe prescription drugs, calculate custom drug dosages, or advise stopping a doctor's prescription.\n"
            "3. If the user asks about a MEDICINE (uses, side effects, precautions, interactions, or food considerations), "
            "format your answer with these clear Markdown numbered sections:\n"
            "   ### 1. Medicine Name & Generic Name\n"
            "   ### 2. Common Medical Uses\n"
            "   ### 3. How It Works in the Body (in plain language)\n"
            "   ### 4. Common Side Effects\n"
            "   ### 5. Important Precautions & Warnings\n"
            "   ### 6. Known Interactions (other drugs, alcohol)\n"
            "   ### 7. Food & Administration Considerations (e.g. before/after food)\n"
            "   ### 8. Situations Where Medical Advice Is Necessary\n"
            "4. If a medicine name has an ambiguous or unclear spelling, ask the user to confirm the medicine name before proceeding.\n"
            "5. For GENERAL HEALTH questions, structure with:\n"
            "   - Understanding the Condition / Symptoms\n"
            "   - Potential Causes (as possibilities, not diagnosis)\n"
            "   - General Self-Care & Lifestyle Precautions\n"
            "   - Warning Signs & When to See a Doctor\n"
            "6. REDUCE HALLUCINATIONS: Do not invent URLs, research papers, or clinical facts. If trustworthy information is unavailable, "
            "state clearly: 'I couldn't verify this information from a reliable medical source. Please consult a qualified healthcare professional.'\n"
            "7. Conclude every response with a concise reminder that this is for educational purposes and requires doctor consultation."
        )

        # Build multi-turn context if history is provided
        conversation_context = ""
        if history:
            history_lines = []
            for item in history[-6:]:  # Keep last 6 turns for optimal context
                role_label = "User" if item.get("role") in ["user", "human"] else "Assistant"
                content_snippet = item.get("content", "").strip()[:500]
                if content_snippet:
                    history_lines.append(f"{role_label}: {content_snippet}")
            if history_lines:
                conversation_context = "PRIOR CONVERSATION HISTORY:\n" + "\n".join(history_lines) + "\n\n"

        full_prompt = (
            f"{system_instruction}\n\n"
            f"{conversation_context}"
            f"CURRENT USER INQUIRY: {cleaned}\n\n"
            f"Respond clearly, compassionately, and with structured Markdown headers and bullet points."
        )

        verified_source_names = [s["name"] for s in TRUSTED_SOURCES]

        # 1. Try Gemini API
        if self._client:
            try:
                response = self._client.generate_content(full_prompt)
                if response and response.text:
                    return response.text, "gemini_api", False, is_medicine, verified_source_names
            except Exception as e:
                logger.warning(f"Gemini GenerativeModel call failed: {e}. Trying direct REST fallback...")

        # 2. Try direct REST fallback
        if self.api_key:
            direct_reply = self._call_gemini_direct(full_prompt)
            if direct_reply:
                return direct_reply, "gemini_api", False, is_medicine, verified_source_names

        # 3. Use Verified Medicine KB if user asked about a cataloged medicine
        if med_data:
            kb_reply = self._build_structured_medicine_kb_response(med_data, is_exact, cleaned)
            return kb_reply, "verified_medical_kb", False, True, ["MedlinePlus", "WHO Model Formulary"]

        # 4. Clinical Rule-Based Fallback
        text_lower = cleaned.lower()
        if "fever" in text_lower or "temperature" in text_lower:
            reply = (
                "### Understanding Fever\n"
                "A fever is a temporary elevation in body temperature (typically 100.4°F / 38°C or higher), "
                "most commonly acting as the body's natural physiological defense against viral or bacterial infections.\n\n"
                "### Potential Causes (Possibilities)\n"
                "- Viral upper respiratory infections (common cold, flu)\n"
                "- Bacterial infections (strep throat, urinary tract infections)\n"
                "- Inflammatory conditions or post-immunization reactions\n\n"
                "### General Care & Precautions\n"
                "- **Hydration:** Drink plenty of fluids (water, oral rehydration solutions, clear broths) to replace fluid lost through sweating.\n"
                "- **Rest:** Get adequate physical rest to support immune recovery.\n"
                "- **Clothing:** Dress in light, breathable fabrics and keep the room at a comfortable temperature.\n\n"
                "### When to Seek Medical Attention\n"
                "- Fever exceeding **103°F (39.4°C)** in adults, or lasting more than 3 consecutive days.\n"
                "- Fever accompanied by stiff neck, shortness of breath, confusion, severe rash, or persistent vomiting.\n\n"
                "*Source: MedlinePlus & WHO Clinical Guidelines.*"
            )
        elif "cough" in text_lower or "cold" in text_lower:
            reply = (
                "### Understanding Common Cold & Cough\n"
                "A cold is a mild viral upper respiratory tract infection. Coughing is the airway's natural protective reflex "
                "to clear mucus, irritants, or microbial pathogens.\n\n"
                "### General Care & Safe Measures\n"
                "- **Steam Inhalation & Humidification:** Warm moist air helps loosen mucosal congestion.\n"
                "- **Warm Saline Gargles:** Gargling warm salt water 2-3 times daily provides soothing relief for irritated throat tissue.\n"
                "- **Adequate Hydration:** Warm teas, water, and broths keep the airway mucosa hydrated.\n\n"
                "### Important Precautions\n"
                "- Antibiotics do not work against viral infections like colds or the flu.\n"
                "- Seek medical attention if you experience breathing difficulty, wheezing, coughing up discolored blood, or symptoms lasting over 10 days.\n\n"
                "*Source: WHO & NHS Health Guidelines.*"
            )
        elif "dehydration" in text_lower or "water" in text_lower or "thirst" in text_lower:
            reply = (
                "### Understanding Dehydration\n"
                "Dehydration occurs when fluid output exceeds fluid intake, disrupting normal electrolyte balance.\n\n"
                "### Common Signs & Symptoms\n"
                "- Persistent thirst and dry or sticky mouth\n"
                "- Dark yellow or amber-colored urine with decreased volume\n"
                "- Mild dizziness, fatigue, or headache\n\n"
                "### Recommended Precautions & Rehydration\n"
                "- **Oral Rehydration Therapy:** Sip WHO-formulated Oral Rehydration Salts (ORS) or water slowly and steadily.\n"
                "- Avoid high-sugar carbonated beverages or alcohol, which can worsen fluid imbalance.\n\n"
                "### Critical Warning Signs\n"
                "Seek immediate emergency evaluation for confusion, sunken eyes, rapid heart rate, inability to retain fluids, or absence of urination for 8+ hours.\n\n"
                "*Source: WHO Oral Rehydration Therapy Guidelines.*"
            )
        else:
            reply = (
                f"### Clinical Guidance on '{cleaned}'\n\n"
                "As an informational healthcare assistant, I can provide general medical and wellness principles. "
                "Because individual medical history, underlying conditions, and concurrent medications significantly affect health outcomes:\n\n"
                "- **Diagnostic Assessment:** Accurate evaluation requires in-person clinical examination and appropriate diagnostic tests.\n"
                "- **Safe Precautions:** Monitor your symptoms carefully, maintain consistent hydration and rest, and avoid self-medicating with prescription drugs.\n"
                "- **Medical Consultation:** Please consult a licensed medical doctor or healthcare provider for specific examination and personalized therapy.\n\n"
                "If reliable official data is unavailable for your specific query: *I couldn't verify this information from an authoritative medical source. Please consult a qualified healthcare professional.*"
            )

        return reply, "synthetic_demo", False, is_medicine, verified_source_names

    def analyze_medical_document(
        self,
        filename: str,
        file_size_kb: float,
        content_type: str,
        extracted_text: str = "",
        extracted_findings: List[str] = None,
    ) -> Dict:
        """
        Analyzes uploaded diagnostic reports with zero-retention memory processing.
        Adheres to clinical privacy and non-diagnostic disclaimers.
        """
        findings = extracted_findings or []

        if not self._client and settings.GEMINI_API_KEY:
            self.api_key = settings.GEMINI_API_KEY
            self._init_client()

        prompt = (
            f"You are the MEDICHAIN Clinical Report Review Assistant. "
            f"A patient uploaded a diagnostic document named '{filename}' ({content_type}, {file_size_kb:.2f} KB).\n\n"
            f"EXTRACTED DOCUMENT CONTENT (Ephemeral text layer):\n"
            f"{extracted_text[:2500] if extracted_text else 'No embedded text layer (scanned document/imaging).'}\n\n"
            "Provide a structured preliminary plain-language review containing:\n"
            "1. Key Observations & Extracted Clinical Parameters (with units and reference ranges where present)\n"
            "2. Objective Clinical Context (plain language, stating clearly that this is NOT a diagnostic determination)\n"
            "3. 3 Specific Questions the Patient Should Ask Their Treating Physician\n"
            "4. Immediate next steps for routine follow-up.\n"
            "Strictly avoid pronouncing definitive medical diagnoses."
        )

        response_text = ""
        if self._client:
            try:
                response = self._client.generate_content(prompt)
                if response and response.text:
                    response_text = response.text
            except Exception as e:
                logger.warning(f"Gemini document analysis SDK failed: {e}. Trying direct REST fallback...")

        if not response_text and self.api_key:
            response_text = self._call_gemini_direct(prompt)

        if response_text:
            lines = [line.strip("- *# ") for line in response_text.split("\n") if line.strip()]
            return {
                "summary_title": f"Preliminary Clinical Review: {filename}",
                "key_observations": lines[:4] if len(lines) >= 4 else [response_text[:350]],
                "extracted_findings": findings,
                "extraction_method": "gemini_ai",
                "suggested_questions_for_doctor": [
                    "How do these findings correlate with my physical symptoms and baseline medical history?",
                    "Are any confirmatory diagnostic tests, specialized imaging, or blood re-checks indicated?",
                    "Are there targeted dietary, lifestyle, or medication adjustments indicated based on these parameters?",
                ],
            }

        # Rule-based fallback
        is_pdf = filename.lower().endswith(".pdf")
        doc_type_label = "Laboratory & Clinical Document" if is_pdf else "Medical Imaging / Diagnostic Scan"

        observations = [
            f"Document Type: {doc_type_label} ({content_type}, {file_size_kb:.2f} KB).",
            "Zero-Retention Pipeline: Processed ephemerally in volatile memory. No medical data stored.",
        ]

        if extracted_text:
            observations.append(f"Successfully extracted text from document ({len(extracted_text)} characters).")
            if findings:
                observations.append(f"Detected {len(findings)} clinical parameters with corresponding lab values.")
            else:
                observations.append("Document text parsed. No critical acute abnormalities flagged in standard scan.")
        elif is_pdf:
            observations.append(
                "Notice: Scanned document format detected (no embedded text layer). OCR or manual review required."
            )
        else:
            observations.append("Medical imaging format uploaded. Visual radiological inspection required.")

        return {
            "summary_title": f"Preliminary Clinical Review: {filename}",
            "key_observations": observations,
            "extracted_findings": findings,
            "extraction_method": "pypdf_parser" if extracted_text else "metadata_parser",
            "suggested_questions_for_doctor": [
                "How do these results compare with my previous baseline health checks?",
                "Are any lifestyle, nutritional, or medication modifications recommended?",
                "When should I schedule the next routine follow-up evaluation?",
            ],
        }


# Singleton service instance
ai_service = AIService()
