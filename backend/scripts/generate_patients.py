"""
Generate 200 synthetic patients and load into PostgreSQL + ChromaDB.
Run with: python -m scripts.generate_patients
Run with: python -m scripts.generate_patients --chromadb-only  (to re-index existing patients)
"""

import argparse
import asyncio
import random
from datetime import date, timedelta
from app.database import engine, async_session, Base
from app.models.patient import Patient
from app.services.chromadb_service import chromadb_service
from app.services.ollama_service import ollama_service
from sqlalchemy import select, func

FIRST_NAMES_F = [
    "Emily", "Sarah", "Maria", "Jessica", "Jennifer", "Amanda", "Linda", "Patricia",
    "Elizabeth", "Susan", "Margaret", "Dorothy", "Lisa", "Nancy", "Karen", "Betty",
    "Helen", "Sandra", "Donna", "Carol", "Ruth", "Sharon", "Michelle", "Laura",
    "Mei", "Aisha", "Priya", "Fatima", "Yuki", "Rosa", "Olga", "Ingrid",
    "Amara", "Keiko", "Sonia", "Anita", "Lucia", "Nadia", "Elena", "Zara",
]

FIRST_NAMES_M = [
    "James", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas",
    "Charles", "Daniel", "Matthew", "Anthony", "Mark", "Donald", "Steven", "Paul",
    "Andrew", "Joshua", "Kenneth", "Kevin", "Brian", "George", "Timothy", "Ronald",
    "Wei", "Mohammed", "Raj", "Carlos", "Hiroshi", "Ivan", "Ahmed", "Lars",
    "Kwame", "Takeshi", "Diego", "Omar", "Andrei", "Hassan", "Jin", "Mateo",
]

LAST_NAMES = [
    "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez",
    "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor",
    "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White", "Harris",
    "Chen", "Kim", "Patel", "Nguyen", "Yamamoto", "Singh", "Ali", "Johansson",
    "Okonkwo", "Tanaka", "Schmidt", "Ivanov", "Santos", "Kowalski", "Muller", "Park",
]

STREETS = [
    "Main St", "Oak Ave", "Elm Dr", "Maple Ln", "Cedar Rd", "Pine St", "Birch Ave",
    "Walnut Dr", "Cherry Ln", "Spruce Rd", "Washington Blvd", "Lincoln Ave",
    "Park Dr", "Lake St", "River Rd", "Hill Ave", "Valley Dr", "Forest Ln",
]

CITIES = [
    "Springfield", "Riverside", "Georgetown", "Fairview", "Madison",
    "Clinton", "Franklin", "Arlington", "Salem", "Burlington",
]

STATES = ["CA", "TX", "FL", "NY", "IL", "PA", "OH", "GA", "NC", "MI"]

ARCHETYPES = [
    {
        "conditions": ["Type 2 Diabetes"],
        "medications": ["Metformin 500mg BID", "Lisinopril 10mg QD"],
        "risk_factors": ["Age >50", "Obesity", "Family history"],
        "risk_range": (55, 85),
        "notes_template": "Patient managing Type 2 Diabetes. {compliance} Blood glucose levels {glucose}. Last A1C: {a1c}%.",
    },
    {
        "conditions": ["Type 2 Diabetes", "Hypertension"],
        "medications": ["Metformin 1000mg BID", "Lisinopril 20mg QD", "Atorvastatin 40mg QHS"],
        "risk_factors": ["Age >50", "Obesity", "Hypertension", "Hyperlipidemia"],
        "risk_range": (65, 90),
        "notes_template": "Complex patient with diabetes and hypertension. {compliance} BP: {bp}. A1C: {a1c}%.",
    },
    {
        "conditions": ["Hypertension"],
        "medications": ["Amlodipine 5mg QD", "Hydrochlorothiazide 25mg QD"],
        "risk_factors": ["High sodium diet", "Sedentary lifestyle"],
        "risk_range": (40, 70),
        "notes_template": "Hypertension management. {compliance} Current BP: {bp}. {lifestyle}",
    },
    {
        "conditions": ["COPD"],
        "medications": ["Albuterol inhaler PRN", "Tiotropium 18mcg QD"],
        "risk_factors": ["Smoking history", "Environmental exposure"],
        "risk_range": (55, 85),
        "notes_template": "COPD patient. {smoking} FEV1: {fev1}% predicted. {exacerbations}",
    },
    {
        "conditions": ["COPD", "Coronary Artery Disease"],
        "medications": ["Albuterol inhaler PRN", "Atorvastatin 40mg QHS", "Aspirin 81mg QD"],
        "risk_factors": ["Smoking history", "CAD", "Age >60"],
        "risk_range": (70, 95),
        "notes_template": "High-risk patient with COPD and CAD. {smoking} Cardiac status: {cardiac}. FEV1: {fev1}%.",
    },
    {
        "conditions": ["Asthma"],
        "medications": ["Fluticasone inhaler BID", "Albuterol PRN"],
        "risk_factors": ["Allergies", "Environmental triggers"],
        "risk_range": (20, 45),
        "notes_template": "Asthma well-controlled. {compliance} Peak flow: {peak_flow}% of personal best.",
    },
    {
        "conditions": ["Chronic Kidney Disease"],
        "medications": ["Losartan 50mg QD", "Sodium bicarbonate 650mg TID"],
        "risk_factors": ["Diabetes history", "Hypertension", "Age >60"],
        "risk_range": (60, 90),
        "notes_template": "CKD stage {ckd_stage}. eGFR: {egfr} mL/min. {compliance} Monitoring renal function.",
    },
    {
        "conditions": ["Heart Failure"],
        "medications": ["Carvedilol 25mg BID", "Furosemide 40mg QD", "Lisinopril 10mg QD"],
        "risk_factors": ["CAD history", "Age >65", "Reduced EF"],
        "risk_range": (70, 95),
        "notes_template": "Heart failure with {ef_type}. EF: {ef}%. NYHA Class {nyha}. {compliance}",
    },
    {
        "conditions": ["Depression", "Anxiety"],
        "medications": ["Sertraline 100mg QD"],
        "risk_factors": ["Social isolation", "Chronic pain"],
        "risk_range": (30, 55),
        "notes_template": "Managing depression and anxiety. PHQ-9: {phq9}. GAD-7: {gad7}. {therapy}",
    },
    {
        "conditions": ["Osteoarthritis"],
        "medications": ["Acetaminophen 500mg PRN", "Meloxicam 15mg QD"],
        "risk_factors": ["Age >60", "Obesity", "Joint overuse"],
        "risk_range": (25, 50),
        "notes_template": "Osteoarthritis affecting {joints}. Pain level: {pain}/10. {mobility}",
    },
    {
        "conditions": ["Type 1 Diabetes"],
        "medications": ["Insulin glargine 20 units QHS", "Insulin lispro sliding scale"],
        "risk_factors": ["Autoimmune condition", "Hypoglycemia risk"],
        "risk_range": (50, 80),
        "notes_template": "Type 1 Diabetes. Insulin pump: {pump}. Last A1C: {a1c}%. {compliance}",
    },
    {
        "conditions": ["Atrial Fibrillation"],
        "medications": ["Apixaban 5mg BID", "Metoprolol 50mg BID"],
        "risk_factors": ["Age >65", "Stroke risk"],
        "risk_range": (55, 80),
        "notes_template": "AFib management. CHA2DS2-VASc: {chads}. Rate controlled. {compliance}",
    },
]


def generate_name(gender: str) -> str:
    if gender == "Female":
        return f"{random.choice(FIRST_NAMES_F)} {random.choice(LAST_NAMES)}"
    return f"{random.choice(FIRST_NAMES_M)} {random.choice(LAST_NAMES)}"


def generate_dob(min_age: int = 18, max_age: int = 85) -> date:
    age = random.randint(min_age, max_age)
    return date.today() - timedelta(days=age * 365 + random.randint(0, 364))


def generate_ssn() -> str:
    return f"{random.randint(100,999)}-{random.randint(10,99)}-{random.randint(1000,9999)}"


def generate_address() -> str:
    num = random.randint(100, 9999)
    street = random.choice(STREETS)
    city = random.choice(CITIES)
    state = random.choice(STATES)
    zip_code = random.randint(10000, 99999)
    return f"{num} {street}, {city}, {state} {zip_code}"


def generate_notes(archetype: dict) -> str:
    template = archetype["notes_template"]
    replacements = {
        "compliance": random.choice(["Good medication compliance.", "Occasionally misses doses.", "Excellent adherence to treatment plan."]),
        "glucose": random.choice(["within target range", "trending upward", "well-controlled", "variable"]),
        "a1c": str(round(random.uniform(5.5, 10.5), 1)),
        "bp": f"{random.randint(110, 165)}/{random.randint(65, 100)}",
        "lifestyle": random.choice(["Encouraged to increase physical activity.", "Started walking program.", "Dietary counseling provided."]),
        "smoking": random.choice(["Former smoker, quit 5 years ago.", "Current smoker, counseled on cessation.", "Never smoker."]),
        "fev1": str(random.randint(35, 85)),
        "exacerbations": random.choice(["No recent exacerbations.", "1 exacerbation in past 6 months.", "2 exacerbations this year."]),
        "cardiac": random.choice(["Stable", "Improving", "Requires monitoring"]),
        "peak_flow": str(random.randint(70, 100)),
        "ckd_stage": str(random.randint(2, 4)),
        "egfr": str(random.randint(15, 75)),
        "ef_type": random.choice(["reduced ejection fraction (HFrEF)", "preserved ejection fraction (HFpEF)"]),
        "ef": str(random.randint(20, 60)),
        "nyha": random.choice(["II", "III", "IV"]),
        "phq9": str(random.randint(5, 20)),
        "gad7": str(random.randint(5, 18)),
        "therapy": random.choice(["Attending weekly therapy.", "Referred to CBT program.", "Considering therapy options."]),
        "joints": random.choice(["bilateral knees", "right hip", "hands and knees", "lumbar spine"]),
        "pain": str(random.randint(3, 8)),
        "mobility": random.choice(["Ambulatory with cane.", "Full mobility.", "Limited range of motion."]),
        "pump": random.choice(["Yes", "No, uses pens"]),
        "chads": str(random.randint(1, 6)),
    }
    result = template
    for key, val in replacements.items():
        result = result.replace(f"{{{key}}}", val)
    return result


async def generate(chromadb_only: bool = False):
    async with async_session() as db:
        # Check if patients already exist
        count = await db.scalar(select(func.count(Patient.id)))

        if chromadb_only:
            # ChromaDB-only mode: fetch existing patients and re-embed them
            if not count or count == 0:
                print("Error: No patients found in PostgreSQL. Cannot re-index ChromaDB.")
                print("Run without --chromadb-only to generate patients first.")
                return

            print(f"ChromaDB re-indexing mode: Fetching {count} existing patients from PostgreSQL...")
            result = await db.execute(select(Patient))
            patients_data = result.scalars().all()
            print(f"Fetched {len(patients_data)} patients. Skipping patient generation.")
        else:
            # Normal mode: generate new patients
            if count and count >= 200:
                print(f"Database already has {count} patients. Skipping generation.")
                return

            print("Generating 200 synthetic patients...")
            patients_data = []

            for i in range(200):
                gender = random.choice(["Male", "Female"])
                archetype = random.choice(ARCHETYPES)
                risk_low, risk_high = archetype["risk_range"]

                # Add some randomized extra conditions occasionally
                conditions = list(archetype["conditions"])
                if random.random() < 0.2:
                    extra = random.choice(["Obesity", "Sleep Apnea", "Hypothyroidism", "GERD", "Migraine"])
                    if extra not in conditions:
                        conditions.append(extra)

                allergies_options = [[], ["Penicillin"], ["Sulfa drugs"], ["NSAIDs"], ["Latex"],
                                    ["Penicillin", "Sulfa drugs"], ["Codeine"]]

                patient = Patient(
                    patient_id=f"PT-{str(i + 1).zfill(3)}",
                    name=generate_name(gender),
                    date_of_birth=generate_dob(),
                    gender=gender,
                    ssn=generate_ssn(),
                    address=generate_address(),
                    conditions=conditions,
                    medications=list(archetype["medications"]),
                    allergies=random.choice(allergies_options),
                    risk_score=random.randint(risk_low, risk_high),
                    risk_factors=list(archetype["risk_factors"]),
                    last_visit=date.today() - timedelta(days=random.randint(1, 90)),
                    next_appointment=date.today() + timedelta(days=random.randint(7, 60)),
                    notes=generate_notes(archetype),
                )
                db.add(patient)
                patients_data.append(patient)

            await db.commit()
            print(f"Created 200 patients in PostgreSQL.")

        # Embed into ChromaDB
        print("Embedding patients into ChromaDB for RAG...")
        embedded = 0
        for p in patients_data:
            doc_text = (
                f"Patient {p.name} (ID: {p.patient_id}). "
                f"DOB: {p.date_of_birth}. Gender: {p.gender}. "
                f"Conditions: {', '.join(p.conditions or [])}. "
                f"Medications: {', '.join(p.medications or [])}. "
                f"Allergies: {', '.join(p.allergies or [])}. "
                f"Risk Score: {p.risk_score}. "
                f"Risk Factors: {', '.join(p.risk_factors or [])}. "
                f"Notes: {p.notes}"
            )
            metadata = {
                "patient_id": p.patient_id,
                "name": p.name,
                "gender": p.gender,
                "risk_score": p.risk_score,
            }
            try:
                embedding = await ollama_service.embed(doc_text)
                chromadb_service.add_patient(p.patient_id, doc_text, metadata, embedding)
                embedded += 1
                if embedded % 20 == 0:
                    print(f"  Embedded {embedded}/200 patients...")
            except Exception as e:
                # If Ollama not available, add without embedding
                print(f"  Warning: Could not embed {p.patient_id}: {e}")
                try:
                    chromadb_service.collection.add(
                        ids=[p.patient_id],
                        documents=[doc_text],
                        metadatas=[metadata],
                    )
                    embedded += 1
                except Exception:
                    pass

        print(f"Embedded {embedded} patients into ChromaDB.")
        print("Synthetic patient generation complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate synthetic patients and embed into PostgreSQL + ChromaDB"
    )
    parser.add_argument(
        "--chromadb-only",
        action="store_true",
        help="Only re-index existing patients into ChromaDB (skip patient generation)"
    )
    args = parser.parse_args()

    asyncio.run(generate(chromadb_only=args.chromadb_only))
