import requests
import json

auth_url = "https://home.nest.com/login/oauth2?client_id=243d5e17-9056-4055-b112-4dd546236232&state=STATE"
token_url = "https://api.home.nest.com/oauth2/access_token"
base_url = "https://developer-api.nest.com"

client_id = "243d5e17-9056-4055-b112-4dd546236232"
client_secret = "4Zelj78J51x7VUUwYgDM0vPq6"
access_code = "HYSN4MG5"
grant_type = "authorization_code"

payload = "client_id=" + client_id + "&client_secret=" + client_secret + "&grant_type=" + grant_type + "&code=" + access_code

headers = {
    'Content-Type': "application/x-www-form-urlencoded",
    'Cache-Control': "no-cache"
    }

response = requests.request("POST", token_url, data=payload, headers=headers)

# This should be a case like statement to be more precise than just exiting.
# Should look at making this a function.
if response.status_code == 400:
    print("Unable to connect to the Nest service.  Response was: ", response.status_code, " : ",
          response.json()["error"], " -> ", response.json()["error_description"])
    exit(-1)
elif response.status_code == 401:
    print("Not authorized")
    print("Returned text was: ",response.json())
    exit(-1)

else:
    print("Connected to Nest account.  Returned response code was", response.status_code)
    print("Returned text was: ",response.json())

access_token = "Bearer " + response.json()["access_token"]
token_expires = response.json()["expires_in"]

print("acess token = ",access_token)
print("Token expires in: ",token_expires)

#retrive the full information from the structure

headers = {
    'Content-Type': "application/json",
    'Authorization': "Bearer c.12EQuKMcT1HML0mPaUAriyo46XSIUIqtURo6Tca64d2w23Brvy0Kpagxod2kZ14SS8tGmRDazggifx6ir1XoECLzlRDKHwdP1j99lvvHCZXDPTHptMyjDPqKQ13qLigoK5J79TBaCD3L4EW9",
    'Cache-Control': "no-cache"
    }

# headers = {
    # 'Content-Type': "application/json",
    # 'Authorization': access_token,
    # 'Cache-Control': "no-cache",
    # 'Postman-Token': "9b6e5ef9-1711-ca91-f888-2aa3932b9136"
    # }
response = requests.request("GET", base_url, headers=headers)
if response.status_code != 200:
    print("Unable to connect to the Nest api service.  Exiting.")
    print("Unable to connect to the Nest service.  Response was: ", response.status_code, " : ",
          response.json())
    exit(-1)
else:
    print("Connected to developer API account.  Returned response code was", response.status_code)
    print(response.text)

res = response.json()
print(json.dumps(res, indent=3))

