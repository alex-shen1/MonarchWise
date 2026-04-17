from monarchmoney import MonarchMoney
import json
import hashlib
import os
from clients import monarch_helper as mhelper
import re
from zoneinfo import ZoneInfo
from datetime import datetime

EXCLUDED_TRANSACTIONS_PATH = 'excluded.json'


class MonarchClient(object):
    def __init__(self):
        self.client = None
        self.email = None
        self.password = None
        self.uuid = None
        self.categories = None
        self.reimbursements_category_id = None

    @classmethod
    async def create(cls, email, password, uuid):
        self = cls()
        self.client = MonarchMoney()
        self.email = email
        self.password = password
        self.uuid = uuid
        self.client = await mhelper.login(self.client, {'username': email, 'password': password}, uuid)
        self.categories = (await self.client.get_transaction_categories())['categories']
        self.reimbursements_category_id = next(
            (c for c in self.categories if c['name'] == 'Splitwise'))['id']
        return self

    async def create_tag_dic(self):
        original_tags = await self.client.get_transaction_tags()
        tags = {}
        for tag in original_tags['householdTransactionTags']:
            tags[tag["name"]] = {"id": tag["id"], "color": tag["color"]}
        return tags
    
    def date_to_iso(self, date, local_timezone="America/Los_Angeles"):
        # If date is naive datetime, assume local timezone
        if date.tzinfo is None or date.tzinfo.utcoffset(date) is None:
            date = date.astimezone()
        # If date is a datetime object with timezone info (not naive), convert to local timezone
        if date.tzinfo is not None and date.tzinfo.utcoffset(date) is not None:
            date = date.astimezone(ZoneInfo(local_timezone))
        
        if isinstance(date, datetime):
            date = date.date().isoformat()
        else:
            raise ValueError("Unsupported date format. Please provide a string or datetime object.")
        return date

    async def new_find_matches(self, splitwise_expenses, mm_account_id, start_date = None):
        '''
        find_matches(self, splitwise_expenses):
            #Remove old sw purchases
            Compare SW expenses with excluded.json
            Keep only new expenses
            
            Get MM tags for SW injested
            
            Get all transactions that have been created and tagged with SW
                get all comments which include sw id
            
            for transaction in SW_expenses:
                #Find out if transaction was already processed
                Compare Price, date, tag, and note as hash?
                if new:
                    Add split transaction
                    Add review
                    Add note
                    add tag
                append to excluded
        '''
        mm_tags = await self.create_tag_dic()
        mm_categories = await self.client.get_transaction_categories()
        splitwise_category_id = next((cat['id'] for cat in mm_categories['categories'] if cat['name'] == 'Splitwise'), None)
        
        mm_transactions = await mhelper.get_transactions(self.client, includeTags=mm_tags['From Splitwise']['id'], start_date=start_date) # Hardcoded value

        # Create a history of all SW transactions already proccessed
        # Processes all transaction notes looking for SW transaction ID's.  Creates a set
        mm_sync_history = set()
        for transaction in mm_transactions['allTransactions']['results']:
            if transaction['amount'] < 0:
                splitwise_id = re.search(r'Splitwise=(\d+)', transaction['notes'])
                if splitwise_id:
                    if splitwise_id in mm_sync_history:
                        raise Exception(f"A duplicate SW_ID has been found in Monarch.  Something is wrong: {splitwise_id}")
                    else:
                        mm_sync_history.add(splitwise_id.group(1))
        
        # Check for account_id.  If none, raise error
        if not mm_account_id:
            message = ("Account ID to bill not specified.\n" +  
                       "It's recommended to select the account you will be paying splitwise from.\n" +
                       "For convienence, this is the account information.  Choose one and add it to .env:\n")
            accounts_info = await self.client.get_accounts()
            for account in accounts_info['accounts']:
                message += f"\t{account['displayName']}: {account['id']}\n"
            raise Exception(message)


        created_transactions = []
        # Go through each SW expense, check to see if it's already been processed and create if it has not been.
        for expense in splitwise_expenses:
            if str(expense['id']) in mm_sync_history:
                continue
                # Could add logic here to verify any changes in splitwise is reflected in monarch
            
            
            merchant = f"SW - {expense['group_name']}"
            notes = f"Splitwise {expense['group_name']}: {expense['description']}"
            date = self.date_to_iso(expense['date'])
            created_transaction = await self.client.create_transaction(
                date,
                mm_account_id,
                expense['amount_owed'],
                merchant,
                splitwise_category_id,
                f"{notes}\nSplitwise={expense['id']}", 
                False
            )
            created_transaction_id = created_transaction['createTransaction']['transaction']['id']
            created_transaction = await self.client.set_transaction_tags(created_transaction_id, mm_tags['From Splitwise']['id'] )
            created_transaction = await self.client.update_transaction(created_transaction_id, needs_review=True)
            

            print(f"""Successfully created an expense with the following details: 
            Expense Description: {notes}
            Expense Cost: {expense['amount_owed']}
            Date: {date}
            Group: {expense['group_name']}""")
        
        # created_transactions.append({'description': description,
        #                         'cost': expense['amount_owed'],
        #                         'groupId': {'name': expense['group_name']}})
        # return created_transactions
                