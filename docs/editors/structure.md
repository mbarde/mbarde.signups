# How a signup sheet is structured

A signup sheet consists of four nested content types:

```text
UTSignupSheet           "Office hours winter term"
├── UTDay               "14.01.2027"
│   ├── UTTimeslot      "10:00 - 10:15"
│   │   ├── UTPerson    "Jane Doe"
│   │   └── UTPerson    "John Smith"
│   └── UTTimeslot      "10:15 - 10:30"
└── UTDay               "21.01.2027"
    └── UTTimeslot      "10:00 - 10:15"
```

`UTSignupSheet`
: The signup sheet itself. This is the page your visitors see and use to sign
  up. It holds all settings that apply to the whole sheet: the introduction
  text, contact information, whether signups have to be confirmed, the
  notification emails, data privacy settings and so on (see
  {doc}`signup-sheet-settings`).

`UTDay`
: A date. Its title (for example `14.01.2027`) is set automatically from the
  date. Days in the past are no longer shown on the signup sheet.

`UTTimeslot`
: A slot on that day, with start and end time, a maximum capacity and
  optionally a waiting list and a registration period (see
  {doc}`timeslots`). Its title (for example `10:00 - 10:15`) is set
  automatically from the times.

`UTPerson`
: A single signup for a timeslot, holding the registrant's name, email
  address and the data of the {doc}`additional form <additional-form>`. Each
  person has a state, for example _Signed up_ or _Waiting list_ (see
  {doc}`signup-states`). Persons are usually not created by editors but by
  visitors filling out the signup form.

A signup sheet can also contain an `EasyForm`, which can be used as
{doc}`additional form <additional-form>`.

## Signups are locked to their timeslot

Persons can't be copied, and they can't be moved to another timeslot. This
makes sure registrants are always informed about the slot they are booked in,
and limits like the capacity of a slot can't be bypassed. To move someone to
a different slot, sign them off and sign them up in the other slot.

When you copy a signup sheet, day or timeslot (for example to use it as a
template for the next event), the persons are not copied along.
