# mbarde.signups

Plone 6 add-on to provide dynamic sign-up forms for events with single or
multiple dates / timeslots available - for example training sessions, office
hours or consultation appointments.

Main features:

- Define date based timeslots users can sign up to
- Timeslots can have capacities, a waiting list and automatic moving up from
  the waiting list
- Registration periods per timeslot
- Optional confirmation of each signup by a manager
- Signups for users without an account, with email verification via one-time
  code
- Logged-in users can watch and manage their own signups
- Customizable notification emails
- Extend the signup form with additional fields via
  [collective.easyform](https://github.com/collective/collective.easyform)
- Data privacy: data usage declaration, consent and automatic deletion of
  personal data

This documentation is split into two parts:

{doc}`admins/index`
: For site administrators: installing the add-on and setting up the Plone site.

{doc}`editors/index`
: For editors managing signup sheets: how a signup sheet is structured and
  which features are available.

```{toctree}
:hidden:
:maxdepth: 2

admins/index
editors/index
```
