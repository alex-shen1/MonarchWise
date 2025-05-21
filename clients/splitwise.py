import logging
import datetime
from splitwise import Splitwise
from functools import lru_cache
# logging.basicConfig(level=logging.DEBUG)


class SplitwiseClient:
    def __init__(self, key, secret, api_key):
        self.client = Splitwise(key, secret, api_key=api_key)
        self.client.getExpenses
        self.clientUserId = self.client.getCurrentUser().getId()

    @lru_cache
    def _get_name(self, id):
        user = self.client.getUser(id)
        # print(f'{user.first_name}{f" {user.last_name}" if user.last_name else ""} is {id}')
        return f'{user.first_name}{f" {user.last_name}" if user.last_name else ""}'

    def get_groups(self):
        groups = self.client.getGroups()
        groups_data = {}
        for group in groups:
            group_id = group.getId()
            group_name = group.getName()
            groups_data[group_id] = group_name
        return groups_data
    
    def get_expenses(self, updated_after=None):
        groups_data = self.get_groups()
        
        expenses_data = []
        offset = 0
        while True:
            page = self.client.getExpenses(limit=100, offset=offset, updated_after=updated_after)
            if not page:
                break
            expenses_data.extend(page)
            offset += 100
        expenses = []

        for expense in expenses_data:
            '''
            Remove unwanted expenses
            Unwanted expenses are settle ups or expenses that do not involve the client user
            '''
            if expense.payment == True:
                continue     
                   
            try:
                if expense.repayments[0].toUser == self.clientUserId:
                    continue
            # Index errors occur when you bill yourself the amount the transaction amount
            except IndexError:
                continue
            
            amount_owed = sum(
                [float(d.amount) for d in expense.repayments if d.fromUser == self.clientUserId])
            # Only include transactions where the user owes money
            if amount_owed == 0:
                continue
            '''
            End remove unwanted expenses
            '''
            
            dt = datetime.datetime.strptime(expense.date, "%Y-%m-%dT%H:%M:%SZ")
            formatted_date = dt.date().isoformat()

            # Possible future upgrade where transactions that were added by you into SW would be added
            # Removed for now as it conflicts with Monarch to SW integration
            # amount_reimbursed = sum(
            #     [float(d.amount) for d in expense.repayments if d.toUser == self.clientUserId])
            
            # Get paid to whom
            paid_to = [d.toUser for d in expense.repayments if d.fromUser == self.clientUserId]
            paid_to = [self._get_name(id) for id in paid_to]
            # Get amount owed
            amount_owed = sum(
                [float(d.amount) for d in expense.repayments if d.fromUser == self.clientUserId]) * -1

            group_id = expense.group_id
            if group_id is None:
                group_name = "None"
            else:
                group_name = groups_data[group_id]
            cost = float(expense.cost)
            expenses.append({
                'total_cost': cost,
                'description': expense.description,
                'date': formatted_date,
                'amount_owed': amount_owed,
                # 'amount_reimbursed': amount_reimbursed
                'group_id': group_id,
                'group_name': group_name,
                'id': expense.id
            })

        return expenses
