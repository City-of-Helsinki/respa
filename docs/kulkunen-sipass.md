# Kulkunen SiPass driver

Kulkunen has an integration for Siemens SiPass access control system. The
integration uses the SiPass HR API for adding access to reservations and
currently supports only PIN-code-based entry.

The SiPass driver will create a new cardholder with a unique PIN code
for each reservation 24 hours before the reservation starts, and it will
remove the cardholder soon after the reservation has ended. The reason
for this is to limit the number of concurrent cardholders. The PIN code
is created at cardholder creation time, and the end-user is sent a notification
email.

The SiPass driver needs some instance-based configuration to work. The
configuration is stored as an JSON object in `AccessControlSystem.driver_config`.

Key            | Description
-------------- | --------------------
tls_client_cert| The client certificated and private key in PEM format 
tls_ca_cert    | The CA certificate (if custom) to trust when connecting to server
api_url        | The API base URL for the service (usually something like `https://example.com/api/V1/hr`)
username       | Username for the API user configured to SiPass
password       | Password for the API user
credential_profile_name | Name of the credential profile for the created cardholders
cardholder_workgroup_name | Name of the workgroup in which to place the cardholder

For each Respa resource that is managed by SiPass, an `AccessControlResource`
object needs to created with the following driver config:

Key            | Description
---------------| --------------------
access_point_group_name | Specifies which access point group to allow access to for this resource

The access point group is configured in SiPass and should contain all the access points
(doors) that need to be opened to allow the user access.
