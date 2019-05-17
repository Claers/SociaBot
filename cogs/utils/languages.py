import json
import os

FR = {}  # type: dict
EN = {}  # type: dict

path = os.path.dirname(os.path.abspath(__file__))

with open(path + '/langs/fr.json') as f:
    FR = json.load(f)

with open(path + '/langs/en.json') as f:
    EN = json.load(f)

ACTUAL = FR
