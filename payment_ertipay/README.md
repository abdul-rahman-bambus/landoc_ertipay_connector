# Payment Provider: Ertipay for Odoo 18 Community

`payment_ertipay` adds Ertipay UPI pay-in support to the Landoc quotation and
website-payment flow. A customer can accept a quotation, choose a down payment
or the full Landoc amount, review any Ertipay commission and GST, and continue
to a UPI application. Gateway charges are collected by Ertipay but never added
to the Landoc invoice.

## Amount and accounting rules

The Odoo payment transaction amount remains the amount due to Landoc. When
**Transaction Charges Applied** is enabled, the gateway request is calculated
as follows:

```text
commission = Landoc amount × transaction percentage
commission GST = commission × transaction tax percentage
Ertipay requested total = Landoc amount + commission + commission GST
```

For example, a Landoc payment of INR 1,000.00 with 2% commission and 18% GST on
that commission produces a commission of INR 20.00, GST of INR 3.60, and an
Ertipay request for INR 1,023.60. The invoice and Odoo reconciliation remain INR
1,000.00. The other values are stored only on the payment transaction and
invoice for gateway payout reconciliation.

The checkout displays the Landoc amount, commission, commission GST, and
Ertipay total when charges are enabled. When charges are disabled, both charge
amounts are zero and Ertipay receives only the selected Landoc amount.

The percentages and calculated amounts are snapshotted on the transaction
before the request. Later configuration changes therefore do not alter the
historical amount sent to Ertipay.

## Environment and endpoints

Configure **API Base URL** as the host only, normally
`https://payin.ertipay.com`. The provider state selects the environment path for
token, UPI, and status calls:

| Odoo provider state | Ertipay API prefix |
| --- | --- |
| Test Mode | `https://payin.ertipay.com/uat` |
| Enabled | `https://payin.ertipay.com/prod` |

The connector normalizes a configured URL that already ends in `/uat` or
`/prod`, preventing duplicate or stale environment paths.

| Operation | Test Mode | Enabled |
| --- | --- | --- |
| Token | `POST /uat/token` | `POST /prod/token` |
| Create UPI payment | `POST /uat/upi` | `POST /prod/upi` |
| Fetch status | `GET /uat/status/<txnRefId>` | `GET /prod/status/<txnRefId>` |

The URLs hosted by Odoo do not use the Ertipay API host:

| Purpose | Odoo route |
| --- | --- |
| Server-to-server notification | `POST /payment/ertipay/callback` |
| Customer return/status refresh | `GET /payment/ertipay/return` |

Supply Ertipay with the absolute callback URL, for example
`https://uat-odoo.example.com/payment/ertipay/callback` during UAT and
`https://odoo.example.com/payment/ertipay/callback` in production. Both URLs
must be public HTTPS endpoints. The UPI `refUrl` is generated from Odoo's base
URL and points to the customer return route.

## Authentication and encryption

The token request sends the configured Pay-In email and API secret. The JWT is
cached on the provider and refreshed before expiry to avoid unnecessary token
generation.

Request and response payloads use the Ertipay-compatible encryption format:

- AES-128-CBC
- 32-character hexadecimal key
- random 16-byte IV per request
- UTF-8 compact JSON input
- `<iv_hex>:<encrypted_hex>` output

The Odoo server must provide the `openssl` executable.

## Callback processing

The callback controller requires:

- encrypted content in `data` or `encryptedData`;
- `x-erti-signature`;
- `x-erti-timestamp`.

It rejects callbacks older than five minutes and verifies the HMAC-SHA256
signature before decryption. After verification, the decrypted plain response
is written to the Odoo server log with the `[Ertipay]` prefix, matched to the
payment transaction, and retained in **Raw Response** for audit.

The connector compares Ertipay's returned `txnAmt`, `amount`, `totalAmount`,
`total`, or `paidAmount` (when supplied) with the snapshotted requested gateway
total. The Landoc transaction amount is never replaced with this gateway total.

| Ertipay result | Odoo behavior |
| --- | --- |
| `S`, amount matches or is not returned | Mark done and run normal Odoo payment post-processing |
| `S`, amount differs | Keep pending for reconciliation review |
| `D` | Keep pending until final confirmation |
| `F` | Keep pending for reconciliation/status follow-up |
| Missing or unknown status | Keep pending |

## Installation and configuration

1. Add this repository to the Odoo addons path.
2. Confirm `openssl` is installed on the Odoo host.
3. Restart Odoo and update the Apps list.
4. Install or upgrade **Payment Provider: Ertipay**.
5. Open **Accounting / Invoicing → Configuration → Payment Providers → Ertipay**.
6. Configure the Merchant ID, Pay-In Email, Pay-In API Secret, 32-character
   Pay-In Encryption Key, Merchant VPA, channel type, and initiation mode.
7. Leave the API Base URL as the host without an environment suffix.
8. Select **Test Mode** for UAT or **Enabled** for production.
9. Optionally enable **Transaction Charges Applied**, then enter the commission
   and GST percentages.
10. Register the appropriate public Odoo callback URL with Ertipay.

Use **Enable API Debug Logs** only while diagnosing an integration. Logs show
endpoints and sanitized payloads; access to Odoo server logs should remain
restricted.

## Final UAT procedure

### Configuration checks

1. Put the provider in **Test Mode** and enter UAT credentials.
2. Confirm token, UPI, and status log entries use `/uat`, never `/prod`.
3. Confirm Ertipay has the UAT Odoo callback URL ending in
   `/payment/ertipay/callback`.
4. Enable transaction charges and configure known test percentages.

### Full-payment test with charges

1. Create and send a quotation with an easily verified total.
2. Accept/sign it and select full payment.
3. Select Ertipay and verify all four checkout values and currency formatting.
4. Verify the displayed total equals Landoc amount + commission + GST.
5. Start payment and confirm the encrypted UPI request uses that total.
6. Complete UPI payment and confirm the callback is accepted and decrypted.
7. Confirm the server log contains the sanitized plain callback response.
8. Confirm the transaction becomes **Done** for a matching success response.
9. Confirm the invoice total and reconciled amount contain only the Landoc
   amount.
10. Compare Requested Gateway Total and Gateway Confirmed Total on the Ertipay
    tabs of the transaction and invoice.

### Down-payment test with charges

Repeat the full-payment test after selecting a down payment. Calculate the fee
from the selected down payment, not from the full quotation total. Confirm the
invoice/payment applies only that Landoc down-payment amount.

### Charges-disabled test

Disable transaction charges and repeat payment. No charge breakdown should be
shown, stored commission and GST must be zero, and the gateway request must
equal the Landoc amount.

### Callback and reconciliation tests

1. Send a valid `S` callback with the requested total: transaction becomes Done.
2. Send `S` with a different amount: transaction stays Pending and the mismatch
   flag is enabled.
3. Send `D`: transaction stays Pending.
4. Send `F`: transaction stays Pending rather than Error.
5. Send an unknown status: transaction stays Pending.
6. Send an invalid signature, expired timestamp, or malformed encrypted body:
   callback is rejected and no transaction is completed.
7. Return through `/payment/ertipay/return` while payment is pending and verify
   that the `/uat/status/<txnRefId>` response is decrypted and processed.
8. Change provider percentages after initiating a payment and verify its stored
   requested fee, GST, and total do not change.

### Manual status refresh during trial/UAT

Ertipay UAT does not complete real UPI payments. To finish a UAT scenario, open
**Accounting / Invoicing → Customers → Payment Transactions**, open the pending
Ertipay transaction, and choose one of these Test Mode-only actions:

- **UAT Mark Successful** posts `S` to `/uat/callback`;
- **UAT Mark Failed** posts `F` to `/uat/callback`.

After Ertipay accepts the simulated result, Odoo immediately calls
`/uat/status/<txnRefId>`, decrypts and logs the plain response, stores the
reconciliation response, and applies the normal callback status rules. Use
**Fetch Ertipay Status** to repeat only the status query if the simulator update
is not immediately visible. UAT simulation is blocked in production; live
transactions rely on Ertipay's automatic callback, with manual status fetching
available as a fallback.

### Production readiness

1. Replace UAT credentials with production credentials.
2. Register the production Odoo callback URL with Ertipay.
3. Change the provider from Test Mode to Enabled.
4. Confirm token, UPI, and status calls now use `/prod`.
5. Perform a controlled low-value payment and complete the same accounting and
   payout reconciliation checks before general release.

## Operational notes

- UPI intent links generally require a mobile device; desktop users may receive
  a QR URL instead.
- The raw callback is retained for support and payout auditing. Restrict access
  to payment transaction records appropriately.
- Failed and amount-mismatched transactions intentionally remain pending so an
  operator can compare the requested and confirmed totals and query Ertipay
  before taking accounting action.
