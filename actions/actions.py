from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

MIN_SYMPTOMS_FOR_DIAGNOSIS = 2

# DICTIONARY KEYS ARE NOW STANDARDIZED TO MATCH THE CANONICAL VALUES FROM NLU.YML
# ADDED MORE SYMPTOMS AND ADJUSTED SCORES FOR BETTER ACCURACY
DISEASE_SYMPTOMS = {
    # --- Allergies ---
    "Eye Allergy": {
        "swelling": 10,
        "burning sensation": 9,
        "eye irritation": 9,
        "watery eyes": 8,
        "red eyes": 7,
        "discomfort": 4
    },
    "Food Allergy": {
        "swelling": 10,        # Handles tongue, lips, etc. via synonyms
        "rashes": 8,           # Added symptom
        "itching": 8,
        "vomiting": 7,
        "nausea": 6,
        "stomach pain": 6,
        "tight": 5
    },
    "Dust Allergy": {
        "sneezing": 9,
        "runny nose": 8,
        "blocked nose": 7,     # Standardized from "blocked"
        "itching": 7,          # Standardized from "itchy"
        "throat irritation": 5,
        "cough": 4,            # Standardized from "coughing"
        "red eyes": 4          # Standardized from "red"
    },
    "Drug Allergy": {
        "breathing problem": 10,
        "swelling": 10,         # Standardized from "lips swell"
        "rashes": 9,
        "itching": 7,
        "dizziness": 5,
        "red eyes": 4,          # Standardized from "red"
        "vomiting": 4           # Standardized from "vomited"
    },
    "Seasonal Allergy": {
        "sneezing": 9,
        "runny nose": 8,
        "watery eyes": 8,
        "itching": 8,
        "blocked nose": 7,
        "breathing problem": 6
    },
    # --- Fevers & Infections ---
    "Dengue Fever": {
        "high fever": 9,
        "headache": 8,
        "pain behind eyes": 8,
        "joint pain": 7,
        "muscle pain": 7,
        "rashes": 6,
        "nausea": 5            # Added symptom
    },
    "Typhoid Fever": {
        "high fever": 9,
        "stomach pain": 8,
        "headache": 7,
        "weakness": 6,
        "loss of appetite": 5,
        "chills": 5            # Added symptom
    },
    "Influenza (Flu)": {
        "fever": 9,
        "body aches": 9,
        "fatigue": 8,
        "cough": 7,
        "chills": 7,           # Added symptom
        "headache": 6,
        "runny nose": 5,
        "sore throat": 5
    },
    "Malaria": {
        "fever": 9,
        "chills": 9,
        "sweating": 8,
        "headache": 6,
        "nausea": 5,
        "vomiting": 5
    },
    "Pneumonia": {
        "cough with phlegm": 9,
        "fever": 8,
        "shortness of breath": 7,
        "chest pain": 6,
        "chills": 5,           # Added symptom
        "fatigue": 4
    },
    "Common Cold": {
        "runny nose": 8,
        "sneezing": 8,
        "sore throat": 7,
        "cough": 6,
        "fever": 4              # Changed from "mild fever" for consistency
    },
    # --- Other Conditions ---
    "Gastritis": {
        "burning ache in stomach": 9,
        "stomach pain": 8,
        "nausea": 7,
        "vomiting": 6,
        "bloating": 5,
        "feeling full": 5
    },
    "Acid Reflux (GERD)": {
        "heartburn": 10,
        "regurgitation of food": 8,
        "chest pain": 7,
        "sour taste": 6,
        "difficulty swallowing": 5,
        "sour liquid": 5
    },
    "Migraine": {
        "throbbing headache": 10,
        "headache on one side": 9,
        "sensitivity to light": 8,
        "sensitivity to sound": 7,
        "nausea": 6,
        "vomiting": 5
    },
    "Chickenpox": {
        "itching": 10,         # Standardized from "itchy rash"
        "blisters": 10,
        "fever": 6,
        "fatigue": 5,
        "headache": 4,
        "loss of appetite": 4
    },
    "Asthma": {
        "wheezing": 10,
        "shortness of breath": 8,
        "chest tightness": 7,
        "cough": 4,           # Standardized
        "chest pain": 2
    },
    "Anemia": {
        "pale skin": 9,
        "fatigue": 8,
        "weakness": 8,
        "dizziness": 6,
        "shortness of breath": 5, # Added symptom
        "cold hands": 5,
        "cold feet": 5
    }
}

class ActionHandleSymptoms(Action):
    def name(self) -> Text:
        return "action_handle_symptoms"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        if tracker.get_slot("diagnosed"):
            current_symptoms = []
            events = [SlotSet("diagnosed", False)]
        else:
            current_symptoms = tracker.get_slot("symptom") or []
            events = []

        new_symptoms = [e['value'] for e in tracker.latest_message.get('entities', []) if e['entity'] == 'symptom']

        for symptom in new_symptoms:
            if symptom.lower() not in current_symptoms:
                current_symptoms.append(symptom.lower())

        if len(current_symptoms) < MIN_SYMPTOMS_FOR_DIAGNOSIS:
            symptom_list_str = ", ".join(current_symptoms)
            dispatcher.utter_message(template="utter_symptoms_acknowledged", symptoms_list=symptom_list_str)
            events.append(SlotSet("symptom", current_symptoms))
            return events

        disease_scores = {}
        for disease, known_symptoms in DISEASE_SYMPTOMS.items():
            score = 0
            for symptom in current_symptoms:
                if symptom in known_symptoms:
                    score += known_symptoms[symptom]
            disease_scores[disease] = score

        max_score = max(disease_scores.values()) if disease_scores else 0
        
        # This threshold is important to prevent low-confidence guesses.
        MINIMUM_SCORE_THRESHOLD = 9

        if max_score < MINIMUM_SCORE_THRESHOLD:
            dispatcher.utter_message(template="utter_cannot_diagnose")
            events.extend([SlotSet("diagnosed", True), SlotSet("symptom", [])])
            return events

        top_diseases = [disease for disease, score in disease_scores.items() if score == max_score]

        if len(top_diseases) == 1:
            diagnosis = top_diseases[0]
            dispatcher.utter_message(template="utter_diagnosis_result", disease=diagnosis)
            events.extend([SlotSet("diagnosed", True), SlotSet("symptom", [])])
            return events
        else:
            possible_diseases_str = ", ".join(top_diseases)
            dispatcher.utter_message(
                template="utter_ask_clarifying_symptom",
                possible_diseases=possible_diseases_str
            )
            events.append(SlotSet("symptom", current_symptoms))
            return events