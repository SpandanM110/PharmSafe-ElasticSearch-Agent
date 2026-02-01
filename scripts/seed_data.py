"""
Seed PharmaSafe indices with synthetic data.
Run: python scripts/seed_data.py
Requires: indices created (run create_indices.py first)
"""
import os
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv

load_dotenv()

from elasticsearch import Elasticsearch

ES_ENDPOINT = os.getenv("ES_ENDPOINT")
ES_API_KEY = os.getenv("ES_API_KEY")

if not ES_ENDPOINT or not ES_API_KEY:
    print("Missing ES_ENDPOINT or ES_API_KEY.")
    sys.exit(1)

client = Elasticsearch(ES_ENDPOINT, api_key=ES_API_KEY)

# Synthetic patients (including Sarah Mitchell from the plan)
PATIENTS = [
    {"patient_id": "PT-4821", "full_name": "Sarah Mitchell", "date_of_birth": "1957-03-15", "age": 67,
     "allergies": ["penicillin"], "chronic_conditions": ["heart_disease", "hypertension"],
     "primary_care_doctor": "Dr. James Chen", "last_visit_date": "2025-01-20"},
    {"patient_id": "PT-4822", "full_name": "Robert Williams", "date_of_birth": "1962-08-22", "age": 62,
     "allergies": [], "chronic_conditions": ["diabetes", "hyperlipidemia"],
     "primary_care_doctor": "Dr. Maria Santos", "last_visit_date": "2025-01-18"},
    {"patient_id": "PT-4823", "full_name": "Emily Davis", "date_of_birth": "1985-11-03", "age": 39,
     "allergies": ["sulfa"], "chronic_conditions": ["anxiety"],
     "primary_care_doctor": "Dr. James Chen", "last_visit_date": "2025-01-15"},
]

# Medications per patient (Sarah matches the plan example)
# source: "prescription" | "otc" | "supplement"
# interaction_checked: true = historical (batch processor skips); false = new prescription to check
MEDICATIONS = [
    # Sarah Mitchell - Warfarin + Aspirin interaction
    {"medication_id": "MED-001", "patient_id": "PT-4821", "drug_name": "Aspirin", "drug_class": "antiplatelet",
     "dosage_mg": 81.0, "frequency": "once_daily", "prescribing_doctor": "Dr. James Chen",
     "prescribed_date": "2024-06-01", "status": "active", "indication": "cardiovascular prevention", "source": "prescription", "interaction_checked": True},
    {"medication_id": "MED-002", "patient_id": "PT-4821", "drug_name": "Lisinopril", "drug_class": "ACE_inhibitor",
     "dosage_mg": 10.0, "frequency": "once_daily", "prescribing_doctor": "Dr. James Chen",
     "prescribed_date": "2024-05-15", "status": "active", "indication": "blood pressure management", "source": "prescription", "interaction_checked": True},
    {"medication_id": "MED-003", "patient_id": "PT-4821", "drug_name": "Metoprolol", "drug_class": "beta_blocker",
     "dosage_mg": 25.0, "frequency": "twice_daily", "prescribing_doctor": "Dr. James Chen",
     "prescribed_date": "2024-07-10", "status": "active", "indication": "heart rate control", "source": "prescription", "interaction_checked": True},
    {"medication_id": "MED-004", "patient_id": "PT-4821", "drug_name": "Atorvastatin", "drug_class": "statin",
     "dosage_mg": 20.0, "frequency": "once_daily", "prescribing_doctor": "Dr. James Chen",
     "prescribed_date": "2024-04-20", "status": "active", "indication": "cholesterol management", "source": "prescription", "interaction_checked": True},
    # Sarah - OTC (self-reported for joint pain)
    {"medication_id": "MED-008", "patient_id": "PT-4821", "drug_name": "Ibuprofen", "drug_class": "NSAID",
     "dosage_mg": 200.0, "frequency": "as_needed", "prescribing_doctor": "Self", "prescribed_date": "2024-01-01",
     "status": "active", "indication": "joint pain", "source": "otc", "interaction_checked": True},
    # Robert Williams
    {"medication_id": "MED-005", "patient_id": "PT-4822", "drug_name": "Metformin", "drug_class": "biguanide",
     "dosage_mg": 500.0, "frequency": "twice_daily", "prescribing_doctor": "Dr. Maria Santos",
     "prescribed_date": "2024-08-01", "status": "active", "indication": "diabetes management", "source": "prescription", "interaction_checked": True},
    {"medication_id": "MED-006", "patient_id": "PT-4822", "drug_name": "Sertraline", "drug_class": "SSRI",
     "dosage_mg": 50.0, "frequency": "once_daily", "prescribing_doctor": "Dr. Maria Santos",
     "prescribed_date": "2024-09-15", "status": "active", "indication": "depression", "source": "prescription", "interaction_checked": True},
    # Robert - supplement
    {"medication_id": "MED-009", "patient_id": "PT-4822", "drug_name": "St. John's Wort", "drug_class": "herbal",
     "dosage_mg": 300.0, "frequency": "once_daily", "prescribing_doctor": "Self", "prescribed_date": "2024-11-01",
     "status": "active", "indication": "mood support", "source": "supplement", "interaction_checked": True},
    # Emily Davis
    {"medication_id": "MED-007", "patient_id": "PT-4823", "drug_name": "Escitalopram", "drug_class": "SSRI",
     "dosage_mg": 10.0, "frequency": "once_daily", "prescribing_doctor": "Dr. James Chen",
     "prescribed_date": "2024-10-01", "status": "active", "indication": "anxiety", "source": "prescription", "interaction_checked": True},
]

def _pair_key(a: str, b: str) -> str:
    return f"{min(a, b)}|{max(a, b)}"


# Drug interactions (from plan + common pairs). pair_key = alphabetical "DrugA|DrugB" for LOOKUP JOIN
DRUG_INTERACTIONS = [
    {"interaction_id": "INT-001", "drug_a": "Warfarin", "drug_b": "Aspirin", "pair_key": _pair_key("Warfarin", "Aspirin"),
     "class_a": "anticoagulant", "class_b": "antiplatelet",
     "severity": "critical",
     "mechanism": "Both inhibit platelet function via different pathways, dramatically increasing bleeding risk",
     "clinical_effect": "Risk of serious gastrointestinal or intracranial bleeding",
     "recommendation": "Do not dispense. Contact prescribing physician immediately.",
     "evidence_level": "high"},
    {"interaction_id": "INT-002", "drug_a": "Warfarin", "drug_b": "Atorvastatin", "pair_key": _pair_key("Warfarin", "Atorvastatin"),
     "class_a": "anticoagulant", "class_b": "statin",
     "severity": "moderate",
     "mechanism": "Statins can increase Warfarin metabolism variability",
     "clinical_effect": "Unpredictable INR levels — risk of over or under-anticoagulation",
     "recommendation": "Dispense with caution. Require INR monitoring within 3 days.",
     "evidence_level": "high"},
    {"interaction_id": "INT-003", "drug_a": "Sertraline", "drug_b": "Warfarin", "pair_key": _pair_key("Sertraline", "Warfarin"),
     "class_a": "SSRI", "class_b": "anticoagulant",
     "severity": "moderate",
     "mechanism": "SSRIs inhibit platelet serotonin uptake and can potentiate anticoagulation",
     "clinical_effect": "Increased bleeding risk",
     "recommendation": "Monitor INR closely. Consider alternative antidepressant.",
     "evidence_level": "moderate"},
    {"interaction_id": "INT-004", "drug_a": "Aspirin", "drug_b": "Ibuprofen", "pair_key": _pair_key("Aspirin", "Ibuprofen"),
     "class_a": "antiplatelet", "class_b": "NSAID",
     "severity": "moderate",
     "mechanism": "Ibuprofen can reduce aspirin's cardioprotective effect when taken together",
     "clinical_effect": "Reduced antiplatelet efficacy",
     "recommendation": "Take ibuprofen at least 2 hours after aspirin, or use alternative pain reliever.",
     "evidence_level": "high"},
    {"interaction_id": "INT-005", "drug_a": "Escitalopram", "drug_b": "Tramadol", "pair_key": _pair_key("Escitalopram", "Tramadol"),
     "class_a": "SSRI", "class_b": "opioid",
     "severity": "critical",
     "mechanism": "Both increase serotonin; risk of serotonin syndrome",
     "clinical_effect": "Serotonin syndrome — agitation, hyperthermia, autonomic instability",
     "recommendation": "Do not dispense together. Use alternative pain management.",
     "evidence_level": "high"},
    # OTC / Supplement interactions (Phase 1.3)
    {"interaction_id": "INT-006", "drug_a": "St. John's Wort", "drug_b": "Warfarin", "pair_key": _pair_key("St. John's Wort", "Warfarin"),
     "class_a": "herbal", "class_b": "anticoagulant",
     "severity": "moderate",
     "mechanism": "St. John's Wort induces CYP enzymes, accelerating Warfarin metabolism",
     "clinical_effect": "Reduced anticoagulant effect — risk of thrombosis",
     "recommendation": "Avoid combination. If Warfarin needed, discontinue St. John's Wort 2 weeks prior. Monitor INR closely.",
     "evidence_level": "high"},
    {"interaction_id": "INT-007", "drug_a": "Ibuprofen", "drug_b": "Warfarin", "pair_key": _pair_key("Ibuprofen", "Warfarin"),
     "class_a": "NSAID", "class_b": "anticoagulant",
     "severity": "moderate",
     "mechanism": "NSAIDs inhibit platelet function and can cause GI bleeding; additive with anticoagulants",
     "clinical_effect": "Increased bleeding risk, especially gastrointestinal",
     "recommendation": "Avoid if possible. If needed, use lowest dose, shortest duration. Consider acetaminophen instead.",
     "evidence_level": "high"},
    {"interaction_id": "INT-008", "drug_a": "St. John's Wort", "drug_b": "Sertraline", "pair_key": _pair_key("St. John's Wort", "Sertraline"),
     "class_a": "herbal", "class_b": "SSRI",
     "severity": "moderate",
     "mechanism": "Both increase serotonin; additive effect",
     "clinical_effect": "Risk of serotonin syndrome",
     "recommendation": "Avoid combination. Discontinue St. John's Wort before starting SSRI.",
     "evidence_level": "moderate"},
]

# Phase 2.1: Drug–food interactions
DRUG_FOOD_INTERACTIONS = [
    {"food_id": "DF-001", "drug_name": "Warfarin", "food": "vitamin_K",
     "severity": "moderate",
     "mechanism": "Vitamin K antagonizes Warfarin's anticoagulant effect",
     "clinical_effect": "Reduced anticoagulant effect — risk of thrombosis",
     "recommendation": "Maintain consistent vitamin K intake. Avoid large amounts of leafy greens (kale, spinach)."},
    {"food_id": "DF-002", "drug_name": "Atorvastatin", "food": "grapefruit",
     "severity": "moderate",
     "mechanism": "Grapefruit inhibits CYP3A4, increasing statin levels",
     "clinical_effect": "Increased statin exposure — risk of myopathy, rhabdomyolysis",
     "recommendation": "Avoid grapefruit and grapefruit juice. Use alternative statin if needed."},
    {"food_id": "DF-003", "drug_name": "Simvastatin", "food": "grapefruit",
     "severity": "moderate",
     "mechanism": "Grapefruit inhibits CYP3A4, increasing statin levels",
     "clinical_effect": "Increased statin exposure — risk of myopathy",
     "recommendation": "Avoid grapefruit. Consider atorvastatin or pravastatin."},
    {"food_id": "DF-004", "drug_name": "Metformin", "food": "alcohol",
     "severity": "moderate",
     "mechanism": "Alcohol increases risk of lactic acidosis with metformin",
     "clinical_effect": "Lactic acidosis — rare but serious",
     "recommendation": "Limit alcohol. Avoid binge drinking."},
    {"food_id": "DF-005", "drug_name": "MAOI", "food": "tyramine",
     "severity": "critical",
     "mechanism": "Tyramine in aged foods can cause hypertensive crisis with MAOIs",
     "clinical_effect": "Hypertensive crisis — headache, stroke risk",
     "recommendation": "Avoid aged cheese, cured meats, fermented foods. Strict tyramine-free diet."},
]

# Phase 2.2: Drug contraindications (drug vs chronic_condition)
DRUG_CONTRAINDICATIONS = [
    {"contra_id": "DC-001", "drug_name": "Ibuprofen", "drug_class": "NSAID", "condition": "kidney_disease",
     "severity": "moderate",
     "recommendation": "Avoid or use with caution. NSAIDs can worsen kidney function. Consider acetaminophen."},
    {"contra_id": "DC-002", "drug_name": "Naproxen", "drug_class": "NSAID", "condition": "kidney_disease",
     "severity": "moderate",
     "recommendation": "Avoid in CKD. Use acetaminophen for pain."},
    {"contra_id": "DC-003", "drug_name": "Ibuprofen", "drug_class": "NSAID", "condition": "peptic_ulcer",
     "severity": "moderate",
     "recommendation": "Avoid. NSAIDs increase ulcer risk. Use acetaminophen or COX-2 selective agent with PPI."},
    {"contra_id": "DC-004", "drug_class": "NSAID", "condition": "heart_disease",
     "severity": "moderate",
     "recommendation": "Use with caution. NSAIDs may increase cardiovascular risk. Prefer naproxen if NSAID needed."},
    {"contra_id": "DC-005", "drug_name": "Metformin", "drug_class": "biguanide", "condition": "kidney_disease",
     "severity": "moderate",
     "recommendation": "Contraindicated if eGFR < 30. Dose adjustment if eGFR 30–45. Monitor kidney function."},
]

# Phase 2.3: Drug dose ranges (drug, indication, min_mg, max_mg)
DRUG_DOSE_RANGES = [
    {"dose_id": "DD-001", "drug_name": "Warfarin", "indication": "atrial_fibrillation", "min_mg": 1.0, "max_mg": 10.0, "frequency": "once_daily", "unit": "mg"},
    {"dose_id": "DD-002", "drug_name": "Warfarin", "indication": "DVT", "min_mg": 2.0, "max_mg": 10.0, "frequency": "once_daily", "unit": "mg"},
    {"dose_id": "DD-003", "drug_name": "Metformin", "indication": "diabetes", "min_mg": 500.0, "max_mg": 2550.0, "frequency": "twice_daily", "unit": "mg"},
    {"dose_id": "DD-004", "drug_name": "Lisinopril", "indication": "hypertension", "min_mg": 2.5, "max_mg": 40.0, "frequency": "once_daily", "unit": "mg"},
    {"dose_id": "DD-005", "drug_name": "Atorvastatin", "indication": "cholesterol", "min_mg": 10.0, "max_mg": 80.0, "frequency": "once_daily", "unit": "mg"},
    {"dose_id": "DD-006", "drug_name": "Sertraline", "indication": "depression", "min_mg": 25.0, "max_mg": 200.0, "frequency": "once_daily", "unit": "mg"},
]

# Phase 3.1: Beers criteria (elderly age 65+)
BEERS_CRITERIA = [
    {"beers_id": "BC-001", "drug_name": "Ibuprofen", "drug_class": "NSAID",
     "concern": "Increased risk of GI bleeding, peptic ulcer, AKI in elderly",
     "recommendation": "Avoid chronic use. Use lowest effective dose, shortest duration. Consider acetaminophen.",
     "severity": "moderate"},
    {"beers_id": "BC-002", "drug_name": "Naproxen", "drug_class": "NSAID",
     "concern": "Same as NSAIDs — GI bleeding, kidney risk in elderly",
     "recommendation": "Avoid chronic use. Prefer acetaminophen.",
     "severity": "moderate"},
    {"beers_id": "BC-003", "drug_name": "Diazepam", "drug_class": "benzodiazepine",
     "concern": "Increased fall risk, cognitive impairment in elderly",
     "recommendation": "Avoid. Use shorter-acting alternatives (lorazepam) if needed.",
     "severity": "moderate"},
    {"beers_id": "BC-004", "drug_name": "Amitriptyline", "drug_class": "tricyclic",
     "concern": "Anticholinergic effects, fall risk, confusion in elderly",
     "recommendation": "Avoid. Prefer SSRIs or other antidepressants.",
     "severity": "moderate"},
    {"beers_id": "BC-005", "drug_name": "Metoclopramide", "drug_class": "prokinetic",
     "concern": "Extrapyramidal effects, tardive dyskinesia risk in elderly",
     "recommendation": "Avoid. Limit to 12 weeks if used.",
     "severity": "moderate"},
]


def index_bulk(index: str, docs: list, id_field: str = None):
    from elasticsearch import helpers
    actions = []
    for d in docs:
        doc = dict(d)
        _id = doc.get(id_field, str(uuid.uuid4())) if id_field else str(uuid.uuid4())
        # Keep id_field in _source so ES|QL can query it (don't pop)
        actions.append({"_index": index, "_id": _id, "_source": doc})
    helpers.bulk(client, actions, raise_on_error=True)
    print(f"Indexed {len(actions)} docs to {index}")


def main():
    index_bulk("patients", PATIENTS, "patient_id")
    index_bulk("medications", MEDICATIONS, "medication_id")
    index_bulk("drug_interactions", DRUG_INTERACTIONS, "interaction_id")
    index_bulk("drug_food_interactions", DRUG_FOOD_INTERACTIONS, "food_id")
    index_bulk("drug_contraindications", DRUG_CONTRAINDICATIONS, "contra_id")
    index_bulk("drug_dose_ranges", DRUG_DOSE_RANGES, "dose_id")
    index_bulk("beers_criteria", BEERS_CRITERIA, "beers_id")
    print("Seeding complete.")
    print("Phase 2 tests: Check Warfarin for Sarah Mitchell (drug-food: vitamin K)")
    print("  Check Ibuprofen for Sarah Mitchell (contraindication: heart_disease)")
    print("  Check Warfarin 5mg for Sarah Mitchell for atrial fibrillation (dose validation)")
    print("Phase 3 tests: Check Ibuprofen for Sarah Mitchell (Beers: age 67)")
    print("  Show alert history for Sarah Mitchell")


if __name__ == "__main__":
    main()
