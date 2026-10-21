# Signup states, confirmation and waiting list

## States

Each signup (`UTPerson`) is in one of these states:

| State                    | Id            | Meaning                                                         |
| ------------------------ | ------------- | --------------------------------------------------------------- |
| Waiting for confirmation | `unconfirmed` | A manager has to confirm the signup                             |
| Signed up                | `signedup`    | The person is signed up for the slot and occupies a place       |
| Waiting list             | `waiting`     | The person is on the waiting list of the slot                   |
| Signed off               | `signedoff`   | The signup has been cancelled (by the person or by a manager)   |

Only _Signed up_ persons count towards the capacity of a slot.

## What happens when someone signs up

Without confirmation (default)
: If the slot has free places, the person is _signed up_ immediately. If
  the slot is full and has a waiting list, the person is put on the _waiting
  list_. Otherwise the slot can't be selected.

With _Manager has to confirm signups_
: Every new signup starts as _waiting for confirmation_, even if the slot
  is full - the manager then decides whether to sign the person up, put
  them on the waiting list or sign them off. The registrant gets the _wait
  for confirmation_ email, the contact address gets a notification.

In each case, the registrant receives the matching {doc}`email <emails>`.

## Confirming signups

Open the person (from the timeslot or the
{doc}`manager summary <managing-signups>`) and use the buttons to confirm the
signup or to put the person on the waiting list, or use the _State_ menu of
the toolbar. A person can only be signed up while the slot has free places.

## Waiting list and automatic move up

If _Automatic move up from waiting list_ is enabled in the signup sheet
(default), a free place is filled automatically from the waiting list:

- when a signed up person signs off, and
- when the capacity of the slot is increased.

The person who has been waiting longest is moved up first, and gets the
confirmation email.

Moving a signed up person to the waiting list does **not** move up anyone
else - this is how you reduce the capacity of a slot (see
{doc}`timeslots`).

:::{note}
If a slot has free places while people are on the waiting list (for example
when automatic move up is disabled), the timeslot page shows a hint. Reduce
the capacity or sign up someone from the waiting list.
:::

## Signing up again

If a person who signed off signs up for the same slot again, their previous
signup is reused and goes through the normal process again.
