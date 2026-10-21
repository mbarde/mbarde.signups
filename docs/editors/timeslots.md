# Days and timeslots

## Timeslot settings

Start Time, End Time
: The time range of the slot. The title of the timeslot is set from these
  automatically.

Name
: Optional name, shown if _Show individual time slot names_ is enabled in
  the signup sheet.

Max capacity
: How many persons can sign up for this slot. Default: 1.

Allow waiting list
: Once the slot is full, further signups go to the waiting list, see
  {doc}`signup-states`.

## Creating a series of timeslots

To fill a day with equally sized, back-to-back timeslots (for example four
slots of 15 minutes each for office hours), use the form on the day's page
instead of adding the slots one by one. Enter

- the starting time,
- the duration of each timeslot in minutes,
- the number of timeslots,
- the max capacity of each timeslot and
- whether to allow a waiting list.

## Registration period

Each timeslot can have a registration period, using the _Publishing date_
and _Expiration date_ fields in the _Dates_ tab of the timeslot. Signups for
the slot are only possible in between. This allows, for example, opening the
registration for all slots at a certain time, or closing it a day before the
event.

## Changing the capacity

Increasing the capacity
: If there are people on the waiting list, they automatically fill the new
  places (oldest signup first) - as long as _Automatic move up from waiting
  list_ is enabled in the signup sheet.

Reducing the capacity
: The capacity can't be reduced below the number of people already signed
  up. Move some of them to the waiting list or sign them off first.

Disabling the waiting list
: Only possible once nobody is on the waiting list anymore. Sign them up or
  sign them off first.
