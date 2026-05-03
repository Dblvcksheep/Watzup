import requests
import os
import json
import random
import re
from dotenv import load_dotenv

load_dotenv()

client_seccret = os.environ["NOMBANK_CLIENT_SECRET"]
client_id = os.environ["NOMBANK_CLIENT_ID"]
account_id = os.environ["NOMBANK_ACCOUNT_ID"]


NOMBANK_ALIASES = {
    "uba": ["united bank for africa"],
    "gtb": ["guaranty trust bank", "gtbank"],
    "fcmb": ["first city monument bank"],
    "fidelity": ["fidelity bank"],
    "firstbank"or 'first bank': ["first bank of nigeria"],
    "stanbic": ["stanbic ibtc bank"],
    "ecobank": ["eco bank", "ecobank nigeria"],
    "opay":["paycom"]
}

reason =['Goods', 'Services', 'Bills', 'Gift', 'Loan']

with open('nombanks.json', 'r') as f:
    nombanks=json.load(f)

def nombank_access_token(clientid, client_secret, acctid):
    url = "https://api.nomba.com/v1/auth/token/issue"

    payload = {
        "grant_type": "client_credentials",
        "client_id": clientid,
        "client_secret": client_secret
    }
    headers = {
        "accountId": acctid,
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers,timeout=10)
    token = response.json()
    return token

def match_nombank(user_input):
    user_input = normalize(user_input)


    for bank in nombanks:
        bank_name = normalize(bank['name'])


        # 1. Alias match (UBA, GTB, etc.)
        if user_input in NOMBANK_ALIASES:
            if bank_name in NOMBANK_ALIASES[user_input]:
                return bank['code']

        # 2. Containment match
        if user_input in bank_name or bank_name in user_input:
            return bank['code']


    return None

def revoke_access(access, clientid):
    url = "https://api.nomba.com/v1/auth/token/revoke"

    payload = {
        "clientId": clientid,
        "access_token": access
    }
    headers = {"Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers,timeout=10)

    return response.json()

def nombank_balance(acctid, access_token):
    url = "https://api.nomba.com/v1/accounts/balance"

    headers = {
        "accountId": acctid,
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(url, headers=headers,timeout=10)

    return response.json()

def create_virtual(access_token,acct_id,account_ref,account_name):
    url = "https://api.nomba.com/v1/accounts/virtual"

    payload = {
        "accountRef": str(account_ref),
        "accountName": f"{account_name}",
        "currency": "NGN"
    }
    headers = {
        "accountId": acct_id,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers,timeout=10)

    return response.json()
def normalize(name):
    import re
    name = name.lower()
    name = re.sub(r'\(.*?\)', '', name)
    name = re.sub(r'[^a-z0-9 ]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name
def name_tokens(name):
    return set(normalize(name).split())

def names_match(input_name, resolved_name, threshold=0.6):
    input_tokens = name_tokens(input_name)
    resolved_tokens = name_tokens(resolved_name)

    if not input_tokens or not resolved_tokens:
        return False

    intersection = input_tokens & resolved_tokens
    score = len(intersection) / max(len(input_tokens), len(resolved_tokens))

    return score >= threshold

def resolve_nombank(acct_num,bank_code, name, access_token,acct_id ):
    name=normalize(name)

    url = "https://api.nomba.com/v1/transfers/bank/lookup"

    payload = {
        "accountNumber": acct_num,
        "bankCode": bank_code
    }
    headers = {
        "accountId": acct_id,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers,timeout=10)

    data= response.json()
    if data['description'] != "SUCCESS":
        return False
    acct_name = data['data']['accountName']
    acct_name = normalize(acct_name)
    return names_match(name, acct_name)

def nombank_transfer(amount, acct_number, acct_name, bankcode, reference, sender, acct_id, access_token):
    url = "https://api.nomba.com/v2/transfers/bank"

    payload = {
        "amount": amount,
        "accountNumber": str(acct_number),
        "accountName": acct_name,
        "bankCode": str(bankcode),
        "merchantTxRef": str(reference),
        "senderName": str(sender),
        "narration": random.choice(reason)
    }
    headers = {
        "accountId": acct_id,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers,timeout=10)

    return response.json()

def nombank_confirm(reference, acct_id, access_token):
    url = "https://api.nomba.com/v1/transactions/accounts/single"

    payload = {
        "merchantTxRef": str(reference),
    }
    headers = {
        "accountId": acct_id,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url,params=payload, headers=headers)

    return response.json()

access = nombank_access_token(client_id,client_seccret,account_id)
if access['description'] == 'Successful':
    access_token = access['data']['access_token']

virtual=create_virtual(access_token,account_id,"watzup-12345-ref","leonard name")

print(virtual)

revoke_access(access_token, client_id)

