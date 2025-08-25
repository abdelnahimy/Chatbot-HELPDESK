import json

def extract_tags(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    tags = [intent['tag'] for intent in data.get('intents', [])]

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(tags, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    extract_tags('jira-chatbot\data\intents.json', 'tags.json')
    print("Les tags ont été extraits et enregistrés dans 'tags.json'.")
