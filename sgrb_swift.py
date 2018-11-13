#!/home/antoniar/JupyterEnv/bin/python

#################### WARNING: Turn off sending triggers when testing!!!!!!!!!!!!!

import numpy as np
import scipy as sp
import os
from datetime import datetime
from datetime import timedelta
from datetime import time
import tkp.utility.coordinates as tkpcoords
import logging
import sys
import six
import voeventparse
import pandas
import requests
import pytz
#import xml.etree.ElementTree as ET
from lxml import etree as ET
import lofar_maintenance

import astropy.units as u
from astropy.time import Time
from astropy.coordinates import SkyCoord, EarthLocation, AltAz 

#from fourpiskytools.notify import Notifier



################# Runing the 4PiSky Broker #################
# This script is called when the broker receives a VOEvent from the 4PiSky Boker.
# See the example here: https://github.com/4pisky/fourpiskytools/blob/master/examples/listen_for_voevents.sh
# Edit line 14 of this script to HANDLER=./sgrb_swift.py


# Some variables that I need everywhere, so to make life easier...
global ObsMax, ObsMin, AltCut, MaxDwell, Name, email, phoneNumber, Affiliation, ProjectCode, GRB_trig_dur, template, username,LOFARlocation

ObsMax= 120. #time in minutes
ObsMin= 30.
AltCut=15. #minimum elevation for observations in degrees
MaxDwell=8. # maximum dwell time in minutes
MinDwell=4. # minimum dwell time (while testing)
LOFARlocation = EarthLocation(lat=52.9088*u.deg,lon=6.8689*u.deg,height=0.*u.m)
CalObsT = 10.

Name = "Antonia Rowlinson"
username = 'antoniar'
email = "rowlinson@astron.nl"
phoneNumber = "799"
Affiliation = "ASTRON"
ProjectCode = 'LC10_012'
#ProjectCode = 'test-triggers-low'
GRB_trig_dur = 1.
template = 'sgrb_template.xml'

#################
# This code is edited from Tim's example here: https://github.com/4pisky/fourpiskytools/blob/master/examples/process_voevent_from_stdin_2.py
# Some of these can be used directly from the 4pisky tutorials but not all.

logging.basicConfig(filename='sgrb_swift.log',level=logging.INFO)
logger = logging.getLogger('notifier')
logger.handlers.append(logging.StreamHandler(sys.stdout))

def main():
    if six.PY2:
        stdin = sys.stdin.read()
    else:
        # Py3:
        stdin = sys.stdin.buffer.read()
    v = voeventparse.loads(stdin)
    handle_voevent(v)  
    return 0

def calcAltAz(time,RA,Dec):
    time = Time(time.strftime("%Y-%m-%d %H:%M:%S"))
    position = SkyCoord(RA,Dec,unit='deg')
    AltAzPos = position.transform_to(AltAz(obstime=time,location=LOFARlocation))
    return AltAzPos.alt.deg
    

def handle_voevent(v):
    # edited
    #logger.info(format(v.attrib['ivorn']))
    if is_grb(v):
        #logger.info('is GRB')
        RA, Dec, time, parameters, ivorn = handle_grb(v)
        logger.info('TrigID: '+format(parameters[None]['TrigID']['value'])+','+format(time)+','+str(RA)+','+str(Dec)+','+format(parameters[None]['Integ_Time']['value'])+','+format(parameters['Misc_Flags']['Delayed_Transmission']['value']))
        now = datetime.utcnow().replace(tzinfo=pytz.utc)
        logger.info(now)
        logger.info(time)
        logger.info(now - time)
        if now-time < timedelta(minutes=10):
            filterSGRBs(RA, Dec, now, parameters, v)
        else:
            logger.info('Delayed trigger, arriving >10min after GRB')
    elif is_swift_pointing(v):
        #logger.info('is Swift pointing')
        handle_pointing(v)
    elif is_ping_packet(v):
        #logger.info('is ping packet')
        handle_ping_packet(v)
    else:
        #logger.info('is something else')
        handle_other(v)
        
def is_grb(v):
    # edited to give more alerts to test my code
    ivorn = v.attrib['ivorn']
    if ivorn.find("ivo://nasa.gsfc.gcn/SWIFT#BAT_GRB_Pos") == 0:
        return True
    #if ivorn.find("ivo://nasa.gsfc.gcn/SWIFT#BAT_SubSubThresh_Pos") == 0: ##
    #    return True
    return False

def is_swift_pointing(v):        
    ivorn = v.attrib['ivorn']
    if ivorn.startswith("ivo://nasa.gsfc.gcn/SWIFT#Point_Dir_"):
        return True
    return False

def is_ping_packet(v):
    ivorn = v.attrib['ivorn']
    role = v.attrib['role']
    ivorn_tail = ivorn.rsplit('/', 1)[-1]
    stream = ivorn_tail.split('#')[0]
    if ( role == voeventparse.definitions.roles.test and
         stream == 'TEST'
        ):
        return True
    return False

def handle_grb(v):
    # edited
    #logger.info('in handle grb')
    ivorn = v.attrib['ivorn']
    logger.info("VOEvent received. IVORN: "+ivorn)
    coords = voeventparse.get_event_position(v)
    ra=coords.ra
    dec=coords.dec
    time = voeventparse.convenience.get_event_time_as_utc(v, index=0) # this is a datetime.datetime object
    parameters = voeventparse.convenience.pull_params(v) 
#    integ_time = parameters[None]['Integ_Time']['value']
#    text = "Swift packet received, coords are {}".format(coords)
#    logger.info(text)
#    handle_other(v)
    return ra, dec, time, parameters, ivorn

def handle_pointing(v):
    #logger.info('in handle pointing')
    ivorn = v.attrib['ivorn']
    coords = voeventparse.get_event_position(v)
    text = "Swift repointing, coords are {}".format(coords)
    #logger.info(text)
    #handle_other(v)
    #return 

def handle_ping_packet(v):
   #logger.info("Packet received matches 'ping packet' filter.")
   handle_other(v)

def handle_other(v):
    ivorn = v.attrib['ivorn']
    #logger.info("VOEvent received. IVORN: "+ivorn)

    
################# Filter the possible short GRBs and send alert #################

def filterSGRBs(RA, Dec, time, parameters,v):
    # Trig_dur needs to be less than the input, readFromEvent needs to be checked.
    logger.info('TrigID: '+format(parameters[None]['TrigID']['value'])+', '+'In SGRB filtering code')
#    if (parameters['Misc_Flags']['Delayed_Transmission']['value'] != False): #first only trigger on non-delayed bursts
        #logger.info('TrigID: '+format(parameters[None]['TrigID']['value'])+', '+'prompt transmission')
    if float(parameters[None]['Integ_Time']['value']) < GRB_trig_dur:
        # calculate time of event in mjds
        logger.info('TrigID: '+format(parameters[None]['TrigID']['value'])+', '+'Integration time check passed. '+str(parameters[None]['Integ_Time']['value'])+','+str(GRB_trig_dur))
        #mjds=86400.*tkpcoords.julian_date(time,modified=True)
        # Altitude needs to be greater than the input
        #calcAlt =  calcAltAz(time,RA,Dec) #tkpcoords.altaz(mjds, RA, Dec, lat=52.9088)[0]
        #logger.info('TrigID: '+format(parameters[None]['TrigID']['value'])+', '+'Checking altitude: '+str(calcAlt)+','+str(AltCut))
        #if calcAlt > AltCut:
            # Source needs to stay above horizon
        index = horizon(time,RA, Dec)
        logger.info('TrigID: '+format(parameters[None]['TrigID']['value'])+', '+'Index from altitude check: '+str(index))
        if index != 0:
            # we need a calibrator source
            calibrator = find_cal(time,RA, Dec,index)
            if calibrator['Calibrators'] != 'None':
                logger.info('TrigID: '+format(parameters[None]['TrigID']['value'])+', '+'Calibrator found: '+str(calibrator['Calibrators'])+','+str(calibrator['CalRA'])+','+str(calibrator['CalDec']))
                xmlname = writeXMLfiles(format(parameters[None]['TrigID']['value']),time,RA, Dec,calibrator,index)
                logger.info('TrigID: '+format(parameters[None]['TrigID']['value'])+', '+'XML file written to: '+xmlname)
                sendXMLtoLOFAR(xmlname)
            else:
                logger.info('TrigID: '+format(parameters[None]['TrigID']['value'])+', '+'Failed to find a calibrator')
        else:
            logger.info('TrigID: '+format(parameters[None]['TrigID']['value'])+', '+'Not above horizon within time constraints')
    else:
        logger.info('TrigID: '+format(parameters[None]['TrigID']['value'])+', '+'Likely long GRB, '+format(parameters[None]['Integ_Time']['value']))
    #else:
    #    logger.info('TrigID: '+format(parameters[None]['TrigID']['value'])+', '+'Delayed trigger')

################# Check the elevation of the source #################

def horizon(time,RA,Dec):
            az0=calcAltAz(time+timedelta(minutes=MaxDwell),RA,Dec) #tkpcoords.altaz(mjds+(60.*(MaxDwell)), RA, Dec, lat=52.9088)[0]
            az0b=calcAltAz(time+timedelta(minutes=MaxDwell),RA,Dec) #tkpcoords.altaz(mjds, RA, Dec, lat=52.9088)[0]
            az2=calcAltAz(time+timedelta(minutes=(MaxDwell+ObsMax)),RA,Dec) #tkpcoords.altaz(mjds+(60.*(ObsMax+MaxDwell)), RA, Dec, lat=52.9088)[0]
            az1=calcAltAz(time+timedelta(minutes=(MaxDwell+ObsMin)),RA,Dec) #tkpcoords.altaz(mjds+(60.*(ObsMin+MaxDwell)), RA, Dec, lat=52.9088)[0]
            #logger.info(format(mjds)+','+format(mjds+60.*(MaxDwell))+','+format(MaxDwell))
            #logger.info(format(az0)+','+format(az0b)+','+format(az2)+','+format(az1))
            if az0<AltCut: # the source is below minimum at start
                return 0   
            if az0b>AltCut: # wait till dwell time to start observations
                if az1<AltCut: # the source sets before the minimum observation duration
                    return 0
                if az2>AltCut: # the source is above the minimum for the whole observation
                    return 1
                if az1>AltCut and az2<AltCut: # the source drops between the max and min time
                    return 2
            if az0>AltCut and az0b<AltCut: # wait till dwell time to start observations
                if az1<AltCut: # the source sets before the minimum observation duration
                    return 0
                if az2>AltCut: # the source is above the minimum for the whole observation
                    return 3
                if az1>AltCut and az2<AltCut: # the source drops between the max and min time
                    return 4
        
    # if 1 is returned, ask for the full time immediately, no constraints
    # if 2 is returned just ask for minimum (until smarter method, 
    # this also helps if there is a delay) and no constraints.
    # the max dwell time is considered here - if source would set during 
    # the latest possible observation, we will not observe
    # need to keep the dwell time short for now.
    # if 0 is returned, don't observe
    # 3 returned, start full observation after dwell time
    # 4 returned, ask for minimum duration after the dwell time
 
  

def find_cal(time,RA, Dec, index):
    calibrators=pandas.read_csv('calibrators.csv',sep=',',header=0)
    separation=648000.
    for index2, cal in calibrators.iterrows():
        septmp = tkpcoords.angsep(RA, Dec, float(cal.ra), float(cal.dec))
        startT = time+timedelta(minutes=MinDwell)
        if index == 1:
            timeStart = startT+timedelta(minutes=ObsMax+MaxDwell+2.)
            timeEnd = timeStart+timedelta(minutes=CalObsT)
            #mjds_start = mjds
            #mjds_end = mjds+(60.*(MaxDwell+ObsMax))
        elif index == 2:
            timeStart = startT+timedelta(minutes=ObsMin+MaxDwell+2.)
            timeEnd = timeStart+timedelta(minutes=CalObsT)
            #mjds_start = mjds
            #mjds_end = mjds+(60.*(MaxDwell+ObsMin))            
        elif index == 3:
            timeStart = startT+timedelta(minutes=ObsMax+MaxDwell+2.)
            timeEnd = timeStart+timedelta(minutes=CalObsT)
            #mjds_start = mjds+(60.*(MaxDwell))  
            #mjds_end = mjds+(60.*(MaxDwell+ObsMax))              
        elif index == 4:
            timeStart = startT+timedelta(minutes=ObsMin+MaxDwell+2.)
            timeEnd = timeStart+timedelta(minutes=CalObsT)
            #mjds_start = mjds+(60.*(MaxDwell))
            #mjds_end = mjds+(60.*(MaxDwell+ObsMin))      
        else:
            return {          'Calibrators':'None',
                              'CalSep':0,
                              'CalRA':0,
                              'CalDec':0}
        
        alt_start = calcAltAz(timeStart,RA,Dec) #tkpcoords.altaz(mjds_start, cal.ra, cal.dec, lat=52.9088)[0]
        alt_end = calcAltAz(timeEnd,RA,Dec) #tkpcoords.altaz(mjds_end, cal.ra, cal.dec, lat=52.9088)[0]
        if septmp < separation and alt_start > AltCut and alt_end > AltCut:
            separation = septmp
            optcal = cal.src
            optra = cal.ra
            optdec = cal.dec
    if optcal:
        return {'Calibrators':optcal,
                              'CalSep':(separation/(60.*60.)),
                              'CalRA':optra,
                              'CalDec':optdec}
    else:
        return {'Calibrators':'None',
                              'CalSep':0,
                              'CalRA':0,
                              'CalDec':0}





################# Write the XML for LOFAR #################
def generateXML(GRB,RA,Dec,CalRA,CalDec,start,maxDur,minDur,end,calname,startCal,endCal,stations):
    # this is particularly ugly so I suspect there is a better way? Also specific for the sgrb_template.xml
    
    tree = ET.parse(template)
    root = tree.getroot()

    if len(stations) != 0:
        for station in stations:
            for child in root.iter('specification'):
                for child2 in child.findall('activity'):
                    for child3 in child2.findall('observation'):
                        for child4 in child3.findall('stationSelectionSpecification'):
                            for child5 in child4.findall('stationSelection'):
                                for child6 in child5.findall('stations'):
                                    for child7 in child6.findall('station'):
                                        for child8 in child7.findall('name'):
                                            #print(child8.tag, child8.attrib)
                                            #print child8.text
                                            if child8.text==station:
                                                child6.remove(child7)
                                                child7.remove(child8)
                                                logger.info(station+' is removed due to maintenance')
    
    for child in root.iter('userName'):
        child.text = username
    for child in root.findall('contactInformation'):
        for child2 in child.findall('name'):
            child2.text = Name
        for child2 in child.findall('email'):
            child2.text = email
        for child2 in child.findall('phoneNumber'):
            child2.text = phoneNumber
        for child2 in child.findall('affiliation'):
            child2.text = Affiliation
    for child in root.findall('projectReference'):
        for child2 in child.findall('ProjectCode'):
            child2.text = ProjectCode
    for child in root.findall('specification'):
        for child2 in child.findall('projectReference'):
            for child3 in child2.findall('ProjectCode'):
                child3.text = ProjectCode
        for child2 in child.iter('container'):
            for child3 in child2.findall('folder'):
                for child4 in child3.findall('name'):
                    if child4.text == "TestOpened_1":
                        child4.text = 'Trig'+str(GRB)
        for child2 in child.findall('activity'):
            for child3 in child2.findall('observation'):
                for child4 in child3.findall('timeWindowSpecification'):
                    for child5 in child4.findall('minStartTime'):
                        child5.text = start
                    for child5 in child4.findall('maxEndTime'):
                        child5.text = end
                    for child5 in child4.findall('duration'):
                        for child6 in child5.findall('duration'):
                            if child6.text == "PT7200S":
                                child6.text="PT"+str(int(maxDur)*60)+"S"
                for child4 in child3.findall('name'):
                    if child4.text == "3C295/1/TO":
                        child4.text=calname+'/1/TO'
                        for child6 in child3.findall('timeWindowSpecification'):
                            for child5 in child6.findall('minStartTime'):
                                child5.text = startCal
                            for child5 in child6.findall('maxEndTime'):
                                child5.text = endCal
                                for child5 in child4.findall('duration'):
                                    for child6 in child5.findall('duration'):
                                        if child6.text == "PT120S":
                                            child6.text="PT"+str(int(CalObsT)*60)+"S"
                for child4 in child3.findall('description'):
                    if child4.text == "3C295/1/TO (Target Observation)":
                        child4.text=calname+'/1/TO (Target Observation)'
        for child2 in child.findall('activity'):
            for child3 in child2.findall('measurement'):
                for child4 in child3.iter('name'):
                    if child4.text == "Target":
 #                       child4.text = 'Trig'+str(GRB)
                        for child5 in child3.findall('ra'):
                            child5.text = str(RA)
                        for child5 in child3.findall('dec'):
                            child5.text = str(Dec)
                    if child4.text == "Calibrator":
 #                       child4.text = calname
                        for child5 in child3.findall('ra'):
                            child5.text = str(CalRA)
                        for child5 in child3.findall('dec'):
                            child5.text = str(CalDec)
                              
    tree.write(str(GRB)+'.xml',xml_declaration=True)
    return str(GRB)+'.xml'

def writeXMLfiles(GRB,time,RA, Dec,calibrator,index):
    if index != 0:
        starttime = time+timedelta(minutes=MinDwell)
        if index == 1:
            start=starttime.strftime("%Y-%m-%dT%H:%M:%S")
            maxDur = ObsMax
            endtime =  starttime+timedelta(minutes=maxDur)
            end = endtime.strftime("%Y-%m-%dT%H:%M:%S")
        elif index == 2:
            start=starttime.strftime("%Y-%m-%dT%H:%M:%S")
            maxDur = ObsMin
            endtime =  starttime+timedelta(minutes=maxDur)
            end = endtime.strftime("%Y-%m-%dT%H:%M:%S")
        elif index == 3:
            starttime=starttime+timedelta(seconds=MaxDwell*60.)
            start=starttime.strftime("%Y-%m-%dT%H:%M:%S")
            maxDur = ObsMax
            endtime =  starttime+timedelta(minutes=maxDur)
            end = endtime.strftime("%Y-%m-%dT%H:%M:%S")
        elif index == 4:
            starttime=starttime+timedelta(seconds=MaxDwell*60.)
            start=starttime.strftime("%Y-%m-%dT%H:%M:%S")
            maxDur = ObsMin
            endtime =  starttime+timedelta(minutes=maxDur)
            end = endtime.strftime("%Y-%m-%dT%H:%M:%S")

        startCal = endtime+timedelta(minutes=2.)
        startCal = startCal.strftime("%Y-%m-%dT%H:%M:%S")
        endCaltmp = endtime+timedelta(minutes=20.)
        endCal = endCaltmp.strftime("%Y-%m-%dT%H:%M:%S")
        stations = check_LOFAR_maintenance(starttime,endCaltmp)
        xmlname = generateXML(GRB,RA,Dec,calibrator['CalRA'],calibrator['CalDec'],start,maxDur,ObsMin,end,calibrator['Calibrators'],startCal,endCal,stations)
        return xmlname

#test generateXML
#generateXML(123.4,56.7,10.2,45.3,"2018-11-23T15:21:44","7200","720")

def sendXMLtoLOFAR(xmlname): # code received from Auke last year, needs updating...
    os.system("echo curl --insecure --data-binary @"+xmlname+" --netrc 'https://proxy.lofar.eu/rtrest/triggers/?format=json'")
    os.system("curl --insecure --data-binary @"+xmlname+" --netrc 'https://proxy.lofar.eu/rtrest/triggers/?format=json'")

def check_LOFAR_maintenance(start,end):
    start=start.strftime("%Y-%m-%d %H:%M:%S")
    end=end.strftime("%Y-%m-%d %H:%M:%S")
    stations=lofar_maintenance.getMaintenance(start,end)
    return stations

    
if __name__ == '__main__':
    sys.exit(main())
