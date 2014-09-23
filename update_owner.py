##################################################
#Check for CSV File for Manual Update of Record
###########
#Gets UserIds via UDS API, Gets Users Assoc. Devices
#Updates Phones with UserId's in OwnerUserId Field
#Additions:
###########
#GetPhone Description so you know more about the 
#Device You are Making Mods to
###########
#Checking to See if there is a Current Value for
#OwnerUser, If it is the same then Move On
#If Different, Ask to Overwrite
###########
#Use Exclusivity File to Skip Over Certain Users
#Or Skip over Device Pools
##################################################
from lxml import etree
from lxml.etree import tostring
import requests
import sys
from datetime import datetime
from getpass import getpass
import time
global url,num,axlurl,userDict,header
userDict = {}
num = 0
#ip = '10.10.1.100'
ip = raw_input('What is the IP/Hostname of your CUCM? $')
max_count = 6
url = 'https://%s:8443/cucm-uds/users?last=&max=%s' % (ip,max_count)
axlurl = 'https://%s:8443/axl/' % ip
header = {
          'Content-type' : 'text/xml',
          'SOAPAction' : 'CUCM:DB ver=9.1',
         }

def csoapd(func):
    env_nsuri = 'http://schemas.xmlsoap.org/soap/envelope/'
    axl_nsuri = 'http://www.cisco.com/AXL/API/9.1'
    env_ns = '{%s}' % env_nsuri
    axl_ns = '{%s}' % axl_nsuri
    nmap = {'soapenv' : env_nsuri,
            'ns' : axl_nsuri
            }
    soapd = etree.Element(env_ns+'Envelope',nsmap=nmap)
    body_e = etree.SubElement(soapd, env_ns+'Body')
    if func:
        ph_e = etree.SubElement(body_e,axl_ns+func)
        name_e = etree.SubElement(ph_e, 'name')
        if func == 'getPhone':
            retag_e = etree.SubElement(ph_e,'returnedTags')
            dp_e = etree.SubElement(retag_e,'devicePoolName')
            des_e = etree.SubElement(retag_e,'description')
            ownu_e = etree.SubElement(retag_e, 'ownerUserName')
            return soapd,name_e,ownu_e
        else:
            ownu_e = etree.SubElement(ph_e, 'ownerUserName')
            return soapd,name_e,ownu_e  
    return soapd,body_e,axl_ns    

def getUserReq(u):
    soapd,body_e,axl_ns = csoapd(None)
    getu_e = etree.SubElement(body_e, axl_ns+'getUser')
    uid_e = etree.SubElement(getu_e, 'userid')
    uid_e.text = u
    asdev_e = etree.SubElement(getu_e, 'associatedDevices')
    dev_e = etree.SubElement(asdev_e, 'device')
    return soapd

def getUserResp(d):
    global user,pwd
    devlist = []
    r2 = requests.post(axlurl,verify=False,data=d,auth=(user,pwd))
    while r2.status_code == 401:
        print 'Bad UserName and/or Password.'
        user = raw_input('Please enter your username $')
        pwd = getpass('Please enter your password $')
        r2 = requests.post(axlurl,verify=False,data=d,auth=(user,pwd))
        continue
    respdoc = etree.XML(r2.content)
    dev_tnode = etree.XPath('//device/text()')
    dev_tnode = dev_tnode(respdoc)
    for dev in dev_tnode:
        devlist.append(dev)
    #print devlist
    return devlist

def listDevs(u):
    reqDoc = getUserReq(u)
    devlist = getUserResp(etree.tostring(reqDoc))
    return devlist

def parseUsers(doc):
    global num,totUsers
    ucount = 0
    userElem = etree.XPath('//user/userName')
    if userElem(doc):
        for userId in userElem(doc):
            devlist = listDevs(userId.text)
            ucount += 1
            totUsers -= 1
            if not devlist:
                #Log users who don't have an Associated Device
                logfile = open('log_'+str(datetime.now().date()), 'a')
                logfile.write(str(datetime.now()) + ' %s ' % userId)
                logfile.write('does not have an associated device\n')
                logfile.close()
                if ucount == max_count:
                    num += max_count
                    return True
                continue
            else:
                userDict[userId.text] = devlist
            if ucount == max_count:
                num += max_count
                return True
    else:
        return False

def submitReq(d,func):
    data = etree.tostring(d,pretty_print=True)
    r = requests.post(axlurl,data=data,headers=header,verify=False,auth=(user,pwd))
    #print etree.tostring(etree.XML(r.content),pretty_print=True)
    if func:
        dp_name = etree.XPath('//devicePoolName/text()')
        desc = etree.XPath('//description/text()')
        oun = etree.XPath('//ownerUserName/text()')
        try:
            oun = oun(etree.XML(r.content))[0]
        except IndexError:
            oun = ''
        try:
            dp_name = dp_name(etree.XML(r.content))[0]
        except IndexError:
            return ''
        try:
            desc = desc(etree.XML(r.content))[0]
            return oun,dp_name,desc
        except IndexError:
            return None
    return r.status_code

def updatePhones(uid,d,n,o,exlist):
    #print etree.tostring(d,pretty_print=True)
    dlist = userDict[uid]
    #print dlist
    for dev in dlist:
        n.text = dev
        ex_uid,dp_name,desc = submitReq(d,'getPhone')
        print 'Verifying configuration of %s with description %s.' % (dev,desc)
        if dp_name in exlist:
            print '%s device pool is being excluded, skipping to the next device.' % dp_name
            logfile = open('log_'+str(datetime.now().date()), 'a')
            logfile.write(str(datetime.now())+' %s\'s devicepool %s has been excluded.\n' % (desc,dp_name))
            logfile.close()
            continue
        if ex_uid:
            if ex_uid != uid:
                print '%s\'s owner user is %s.' % (dev, ex_uid)
                print 'The UserName you want to apply is %s.' % uid
                resp = raw_input('Would you like to overwrite the existing value? Y/N$')
                if 'y' in resp.lower():
                    d = csoapd('updatePhone')
                else:
                    print 'Keeping the value as is.'
                    continue
            else:
                print '%s is already configured with: %s' % (dev, ex_uid)
                time.sleep(2)
                continue
        print 'Applying %s as the owner userName' % uid,
        print 'for device with name %s and description %s.' % (dev,desc)
        upd,nm_e,oun_e = csoapd('updatePhone')
        nm_e.text = dev
        oun_e.text = uid
        #print etree.tostring(upd,pretty_print=True)
        result = submitReq(upd,None)
        if result == requests.codes.ok:
            print '%s was updated successfully.' % dev
        else:
            print 'Something went wrong.'

def processData():
    d,name_e,ownu_e = csoapd('getPhone')
    try:
        excl_list = open('exclusionlist.txt','r').read().split('\n')
    except IOError:
        excl_list = 'FileNotFound'
    for userId in userDict:
        if userId in excl_list:
            print '%s has been excluded.' % userId
            continue
        updatePhones(userId,d,name_e,ownu_e,excl_list)

def main():
    #Main Function
    global user, pwd
    user = raw_input('Enter your username $')
    pwd = getpass('Enter your password $')
    #######################################################
    use_file = raw_input('Do you want to use a CSV File y/n? $')
    if 'y' in use_file.lower():
        try:
            input_csv = open('updatePhone.csv','rb')
            updph_csv = input_csv.read()
            updph_csv = updph_csv.split('\r\n')
            updph_csv.remove(updph_csv[0])
            print updph_csv
            if updph_csv:
                for devuser in updph_csv:
                    if devuser:
                        soapd,name_e,ownu_e = csoapd('updatePhone')
                        du_list = devuser.split(',')
                        name_e.text = du_list[0]
                        ownu_e.text = du_list[1]
                        result = submitReq(soapd,None)
                        while result == 401:
                            print 'Bad UserName and/or Password.'
                            user = raw_input('Please enter your username $')
                            pwd = getpass('Please enter your password $')
                            result = submitReq(soapd,None)
                            continue
                        if result == requests.codes.ok:
                            print '%s was updated with %s username.' % (du_list[0],du_list[1])
                    else:
                        sys.exit(0)                   
            else:
                print 'Manual File Procedure Not Used.'
        except IOError:
            print 'Update Phone CSV File Not Found.'
            cont = raw_input('Do you wish to continue? y/n $')
            if 'n' in cont:
                sys.exit(0)
    else:
        #######################################################
        global totUsers
        totu_url = 'https://%s:8443/cucm-uds/users?&max=0' % ip
        r = requests.get(totu_url,verify=False,auth=(user,pwd))
        totUsers = int((etree.XPath('//users/@totalCount'))(etree.XML(r.content))[0])
        print 'There are %d total users on this system.' % totUsers
        while(totUsers is not 0):
            start_query = '&start=%s' % str(num)
            r = requests.get(url+start_query, verify=False, auth=(user,pwd))
            parseUsers(etree.XML(r.content))
        processData()

if __name__ == '__main__':
  main()