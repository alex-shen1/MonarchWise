from monarchmoney import MonarchMoney
import json
import hashlib
import os
from clients import monarch_helper as mhelper
import re

EXCLUDED_TRANSACTIONS_PATH = 'excluded.json'


class MonarchClient(object):
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

    async def new_find_matches(self, splitwise_expenses, mm_account_id):
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
        
        
        mm_transactions = await mhelper.get_transactions(self.client, includeTags=mm_tags['From Splitwise']['id']) # Hardcoded value
        # mm_transactions = await mhelper.get_transactions(self.client, limit=1000, synced_from_institution = False) # Hardcoded value
        mm_sync_history = set()
        for transaction in mm_transactions['allTransactions']['results']:
            if transaction['amount'] < 0:
                splitwise_id = re.search(r'Splitwise=(\d+)', transaction['notes'])
                if splitwise_id:
                    if splitwise_id in mm_sync_history:
                        raise Exception(f"A duplicate SW_ID has been found in Monarch.  Something is wrong: {splitwise_id}")
                    else:
                        mm_sync_history.add(splitwise_id.group(1))
        
        if not mm_account_id:
            message = ("Account ID to bill not specified.\n" +  
                       "It's recommended to select the account you will be paying splitwise from.\n" +
                       "For convienence, this is the account information.  Choose one and add it to .env:\n")
            accounts_info = await self.client.get_accounts()
            for account in accounts_info['accounts']:
                message += f"\t{account['displayName']}: {account['id']}\n"
            raise Exception(message)
            
        created_transactions = []
        for expense in splitwise_expenses:
            if str(expense['id']) in mm_sync_history:
                continue
                # Could add logic here to verify any changes in splitwise is reflected in monarch
            
            
            merchant = f"SW - {expense['group_name']}"
            notes = f"Splitwise {expense['group_name']}: {expense['description']}"
            created_transaction = await self.client.create_transaction(
                expense['date'],
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
            Group: {expense['group_name']}""")
        
        # created_transactions.append({'description': description,
        #                         'cost': expense['amount_owed'],
        #                         'groupId': {'name': expense['group_name']}})
        # return created_transactions
                
            
            
            
                
    
    async def find_matches(self, splitwise_expenses):
        txns = []
        offset = 0
        batch_size = 400
        total_transactions = float('inf')

        with open(EXCLUDED_TRANSACTIONS_PATH, 'r') as f:
            excluded = json.load(f)

        while True:
            if offset > total_transactions:
                break

            response = await self.client.get_transactions(limit=batch_size, offset=offset)
            txns += response['allTransactions']['results']

            offset += batch_size
            total_transactions = response['allTransactions']['totalCount']

        for txn in txns:
            if txn['isSplitTransaction']:
                continue

            amount = -1 * txn['amount']
            if amount in splitwise_expenses.keys():
                splitwise_expense = splitwise_expenses[amount]

                monarch_id = txn['id']
                txn_hash = hashlib.sha256(
                    monarch_id.encode('utf-8')).hexdigest()

                if txn_hash not in excluded:
                    monarch_merchant = txn['merchant']['name']
                    original_category = txn['category']['id']
                    reimbursement = splitwise_expense['amount_reimbursed']

                    split_data = [
                        {
                            'merchantName': monarch_merchant,
                            'amount': -1 * (amount - reimbursement),
                            'categoryId': original_category,
                            'notes': splitwise_expense['description']
                        },
                        {
                            'merchantName': monarch_merchant,
                            'amount': -1 * (reimbursement),
                            'categoryId': self.reimbursements_category_id,
                            'notes': splitwise_expense['description']
                        }
                    ]

                    print(
                        f'Splitting transaction for {monarch_merchant} ({splitwise_expense["description"]}) into ${reimbursement} reimbursed and {amount - reimbursement} for {txn["category"]["name"]}')
                    print('Confirm? Y/N')
                    valid_response = False
                    while not valid_response:
                        response = input()
                        if response.lower() == 'y':
                            valid_response = True
                            print(await self.client.update_transaction_splits(monarch_id, split_data))
                        elif response.lower() == 'n':
                            valid_response = True
                            print('Transaction has been marked as excluded.')
                            excluded.append(txn_hash)

        with open(EXCLUDED_TRANSACTIONS_PATH, 'w') as f:
            json.dump(excluded, f, indent=4)
