
import pandas as pd
import numpy as np
import os
import json
import re
import requests
from tqdm import tqdm
import jaro
import sys
from toolbox.processing_functions import find_columns


def custom_ingreds_field(self, number):
    if self['fertiliser_custom_ingreedients_' + number].item() == 'True':
        custom_ingreds_self = {'n_total_percentage': np.array(self['fertiliser_custom_ingreedients_n_total2_percentage_' + number].round(3)).tolist()[0]
            , 'n_ammonia_percentage'   : np.array(self['fertiliser_custom_ingreedients_n_ammonia_percentage_' + number].round(3)).tolist()[0]
            , 'n_nitric_percentage'    : np.array(self['fertiliser_custom_ingreedients_n_nitric_percentage_' + number].round(3)).tolist()[0]
            , 'n_urea_percentage'      : np.array(self['fertiliser_custom_ingreedients_n_urea_percentage_' + number].round(3)).tolist()[0]
            , 'p2o5_percentage'        : np.array(self['fertiliser_custom_ingreedients_p2o5_percentage_' + number].round(3)).tolist()[0]
            , 'p2o5_percentage_type_id': np.array(self['fertiliser_custom_ingreedients_p2o5_percentage_type_id_' + number].fillna(0).astype(int)).tolist()[0]
            , 'k2o_percentage'         : np.array(self['fertiliser_custom_ingreedients_k2o_percentage_' + number].round(3)).tolist()[0]
            , 'k2o_percentage_type_id' : np.array(self['fertiliser_custom_ingreedients_k2o_percentage_type_id_' + number].fillna(0).astype(int)).tolist()[0]}
    else:
        custom_ingreds_self = {}
    return custom_ingreds_self

def loop_through_farms_JSON (self):
    json_all_farms = []
    for farm_id, data in self.groupby('farm_identifier'):
        # __________________________________
        farm = {}
        farm['country'] = np.array(data['farm_country']).tolist()[0]
        farm['territory'] = np.array(data['farm_territory']).tolist()[0]
        farm['climate'] = np.array(data['farm_climate']).tolist()[0]
        farm['average_temperature'] = {'value': np.array(data['farm_average_temperature_value'].astype(int)).tolist()[0]
            , 'unit': np.array(data['farm_average_temperature_unit']).tolist()[0]}  # if not use 5 to mean degrees celcius
        farm['farm_identifier'] = farm_id
        # __________________________________
        # __________________________________
        crop = {}
        crop['type'] = np.array(data['crop_type']).tolist()[0]
        crop['field_size'] = {'value': np.array(data['crop_field_size_value']).tolist()[0]
            , 'unit': np.array(data['crop_field_size_unit']).tolist()[0]}
        if data['crop_soil_organic_matter'].item() == 5:
            crop['soil'] = {'texture_id': np.array(data['crop_soil_texture_id']).tolist()[0]
                , 'organic_matter_id': np.array(data['crop_soil_organic_matter']).tolist()[0]
                , 'organic_matter_custom': np.array(data['crop_organic_matter_custom'].astype(float)).tolist()[0]
                , 'moisture_id': np.array(data['crop_soil_moisture']).tolist()[0]
                , 'drainage_id': np.array(data['crop_soil_drainage']).tolist()[0]
                , 'ph_id': np.array(data['crop_soil_ph']).tolist()[0]}
        else:
            crop['soil'] = {'texture_id': np.array(data['crop_soil_texture_id']).tolist()[0]
                , 'organic_matter_id': np.array(data['crop_soil_organic_matter']).tolist()[0]
                , 'moisture_id': np.array(data['crop_soil_moisture']).tolist()[0]
                , 'drainage_id': np.array(data['crop_soil_drainage']).tolist()[0]
                , 'ph_id': np.array(data['crop_soil_ph']).tolist()[0]}
            
        crop['product_fresh'] = {'value': np.array(data['crop_product_fresh_value']).tolist()[0]
            , 'unit': np.array(data['crop_product_fresh_unit']).tolist()[0]}
        crop['product_finished'] = {'value': np.array(data['crop_product_finished_value']).tolist()[0]
            , 'unit': np.array(data['crop_product_finished_unit']).tolist()[0]}
        if data['crop_residue_value'].item() != 'null':
            crop['residue'] = {'value': np.array(data['crop_residue_value']).tolist()[0]
                , 'unit': np.array(data['crop_residue_unit']).tolist()[0]
                , 'management': np.array(data['crop_residue_management']).tolist()[0]}
        else:
            crop['residue'] = {}
        if data['crop_type'].item() == 'Potato':
            crop['seed_amount'] = {'value': np.array(data['crop_seed_amount_value']).tolist()[0]
                , 'unit': np.array(data['crop_seed_amount_unit']).tolist()[0]}
        else:
            crop['seed_amount'] = {}
        crop['irrigation_calculation_type'] = np.array(data['crop_irrigation_calculation_type']).tolist()[0]
        # __________________________________
        # __________________________________
        type4 = []
        out = {}

        list_of_cols = data.loc[:, (data.columns.str.contains('type4_type_id_'))]
        list_of_numbers = [re.findall('\d+', x)[0] if '_' in x else x for x in list_of_cols]

        for i in list_of_numbers:
            if data['type4_application_rate_value_' + i].item() > 0:
                out['type_id'] = np.array(data['type4_type_id_' + i].fillna(0).astype(int)).tolist()[0]
                out['category_id'] = np.array(data['type4_category_id_' + i].fillna(0).astype(int)).tolist()[0]
                out['percentage_rate'] = np.array(data['type4_percentage_rate_' + i]).tolist()[0]
                out['application_rate'] = {'value': np.array(data['type4_application_rate_value_' + i]).tolist()[0]
                    , 'unit': np.array(data['type4_application_rate_unit_' + i]).tolist()[0]}
                type4.append(out.copy())
        # __________________________________
        # __________________________________
        machinery = []
        out = {}

        list_of_cols = data.loc[:, (data.columns.str.contains('mach_op'))]
        list_of_numbers = [re.findall('\d+', x)[0] if '_' in x else x for x in list_of_cols]

        for i in list_of_numbers:
            if data['mach_op_' + i].astype(float).item() > 0:
                out['op'] = np.array(data['mach_op_' + i]).tolist()[0]
                out['number'] = np.array(data['mach_number']).tolist()[0]
                out['machinery'] = np.array(data['mach_machinery_' + i]).tolist()[0]
                out['type'] = np.array(data['mach_type_' + i]).tolist()[0]

                machinery.append(out.copy())
        # __________________________________

        final_json = {}

        final_json['farm'] = farm
        final_json['crop'] = crop
        final_json['metricQ'] = type4
        final_json['machinery'] = machinery
        # __________________________________
        # __________________________________
        json_all_farms.append(final_json.copy())

    #print(json.dumps(json_all_farms, indent=2))
    return json_all_farms

def api_response(json_all_farms):

    # insert your API key and include in headers
    API_KEY = "key"
    APP_KEY = "key"
    HEADERS = {
        "Content-Type": "application/json"
    }

    crop_output = requests.post(
        f"URLHERE?api_app_key={APP_KEY}&api_key={API_KEY}"
        , json=json_all_farms  # our JSON we just made
        , headers=HEADERS)

    if crop_output.status_code != 200:
        print(crop_output.json())
        raise SystemExit(
            f"Stop right there! \n \n There is an issue with the call \n ~ Response = {crop_output.status_code}")
    else:
        print(crop_output.json())
        # the index below removes the final dict which is =  {'information':{'cft_version': '1.1.1'}}
        return crop_output.json()[0:-1]

def create_JSON_to_df(self):
    dfs = []
    for farm in tqdm(range(len(self))):
        # ________farm name_________
        farm_indentifier = pd.DataFrame([self[farm]['farm']])

        # ________summary_________
        summary = pd.DataFrame(self[farm]['summary'])
        summary = summary.rename(columns={'emissions_total': 'emissions_total_kgCO2e'
            , 'emissions_per_area': 'emissions_per_area_kgCO2e/ha'
            , 'emissions_per_product': 'emissions_per_product_kgCO2e/tone'})
        summary = summary.loc[:0]

        # ________emissions totals_________
        emissions = pd.DataFrame(self[farm]['total_emissions'])
        out = []
        for section, df in emissions.groupby('name'):
            df = df.rename(columns={'CO2': section + '_CO2'
                , 'N2O': section + '_N2O'
                , 'CH4': section + '_CH4'
                , 'total_CO2e': section + '_total_CO2e'
                , 'total_CO2e_per_area': section + '_total_CO2e_per_area'
                , 'total_CO2e_per_product': section + '_total_CO2e_per_product'
                                    })
            df = df.drop('name', axis=1)
            df[df.columns.tolist()] = df[df.columns.tolist()].astype(float)
            out.append(df)
        emissions_out = pd.concat(out).fillna(0).sum(axis=0, skipna=True).reset_index().transpose()
        new_header = emissions_out.iloc[0]  # grab the first row for the header
        CO2_tots = emissions_out[1:]  # take the data less the header row
        CO2_tots.columns = new_header  # set the header row as the df header
        
        # ________final farm_________
        output = farm_indentifier.join(summary).join(CO2_tots)
        dfs.append(output)

    end_df = pd.concat(dfs)
    return end_df


## map strings 95% confidence
def get_mapped_to_cft(row, id_type):
    name_list = id_type['Name'].unique()
    for ref in name_list:
        score = jaro.jaro_winkler_metric(row, ref)
        if score >= 0.90:
            return ref
