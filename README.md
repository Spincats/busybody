# busybody

Neighborhood watch for your SaaS apps.

## Setup

### Python Environment

Depending on your choice of system, please use the package manager of your choice to install `python-3.6`, `pip`, and `virtualenv`. 

Now, selecting a directory that can host executable files, create a virtualenv:

> $ virtualenv busybodyenv

Once that is complete, move into the new `busybodyenv` (or whatever you named your virtualenv) directory and activate your new virtual environment:

> $ . ./bin/activate

Now that we're in the environment, please download `busybody` from your choice of source. For example:

> $(busybodyenv) git clone git@github.com:Spincats/busybody.git

Now move into that new directory and install `busbody`'s requirements:

> $(busybodyenv) pip install -r requirements.txt

On certain systems, installing these dependencies from `pip` may fail. In that case, check your package manager for pre-built packages under that name and then re-run the above command until it succeeds. Those systems will generally need to instantiate the virtualenv with the `--system-site-packages` option.

### Scaling

`busybody` is designed to scale horizontally. The polling and analysis portions of the application can be run separately with the `--mode` flag. As such, pollers may be staggered or run on multiple machines. Additionally, the per-user model that is constructed lends itself naturally to sharding if the analysis function needs to be scaled.

### Config File

The `busybody` configuration file is a YAML config file that allows you to configure most settings within the script. Some settings are available at the command line (mostly runtime options like verbosity and log output file).

The config file can be placed anywhere, but if a location is not given at runtime, the script will default to looking in `~/.config/busybody/config.yml` or `./config.yml` in that order for the config.

The format of the config file is standard YAML formatting. Top-level dictionaries correspond to the major functions of `busybody`, and though there may be a few standard items within them, most are module specific and explained in the README.md files within the module directories.

Top-level configuration items are:

> pollers

> persistence

> analysis

> notifiers

As noted above, each of those should be a standard YAML dictionary, an example of which can be found in the example.yml file.

There are a few lower-level configuration options of special note that will not be covered in the per-module READMEs as they apply either to the system as a whole, or to multiple types of modules. These are:

> enabled

This is a dummy dictionary entry that may be provided within any module that needs no further configuration, but that needs to be listed in a particular section. Any module that you wish to poll from **must** be listed inside the "pollers" top-level dictionary. Similarly, any module that you wish to perform analysis on **must** be listed inside of the "analysis" top-level dictionary.


> geoip

This dictionary inside of the "analysis" top-level dictionary should contain two entries that point to databases provided by MaxMind. The "city\_db" entry should be a MaxMind city-resolution database. The "asn\_db" should be a MaxMind IP-\>ASN database. Both are freely available from [MaxMind's site](http://dev.maxmind.com/geoip/geoip2/geolite2/).

> history\_limit

This is a string entry within the "analysis" top-level dictionary. It represents the amount of time backwards (in seconds) that should be included in each analysis run. This can be very useful to allow trends to age out and to prevent the unbounded growth of the analysis application as you accumulate events.

> user\_domain

This is a string entry within any module dictionary inside of the "analysis" top-level dictionary. This string provides a domain to append to the user names from the module to convert them into email-style strings. NOTE: This is a blunt tool that will be insufficient for many cases. It is applied prior to the below "user\_map", however, so it may be useful for an initial pass with later corrections. Generally, it is preferable to already have emails in the logs as they serve as a consistent cross-service user identifier.

> user\_map

This can be a dictionary within any module dictionary inside of the "analysis" top-level dictionary. It provides a mapping between a source user value (key) and a final user value (value). This can be useful, for example, if a user has signed up for a service with their personal email, so that you can continue to properly correlate those log events with their other entries from other services.

> geoip

This dictionary inside of the "analysis" top-level dictionary should contain two entries that point to databases provided by MaxMind. The "city\_db" entry should be a MaxMind city-resolution database. The "asn\_db" should be a MaxMind IP-\>ASN database. Both are freely available from [MaxMind's site](http://dev.maxmind.com/geoip/geoip2/geolite2/).

> enabled

This is a dummy dictionary entry that may be provided within any module that needs no further configuration, but that needs to be listed in a particular section. Any module that you wish to poll from **must** be listed inside the "pollers" top-level dictionary. Similarly, any module that you wish to perform analysis on **must** be listed inside of the "analysis" top-level dictionary.

## Output

It is recommended to run Busybody with the verbose flag and redirecting output to a file until you are certain that the configuration is correct. This is usually sufficient to identify issues with your configuration. Debug mode (`-vv`) logs a significant amount of information and may log sensitve information and should be used with care.

As a note, the output of this program will be the result of statistical tests run on the input logs. Depending on the nature of your incoming logs, some things that may seem suspicious may not be sufficiently disctinct from the background noise for this program to alert on. Similarly some innocuous activities may be flagged because they are a significant deviation from what our model believes the norm to be.

Interpretation of the output may require an analyst to review other entries from the user that has been flagged in order to determine the cause of the flag. Please bear that in mind and only take action against a flagged user account if further investigation shows that such action is merited. Just like an actual neighborhood watch, just taking reports at face value may lead to undesirable outcomes.


## Documentation of the model

This machine learning model uses an isolation forest as the final decision function because of its parameter-free nature, and its well-recognized performance in higher-dimensional data (O(n) time and O(1) space), which may occur when parsing text as we are. Each user gets assigned their own model to ensure that users with less concrete clusters of activity don't mask anomalous behavior of those who have more tightly clustered activity.

There are four components at this time going into the final decision function. These are:

### Device Identifier

This is primarily the user-agent, which is being run through the term frequency inverse-document frequency (tf-idf) vectorizer. Ideally we would have both user agent and some form of other "device" identifier (like a random UUID) so that we could assess whether a new connection was really from a new device or from a device that we know. Unfortunately, none of the existing modules expose this information (and, in fact, only Slack is exposing the user-agent).

### IP Geolocation

One piece of data that we attempt to gather from the IP is the geolocation, using databases from MaxMind. This information may not always be accurate, but can provide a helpful clue in many cases about the likelihood that a connection is part of the user's normal patterns.

### IP ASN Organization

The other piece of the puzzle that comes from the IP is the owning ASN's organization name. This allows the model to correlate different networks (that may geolocate to different locations) that are owned by the same group. For example, many mobile network providers have numerous ranges that they may assign IPs from and these ranges are often assigned at the national level, so even remaining within a limited geographical area may not guarantee an IP that geolocates to that area. This field is also run through tf-idf to turn the text into useful numbers, which allows us to account for minor differences is organization name across ASNs belonging to larger organizations.


## Changelog

* 1.0 - Initial public release
    * Functional ML core using isolation forest and a per-user IP location, ASN, and user-agent model.
    * GSuite module for polling
    * Slack module for polling and notifying
    * Flatfile module for persistence
    * Documentation
