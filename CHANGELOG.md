# Changelog

## 0.16 - 2021-08-22

* New: job system without server

## 0.15.2 - 2021-07-28

* Fix: forgotten imports of some functions

## 0.15.1 - 2021-07-23

* Server launched with a dedicated script

## 0.15 - 2021-07-19

* New: job server
* New: import of namers, fixers, checkers and evaluations
* Scripts must now be launched from a Hateno-compatible folder
* Explorer now shows the minimum of a search
* Mapper now generates the simulations by batch when possible
* Remote working directory is now created if it does not exist yet
* Settings tags changed
* Fix: harmonized behavior for paths of program files

## 0.14.1 - 2021-04-07

* Fix: settings tags are taken into account in a search

## 0.14 - 2021-04-03

* New: SSH gates support
* New: `exists()` method in Manager
* Explorer split into Mapper and Explorer
* Evaluations functions are now defined in the config folder
* Local mode is now faster
* Simulations that do not exist anymore are automatically deleted during `update()`
* Fix: multiple namers can be applied

## 0.13 - 2021-01-11

* New: configs and skeletons can be imported from another folder
* New: search for a specific value in Explorer
* New: secant method in Explorer
* New: program files description
* Settings of type list are handled
* Use of a temporary directory right in Hateno folder
* Custom namers, fixers and checkers can be defined in dedicated files
* Checkers now admit arguments
* Option to not send a file that has not been modified
* Fix: successful simulations are now extracted even if there are failed ones

## 0.12 - 2020-11-07

* New `default_config` key in configuration to define the default config to use in the Maker
* Custom namers and fixers can be imported in the scripts
* Simulations can be added/deleted from their folders
* Addition datetime stored in the simulations list
* JSON generators can now admit parameters
* Settings tags in Explorer maps
* Depth passed to evaluation function in the Explorer
* Configs and skeletons from Folder
* New default namers to prepend indexes
* Configuration file renamed to `hateno.conf`
* Simulations archives stored in a subfolder
* Fix: strings in `only_if` are not a problem anymore
* Fix: Maker can be used safely in `generate_only` mode

## 0.11.1 - 2020-10-26

* Maps' outputs stored in search iterations

## 0.11 - 2020-10-24

* New: Explorer
* New: jobs progress indicator
* New: watch mode in hateno-jobs to watch a jobs states file
* New: read-only mode in Manager
* Configurations and skeletons files all moved to `.hateno`
* Maker adds simulations right after downloading them
* The copied list in hateno-maker can be merged with another
* Events have their own separate class
* Fix: progress bars are now fully erased, even with high numbers
* Fix: jobs progress bars removed when the Maker is paused

## 0.10.1 - 2020-09-03

* Fix: bug preventing the use of global settings tags in global settings

## 0.10 - 2020-08-09

* New: jobs manager
* New: Maker events
* New: option to create a copy of the simulations to generate in the maker script
* Maker can be paused during the "waiting for jobs" step
* Maker UI separated from main class

## 0.9 - 2020-07-27

* New: options in settings tags to access specific sets and indexes
* New: fixer to protect strings with spaces
* New: default `namers` and `fixers` keys in sets and settings
* New: context manager for Maker, Manager and RemoteFolder
* New: clear folder method and script
* Port can now be indicated for a remote folder
* New interface to interact with UI objects
* Precision of progress bars' percentages can be set
* Bug fixes

## 0.8 - 2020-07-02

* New: namers are functions allowing to alter the name of settings during execution
* New: script `init` to initialize a folder
* New: global script `hateno` to run all the other scripts
* New: FCollection to manage a collection of functions
* Configuration files moved to `.hateno` folder
* Fixers available at the sets level
* Configuration key `fixes` changed to `fixers`
* Manager and Generator can be created without Folder instance
* Manager can detect if an instance is already running for the current folder
* Fixers, generators and checkers are now stored in an FCollection
* Bugs fixes

## 0.7 - 2020-06-19

* Transformation script/method can be used to change the settings of a simulation
* A simulation can be deleted from its settings file
* Maker generates the settings file

## 0.6.2 - 2020-06-17

* Fix: wrong behavior in some `only_if` tests

## 0.6.1 - 2020-06-15

* Evaluation delimiters

## 0.6 - 2020-06-02

* More tests allowed in `only_if`, comparisons with other settings, arithmetic operations, etc.

## 0.5 - 2020-05-26

* Simulations can be transformed
* Settings file can be added to extracted simulations

## 0.4 - 2020-05-21

* Fixers can be applied to specific settings only
* New default fixers for lists
* Limits for the generator can be set by subgroups number only
* Fix: global checker noMore is not too greedy anymore

## 0.3 - 2020-05-16

* New structure in the simulations list
* New way to define simulations settings
* Simulations list update method
* Method to access the full settings of a simulation
* New parameter `only_if` for settings
* Max subgroups parameter in generator recipe
* Fix: one-entry simulations list in `hateno-manager`

## 0.2 - 2020-04-08

* Local mode in `RemoteFolder`

## 0.1 - 2020-03-24

* First version
