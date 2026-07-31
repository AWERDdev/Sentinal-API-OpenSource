## 🚨 Local Development & Email Testing Notes (Resend API)

When testing the Canary Token trigger system locally on `localhost`, you may encounter an **HTTP 403 / Domain Restriction** error from the Resend API. 

### Why this happens:
By default, unverified free-tier Resend accounts operate under a strict sandbox mode. Resend will prevent emails from being delivered to arbitrary domains/addresses until you verify a custom domain via DNS records.

### How to test locally without a custom domain:
To successfully receive breach notification emails during local manual testing:
1. Ensure the email address you pass in your configuration payload matches the **exact email address you used to sign up for your Resend account**.
2. Alternatively, hardcode your Resend registration email into the `to` field of the `send_security_alert` function within `routes/canary_trigger.py` temporarily for testing.

Once the application is deployed to production with a verified custom domain, alerts can be dynamically routed to any user-specified email


## Update

Email sending now  works instead of using Resend API now using google smtp email sending to send emails when triggering the tokens make sure to check your spam to see the email from the app