# Data privacy

The _Data privacy_ tab of the signup sheet contains:

Data usage declaration
: Describe specifically what happens with the collected personal data, what
  it is used for and how long it is stored. Shown in the signup form.

User has to consent to the data usage declaration in order to sign up
: Registrants have to tick a checkbox to consent before they can sign up.
  Whether consent is required can be derived from Art. 6 GDPR. Default: on.
  The time of consent and a copy of the declaration text at that time are
  stored with each signup, so a later change of the declaration doesn't
  change what a person consented to.

Automatically delete personal data after (days)
: Number of days after the date of a day after which the signups of that day
  are deleted automatically. Leave empty to disable automatic deletion.

:::{important}
Automatic deletion only works if your administrator has set up the
corresponding cron job (see {doc}`../admins/data-privacy`).
:::
