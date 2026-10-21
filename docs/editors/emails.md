# Notification emails

All emails sent to registrants can be customized in the _Mail settings_ tab
of the signup sheet. Each email has a subject and a content field, pre-filled
with a default text in the language of the signup sheet.

| Email                    | Sent when                                                                                  |
| ------------------------ | ------------------------------------------------------------------------------------------ |
| Email verification       | A visitor who is not logged in signs up (if _Email verification for external users_ is on) |
| Confirmation             | A person is signed up                                                                      |
| Wait for confirmation    | A person signs up and _Manager has to confirm signups_ is on                               |
| Waiting list             | A person is put on the waiting list                                                        |
| Cancellation             | A signup is cancelled                                                                      |

_Suffix for authenticated users_ is appended to all of these emails, but
only for signups made by a logged-in user. By default it contains a link to
their signups. Leave it empty to append nothing.

If _Send notification mails to contact info_ is enabled, the contact address
additionally receives a notification on new signups and cancellations.

## Placeholders

These placeholders are replaced in subject and content:

| Placeholder        | Replaced with                                                                                                |
| ------------------ | ------------------------------------------------------------------------------------------------------------ |
| `$$name$$`         | Full name of the registrant                                                                                  |
| `$$title$$`        | Title of the signup sheet                                                                                    |
| `$$url$$`          | URL of the signup sheet                                                                                      |
| `$$user_url$$`     | URL to view and manage your own signups (not in the email verification email)                                |
| `$$sign_off_url$$` | URL to sign off from this signup directly, without logging in (only in confirmation, wait for confirmation and waiting list emails) |
| `$$slot$$`         | Date and time of the slot (name of the slot if date and time are hidden)                                     |
| `$$data$$`         | Data entered in the {doc}`additional form <additional-form>`                                                 |
| `$$code$$`         | One-time verification code (only in the email verification email)                                           |
