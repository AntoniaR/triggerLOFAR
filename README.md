# TriggerLOFAR

This repository contains the trial version of the code required to trigger LOFAR (the LOw Frequency ARray).

## Basic Principle

Transient events are listened for using a VOEvent Broker, which is listening to another VOEvent Broker (such as the 4PiSky Broker).
When a VOEvent is received, it is first processed to check if it is one of the VOEvents users are specifically interested in.
The VOEvent information is then passed to filtering code that determines if the transient event:

1. Meets the required observing criteria (e.g. duration of transient)

2. Is observable within the time requirements (e.g. above horizon and has a calibrator)

If the event passes these criteria, a trigger xml document is created using an existing template. This event is then submitted to the LOFAR systems (n.b. the submitter needs an active LOFAR proposal, with associated username/password, and for their compute system to be whitelisted)

## Requirements

This code is utilising the following external software packages (that will install their dependencies upon first install)

* 4PiSky Tools (and subscribed to their broker) [https://github.com/4pisky/fourpiskytools](https://github.com/4pisky/fourpiskytools) which is built upon:
..* Comet [http://comet.transientskp.org/en/stable/](http://comet.transientskp.org/en/stable/)
..* VOEvent-parse [http://voevent-parse.readthedocs.io/en/stable/](http://voevent-parse.readthedocs.io/en/stable/)
* The LOFAR Transients Pipeline tools [https://github.com/transientskp/tkp](https://github.com/transientskp/tkp)

Python Modules:
* numpy
* scipy 
* os
* datetime
* logging
* sys
* six
* pandas
* requests
* xml

## Example

This repository contains an example code to trigger LOFAR observations on a short GRB detected by the Swift Satellite.

