# Setup

The `flatfile` module requires no setup in order to operate, except that your calling user should have read and write permissions on the location where you wish to store logs.

## Configuration File

Flatfile only exists within the "persistence" top-level dictionary in the configuration file.

The "persistence" dictionary may only contain one backend at a time. This is enforced by not having "flatfile" be a sub-dictionary, but rather by having a "module" key within the "persistence" dictionary that may take "flatfile" as a value. Other values used by `flatfile` are:

> log\_directory          - The directory in which you would like to store log files.
