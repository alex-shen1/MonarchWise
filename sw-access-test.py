from splitwise import Splitwise

sw_key  = "hWpvC70yoZt8Ssmn1eJQ6p6LZxAvjWDrF2JlmYme"
secret  = "ewayDxpFcnLlcxVBulnRL9pToESRxeqd2n0291qW"
api_key = "d4Mu0ztVY5hJ1yVn41bc6TqWpb2dAPFj6WDXR8Ar "
sObj = Splitwise(sw_key,secret, api_key=api_key)

current = sObj.getCurrentUser()

print("Current User:")
print(current.id)

expenses = sObj.getExpenses(limit=10)
print("\nExpenses:")
print("Total Expenses:", len(expenses))

users = sObj.getUser(46365980)

print("User Details:")
print(f'User ID: {users.id}')
print(f'User Name: {users.first_name} {users.last_name}')
print(f'User Email: {users.email}')
