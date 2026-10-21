# Signup sheet settings

These settings are found when editing a `UTSignupSheet`.

## Default

Text
: Formatted text displayed above the signup form.

Contact information
: Email address of the manager of the signup sheet. Used as sender of the
  notification emails and shown to registrants.

Send notification mails to contact info
: Notify the contact address about new signups and cancellations.
  Default: on.

Manager has to confirm signups
: Every signup has to be confirmed (or rejected) by a manager first, see
  {doc}`signup-states`. Default: off.

Allow signup for external user
: Allow signups by visitors who don't have an account (who are not logged
  in). Default: off.

Email verification for external users
: Visitors who are not logged in have to verify their email address with a
  one-time code before their signup is completed. Default: on.

Lock personal data
: Prename, surname and email address can't be changed in the signup form,
  they are only pre-filled from the logged-in user's account. Only available
  if signup for external users is disabled. Default: off.

Allow signup for multiple slots
: Allow a person to sign up for more than one slot of this signup sheet.
  Default: off.

Automatic move up from waiting list
: If a signup is cancelled, the first person on the waiting list is signed
  up automatically, see {doc}`signup-states`. Default: on.

Show individual time slot names
: Show the optional names of the timeslots.

Hide availability
: Don't show how many places are left in a slot.

Hide date and time
: For signups that are not bound to a certain date and time. Slots are then
  labeled with their name (if _Show individual time slot names_ is on) or
  with the title of the signup sheet.

Additional form
: An `EasyForm` with further fields to fill in when signing up, see
  {doc}`additional-form`.

## Data privacy

See {doc}`data-privacy`.

## Mail settings

See {doc}`emails`.
