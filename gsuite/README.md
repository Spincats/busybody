# Setup

The `gsuite` module requires service user credentials in order to operate.

## Service User Generation

To create the required service user, follow the instructions from [Google](https://developers.google.com/admin-sdk/reports/v1/guides/delegation) about setting up a service user and performing account-wide delegation. Make note of where you store the downloaded credential file.

## Configuration File

GSuite may exist under the "pollers" and/or "analysis" top-level dictionaries in the configuration file.

The "gsuite" dictionary within the "pollers" dictionary may contain:

> credential\_file         - The location of the JSON credentials file for the service user.

> admin\_email             - The admin whose user should be assumed during polling.

The "gsuite" dictionary within the "analysis" dictionary has no special options.
