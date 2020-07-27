# Changelog

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
