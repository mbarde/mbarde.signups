# Setup

## Mail server

Signups, cancellations and email verification all send emails. Make sure
the MailHost of your site is configured properly in _Site Setup > Mail_ (see
the [Plone documentation](https://6.docs.plone.org/admin-guide/configure-mail.html)).

:::{important}
Without a working mail server, signups fail with an error as soon as a
notification email is sent.
:::

## Identifying users by their email address

Signups are identified by the email address of the registrant. This is how a
logged-in user's own signups are recognized (for example in _My signups_) and
how duplicate signups are prevented.

So in order to do a proper matching you need to either

- set _Use email address as login name_ in _Site Setup > Security_,

or

- make sure your users have a member property holding their email address
  (by default `email`, see below).

## Control panel

The control panel _Site Setup > mbarde.signups Settings_
(`@@mbarde-signups-controlpanel`) maps Plone member properties to the
personal data fields of the signup form. For logged-in users, these fields
are then pre-filled with their own data.

Member property for prename
: Leave empty to not pre-fill the prename.

Member property for surname
: Leave empty to not pre-fill the surname.

Member property for email address
: Default: `email`. Also used to recognize a logged-in user's own
  signups (unless the site uses the email address as login name, in which
  case the login name is used instead).

## Permissions

The add-on defines these permissions, which by default are granted to
_Manager_, _Site Administrator_, _Owner_ and _Contributor_:

| Permission                             | Allows to                                                                              |
| -------------------------------------- | -------------------------------------------------------------------------------------- |
| `mbarde.signups: Add UTSignupSheet`    | Create signup sheets                                                                   |
| `mbarde.signups: Add UTDay`            | Add days to a signup sheet                                                             |
| `mbarde.signups: Add UTTimeslot`       | Add timeslots to a day                                                                 |
| `mbarde.signups: Add UTPerson`         | Add persons to a timeslot manually                                                     |
| `mbarde.signups: Manage Schedule`      | View days, timeslots and persons, the manager summary, CSV export and remove all persons |

Signing up itself only requires the _View_ permission on the signup sheet.
To give a team the ability to manage a particular signup sheet, share it
with them using the _Can add_ (Contributor) role.
