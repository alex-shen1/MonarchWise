# MonarchWise

Reads expenses recorded in [Splitwise](https://www.splitwise.com/) and translates them into transaction splits in [Monarch Money](https://www.monarchmoney.com/). Not deployed anywhere, so you'll have to generate your own Splitwise app and provide the key/secret/API key in an `.env` file with the format shown in `.env.template`. Unfortunately, Monarch doesn't support app/token authentication at the moment, so you'll also need to provide your email/username in the same `.env` file.

## Notes to self
For whatever reason, after a transaction split Monarch creates separate objects with separate IDs, and the original transaction ID will no longer appear in the response from `client.get_transactions()`. However, with the split transaction ID, you can call `client.get_transaction_details(split_id)`, find the original transaction ID, then call `client.get_transaction_splits(original_id)` to get the relevant information. 