# Kulkunen

Kulkunen is an app that enables Respa to control external access control systems (ACSs).
It has a driver abstraction which facilitates adding support for ACSs from different
vendors.

## Architecture

Each Kulkunen model has a `driver_data` attribute for storing driver-specific data.
It is fully controlled by the ACS driver. Some models have a `driver_config` attribute
for storing driver-specific configuration data, such as external API URLs and credentials.

One Respa resource can be managed by at most one ACS instance. Each resource must be
configured with an `AccessControlResource` object. The configuration must be done
programmatically (for now).

Kulkunen registers to listen for signals for reservation confirmation, modification
and cancellation events.

Currently, the `sync_kulkunen` management command must be called regularly (from cron,
for example) to perform operations on the external ACSs.

### Reservation confirmation

When a new reservation is confirmed for a Respa resource that has a corresponding
`AccessControlResource` object, the following happens:

1. `AccessControlResource.grant_access()` is called by the signal handler.
2. `grant_access()` creates an `AccessControlGrant` object that stores the Kulkunen
state related to the reservation. The grant starts its life in `requested` state.
3. The ACS driver is then asked to mark the grant for installation to the external ACS
by calling `AccessControlDriver.prepare_install_grant()`. The base driver marks the grant
to be installed immediately, but e.g. the SiPass driver will defer installation to
24h before the start time of the grant.
4. `sync_kulkunen` management command is eventually called. It will check for grants
that are due for installation and call `AccessControlGrant.install()` on each one.
5. `AccessControlGrant.install()` will change the grant state to `installing` and attempt
to perform the necessary API calls for granting access to the reservation on the external
ACS by calling `AccessControlDriver.install_grant()`. If the driver raises an exception,
a retry is scheduled for later.
6. After the grant is installed successfully, the ACS driver sets the grant to the `installed`
state. If the grant needs explicit removal from the external ACS, the driver may
set the `AccessControlGrant.remove_at` timestamp to when the grant needs to removed.

### Reservation cancellation

1. `AccessControlResource.revoke_access()` is called by the signal handler.
2. If there is an active grant for the reservation, `revoke_access()` calls
`AccessControlGrant.cancel()`.
3. `AccessControlGrant.cancel()` sets the state of the grant to `cancelled` and
marks it for removal by the driver by calling `AccessControlSystem.prepare_remove_grant()`.
By default the grant is marked for immediate removal, but the driver may override the method
and remove it at a later time or through other means.
4. `sync_kulkunen` management command is called, and `AccessControlDriver.remove_grant()` called
for each grant that should be removed.
