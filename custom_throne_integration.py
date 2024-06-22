import requests
import re as regex
from dateutil import parser
from datetime import datetime
import time

startAlert = "\"overlayInformation\":"
startWishlist = "\"paymentConfiguration\":"
fieldName = "\s*\"([^\"]+)\":"
fieldValue = "\s*\"stringValue\":\s*\"(.*)\"$"
createTime = "\"createTime\":\s*\"([^\"]+)\""

def getData(throneId, callback1, callback2):
    r = requests.post("https://firestore.googleapis.com/google.firestore.v1.Firestore/Listen/channel?VER=8&database=projects%2Fonlywish-9d17b%2Fdatabases%2F(default)&RID=86337&CVER=22&X-HTTP-Session-Id=gsessionid&zx=pwfobapf7prw&t=1", data="headers=X-Goog-Api-Client%3Agl-js%2F%20fire%2F9.13.0%0D%0AContent-Type%3Atext%2Fplain%0D%0AX-Firebase-GMPID%3A1%3A889136776977%3Aweb%3Accd737342a13c67cc3aeb0%0D%0A&count=3&ofs=0&req0___data__=%7B%22database%22%3A%22projects%2Fonlywish-9d17b%2Fdatabases%2F(default)%22%2C%22addTarget%22%3A%7B%22query%22%3A%7B%22structuredQuery%22%3A%7B%22from%22%3A%5B%7B%22collectionId%22%3A%22wishlistItems%22%7D%5D%2C%22orderBy%22%3A%5B%7B%22field%22%3A%7B%22fieldPath%22%3A%22__name__%22%7D%2C%22direction%22%3A%22ASCENDING%22%7D%5D%7D%2C%22parent%22%3A%22projects%2Fonlywish-9d17b%2Fdatabases%2F(default)%2Fdocuments%2Fcreators%2F" + throneId + "%22%7D%2C%22targetId%22%3A2%7D%7D&req1___data__=%7B%22database%22%3A%22projects%2Fonlywish-9d17b%2Fdatabases%2F(default)%22%2C%22addTarget%22%3A%7B%22documents%22%3A%7B%22documents%22%3A%5B%22projects%2Fonlywish-9d17b%2Fdatabases%2F(default)%2Fdocuments%2Fintegrations%2F" + throneId + "%2FprovidersPublic%2Fstream-alerts-browser-source%22%5D%7D%2C%22targetId%22%3A6%7D%7D&req2___data__=%7B%22database%22%3A%22projects%2Fonlywish-9d17b%2Fdatabases%2F(default)%22%2C%22addTarget%22%3A%7B%22query%22%3A%7B%22structuredQuery%22%3A%7B%22from%22%3A%5B%7B%22collectionId%22%3A%22overlays%22%7D%5D%2C%22where%22%3A%7B%22fieldFilter%22%3A%7B%22field%22%3A%7B%22fieldPath%22%3A%22creatorId%22%7D%2C%22op%22%3A%22EQUAL%22%2C%22value%22%3A%7B%22stringValue%22%3A%22" + throneId + "%22%7D%7D%7D%2C%22orderBy%22%3A%5B%7B%22field%22%3A%7B%22fieldPath%22%3A%22createdAt%22%7D%2C%22direction%22%3A%22DESCENDING%22%7D%2C%7B%22field%22%3A%7B%22fieldPath%22%3A%22__name__%22%7D%2C%22direction%22%3A%22DESCENDING%22%7D%5D%2C%22limit%22%3A1%7D%2C%22parent%22%3A%22projects%2Fonlywish-9d17b%2Fdatabases%2F(default)%2Fdocuments%22%7D%2C%22targetId%22%3A10%7D%7D")
    #print(r)
    #print(r.headers)
    #print(r.text)
    r.raise_for_status()
    sessionId = r.headers['X-HTTP-Session-Id']
    SID = regex.search("\"c\",\"([^\"]+)\"", r.text).group(1)
    s = requests.Session()
    r2 = s.get("https://firestore.googleapis.com/google.firestore.v1.Firestore/Listen/channel?gsessionid=" + sessionId + "&VER=8&database=projects%2Fonlywish-9d17b%2Fdatabases%2F(default)&RID=rpc&SID=" + SID + "&CI=0&AID=11&TYPE=json&zx=xamtgicjdy1d&t=1", stream=True)
    currentData = {}
    prevLine = ""
    for line in r2.iter_lines():
        string = line.decode("utf-8")
        #print(string)
        if startAlert in string:
            currentData["alert"] = True
        if startWishlist in string:
            currentData["wishlist"] = True
        if regex.search(fieldValue, string):
            m1 = regex.search(fieldName, prevLine)
            m2 = regex.search(fieldValue, string)
            if m1 and m2:
                name = m1.group(1)
                value = m2.group(1)
                currentData[name] = value
        if regex.search(createTime, string):
            stringTime = regex.search(createTime, string).group(1)
            t = parser.parse(stringTime).timestamp()
            currentData["time"] = t
        if string.startswith("]"): # messages end with ]] and some numbers
            if currentData.get("alert"):
                onUpdate(currentData, callback1)
            if currentData.get("wishlist"):
                onUpdate(currentData, callback2)
            currentData = {}
        prevLine = string
    #print(r2)
    r2.raise_for_status()

lastTime = datetime.now().timestamp()
def onUpdate(item, callback):
    global lastTime
    # skip old things that are re-sent
    t = item["time"]
    if t <= lastTime:
        #print("skipping")
        return
    lastTime = t
    #print(dono)
    callback(item)

def watchThrone(username, donoCallback, wishlistCallback):
    r = requests.get("https://throne.com/_next/data/8hxxEUYo7kjl5wy3584Xs/" + username + ".json?slug=" + username)
    userId = regex.search("\"_id\":\s*\"([^\"]+)\"", r.text).group(1)
    delay = 0
    while True:
        try:
            getData(userId, donoCallback, wishlistCallback)
            delay = 0
        except Exception as e:
            print(e)
            # retry with exponential backoff
            if delay == 0:
                delay = 30
            else:
                delay *= 2
        if delay > 0:
            print("waiting", delay, "seconds before reconnecting to throne")
            time.sleep(delay)

