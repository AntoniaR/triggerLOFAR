# TriggerLOFAR

This repository contains the trial version of the code required to trigger LOFAR (the LOw Frequency ARray).

## Basic Principle

Transient events are listened for using a VOEvent Broker, which is listening to another VOEvent Broker (such as the 4PiSky Broker).
When a VOEvent is received, it is first processed to check if it is one of the VOEvents users are specifically interested in.
The VOEvent information is then passed to filtering code that determines if the transient event:

1. Meets the required observing criteria (e.g. duration of transient)

2. Is observable within the time requirements (e.g. above horizon and has a calibrator, identified using [calibrators.csv](https://github.com/AntoniaR/triggerLOFAR/blob/master/calibrators.csv))

If the event passes these criteria, a trigger xml document is created using an existing template. This event is then submitted to the LOFAR systems (n.b. the submitter needs an active LOFAR proposal, with associated username/password, and for their compute system to be whitelisted)

## Requirements

This code is utilising the following external software packages (that will install their dependencies upon first install)

* 4PiSky Tools (and subscribed to their broker) [https://github.com/4pisky/fourpiskytools](https://github.com/4pisky/fourpiskytools) which is built upon:
  * Comet [http://comet.transientskp.org/en/stable/](http://comet.transientskp.org/en/stable/)
  * VOEvent-parse [http://voevent-parse.readthedocs.io/en/stable/](http://voevent-parse.readthedocs.io/en/stable/)
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

The code is [sgrb_swift.py](https://github.com/AntoniaR/triggerLOFAR/blob/master/sgrb_swift.py)

To test this code, run `cat ivo_nasa.gsfc.gcn_SWIFT#BAT_GRB_Pos_817345-759.xml | ./sgrb_swift.py` which should give the output:
```TrigID: 817345, In SGRB filtering code
TrigID: 817345, prompt transmission
TrigID: 817345, Integration time check passed. 0.512,1.0
TrigID: 817345, Checking altitude: 26.4376522849,10.0
TrigID: 817345, Index from altitude check: 1
TrigID: 817345, Calibrator found: 3C147
TrigID: 817345, XML file written to: 817345.xml
```

This output will be on both the terminal and in a logfile called sgrb_swift.log.
It will also produce the triggering xml file with the name being the Trigger ID of the transient source from the satellite.

To run this code in realtime, it is activated using the bash script [listen_for_voevents](https://github.com/AntoniaR/triggerLOFAR/blob/master/listen_for_voevents.sh). This starts the VOEvent broker, listens to the events from the 4PiSky broker and passes the events received to the script sgrb_swift.py.
