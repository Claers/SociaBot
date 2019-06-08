import json
import os

import cogs.utils.models as models

FR = {}  # type: dict
EN = {}  # type: dict

path = os.path.dirname(os.path.abspath(__file__))

with open(path + '/langs/fr.json') as f:
    FR = json.load(f)

with open(path + '/langs/en.json') as f:
    EN = json.load(f)


def return_string(user, string_title, string_number=0):
    language = user.language
    print(user.language)
    if language == "FR":
        return FR[string_title][string_number]
    elif language == "EN":
        return EN[string_title][string_number]


def set_actual_lang_for_user(user, language):
    if language == "FR":
        user.language = "FR"
    elif language == "EN":
        user.language = "EN"
    models.session.flush()
    models.session.commit()


ACTUAL = FR
