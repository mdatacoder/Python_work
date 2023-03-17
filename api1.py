import sys
import requests
import json
import logging
import time
import pandas as pd
from tqdm import tqdm
import numpy as np
import os

USER = os.getcwd().split('\\')[2]
OUTPUTS_PATH = fr"C:\Users\{USER}\{path here}"

logging.captureWarnings(True)

# good to define the URLs up here so they can be changed easily
scheme = "https://"
host = "enter the api.name_here"
basePathcontrol_one = "/base/control_one/v1/"
basePathcontrol_two = "/base/control_two/v1/"
basePathcontrol_three = "/base/control_three/v1/"

# auth URLs and data
auth_server_url = 'url to connect for token'
client_id = 'add id here'.encode('utf-8')
client_secret = 'add secret here'.encode('utf-8')  # password
# password

max_token_retries = 5  # max number of times to ask for a token

# harvest year of interest
year_start = "2022"
site_key_of_interest = 0


##
##    function to obtain a new OAuth 2.0 token from the authentication server
##
def get_new_token():
    # this first bit is us giving information so we can get a token (imagine a coin to use a pay phone)
    # similaraly to the payphone exampe, the token has an expiry but you would need to check with every new site you go to

    token_req_payload = {'grant_type': 'client_credentials'}
    # conect to the server, add the req payload (asking what we want) then give our credentials
    token_response = requests.post(auth_server_url,
                                   data=token_req_payload, verify=False, allow_redirects=False,
                                   auth=(client_id, client_secret))
    # if response is not 200 then we did not succeed
    if token_response.status_code != 200:
        print("Failed to obtain token from the OAuth 2.0 server", file=sys.stderr)
        sys.exit(1)
    # if we did succeed we now have a token to use to access muddyboots
    print("Successfuly obtained a new token")
    tokens = json.loads(token_response.text)
    return tokens['access_token']  # this is just referencing the token number within the dict
    ## END OF FUNCTION ~~
def fetch_data(basePath, query,token):  # pass the basePath - the endpoint of interest, your query to perform and the auth token.
    # build query URL
    url = scheme + host + basePath + query
    # print(url)
    ##  call the API with the token
    api_call_headers = {'Authorization': 'Bearer ' + token}
    api_call_response = requests.get(url, headers=api_call_headers, verify=False)

    if api_call_response.status_code == 429:
        time.sleep(1)
        api_call_response = requests.get(url, headers=api_call_headers, verify=False)

    token_tries = 0
    while (
            token_tries < max_token_retries):  # only hit the auth endpoint a few times if its not responding to our request
        if api_call_response.status_code == 401:  # token has expired, get a new token
            token = get_new_token()
            time.sleep(1)  # sleep before trying again
            token_tries += 1  # increments by 1
        else:
            # api call ahs been successful, retun the response
            # print(api_call_response.text)
            return api_call_response
    # if we get here then there is no point to continue so exit the program
    print("Token expired and failed to obtain a new token from the OAuth 2.0 server", file=sys.stderr)
    sys.exit(1)
def fetch_ferts(query, token):
    list_of_ferts = fetch_data(basePathcontrol_one, query, token).json()['content']
    for fert in list_of_ferts:
        if fert['fertApplications']:  # if we have some fert apps, print out
            for fert_product in fert['fertApplications']:
                fert_product_info = fetch_data(basePathcontrol_three, 'ferts/' + fert_product['productKey'], token).json()[
                    'content']
                list_of_ferts[0].copy().update(fert_product_info.copy()[0])

        # loop through each organic matter applied as part of this fert activity
        if fert['organicMatterApplications']:  # if we have organic matter apps, step through
            for organic_product in (fert['organicMatterApplications']):
                organic_matter_info = \
                fetch_data(basePathcontrol_three, 'organicmatter/' + organic_product['productKey'], token).json()['content']
                list_of_ferts[0].copy().update(organic_matter_info.copy()[0])
        return list_of_ferts.copy()
def fetch_spray(query, token):
    list_of_sprays = fetch_data(basePathcontrol_one, query, token).json()['content']
    for spray in list_of_sprays:
        for application in spray['applications']:
            spray_product_info = \
            fetch_data(basePathcontrol_three, 'cropprotection/' + application['productKey'], token).json()['content']
            list_of_sprays[0].copy().update(spray_product_info[0].copy())
    return list_of_sprays.copy()
def fetch_product(query, token):
    product_name = fetch_data(basePathcontrol_three, query, token).json()['content']
    return product_name
def get_field_name(key, token):
    query = "fields/" + key
    field_data = fetch_data(basePathcontrol_two, query, token)

    if field_data:
        return field_data.json()['content'][0]['name']
    else:
        return 0


if __name__ == "__main__":

    ## obtain a token before calling the API for the first time
    # token = get_new_token()
    # added the try / except for use in jupyter where we might not need to keep getting a token
    try:
        token
    except NameError:
        token = get_new_token()

    # grab the site data from the sites endpoint, if a site is specified at top of code then fetch just that one
    if (site_key_of_interest != 0):
        query = "sites/" + site_key_of_interest
    else:
        query = "sites/"
    sites = fetch_data(basePathcontrol_two, query, token)
    list_of_sites = sites.json()['content']

    # now we loop through each site and pull out the field information for each
    full_list_fields = {}
    for site in tqdm(list_of_sites):
        if site['name'] not in ['test','Test']:
            individual_crop_full_list = []
            token = get_new_token()
            site_name = site['name']
            site_uuid = site['key']
            #########  CROPS #########

            # hit the api to get the crops for our site
            site_crops_query = "crops/?sitekey=" + site_uuid + "&harvestyear=" + str(year_start)

            try:
                list_of_crops = fetch_data(basePathcontrol_two, site_crops_query, token).json()['content']
            except KeyError:
                list_of_crops = fetch_data(basePathcontrol_two, site_crops_query, token).json()
            # else:
            #    list_of_crops = []

            if len(list_of_crops) > 0:
                if type(list_of_crops) == dict:
                    list_of_crops = [list_of_crops]
                # looping through the crops
                for crop in list_of_crops:
                    crop_info = {"cropType": crop['cropType']
                        , "variety": crop['variety']
                        , "area" + str(crop['area']['unit']): crop['area']['value']
                        , 'HarvestYear': year_start
                        , 'FieldUuid': crop['fieldKey']
                        , 'FieldName': get_field_name(crop['fieldKey'], token)
                                 }

                    if crop['cropType'] in ["W Wheat"]:

                        # hit the api to get the fert control_one for our crop and harvest year
                        crop_fert_query = "fert?harvestYear=" + year_start + "&cropKey=" + crop['key']
                        print(crop_fert_query)

                        try:
                            crop_fert_result = fetch_ferts(crop_fert_query, token)
                            if crop_fert_result != []:
                                if type(crop_fert_result) == dict:
                                    crop_fert_result = [crop_fert_result]
                                try:
                                    for product in range(len(crop_fert_result)):
                                        try:
                                            fert_more = fetch_product(
                                                "ferts/" + crop_fert_result[product]['fertApplications'][0]['productKey'],
                                                token)[0]
        
        
                                        except IndexError:
                                            fert_more = fetch_product(
                                                "ferts/" + crop_fert_result[product]['organicMatterApplications'][0][
                                                    'productKey'], token)[0]
                                        crop_fert_result[product]['productName'] = str(fert_more['name'])
                                        crop_fert_result[product]['productManufacturer'] = str(fert_more["manufacturer"])
                                except TypeError:
                                    crop_fert_result = {'none'}
                            else:
                                crop_fert_result = {'none'}
                        except KeyError:
                            # this is to capture KeyError: 'content'
                            crop_fert_result = {'none'}
                        
                        #########   SPRAY control_one  #######

                        # hit the api to get the spray control_one for our crop and harvest year
                        crop_spray_query = "spray?harvestYear=" + year_start + "&cropKey=" + crop['key']
                        print(crop_spray_query)

                        try:
                            crop_spray_result = fetch_spray(crop_spray_query, token)
                            if crop_spray_result != []:
                                if type(crop_spray_result) == dict:
                                    crop_spray_result = [crop_spray_result]
                                try:
                                    for product in range(len(crop_spray_result)):
                                        spray_more = fetch_product(
                                            "cropprotection/" + crop_spray_result[product]['applications'][0]['productKey'],
                                            token)[0]
                                        crop_spray_result[product]['productName'] = str(spray_more["name"])
                                        crop_spray_result[product]['productManufacturer'] = str(spray_more["manufacturer"])
                                        crop_spray_result[product]['productType'] = str(spray_more["classification"])
                                except TypeError:
                                    crop_spray_result = {'none'}
                            else:
                                crop_spray_result = {'none'}
                        except KeyError:
                            crop_spray_result = {'none'}
                        
                        
                        
                        #########   CONCAT ALTOGETHER  #######
                        crop_info['fertilisers'] = crop_fert_result
                        crop_info['sprays'] = crop_spray_result
                        individual_crop_full_list.append(crop_info)
                    else:
                        pass

            else:
                pass

            full_list_fields[str(site_name)] = individual_crop_full_list
        else:
            pass


print(full_list_fields.keys())

def flatten_json(self):
    out = {}
    def flatten(self, name=''):
        if type(self) is dict:
            for a in self:
                flatten(self[a], name + a + '_')
        elif type(self) is list:
            i = 0
            for a in self:
                i += 1
                flatten(a, name + str(i) + '_')
        else:
            out[name[:-1]] = x
    flatten(self)
    return out
def single_line_dict(self, key):
    df = pd.DataFrame([self[key]])
    #df.columns = df.columns.str.split('ns0:').str[1]
    df = df[sorted(df)]
    return df
def get_dfs(self, key, index=None):
    try:
        a = single_line_dict(self,key)
    except AttributeError:
        a = multi_line_dict(self,key)
    return a
def without_keys(d, keys):
    return {x: d[x] for x in d if x not in keys}
def convert_into_df(dict, invalid=None):
    if invalid:
        df = pd.DataFrame([without_keys(dict, invalid)]) #DONE
    else:
        df = pd.DataFrame([dict])
    df.columns = df.columns.str.replace('ns0:','')
    return df
def pull_fert_app (self,keyword):
    a = convert_into_df(self[keyword][0],{'productRate','nutrients'})
    b = convert_into_df(self[keyword][0]['productRate']).rename(columns={'value':'application rate kg/ha'})['application rate kg/ha']
    if len(self[keyword][0]['nutrients']) >=1:
        c = pd.DataFrame(self[keyword][0]['nutrients']).transpose().reset_index(drop=True)
        c.columns = c.iloc[0]
        c = c.iloc[1:].reset_index(drop=True)
        out = a.join([b,c])
    else:
        out = a.join([b,pd.DataFrame([{'nutrients':np.nan}])])
    return out

# convert JSON into dataframe
fieldList = []
for farm_name in tqdm(full_list_fields.keys()):
    field = pd.DataFrame([{'farm': farm_name}])
    cropList = []
    for cropNo in tqdm(range(len(full_list_fields[farm_name]))):
        cropDict = full_list_fields[farm_name][cropNo]
        crop = convert_into_df(cropDict, invalid={'fertilisers', 'sprays'}).reset_index(drop=True)
        crop.columns = 'crop_' + crop.columns
        try:
            if type(cropDict['fertilisers']) == dict:
                fertList = [cropDict['fertilisers']]
            else:
                fertList = cropDict['fertilisers']

            # we need an exception as some fertilisers pull through as None and a Json will automatically read as empty
            if fertList != {'none'}:
                fertAll = []
                for fertNo in range(len(fertList)):
                    fertDict = fertList[fertNo]
                    fertDict['area' + str(fertDict['area']['unit'])] = fertDict['area']['value']
                    fert = convert_into_df(fertDict,
                                           invalid={'fertApplications', 'organicMatterApplications'}).reset_index(
                        drop=True)
                    fert.columns = 'fert_' + fert.columns
                    fert.rename(columns={'fert_activityType': 'activityType'}, inplace=True)
                    if fertDict['organicMatterApplications'] == []:
                        key = 'fertApplications'
                    else:
                        key = 'organicMatterApplications'
                    new = pull_fert_app(fertDict, key).reset_index(drop=True)
                    new.columns = 'fert_app_' + new.columns
                    ferts_all = field.join([crop, fert, new])
                    fertAll.append(ferts_all)
            else:
                fertAll = []
        except NameError:
            fertAll = []
        try:
            if type(cropDict['sprays']) == dict:
                sprayList = [cropDict['sprays']]
            else:
                sprayList = cropDict['sprays']
                # we need an exception as some spray pull through as None and a Json will automatically read as empty
            if sprayList != {'none'}:
                sprayAll = []
                for sprayNo in range(len(sprayList)):
                    sprayDict = sprayList[sprayNo]
                    sprayDict['area' + str(sprayDict['area']['unit'])] = sprayDict['area']['value']
                    spray = convert_into_df(sprayDict, invalid={'applications'}).reset_index(drop=True)
                    spray.columns = 'spray_' + spray.columns
                    spray.rename(columns={'spray_activityType': 'activityType'}, inplace=True)

                    if type(sprayDict['applications']) == dict:
                        appList = [sprayDict['applications']]
                    else:
                        appList = sprayDict['applications']
                    for appNo in range(len(appList)):
                        appDict = appList[appNo]
                        appDict['productRate_' + str(appDict['productRate']['unitKey']) + '/ha'] = \
                        appDict['productRate']['value']
                        key = 'applications'
                        new = convert_into_df(appDict).reset_index(drop=True)
                        new.columns = 'spray_app_' + new.columns
                        sprays_all = field.join([crop, spray, new])
                        sprayAll.append(sprays_all)
            else:
                sprayAll = []
        except NameError:
            sprayAll = []

        if (fertAll != []) & (sprayAll != []):
            overlap = pd.concat(fertAll).loc[:,
                      pd.concat(fertAll).columns.str.contains('^crop_|^farm', regex=True)].columns.tolist()
            cropList.append(
                pd.merge(pd.concat(fertAll), pd.concat(sprayAll), on=['activityType'] + overlap, how='outer'))
        elif fertAll != []:
            cropList.append(pd.concat(fertAll))
        elif sprayAll != []:
            cropList.append(pd.concat(sprayAll))
        else:
            cropList.append(field.join([crop]))
    try:
        fieldList.append(pd.concat(cropList))
    except:
        pass
out = pd.concat(fieldList)
