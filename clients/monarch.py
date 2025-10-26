from monarchmoney import MonarchMoney
import json
import hashlib

EXCLUDED_TRANSACTIONS_PATH = 'excluded.json'


class MonarchClient(object):
    @classmethod
    async def create(cls, email, password, mfa_secret_key):
        self = cls()
        self.client = MonarchMoney()

        await self.client.login(email=email, password=password, mfa_secret_key=mfa_secret_key, use_saved_session=False)

        self.categories = (await self.client.get_transaction_categories())['categories']
        self.reimbursements_category_id = next(
            (c for c in self.categories if c['name'] == 'Reimbursements'))['id']
        return self

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

                monarch_txn_id = txn['id']
                txn_hash = hashlib.sha256(
                    monarch_txn_id.encode('utf-8')).hexdigest()

                if txn_hash not in excluded:
                    print(txn)
                    monarch_merchant = txn['merchant']['name']
                    original_category = txn['category']['id']
                    reimbursement = splitwise_expense['amount_reimbursed']
                    tag_ids = [tag['id'] for tag in txn['tags']]

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
                            await self.client.update_transaction_splits(monarch_txn_id, split_data)
                            print()
                            x = await self.client.get_transaction_splits(monarch_txn_id)
                            print(type(x))
                            print(x)
                            splits = x['getTransaction']['splitTransactions']
                            print(splits)
                            for split in splits:
                                split_txn_id = split['id']
                                await self.client.set_transaction_tags(split_txn_id, tag_ids)
                        elif response.lower() == 'n':
                            valid_response = True
                            print('Transaction has been marked as excluded.')
                            excluded.append(txn_hash)

        with open(EXCLUDED_TRANSACTIONS_PATH, 'w') as f:
            json.dump(excluded, f, indent=4)
