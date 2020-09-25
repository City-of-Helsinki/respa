Initial API calls for Respa multi-day reservations
==================================================

**VERSION 1.2**

**Change log:**

1.2 - Added field must\_end\_on\_start\_day to multiday settings

1.1 - Changed *min\_days* and *max\_days* to *min\_duration* and
*max\_duration* in multiday settings. Also added new field
*duration\_unit* to the settings.

Get multi day settings
----------------------

Opening hours for single day reservations are received by specifying
start and end dates in resource get requests:

[*https://respa.koe.hel.ninja/v1/resource/avmxnkmjvzya/?start=2020-08-12T06%3A37%3A47.178Z&end=2021-01-31T21%3A59%3A59.999Z*](https://respa.koe.hel.ninja/v1/resource/avmxnkmjvzya/?start=2020-08-12T06%3A37%3A47.178Z&end=2021-01-31T21%3A59%3A59.999Z)

We will use this also for multi day reservations. After making request
with start and end parameters, reservation periods including multi day
reservation settings will be returned:

![](media/image1.png){width="4.458333333333333in"
height="5.145833333333333in"}

-   **start** - Start date of period when these settings apply

-   **end** - End date of period when these settings apply

-   **reservation\_length\_type** - Type of this period. Certain rules
    > apply to certain types. Type choices:

    -   *within\_day* - Reservations allowed within day. Current
        > implementation of Respa only has this type of reservations.
        > Can’t make multi-day reservations during this period.

    -   *whole\_day* - Multi-day reservation type when resource is in
        > reservers use during opening hours.

    -   *over\_night* - Multi-day reservations where resources is in
        > reservers use the whole time. Check-in and check-out times are
        > specified in multiday\_settings.

-   **multiday\_settings** - Settings / restrictions for multi-day
    > reservations.

    -   **duration\_unit -** Determines unit of max\_duration and
        > min\_duration fields

    -   **max\_duration** - Maximum allowed length of reservations
        > during this period.

    -   **min\_duration** - Minimum allowed length of reservations
        > during this period.

        -   Example 1: If **duration\_unit = ’day’,** **max\_duration**
            > = 7 and **min\_duration** = 7: only exactly 7 days long
            > reservations are allowed

        -   Example 2: If **duration\_unit = ‘week’**, **max\_duration**
            > = 3 and **min\_duration** = 1, allowed reservation length
            > is 1, 2 and 3 weeks

        -   Example 3: If **duration\_unit = ‘month’**,
            > **max\_duration** = 3 and **min\_duration** = 1, allowed
            > reservation length is 1, 2 and 3 months

    -   **check\_in\_time** - Time of day when reserver must check in.
        > Specified only if reservation type is *over\_night*.

    -   **check\_out\_time** - Time of day when reserver must check out.
        > Specified only if reservation type is *over\_night*.

    -   **start\_days** - Array of allowed start dates of reservation.
        > Reservations are only allowed to begin on these days.

    -   **must\_end\_on\_start\_day -** Reservations must always end on
        > a start day defined in *start\_days* -field

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

-   **length\_type** - Type of this reservation. Certain rules apply to
    > certain types. Type choices:

    -   *within\_day* - Reservations allowed within day. Current
        > implementation of Respa only has this type of reservations.
        > Can’t make multi-day reservations during this period.

    -   *whole\_day* - Multi-day reservation type when resource is in
        > reservers use during opening hours.

    -   *over\_night* - Multi-day reservations where resources is in
        > reservers use the whole time.

This fields value is automatically filled when making reservations. The
value is determined by **reservation\_length\_type** - field of the
period that the reservation was made in. Value choices are exactly the
same as periods ones.
