Respa multi-day reservations
============================

Overview
--------

This feature adds support for creating multi day reservations in Respa.
Multi-day reservations are created basically same way as within day
reservations, but there are some settings that need to be set for
resources period for multi-day reservations to be allowed. These
settings can be set either in Respa Admin or Django admin panel. These
settings are described in api call examples below.

Payments
--------

Payments app of Respa required minor modifications for it to support
multi-day reservations.

### Product model

Product model of payments app includes methods for calculating price for
reservations. For multi-day reservations, new price type
*PRICE\_PER\_MULTIDAY\_DURATION\_UNIT* has been created. This price type
means that price is set per duration unit. Example:

If in MultidaySetting the duration\_unit is *week* and *min\_duration*
is 1 and *max\_duration* is 3 and in the *Product* data model the price
type is *PRICE\_PER\_MULTIDAY\_DURATION\_UNIT* and *price* is 100e then
1 week = 100e, 2 week = 200e, 3 week = 300e.

### Check price endpoint

When products price type is the new
*PRICE\_PER\_MULTIDAY\_DURATION\_UNIT*, resources periods are required
for calculating the price because multiday settings and
*duration\_unit*-field are set there. Therefore resource must be
specified when calling */v1/order/check\_price/*-endpoint.

Example body:

*{*

*"resource": "awicmityf3fa",*

*"begin": "2020-10-25T10:00:00.000Z",*

*"end": "2020-11-01T09:00:00.000Z",*

*"order\_lines": \[*

*{*

*"product": "awybz77rqqza"*

*}*

*\]*

*}*

Get multi day settings
----------------------

Opening hours for single day reservations are received by specifying
start and end dates in resource get requests:

[*https://respa.koe.hel.ninja/v1/resource/avmxnkmjvzya/?start=2020-08-12T06%3A37%3A47.178Z&end=2021-01-31T21%3A59%3A59.999Z*](https://respa.koe.hel.ninja/v1/resource/avmxnkmjvzya/?start=2020-08-12T06%3A37%3A47.178Z&end=2021-01-31T21%3A59%3A59.999Z)

We will use this also for multi day reservations. After making request
with start and end parameters, reservation periods including multi day
reservation settings will be returned.

Example JSON of multiday settings:

*{*

*"start": "2020-06-25",*

*"end": "2022-06-25",*

*"reservation\_length\_type": "over\_night",*

*"multiday\_settings": {*

*"max\_duration": 3,*

*"min\_duration": 1,*

*"duration\_unit": "week",*

*"check\_in\_time": "12:00:00",*

*"check\_out\_time": "11:00:00",*

*"start\_days": \[*

*"2020-09-17",*

*"2020-10-01",*

*"2020-10-12",*

*"2020-10-04",*

*"2020-10-11",*

*"2020-10-18",*

*"2020-10-25",*

*"2020-11-01",*

*"2020-11-08",*

*"2020-11-15",*

*"2020-12-01",*

*"2020-12-08",*

*"2020-12-15",*

*"2020-09-22"*

*\],*

*"must\_end\_on\_start\_day": false*

*}*

*}*

-   **start** - Start date of period when these settings apply

-   **end** - End date of period when these settings apply

-   **reservation\_length\_type** - Type of this period. Certain rules apply to certain types. Type choices:

    -   *within\_day* - Reservations allowed within day. Current implementation of Respa only has this type of reservations. Can’t make multi-day reservations during this period.

    -   *whole\_day* - Multi-day reservation type when resource is in reservers use during opening hours.

    -   *over\_night* - Multi-day reservations where resources is in reservers use the whole time. Check-in and check-out times are specified in multiday\_settings.

-   **multiday\_settings** - Settings / restrictions for multi-day
    > reservations.

    -   **duration\_unit -** Determines unit of max\_duration and min\_duration fields

    -   **max\_duration** - Maximum allowed length of reservations during this period.

    -   **min\_duration** - Minimum allowed length of reservationsduring this period.

        -   Example 1: If **duration\_unit = ’day’,** **max\_duration** = 7 and **min\_duration** = 7: only exactly 7 days long reservations are allowed

        -   Example 2: If **duration\_unit = ‘week’**, **max\_duration** = 3 and **min\_duration** = 1, allowed reservation length is 1, 2 and 3 weeks

        -   Example 3: If **duration\_unit = ‘month’**, **max\_duration** = 3 and **min\_duration** = 1, allowed reservation length is 1, 2 and 3 months

    -   **check\_in\_time** - Time of day when reserver must check in. Specified only if reservation type is *over\_night*.

    -   **check\_out\_time** - Time of day when reserver must check out. Specified only if reservation type is *over\_night*.

    -   **start\_days** - Array of allowed start dates of reservation. Reservations are only allowed to begin on these days.

    -   **must\_end\_on\_start\_day -** Reservations must always end on a start day defined in *start\_days* -field

Create reservations
-------------------

Reservations are created the same way as single day reservations. Begin
and end datetimes are on different day. Begin and end fields are in
datetime format although time is not relevant for multi-day
reservations. Resource must have periods with multi-day settings
specified for multi-day reservations to be allowed.

*{*

*"resource": "awicmityf3fa",*

*"begin": "2020-08-19T16:00:00+02:00",*

*"end": "2020-08-26T16:00:00+02:00",*

*}*

Get reservations
----------------

With multi-day reservations the fields are mostly same as before. One
field is added:

-   **length\_type** - Type of this reservation. Certain rules apply tocertain types. Type choices:

    -   *within\_day* - Reservations allowed within day. Current implementation of Respa only has this type of reservations. Can’t make multi-day reservations during this period.

    -   *whole\_day* - Multi-day reservation type when resource is in reservers use during opening hours.

    -   *over\_night* - Multi-day reservations where resources is in reservers use the whole time.

This fields value is automatically filled when making reservations. The
value is determined by **reservation\_length\_type** - field of the
period that the reservation was made in. Value choices are exactly the
same as periods ones.
