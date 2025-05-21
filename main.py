from dotenv import load_dotenv
import os
from clients.splitwise import SplitwiseClient
from clients.monarch import MonarchClient
import asyncio
from datetime import date, timedelta

env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)


SPLITWISE_KEY = os.environ['SPLITWISE_KEY']
SPLITWISE_SECRET = os.environ['SPLITWISE_SECRET']
SPLITWISE_API_KEY = os.environ['SPLITWISE_API_KEY']
SPLITWISE_UPDATED_AFTER = os.environ['SPLITWISE_UPDATED_AFTER']

MONARCH_EMAIL = os.environ['MONARCH_EMAIL']
MONARCH_PASSWORD = os.environ['MONARCH_PASSWORD']
MONARCH_UUID = os.environ['MONARCH_UUID']
try:
    MONARCH_ACCOUNT_ID = os.environ['MONARCH_ACCOUNT_ID']
except:
    MONARCH_ACCOUNT_ID = None


def update_env_variable(key, value):
    lines = []
    with open(env_path, "r") as file:
        lines = file.readlines()

    with open(env_path, "w") as file:
        found = False
        for line in lines:
            if key in line:
                file.write(f"{key}={value}\n")
                found = True
            else:
                file.write(line)
        if not found:
            file.write(f"\n{key}={value}\n")

async def main():
    s = SplitwiseClient(SPLITWISE_KEY, SPLITWISE_SECRET, SPLITWISE_API_KEY)
    splitwise_expenses = s.get_expenses(SPLITWISE_UPDATED_AFTER)
    # updates the dated_after variable in the .env file as an time enhancement for multiple runs
    update_env_variable('SPLITWISE_UPDATED_AFTER', '"' + (date.today() - timedelta(days=5)).isoformat() + '"')
    
    m = await MonarchClient.create(MONARCH_EMAIL, MONARCH_PASSWORD, MONARCH_UUID)
    expense_details = await m.new_find_matches(splitwise_expenses, MONARCH_ACCOUNT_ID)


asyncio.run(main())
