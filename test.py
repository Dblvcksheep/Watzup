import json


with open('nigeria.json', 'r') as f:
    states=json.load(f)
for state in states:
    print(state["state"])

for state in states:
    if state["state"] == "LAGOS STATE":
        print(state['lga'])