from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

MIN_SYMPTOMS_FOR_DIAGNOSIS = 2

DISEASE_SYMPTOMS = {
    "Eye Allergy": [
        "red", "watery eyes", "burning sensation", "swollen", "swelling", "discomfort",
        "eye irritation", "swelling around eyes"
    ],
    "Food Allergy": [
        "itching", "lips swelling", "tight", "nausea", "vomiting",
        "stomach pain", "tongue swelling"
    ],
    "Dust Allergy": [
        "sneezing", "blocked", "runny nose", "coughing", "throat irritation",
        "red", "itchy"
    ],
    "Drug Allergy": [
        "rashes", "lips swell", "itching", "breathing problem", "red",
        "vomited", "dizziness"
    ],
    "Seasonal Allergy": [
        "sneezing", "blocked nose", "watery eyes", "itchy", "runny nose",
        "allergy", "breathing problems"
    ],
    "Dengue Fever": [
        "high fever", "headache", "joint pain", "muscle pain", "rash", "pain behind eyes"
    ],
    "Typhoid Fever": [
        "high fever", "weakness", "stomach pain", "headache", "loss of appetite"
    ],
    "Influenza (Flu)": [
        "fever", "cough", "sore throat", "body aches", "fatigue", "runny nose", "headache"
    ],
    "Malaria": [
        "fever", "chills", "sweating", "headache", "nausea", "vomiting"
    ],
    "Pneumonia": [
        "fever", "cough with phlegm", "shortness of breath", "chest pain", "fatigue"
    ],
    "Common Cold": [
        "runny nose", "sneezing", "sore throat", "mild fever", "cough"
    ]
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
            match_count = len(set(current_symptoms) & set(known_symptoms))
            disease_scores[disease] = match_count

        max_symptom_score = max(disease_scores.values()) if disease_scores else 0

        if max_symptom_score < MIN_SYMPTOMS_FOR_DIAGNOSIS:
            dispatcher.utter_message(template="utter_cannot_diagnose")
            events.extend([SlotSet("diagnosed", True), SlotSet("symptom", [])])
            return events

        top_diseases = [disease for disease, score in disease_scores.items() if score == max_symptom_score]

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