# MonarchWise

Reads expenses recorded in [Splitwise](https://www.splitwise.com/) and translates them into transaction splits in [Monarch Money](https://www.monarchmoney.com/). Not deployed anywhere, so you'll have to generate your own Splitwise app and provide the key/secret/API key in an `.env` file with the format shown in `.env.template`. Unfortunately, Monarch doesn't support app/token authentication at the moment, so you'll also need to provide your email/username in the same `.env` file.

## Auth

Monarch requires an email and password for API login; if you created an account with OAuth login e.g. Google Account then you need to manually set an email/password login.

Also, recently they decided to require MFA for API access. Make sure when setting up MFA to record the long string it displays at the bottom below the QR code - this is your `MONARCH_MFA_SECRET_KEY` value. 

## `excluded.json`

Since the transaction dicts are keyed on the dollar quantity, it's not unlikely that at some point you will have collisions between legitimately-split transactions and other payments that happened to be exactly the same value. To store these to prevent revisiting already-excluded transactions while protecting my privacy, the script stores a list of hashes of these transaction IDs. 

## Notes to self
For whatever reason, after a transaction split Monarch creates separate objects with separate IDs, and the original transaction ID will no longer appear in the response from `client.get_transactions()`. However, with the split transaction ID, you can call `client.get_transaction_details(split_id)`, find the original transaction ID, then call `client.get_transaction_splits(original_id)` to get the relevant information. 