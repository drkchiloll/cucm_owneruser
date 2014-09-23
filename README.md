#######################################################
OwnerUserName Updating Utility for CUCM 9.x and Higher
======================================================
#######################################################
REQUIREMENTS:
#################
Python 2.7
LXML Library
REQUESTS Library
#################
Problem to Solve:

Reconciliation of Licensing changes in CUCM 9.x and above. The OwnerUserName needs to be populated for all Devices (at least as many as possible) to use less licenses and/or use the approrpriate level of licenses. In previous versions of CUCM, this particular field on the Device was not necessarily "required" in order to operate effectively, but in newer versions of CUCM all Licensing quantities will be calculated off this particular field on Devices.

Refer to Cisco Live Session BRKUCC-2011 for this problem. Please Note that Cisco does have a potential solution to this problem that is due out by the end of Q4 CY2014.
#################
Running the Application:

Running the utility from Terminal and/or Windows CLI:
python <scriptname>.py
###########################################################
By default, this Application finds all the users on the CUCM using the User Data Service API (we could use AXL for this but UDS uses REST and has less overhead with better built in data throttling). As users are found, we then use AXL to query the user for controlled devices; if the user has devices he/she controls these devices are "written" into a List.

Once the List of all Users is defined, AXL is used once again to getPhone (we have the device (name) for the phone) to check to see if an OwnerUserName is populated for the Device.

IF OwnerUser exists on Device:
	Check the Name:
	IF the Name is the Same as the Name you are On Now
		MOVE On
	IF the Name is Different
		Ask if you want to change the current value [val] to new [val]
ELSE:
	Configure the Device with the User who controls the Device

[The Configuration of the Device requires the updatePhone AXL method]

Previously, if a User is found that doesn't have a Controlled Device, this is logged in a file [log_YYYY-MM-DD]

Along with this Default Method of updating the OwnerUser Field, you can use an Exclusion File that is packaged with these files. You can and should filter on UserNames (admins such as myself tend to "control all devices" and that user could potentially overwrite OwnerUser's of the actual Device Owner). You can also exclude Devices in specific Device Pools as well. Below is example file format:

samwomack
DP_HQ
DP_Columbia

The safest method of Updating Phones/Devices with an ownerUserName is using a CSV file (save as: MS-DOS(csv) in Windows Excel and Windows Comma Separated (csv) in Excel for Mac). If necessary I could create a tool that performs the default above to populate a csv file with Device Name and UserId. Below is the acceptible format for the CSV file:

Device_Name,OwnerUserName
SEP001122334455,samwomack
################################################################