Permissions in Respa
====================

Roles
-----

The following roles are defined for the users of Respa.

- Super User
- General Administrator
- Unit Group Administrator
- Unit Administrator
- Unit Manager
- Unit Viewer
- Reserver i.e. End User


Administration Workflow Example
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here is an example that should help understanding the user roles.

1. Super User (in Django Admin)

   * creates a new Unit Group.

     - Unit Group could be e.g. "Helsinki Libraries" or "Espoo Youth
       Centers"

   * authorizes an user as Unit Group Administrator for the Unit Group.

     - Note: The authorized user should have already logged in to
       Varaamo (or tried to log in to Respa Admin at least once) so that
       the User account exists in the database.

2. Unit Group Administrator (in Respa Admin)

   * creates new Units to the Unit Group.

   * authorizes some users as Unit Administrators for the new units.

3. Unit Administrator (in Respa Admin)

   * authorizes some users as Unit Managers for the unit.

   * grants some users to approve reservations in the unit.

   * creates new Resources to the Unit.

4. Unit Manager (in Respa Admin)

   * updates the details of the Resources in the Unit.

5. Unit Viewer

   * examines and modifies end users reservations on request

6. User with the permission granted in step 3 (in Varaamo)

   * approves reservations.


Permissions
-----------

Super User Permissions
~~~~~~~~~~~~~~~~~~~~~~

**Super Users implicitly have all possible permissions.**

There is some functionality that is only available to the Super Users.
Access to these actions is not implemented via Django Permissions, but
they are still listed here to make it clear that these actions are only
available for the Super Users.  These actions can be performed in the
Django Admin interface.

super
    Can make any changes in Django Admin

can_manage_unit_groups
    Can manage Unit Groups, i.e. create/delete Unit Groups,
    assign/unassign Units to/from Unit Groups, and authorize/unauthorize
    users as Unit Group Administrators.

can_change_unit_of_resource
    Can change the Unit of a Resource (i.e. move the Resource to another
    Unit)

can_manage_all_reservations
    Can display/modify/delete any reservation

Resource Permissions
~~~~~~~~~~~~~~~~~~~~

The resource permissions can be granted individually to any user or user
group on two scopes:

  * Resource Group: The permission is granted to all resources in the
    resource group.
  * Unit: The permission is granted to all resources of the unit.

The explicit resource permissions are implemented with Django Guardian.
All resource permissions are defined in ``resources/models/permissions.py``.


In addition following user roles has resource permissions in Respa:

  * General Administrators (GA)
  * Unit Group Administrator (UGA)
  * Unit Administrators (UA)
  * Unit Manager (UM)
  * Unit Viewer (UV)

These roles implicitly has certain permissions for the resources in
the Unit Group or Unit. All role based permissions are represented in
table below.


====================================== ====== ======= ====== ====== ======
**Permission**                         **GA** **UGA** **UA** **UM** **UV**
-------------------------------------- ------ ------- ------ ------ ------
can_approve_reservation
can_make_reservations                    X       X      X      X
can_modify_reservations                  X       X      X      X      X
can_ignore_opening_hours                 X       X      X      X
can_view_reservation_access_code         X       X      X      X      X
can_view_reservation_extra_fields        X       X      X      X      X
can_view_reservation_user                X       X      X      X      X
can_access_reservation_comments          X       X      X      X      X
can_comment_reservations                 X       X      X      X      X
can_view_reservation_catering_orders     X       X      X      X
can_modify_reservation_catering_orders
can_view_reservation_product_orders
can_modify_paid_reservations
can_bypass_payment                       X       X      X      X
can_create_staff_event                   X       X      X      X
can_create_special_type_reservation      X       X      X      X
can_bypass_manual_confirmation           X       X      X      X
can_create_reservations_for_other_users  X       X      X
can_create_overlapping_reservations      X       X      X      X
can_ignore_max_reservations_per_user     X       X      X      X
can_ignore_max_period                    X       X      X      X
====================================== ====== ======= ====== ====== ======


Definitions of the permissions:

can_approve_reservation
  Can approve reservations

can_make_reservations
  Can make reservations

can_modify_reservations
  Can modify reservations

can_ignore_opening_hours
  Can make reservations outside opening hours

can_view_reservation_access_code
  Can view reservation access code

can_view_reservation_extra_fields
  Can view reservation extra fields

can_view_reservation_user
  Can view reservation user

can_access_reservation_comments
  Can access reservation comments

can_comment_reservations
  Can create comments for a reservation

can_view_reservation_catering_orders
  Can view reservation catering orders

can_modify_reservation_catering_orders
  Can modify reservation catering orders

can_view_reservation_product_orders
  Can view reservation product orders

can_modify_paid_reservations
  Can modify paid reservations

can_bypass_payment
  Can bypass payment when making a reservation

can_create_staff_event
  Can create a reservation that is a staff event

can_create_special_type_reservation
  Can create reservations of a non-normal type

can_bypass_manual_confirmation
  Can bypass manual confirmation requirement for resources

can_create_reservations_for_other_users
  Can create reservations for other registered users

can_create_overlapping_reservations
  Can create overlapping reservations for different resources in single unit even if restricted

can_ignore_max_reservations_per_user
  Can ignore resources max reservations per user rule

can_ignore_max_period
  Can ignore resources max period rule


Respa Admin Permissions
~~~~~~~~~~~~~~~~~~~~~~~

Respa Admin permissions are granted to the Unit Group Administrators
(UGA), Unit Administrators (UA), Unit Managers (UM), Unit Viewers (UV) and General
Administrators (GA).  Most of them are granted per Unit Group or per
Unit basis, but there are also a few general permissions which are not
tied to any object.  The permissions are listed in the following table
with the scope of authorization and the authorized roles.

General Administrator role is not bound to any Unit or Unit Group and so
their permissions are unscoped.

====================================== ============ ====== ======= ====== ====== ======
**Permission**                         **Scope**    **GA** **UGA** **UA** **UM** **UV**
-------------------------------------- ------------ ------ ------- ------ ------ ------
can_login_to_respa_admin               General        X       X      X      X
can_access_permissions_view            General        X       X      X
can_search_users                       General        X       X      X
can_modify_resource                    Unit           X       X      X      X
can_manage_resource_perms              Unit           X       X      X
can_modify_unit                        Unit           X       X      X      X
can_manage_auth_of_unit                Unit           X       X      X
can_create_resource_to_unit            Unit           X       X      X
can_delete_resource_of_unit            Unit           X       X      X
can_manage_auth_of_unit_group          Unit Group     X       X
can_create_unit_to_group               Unit Group     X       X
can_delete_unit_of_group               Unit Group     X       X
====================================== ============ ====== ======= ====== ====== ======

Definitions of the permissions:

can_login_to_respa_admin
    Can login to Respa Admin interface

can_access_permissions_view
    Can access permission management view

can_search_users
    Can search users (by e-mail)

can_modify_resource
    Can modify Resources of the Unit

can_manage_resource_perms
    Can grant Resource Permissions to any user within scope of the
    administrated Unit

can_modify_unit
    Can modify the Unit

can_manage_auth_of_unit
    Can add/remove users as Unit Administrators or Unit Managers

can_create_resource_to_unit
    Can create a new Resource to the Unit

can_delete_resource_of_unit
    Can delete a Resource of the Unit

can_manage_auth_of_unit_group
    Can add/remove users as Unit Group Administrators for the Unit Group.

can_create_unit_to_group
    Can create a new Unit to the Unit Group

can_delete_unit_of_group
    Can delete an Unit of the Unit Group


Implementation of the Roles
---------------------------

Staff Status
~~~~~~~~~~~~

All users having any of these Super User, Administrator or Manager
statuses are considered "staff" and should have the ``is_staff``
property of the User object set to True.

Super User
~~~~~~~~~~

Super User status is granted by setting the ``is_superuser`` property of
the User object to True.

General Administrator
~~~~~~~~~~~~~~~~~~~~~

General Administrator status is granted by setting ``is_general_admin``
property of the User object to True.

Unit Group Administrator
~~~~~~~~~~~~~~~~~~~~~~~~

Unit Group Administrator status is given per Unit Group via an
``UnitGroupAuthorization`` link.  The authorizations of an unit group
called ``unit_group`` can be queried like this::

    >>> unit_group.authorizations.all()
    <QuerySet [
        UnitGroupAuthorization(
            authorized=user1,
            subject=unit_group1,
            level=UnitGroupAuthorizationLevel.admin),
        UnitGroupAuthorization(
            authorized=user2,
            subject=unit_group1,
            level=UnitGroupAuthorizationLevel.admin),
        ...
    ]>

Unit Administrators, Managers and Viewers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Unit Administrator, Unit Manager and Unit Viewer status is given per Unit via an
``UnitAuthorization`` link.  The authorizations of an unit called
``unit`` can be queried like this::

    >>> unit.authorizations.all()
    <QuerySet [
        UnitAuthorization(
            authorized=user1,
            subject=unit1,
            level=UnitAuthorizationLevel.admin),
        UnitAuthorization(
            authorized=user2,
            subject=unit1,
            level=UnitAuthorizationLevel.manager),
        UnitAuthorization(
            authorized=user3,
            subject=unit1,
            level=UnitAuthorizationLevel.viewer),
        ...
    ]>
