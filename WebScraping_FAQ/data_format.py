import json
import random

def convert_to_training_format(input_file, output_file, format_type="classification"):
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    training_data = []
    
    for intent in data['intents']:
        tag = intent['tag']
        patterns = intent['patterns']
        responses = intent['responses']
        
        if format_type == "classification":
            # Pour classification d'intents
            for pattern in patterns:
                training_data.append({
                    "text": pattern,
                    "label": tag
                })
                
        elif format_type == "generation":
            # Pour génération de réponses
            for pattern in patterns:
                response = random.choice(responses)
                training_data.append({
                    "input": pattern,
                    "output": response
                })
                
        elif format_type == "conversation":
            # Format conversationnel
            for pattern in patterns:
                response = random.choice(responses)
                training_data.append({
                    "conversations": [
                        {"role": "user", "content": pattern},
                        {"role": "assistant", "content": response}
                    ]
                })
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(training_data, f, indent=2, ensure_ascii=False)
    
    print(f"Converti {len(training_data)} exemples au format {format_type}")

# Utilisation
convert_to_training_format("intents.json", "training_data.json", "generation")