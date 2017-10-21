# Setup

The `slack` module requires a set of API tokens in order to operate. The polling function requires a standard API token, while the notifier can operate with a "bot" token.

## API Token Generation

To create the required API tokens, direct your browser to the [Slack API Apps list](https://api.slack.com/apps) and (once signed-in to the appropriate team) click on the "Create New App" button. This should present you with a menu that allows you to set a name for the app (we recommend "Busybody") and select the team to enable it on.

Once you enter that information, you will be taken to the detailed settings for your new app. Feel free to set the "Display Information" in a way that makes sense to you and ignore the "App Credentials" presented. Move down to "Bot Users", enable a bot user with the name of your choice, and then move back up to "OAuth & Permissions".

In the OAuth section select the following permissions. In an effort to make you a bit more comfortable with granting these, each will be listed with a full description of what we use it for below:

> admin            - Used to access user logs.

> bot              - Used to act as the bot user.

> chat:write:bot   - Used to send messages as our bot.

> users:read       - Used to access the user list.

> user:read:email  - Used to access the emails of users for correlation with other applications.

Once you have granted those permissions, install the app and take note of the OAuth tokens that have been generated for you.i

## Configuration File

Slack may exist under the "pollers", "analysis", and/or "notifiers" top-level dictionaries in the configuration file.

The "slack" dictionary within the "pollers" dictionary may contain:

> api\_token        - Defines the API token used to poll for user logs and to add the email to logs.

The "slack" dictionary within the "analysis" dictionary has no special options.

The "slack" dictionary within the "notifiers" dictionary may contain:

> api\_token        - Defines the API token ("bot" token) used to send notifications about alerts.

> channel          - Defines the channel or user to send the notification to.
