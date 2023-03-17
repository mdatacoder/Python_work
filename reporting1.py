#%%  Packages list
import pandas as pd
import numpy as np
from numpy import inf
import re
import math
import os
import glob
import datetime
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

# if you want to see a progress bar please install tqdm (i used pip)
from tqdm.notebook import tqdm, trange

from pandas.core.common import SettingWithCopyWarning, warnings
warnings.simplefilter(action="ignore", category=SettingWithCopyWarning)

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4  # also letter might be useful for future projects
from reportlab.lib.colors import HexColor, Color
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.lib.validators import Auto
from reportlab.lib.styles import ParagraphStyle,getSampleStyleSheet

from reportlab.platypus import SimpleDocTemplate, Spacer, PageBreak, Table, TableStyle, CellStyle, Paragraph

from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from reportlab.graphics.shapes import Drawing, Line, Rect
from reportlab.graphics.widgets.table import TableWidget
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.graphics.widgets.adjustableArrow import AdjustableArrow
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import LineChart
from reportlab.graphics.charts.lineplots import LinePlot, SimpleTimeSeriesPlot, LinePlot_label
from reportlab.graphics.charts.piecharts import AbstractPieChart, Pie
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.textlabels import Label
from reportlab.graphics.charts.axes import XCategoryAxis
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_JUSTIFY, TA_LEFT

import timeit
start_time = timeit.default_timer()

#%%  File Paths
# path to store data
raw_folder_loc = fr"C:\Users\{USER}\{path_to_folder}\Report Output\Raw data"
# raw data path
path = f"C:/Users/{USER}/{path_to_folder}/MonthlyData"

#%%  Loop through files

filelist = []
# First we find all of the names in the data
for root, dirs, files in os.walk(path):
    for file in files:
        # append the file name to the list
        filelist.append(os.path.join(root, file))

# the turn into a datframe so we can use
file_df = pd.DataFrame({'filelist': filelist})

# then match the dataframe column filelist with key words in our file
a = file_df[file_df['filelist'].str.contains('file name of data.xlsx.*?', case=False, regex=True)]
# print
path = list(a['filelist'])[0]

# read excel
sheets_dict = pd.read_excel(path, sheet_name = None)

#%%  Loop through sheets (format is one sheet per month)
# convert into one dataframe by looping through each sheet's name and creating a new column for
# each name
full_table = pd.DataFrame()
for name, sheet in sheets_dict.items():
    sheet['sheet'] = name
    sheet = sheet.rename(columns=lambda x: x.split('\n')[-1])
    full_table = full_table.append(sheet)

# rest index back into a df
full_table.reset_index(inplace=True, drop=True)
df = full_table[~full_table['sheet'].str.contains('Field Dictionary')] # removing dictionary of column keys
print('list of all sheet names (should only be dates):',full_table['sheet'].unique())

# save the raw data now transposed as a file for manual checks of data coming in
df.to_csv(os.path.join(raw_folder_loc,'raw_fm_data.csv'), index=None)

# convert sheet to datetime - hopefully this makes graphing set time periods easier
df['DateNo'] = pd.to_datetime(df['DateNo'], format = '%Y-%m')

# Extracting the string value of month short hand %b or full name %B
df['Date'] = df['DateNo'].dt.strftime("%b-%y")

#%%  How we use dates in pdfs
# we use todays date to determine the data period to use in the pdfs
today = date.today()
print('today is the:',today)

# Calculating survey time period dependant on the month we run the code on: to use in PDF's
if today.strftime('%m') in ['08']:
    time_period_pdfs = [(today + relativedelta(months = -12)).strftime('%m-%Y'),today.strftime('%m-%Y')]
    print("fixed period:  >=",time_period_pdfs[0],'and <',time_period_pdfs[1])
elif today.strftime('%m') in ['09','10','11','12']:
    first_aug = datetime.strptime('08/'+today.strftime('%Y'),'%m/%Y')
    time_period_pdfs = [first_aug.strftime('%m-%Y'),(first_aug+ relativedelta(months = 12)).strftime('%m-%Y')]
    print("fixed period:  >=",time_period_pdfs[0],'and <',time_period_pdfs[1])
elif today.strftime('%m') in ['01','02','03','04','05','06','07']:
    first_aug = datetime.strptime('08/'+today.strftime('%Y'),'%m/%Y') + relativedelta(months = -12)
    time_period_pdfs = [first_aug.strftime('%m-%Y'),(first_aug+ relativedelta(months = 12)).strftime('%m-%Y')]
    print("fixed period:  >=",time_period_pdfs[0],'and <',time_period_pdfs[1])

print('/n Min date in df is the ',df['DateNo'].min())
print('/n Max date in df is the ',df['DateNo'].max())

EST_YEAR = (datetime.strptime(time_period_pdfs[0],'%m-%Y') + relativedelta(years=-2)).strftime('%Y')

df = df[(df['DateNo'] >= time_period_pdfs[0]) & (df['DateNo'] < time_period_pdfs[1])]

#%%  12m average calcs
df = df.fillna(0)

# Automated df so cols always in same place: Calves should be int not float as you cannnot have 1.5 of a calf
df.iloc[:, np.r_[6,10:40]] = df.iloc[:, np.r_[6,10:40]].astype(int)


#%%  Function: Simplify reasons
def simplify_reasons(blob):
    if pd.isnull(blob) == True:
        return blob
    elif any(word in blob.lower() for word in ['twin']):
        return 'Twin Calf'
    elif any(word in blob.lower() for word in ['moaeligible']):
        return 'MoaEligible'
    elif any(word in blob.lower() for word in ['tb','no space']):
        return 'No TB Rearing Space'
    elif any(word in blob.lower() for word in ['eartag','tag','ear tag']):
        return 'Eartag Issue'
    elif any(word in blob.lower() for word in ['weight for age']):
        return 'Too small'
    elif any(word in blob.lower() for word in ['passport']):
        return 'No passport'
    elif any(word in blob.lower() for word in ['dead']):
        return 'Dead'
    elif any(word in blob.lower() for word in ['poorly','ill','unwell']):
        return 'Unfit/Unwell'
    else:
        return blob

#%%  Adding Rejections: Calf survey
path = fr"C:\Users\{USER}{path_for_addtions to data}"
# we say pick all files which are the survey but not containing August
csurvey = pd.read_excel(glob.glob(os.path.join(path, '[!August]*Survey*.xlsx' ))[0])
if csurvey.columns.str.contains('unnamed',case=False).any() == True:
    csurvey = pd.read_excel(glob.glob(os.path.join(path, '[!August]*Survey*.xlsx'))[0], skiprows=1)
try:
    csurvey = csurvey[csurvey['Completed On'].notnull()]
except KeyError:
    csurvey = pd.read_excel(glob.glob(os.path.join(path, '[!August]*Survey*.xlsx'))[0], skiprows=1)
    csurvey = csurvey[csurvey['Completed On'].notnull()]
csurvey = csurvey[csurvey['Completed On'].notnull()]

## remove 507 as testing
csurvey = csurvey[~csurvey['Unit ID'].isin(['507',507])]

csurvey = csurvey[(csurvey['Date of rejection'] >= time_period_pdfs[0]) & (csurvey['Date of rejection'] <today.strftime('%Y-%m'))]
# pick the columns we want to stack and save as a list of col names called keys
keys = [c for c in csurvey if c.startswith('Eartag') or c.endswith('[[calf_details_1]]')]

# melt the dataframe with cols we wat to keep as id_vars and the new name of the stacked col as eartags
csurvey = pd.melt(csurvey, id_vars=['list of id cols], value_vars=keys, value_name='Eartag')
print('shape of survey: ',csurvey.shape)

#%%  Processing: Survey Data
cols=['list of cols']
csurvey[cols]
for x in cols:
    csurvey[x] = csurvey[x].str.split('\n').str[0]
# remove empty Eartag rows
csurvey = csurvey[csurvey['Eartag'].notna()]
# find any white space and remove it (just using a space was not working)
csurvey['Eartag'] = csurvey['Eartag'].str.replace(r'\s','')

# we use a (negative lookaround '?<!') to (match any all occurnaces '.*') when (digits are 12 long)
# so because its a negative lookaround it means match any which are not 12 digits long exact
eartgas_incorrect = csurvey['Eartag'].str.findall('.*(?<!\d{12})$').str[0].unique().tolist()

# export the incorrect eartags (shouldn't be an issue in the future but just in case)
csurvey[csurvey['Eartag'].isin(eartgas_incorrect)].to_csv(os.path.join(SHAREPOINT_PATH,'Validations','wrong_eartags.csv'))
# says keep only eartags which are correct
csurvey = csurvey[~csurvey['Eartag'].isin(eartgas_incorrect)]
# find occurnaces when reason == other and replace with our if other column
csurvey.loc[csurvey['Reason']=='Other','Reason'] = csurvey['Reason other']
# change status when health reasons included knuckled
csurvey.loc[(csurvey['Reason']=='Issue A')&(csurvey['Reason other'].str.contains('Issue 2',case=False)),'Status'] = 'Eligible Rejection'
# replace our text reasons with simplfied responses as laid out in the function above
csurvey['Reason'] = csurvey['Reason'].str.lower().apply(lambda x: simplify_reasons(x))

#check output
csurvey['Reason'].replace([np.nan,'nan'],'Other',inplace=True)
print(csurvey['Reason'].unique())
add_rejections = csurvey[['specify_cols_to_keep']]

#%%  Merging rejections to main df

df_cols = df.columns.tolist()
rej_cols = add_rejections.columns.tolist()
overlapping_cols  = [x for x in rej_cols if x in df_cols]

# create list of all IDs
IDs_to_keep = df['Unit ID'].unique()
# only keep the ones that are included in our data to reduce time
add_rejections = add_rejections[add_rejections['Unit ID'].isin(IDs_to_keep)]

oldshape = df.shape[0]
df = df.merge(add_rejections, how='left', on=overlapping_cols) 
print(df.shape[0]-oldshape,"--> if 0 we're all good")


#%%  Function: Merge same farm buisnesses

# loop to transform multiple IDs into one farm unit when multiple Ids are same holding
# little complex as a .agg would require specific col names and we have too many in df
def merge_same_business_farms(liss):
    new = df[df['Unit ID'].isin(liss)]
    cols_to_sum = df.loc[:, df.columns.str.contains('name|of|cols |^go here  ',case=False)].columns.tolist()
    # only select numeric dtypes at end
    cols_to_max = new.drop(cols_to_sum + ['names to drop'],
                           axis=1).select_dtypes(include=[float, int]).columns.tolist()

    summed = new.groupby(['DateNo', 'Date'], as_index=False)[cols_to_sum].sum()
    maxed = new.groupby(['DateNo', 'Date'], as_index=False)[cols_to_max].max()

    return pd.merge(summed, maxed, how='outer', on=['DateNo', 'Date'])

#%%  Using function above

# create the new dfs by selcting the farms to 'smush' together as per our function (this would only need changing if new customers
# required this, very rare)
b = merge_same_business_farms([218,225])
b['Unit ID'] = 218
b['Unit Name'] = 'buisness name here'
b = b.merge(df[df['Unit ID']==218][['cols to keep']]
       , on=['Unit ID','Date'], how='left')
df = pd.concat([df[~df['Unit ID'].isin([218,225])],b])

## Just adding this back in as above farms will be 0 otherwise
df['Date'] = df['DateNo'].dt.strftime('%b-%y')

#%%  if we needed to import a zipfile
"""
import zipfile

# growing zip file for SDDG (beef and dairy units)
path = f"C:/Users/{USER}/{path to use}\myfile.zip"
zf = zipfile.ZipFile(path, 'r')
zf = pd.read_csv(zf.open('file_name.csv'))

"""
#%%  PDF setup

# if the font is a 'true type font' we download (I downloaded from https://www.onlinewebfonts.com/fonts/mary_ann)
# can do the following to add it in:
pdfmetrics.registerFont(TTFont('MaryAnn', os.path.join(SHAREPOINT_PATH,'MaryAnn.ttf')))
pdfmetrics.registerFont(TTFont('MaryAnnBd', os.path.join(SHAREPOINT_PATH,'MaryAnnBold.ttf')))

registerFontFamily('MaryAnn',normal='MaryAnn',bold='MaryAnnBd',italic=None,boldItalic=None)

print('there should be this many pdf outputs:',len(df['Unit ID'].unique()))
#%%  THE LOOP

###########################################################################
#                           DO NOT TOUCH !!!                              #
###########################################################################


def generate_report(df, data, pdf_file_name):
    c = canvas.Canvas(pdf_file_name, pagesize=A4)
    c.setFont('MaryAnnBd', 16, leading=None)
    c.setFillColor(HexColor('#F06C01'))  # orange
    c.drawCentredString(105 * mm, 286 * mm, 'Sainsbury’s Integrated Beef')
    c.drawCentredString(105 * mm, 280 * mm, 'Calf Supply Report')
    c.drawImage(os.path.join(SHAREPOINT_PATH,'sains_logo.png'), 30 * mm, 285 * mm, 40 * mm
                , mask=None, preserveAspectRatio=True, anchorAtXY=True)

    pgwidth = 210
    pgheight = 297

    def find_first_aug_in_period(x):
        if x in ['08']:
            first_aug = datetime.strptime('08/' + today.strftime('%Y'), '%m/%Y') + relativedelta(months=-12)
        elif x in ['09', '10', '11', '12']:
            first_aug = datetime.strptime('08/' + today.strftime('%Y'), '%m/%Y')
        elif x in ['01', '02', '03', '04', '05', '06', '07']:
            first_aug = datetime.strptime('08/' + today.strftime('%Y'), '%m/%Y') + relativedelta(months=-12)

        first_aug = first_aug.strftime('%m-%Y')
        return first_aug

    last_aug_period = datetime.strptime(find_first_aug_in_period(today.strftime('%m')), '%m-%Y') + relativedelta(
        months=12)
    df_to_check = data[
        (data['DateNo'] >= find_first_aug_in_period(today.strftime('%m'))) & (data['DateNo'] < last_aug_period)]

    ###############  SORTING DATA START  ###############
    if (df_to_check['Supplied G'].sum() == 0) & (df_to_check['Supplied K'].sum() >= 1):
        data['calf type'] = 'K'
    elif (df_to_check['Supplied G'].sum() >= 1) & (df_to_check['Supplied K'].sum() == 0):
        data['calf type'] = 'G'
    else:
        data['calf type'] = 'both'

    # sains for 21-22 decided they wanted to sum together all farms schemes
    # this may not be the truth in future:
    klist = sorted(data.loc[:, data.columns.str.contains('^K | K ',case=False)].columns.tolist())
    for a in klist:
        b = a.replace('K ', 'GC ').replace('schema a', 'schema b')
        data[re.sub('K |schema a', '', a).lower()] = data[a] + data[b]
    data.columns = [x.lower() for x in data.columns.tolist()]

    if (data['committed'].sum() == 0) & (data['supplied'].sum() == 0):
        TO_RUN = 'no'
    else:
        TO_RUN = 'yes'

    ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ###
    ###    HERE WE REMOVE ANY SUPPLIED AND REGISTERED FROM CURRENT MONTH        ###
    ###                AS IT MIGHT NOT BE FULL DATASET                          ###
    ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ###
    data.loc[data['dateno'] == today.strftime('%Y-%m'), 'supplied'] = 0
    data.loc[data['dateno'] == today.strftime('%Y-%m'), 'registered'] = 0
    ### ### ### ### ### ### ### ### ### ### ### ###

    ####### NOW ADD EXTRA FIELDS FOR CALCULATING ROLLING COMMIT% #######
    # data = data.rename(columns={'presented_not_collected':'rejection'})

    # create the % difference of supp / committ
    data['calc 5'] = ((data['supplied'] + data['rejection']) * 100) / data['committed']
    data['calc 5'] = data['calc 5'].fillna(0)
    # remove inf meaning infinate values
    data = data.replace([np.inf, -np.inf], np.nan).fillna(0)
    data['calc 5'] = data['calc 5'].astype(int)
    # Producing a rolling mean
    rolling_windows = data['calc 5'].rolling(2, min_periods=1)
    data['rolling mean'] = rolling_windows.mean().round().fillna(0).astype(int)

    ###############  SORTING DATA FINISHED  ###############

    def all_pages(self):
        self.setFont('MaryAnnBd', 10, leading=None)
        self.setFillColor(HexColor('#4C4C4C'))  # grey
        for farmname in data['unit name'].unique():
            self.drawCentredString(190 * mm, 290 * mm, str(farmname))
            # self.drawCentredString(190 * mm, 290 * mm, 'A Farm Name') # FOR EXAMPLE
        self.drawImage(os.path.join(SHAREPOINT_PATH,'sains_logo.png'), 30 * mm, 285 * mm, 40 * mm
                       , mask=None, preserveAspectRatio=True, anchorAtXY=True)
        self.setFont('MaryAnn', 10, leading=None)
        self.drawCentredString(190 * mm, 285 * mm, date.today().strftime("%b, %Y"))
        self.setFont('MaryAnnBd', 10, leading=None)
        for calftype in data['calf type'].unique():
            if data['derogated?'].max() == 2:  # 2 == 'yes'
                self.drawCentredString(190 * mm, 280 * mm, 'Derogated')
            else:
                self.drawCentredString(190 * mm, 280 * mm, str(calftype))

        def draw_page_number(self):
            self.setFont('MaryAnnBd', 8)
            self.setFillColor(HexColor('#4C4C4C'))  # grey
            self.drawRightString(
                105 * mm,
                10 * mm,
                "Page %d" % (self.getPageNumber())
            )

        draw_page_number(c)

    def add_table(self, time_period='Past', ismean=False, cols=None, diff=False, x=None, y=None, headers=True,
                  stripe_rows=False
                  , matrix=False, indpendant=False, month_avg=False, monthly_val=False, page1=False
                  , eartags=False, custom_row_data=None):
        time_periods_ = ['Past', 'Future', 'Fixed']
        if time_period not in time_periods_:
            raise ValueError("Invalid time_period. Expected one of: %s" % sim_types)

        if time_period == 'Past':
            df_sorted = data[data['dateno'] < today.strftime('%m-%Y')]
        if time_period == 'Future':
            df_sorted = data[data['dateno'] >= today.strftime('%m-%Y')]
        elif time_period == 'Fixed':
            # the function returns the Aug at the start of the fixed period depending on todays month and returns %m-%Y
            last_aug_period = datetime.strptime(find_first_aug_in_period(today.strftime('%m')),
                                                '%m-%Y') + relativedelta(months=12)
            df_sorted = data[
                (data['dateno'] >= find_first_aug_in_period(today.strftime('%m'))) & (data['dateno'] < last_aug_period)]

        if eartags == False:
            if df_sorted['committed'].sum() >= 1:
                # create the % difference of supp / committ
                df_sorted['calc 5'] = ((df_sorted['supplied'].sum() + df_sorted[
                    'rejection'].sum()) * 100) / df_sorted['committed'].sum()
                df_sorted['calc 5'] = df_sorted['calc 5'].fillna(0)
                # remove inf meaning infinate values
                df_sorted = df_sorted.replace([np.inf, -np.inf], np.nan).fillna(0)
                df_sorted['calc 5'] = df_sorted['calc 5'].astype(int)

            new = (df_sorted.groupby('unit name', as_index=False)
                   .agg({'committed': 'sum', 'supplied': 'sum', 'rejection': 'sum'
                            , 'derogated?': 'max'})
                   .round()
                   )
            try:
                new[['cols']] = new[['cols']].astype(int)
            except ValueError:
                new = new.fillna(0)
                
            if new['committed'].sum() >= 1:
                # new['commit%'] = (((new['supplied']+new['rejection']) /new['committed']) * 100).astype(int)
                new_100_calves = \
                updated_metric[updated_metric['Unit ID'] == data['unit id'].tolist()[0]]['100% of Calves'].tolist()[0]
                new['calf_supply%'] = (((new['supplied'] + new['rejection']) / new_100_calves) * 100).astype(
                    int)
            else:
                new['calf_supply%'] = 0

            new['derogated?'] = new['derogated?'].replace({1: 'No', 2: 'Yes', 0: 'unknown'})
            # new = new[['committed','supplied','rejection','commit%','derogated?']]
            if page1 == True:
                new = new[['supplied', 'rejection', 'calf_supply%']]
            row = np.array(new).tolist()

        if (matrix == True) & (indpendant == False):
            table_style = []
            table_style.append(('BACKGROUND', (0, 0), (0, 0), HexColor('#DA423F')))
            table_style.append(('GRID', (0, 0), (0, 0), 2, HexColor('#DA423F')))
            table_style.append(('TEXTCOLOR', (0, 0), (0, 0), colors.white))
            table_style.append(('GRID', (1, 0), (1, 0), 2, HexColor('#F7921E')))
            table_style.append(('TEXTCOLOR', (1, 0), (1, 0), colors.black))
            table_style.append(('TEXTCOLOR', (1, 0), (1, 0), colors.white))
            table_style.append(('BACKGROUND', (2, 0), (2, 0), HexColor('#9CCD63')))
            table_style.append(('GRID', (2, 0), (2, 0), 2, HexColor('#9CCD63')))
            table_style.append(('TEXTCOLOR', (2, 0), (2, 0), colors.white))
            table_style.append(('BACKGROUND', (3, 0), (3, 0), HexColor('#55926D')))
            table_style.append(('GRID', (3, 0), (3, 0), 2, HexColor('#55926D')))
            table_style.append(('TEXTCOLOR', (3, 0), (3, 0), colors.white))
            table_style.append(('BACKGROUND', (1, 0), (1, 0), HexColor('#F7921E')))

            row = [['<4%', '4% - <20%', '20% - <25%', '25% +']]
            # ~~~~~~END MATRIX & INDEPENDANT~~~~~~#

        elif (matrix == True) & (indpendant == True):
            if df_sorted['committed'].sum() >= 1:
                try:
                    matrixnum = ((df_sorted['supplied'].sum() * 100) / df_sorted['committed'].sum()).astype(int)
                except ValueError:
                    matrixnum = (df_sorted['supplied'].sum() * 100) / df_sorted['committed'].sum()
                mat = str(matrixnum)
            else:
                matrixnum = 0
                mat = 'value too small'
                if df_sorted['derogated?'].max() == 2:  # 2 == 'yes'
                    mat = 'Derogated'
            table_style = []
            for i in [matrixnum]:
                if i < 100:
                    table_style.append(('BACKGROUND', (0, 0), (-1, -1), HexColor('#DA423F')))
                    table_style.append(('GRID', (0, 0), (-1, -1), 2, HexColor('#DA423F')))
                    table_style.append(('TEXTCOLOR', (0, 0), (-1, -1), colors.white))
                elif (i >= 100) & (i < 125):
                    table_style.append(('BACKGROUND', (0, 0), (-1, -1), HexColor('#9CCD63')))
                    table_style.append(('GRID', (0, 0), (-1, -1), 2, HexColor('#9CCD63')))
                    table_style.append(('TEXTCOLOR', (0, 0), (-1, -1), colors.white))
                elif i > 125:
                    table_style.append(('BACKGROUND', (0, 0), (-1, -1), HexColor('#55926D')))
                    table_style.append(('GRID', (0, 0), (-1, -1), 2, HexColor('#55926D')))
                    table_style.append(('TEXTCOLOR', (0, 0), (-1, -1), colors.white))
                else:
                    table_style.append(('BACKGROUND', (0, 0), (-1, -1), HexColor('#F7921E')))
                    table_style.append(('GRID', (0, 0), (-1, -1), 2, HexColor('#F7921E')))
                    table_style.append(('TEXTCOLOR', (0, 0), (-1, -1), colors.white))
        if eartags == False:
            t = Table(row, colWidths=45 * mm, rowHeights=15 * mm, style=None, splitByRow=1)
            # ~~~~~~END MATRIX & INDEPENDANT~~~~~~#
        if page1 == True:
            t = Table(row, colWidths=60 * mm, rowHeights=15 * mm, style=None, splitByRow=1)
        elif (matrix == True) & (indpendant == True):
            t = Table([[mat + '%']], colWidths=45 * mm, rowHeights=20 * mm, style=None, splitByRow=1)
            if (df_sorted['derogated?'].max() == 2) & (df_sorted['committed'].sum() == 0):  # 2 == 'yes'
                table_style.append(('BACKGROUND', (0, 0), (-1, -1), HexColor('#4C4C4C')))
                table_style.append(('GRID', (0, 0), (-1, -1), 2, HexColor('#4C4C4C')))
                t = Table([[mat]], colWidths=45 * mm, rowHeights=20 * mm, style=None, splitByRow=1)
        elif ismean == True:
            if month_avg == False:
                new = df_sorted.groupby('unit name', as_index=False)[cols].mean() \
                    .round(0)
                try:
                    new[cols] = new[cols].astype(int)
                except ValueError:
                    new[cols] = new[cols]
                row = np.array(new).tolist()
            elif month_avg == True:
                future_month = datetime.strptime(date.today().strftime('%Y-%m'), '%Y-%m') + relativedelta(months=+12)
                df_sorted = data[data['dateno'] < today.strftime('%m-%Y')]
                try:
                    summed = df_sorted['committed'].sum().astype(int)
                    average = (summed / 12).astype(int)
                except ValueError:
                    summed = df_sorted['committed'].sum()
                    average = (summed / 12)
                row = [[summed, average]]
            t = Table(row, colWidths=90 * mm, rowHeights=15 * mm, style=None, splitByRow=1)
        elif monthly_val == True:
            df_sorted = data[data['dateno'] < today.strftime('%m-%Y')]
            try:
                df_sorted[cols] = df_sorted[cols].astype(int)
            except ValueError:
                df_sorted[cols] = df_sorted[cols]
            new2 = np.array(df_sorted[cols]).tolist()
            mon = np.array(df_sorted['date']).tolist()
            row = [mon[0:6], new2[0:6], mon[6:12], new2[6:12]]
            t = Table(row, colWidths=30 * mm, rowHeights=15 * mm, style=None, splitByRow=1)

            table_style = []
            for i, row in enumerate(row):
                if i % 2 == 0:
                    table_style.append(('TEXTCOLOR', (0, i), (-1, i), colors.white))  # orange '#F06C01'
                    table_style.append(('BACKGROUND', (0, i), (-1, i), HexColor('#7F0442')))
                    table_style.append(('GRID', (0, i), (-1, i), 0, colors.white))
                else:
                    table_style.append(('TEXTCOLOR', (0, i), (-1, i), HexColor('#4C4C4C')))  # grey
                    table_style.append(('BACKGROUND', (0, i), (-1, i), colors.white))
                    table_style.append(('GRID', (0, i), (-1, i), 0, colors.white))

        if eartags == False:
            t.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')  # rows,cols
                                      , ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
                                      , ('TEXTCOLOR', (0, 0), (-1, -1), colors.black)
                                      , ('GRID', (0, 0), (-1, -1), 2, HexColor('#F06C01'))  # rows,cols
                                      , ('FONTSIZE', (0, 0), (-1, -1), 16, colors.black)
                                      , ('FONTNAME', (0, 0), (-1, -1), 'MaryAnn')
                                   ]))
        if matrix == True:
            t.setStyle(table_style)
        elif monthly_val == True:
            t.setStyle(table_style)

        if diff == True:
            last = today + relativedelta(months=6)
            df_sorted = data[(data['dateno'] >= today.strftime('%Y-%m')) &
                             (data['dateno'] < last.strftime('%Y-%m'))]
            new = df_sorted.groupby('unit name', as_index=False)[cols].sum() \
                .round(0)
            try:
                new = new[cols].astype(int)
            except ValueError:
                new = new[cols]
            new['Diff'] = new[cols[1]] - new[cols[0]]
            new2 = np.transpose(new)
            new2 = np.array(new2).tolist()
            row = [[cols[0], '', cols[1], '', 'Difference'], new2[0] + [''] + new2[1] + [''] + new2[2]]

            t = Table(row, colWidths=35 * mm, rowHeights=20 * mm, style=None, splitByRow=1)
            t.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')  # cols,rows
                                      , ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
                                      , ('FONTNAME', (0, 0), (-1, -1), 'MaryAnnBd')
                                      , ('FONTSIZE', (0, 0), (-1, -1), 16)
                                   ]))
            table_style = []
            for i, row in enumerate(row):
                if i % 2 == 0:
                    table_style.append(('TEXTCOLOR', (0, i), (-1, i), HexColor('#4C4C4C')))  # grey
                    table_style.append(('BACKGROUND', (0, i), (-1, i), colors.white))
                else:
                    table_style.append(('TEXTCOLOR', (0, i), (-1, i), colors.white))  # orange '#F06C01'
                    table_style.append(('BACKGROUND', (0, i), (-1, i), HexColor('#7F0442')))
                    table_style.append(('TEXTCOLOR', (1, i), (1, i), colors.white))  # orange '#F06C01'
                    table_style.append(('BACKGROUND', (1, i), (1, i), colors.white))
                    table_style.append(('TEXTCOLOR', (3, i), (3, i), colors.white))  # orange '#F06C01'
                    table_style.append(('BACKGROUND', (3, i), (3, i), colors.white))
            t.setStyle(table_style)
            # END OF diff
        if stripe_rows == True:
            if type(custom_row_data) != pd.core.frame.DataFrame:
                styleE = ParagraphStyle(name='Normal', fontName='MaryAnn', fontSize=9.5
                                        , textColor=HexColor('#4C4C4C'), alignment=TA_LEFT)
                styleO = ParagraphStyle(name='Normal', fontName='MaryAnn', fontSize=9.5
                                        , textColor=colors.white, alignment=TA_LEFT)
                row = [['title here:', Paragraph('''
                        decriotion here 
                        ''', styleE)],
                       ['title here:', Paragraph('''
                        decriotion here 
                        ''', styleO)],
                       ['title here:', Paragraph('''
                        decriotion here 
                        ''', styleE)],
                       ['title here:', Paragraph('''
                        decriotion here 
                        ''', styleO)],
                       ['title here:', Paragraph('''
                        decriotion here 
                        ''', styleE)],
                       ['title here:', Paragraph('''
                        decriotion here 
                        ''', styleO)],
                       ['title here:', Paragraph('''
                        decriotion here 
                        ''', styleE)],
                       ['title here:', Paragraph('''
                        decriotion here 
                        ''', styleO)],
                       ]
                t = Table(row, colWidths=[40 * mm, 140 * mm], rowHeights=20 * mm, style=None, splitByRow=1)
            if type(custom_row_data) == pd.core.frame.DataFrame:
                style1 = ParagraphStyle(name='Normal', fontName='MaryAnn', fontSize=10
                                        , textColor=HexColor('#4C4C4C'), alignment=TA_LEFT)
                style2 = ParagraphStyle(name='Normal', fontName='MaryAnnBD', fontSize=10
                                        , textColor=colors.white, alignment=TA_LEFT)

                even = []
                odd = []
                for tag, temp_df in custom_row_data.groupby('Eartag'):
                    loc = custom_row_data.loc[custom_row_data['Eartag'] == tag].index[0]
                    if loc % 2 == 0:
                        reason = temp_df['Reason'].tolist()[0]
                        even.append([Paragraph('''''' + tag, style2), Paragraph('''''' + reason, style1)])
                    if loc % 2 == 1:
                        reason = temp_df['Reason'].tolist()[0]
                        odd.append([Paragraph('''''' + tag, style2), Paragraph('''''' + reason, style1)])
                row = []
                if len(odd) > 0:
                    for index in range(len(odd)):
                        new = even[index] + odd[index]
                        row.append(new)
                        # end of loop #
                    try:
                        if len(even) > len(odd):
                            row.append(even[len(even) - 1])
                    except IndexError:
                        pass
                else:
                    row = [even[0] + ['', '']]

                t = Table(row, colWidths=[35 * mm, 60 * mm, 35 * mm, 60 * mm], rowHeights=10 * mm, style=None,
                          splitByRow=1)

            table_style = []
            for i, row in enumerate(row):
                if i % 2 == 0:  # (i % 2 == 0) & (type(custom_row_data) != pd.core.frame.DataFrame):
                    table_style.append(('TEXTCOLOR', (0, i), (-1, i), HexColor('#4C4C4C')))  # grey
                    if type(custom_row_data) != pd.core.frame.DataFrame:
                        table_style.append(
                            ('BACKGROUND', (0, i), (-1, i), Color(.9412, .4235, .039, alpha=0.2)))  # light plum
                    table_style.append(('VALIGN', (0, i), (-1, i), 'MIDDLE'))
                    table_style.append(('GRID', (0, i), (-1, i), 2, colors.white))
                else:
                    table_style.append(('TEXTCOLOR', (0, i), (-1, i), colors.white))  # orange #F06C01
                    if type(custom_row_data) != pd.core.frame.DataFrame:
                        table_style.append(('BACKGROUND', (0, i), (-1, i), HexColor('#F06C01')))  # plum #7F0442
                    table_style.append(('VALIGN', (0, i), (-1, i), 'MIDDLE'))
                    table_style.append(('GRID', (0, i), (-1, i), 2, colors.white))
            if type(custom_row_data) == pd.core.frame.DataFrame:
                table_style.append(('BACKGROUND', (0, 0), (0, -1), '#F06C01'))
                table_style.append(('BACKGROUND', (2, 0), (2, -1), '#F06C01'))
                table_style.append(('BACKGROUND', (1, 0), (1, -1), Color(.9412, .4235, .039, alpha=0.2)))
                table_style.append(('BACKGROUND', (3, 0), (3, -1), Color(.9412, .4235, .039, alpha=0.2)))

            table_style.append(('FONTNAME', (0, 0), (0, -1), 'MaryAnnBd'))
            t.setStyle(table_style)
            # END OF alt rows

        if diff == True:
            t.wrapOn(self, 60 * mm, 30 * mm)  # w,h
            t.drawOn(self, x, y)
        elif (matrix == True) & (indpendant == True):
            t.wrapOn(self, 40 * mm, 30 * mm)  # w,h
            t.drawOn(self, x, y)
        elif (matrix == True) & (indpendant == False):
            t.wrapOn(self, 100 * mm, 30 * mm)  # w,h
            t.drawOn(self, 15 * mm, y)
        elif monthly_val == True:
            t.wrapOn(self, 180 * mm, 100 * mm)  # w,h
            t.drawOn(self, x, y)
        elif page1 == True:
            t.wrapOn(self, 100 * mm, 30 * mm)  # w,h
            t.drawOn(self, 15 * mm, 25 * mm)
        elif stripe_rows == True:
            if x is not None:
                t.wrapOn(self, 180 * mm, 140 * mm)  # w,h
                t.drawOn(self, x, y)
            else:
                t.wrapOn(self, 100 * mm, 210 * mm)  # w,h
                t.drawOn(self, 15 * mm, 60 * mm)
        else:
            t.wrapOn(self, 100 * mm, 30 * mm)  # w,h
            t.drawOn(self, 15 * mm, 255 * mm)
            # ----------------------------------------
        #   Below is the manual adding of headers
        # ----------------------------------------
        if headers == True:
            if (matrix == True) & (indpendant == False):
                row2 = [['Red', 'Amber', 'Green', 'Green +']]
                t = Table(row2, colWidths=45 * mm, rowHeights=10 * mm, style=None, splitByRow=1)
            elif (month_avg == True) & (ismean == True):
                row2 = [['Commitment for Next 12 Months', 'Monthly Average']]
                t = Table(row2, colWidths=90 * mm, rowHeights=10 * mm, style=None, splitByRow=1)
            elif page1 == True:
                styleBH = ParagraphStyle(name='Normal', fontName='MaryAnnBd', fontSize=10
                                         , textColor=colors.white, alignment=TA_CENTER)
                # a =  '' + date.today().strftime("%b, %Y")
                if data['derogated?'].max() == 2:
                    row2 = [[
                        # Paragraph('''Committed''', styleBH)
                        Paragraph('''Supplied''', styleBH)
                        , Paragraph('''Rejected (Eligible)''', styleBH)
                        # ,Paragraph('''Commitment Met % from '''+ date.today().strftime("%b, %Y")
                        , Paragraph('''Calf Supply %''', styleBH)
                        # ,Paragraph('''Derogation? <br/> ends July 2022''', styleBH)
                    ]]
                else:
                    row2 = [[
                        # Paragraph('''Committed''', styleBH)
                        Paragraph('''Supplied''', styleBH)
                        , Paragraph('''Rejected (Eligible)''', styleBH)
                        # ,Paragraph('''Commitment Met % from '''+ date.today().strftime("%b, %Y")
                        , Paragraph('''Calf Supply %''', styleBH)
                        # ,Paragraph('''Derogation?''', styleBH)
                    ]]
                # row2 = [['committed','supplied','Rejected (Eligible)','Commitment Met %','Derogation?']]
                # (192/len(row2[0]))
                # t=Table(row2, colWidths=48*mm, rowHeights=10*mm, style=None, splitByRow=1)
                t = Table(row2, colWidths=60 * mm, rowHeights=10 * mm, style=None, splitByRow=1)
            else:
                row2 = [['blank', 'blank', 'blank', 'blank']]
                t = Table(row2, colWidths=45 * mm, rowHeights=10 * mm, style=None, splitByRow=1)

            t.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')  # from top left(rows,cols) to
                                      , ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')  # bottom right(rows,cols)
                                      , ('TEXTCOLOR', (0, 0), (-1, -1), colors.white)
                                      , ('GRID', (0, 0), (-1, -1), 2, HexColor('#F06C01'))
                                      , ('BACKGROUND', (0, 0), (-1, -1), HexColor('#F06C01'))
                                      , ('FONTSIZE', (0, 0), (-1, -1), 10)
                                      , ('FONTNAME', (0, 0), (-1, -1), 'MaryAnnBd')
                                   ]))
            if page1 == True:
                t.wrapOn(self, 100 * mm, 10 * mm)  # w,h
                t.drawOn(self, 15 * mm, 15 * mm)  # x,y
            elif (matrix == True) & (indpendant == False):
                t.wrapOn(self, 100 * mm, 10 * mm)  # w,h
                t.drawOn(self, 15 * mm, y - 10 * mm)
            else:
                t.wrapOn(self, 100 * mm, 10 * mm)  # w,h
                t.drawOn(self, 15 * mm, 245 * mm)  # x,y
        ######### END OF ADD TABLE #########

    def add_bar(self, cols, y, legy, time_period='Past', x=None, legx=None, maxval=False, llabels=None
                , wd=None, ht=None, catnames=None, ttl=None, ttly=None, ttlx=None, legend=True, ylab=None
                , grouped=False, stack=False, ttlwidth=None, purple=False, totals=False
                , togroup=False, showaxis=True, add_max=None, transparent=False
                , line=False, legrow=None, linecol=None, page1=False, roundto=None, valuemin=False):
        """
        lcols_labels = list of tuples; (colour of choice, label to colour)
        """
        d = Drawing(200, 100)
        chart = VerticalBarChart()
        chart.x = 20 * mm
        if x:
            chart.x = x
        chart.y = y
        if wd:
            chart.width = wd
        else:
            chart.width = 130 * mm

        if ht:
            chart.height = ht
        else:
            chart.height = 50 * mm

        time_periods_ = ['Past', 'Future', 'Fixed']
        if time_period not in time_periods_:
            raise ValueError("Invalid time_period. Expected one of: %s" % sim_types)

        if time_period == 'Past':
            df_sorted = data[data['dateno'] < today.strftime('%m-%Y')]
        if time_period == 'Future':
            df_sorted = data[data['dateno'] >= today.strftime('%m-%Y')]
        elif time_period == 'Fixed':
            # the function returns the Aug at the start of the fixed period depending on todays month and returns %m-%Y
            last_aug_period = datetime.strptime(find_first_aug_in_period(today.strftime('%m')),
                                                '%m-%Y') + relativedelta(months=12)
            df_sorted = data[
                (data['dateno'] >= find_first_aug_in_period(today.strftime('%m'))) & (data['dateno'] < last_aug_period)]

        if time_period == 'Fixed':
            if showaxis == False:
                df_sorted = df_sorted[df_sorted['dateno'] < today.strftime('%Y-%m')]
            if df_sorted['committed'].sum() >= 1:
                # create the % difference of supp / committ
                df_sorted['calc 5'] = ((df_sorted['supplied'].sum() + df_sorted[
                    'rejection'].sum()) * 100) / df_sorted['committed'].sum()
                df_sorted['calc 5'] = df_sorted['calc 5'].fillna(0)
                # remove inf meaning infinate values
                df_sorted = df_sorted.replace([np.inf, -np.inf], np.nan).fillna(0)
                df_sorted['calc 5'] = df_sorted['calc 5'].astype(int)

        if totals == True:
            new = df_sorted[cols]
            tot_num = new.sum(axis=0)
            new2 = np.array(tot_num).tolist()
            if stack == True:
                new2 = [[new2[0]], [new2[1]]]
                chart.data = new2
                chart.categoryAxis.style = 'stacked'
                chart.bars[0].fillColor = HexColor('#7F0442')  # sains plum - supplied
                chart.bars[1].fillColor = HexColor('#bf82a1')  # sains light plum - rej (eligible)
            else:
                chart.data = [new2]
                chart.bars[0, 0].fillColor = HexColor('#F06C01')
                chart.bars[0, 1].fillColor = HexColor('#cccccc')
                chart.bars[0, 2].fillColor = HexColor('#4C4C4C')
                chart.bars[0, 3].fillColor = HexColor('#7F0442')
                chart.bars[0, 4].fillColor = HexColor('#bf82a1')
                if line == True:
                    chart.bars[0, 0].fillColor = HexColor('#f06c01')  # sains orange
                    chart.bars[0, 1].fillColor = HexColor('#7F0442')  # sains plum

            try:
                chart.barLabelFormat = '%i'
            except OverflowError:
                chart.barLabelFormat = '%s'
            chart.barLabels.nudge = 10  # adding spacing between bars
            chart.barLabels.fontName = 'MaryAnnBd'
            chart.barLabels.fontSize = 10

            if stack == True:
                def bar_format(number):
                    # for our supplied label
                    if number == tot_num[0]:
                        if (tot_num[0] >= 1) & (tot_num[1] == 0):
                            return '(' + str(tot_num[1]) + ')'
                        else:
                            return ''
                    elif number == tot_num[1]:
                        if (tot_num[0] >= 1) & (tot_num[1] == 0):
                            return ''
                        else:
                            return '(' + str(tot_num[1]) + ')'

                chart.barLabelFormat = bar_format

                comm = df_sorted['committed'].sum(axis=0)

                if (tot_num[0] >= 1) & (tot_num[1] == 0):
                    chart.barLabels.nudge = 25
                elif (tot_num[0] >= 1) & (tot_num[1] <= tot_num[0] * 0.5):
                    chart.barLabels.nudge = 25
                elif tot_num[1] <= (comm * 0.1):
                    chart.barLabels.nudge = 25
                else:
                    chart.barLabels.nudge = 16

        elif (grouped == True) | (stack == True):
            new = np.array(df_sorted[cols]).tolist()
            new = np.transpose(new).tolist()
            chart.data = new
            if purple == True:
                chart.bars[0].fillColor = HexColor('#f06c00')
                chart.bars[1].fillColor = HexColor('#cccccc')
                chart.bars[2].fillColor = HexColor('#8c1d55')
                chart.bars[3].fillColor = HexColor('#993668')
            else:
                chart.bars[0].fillColor = HexColor('#F06C01')
                chart.bars[1].fillColor = HexColor('#cccccc')
                chart.bars[2].fillColor = HexColor('#4C4C4C')
                chart.bars[3].fillColor = HexColor('#7F0442')
                chart.bars[4].fillColor = HexColor('#bf82a1')  ###a54f7b
            chart.bars.strokeWidth = 0.2
            chart.bars.strokeColor = colors.white
            if stack == True:
                chart.categoryAxis.style = 'stacked'
        else:
            if togroup:
                id_12months['Name'] = id_12months['Unit ID'].apply(lambda x: 'My Farm' if (x == df) else '')
                group = id_12months.sort_values('Supply Variance (12m avg)').reset_index()
                row_ID = group.index[group['Unit ID'] == df].tolist()[0]
                df_sorted = group

            chart.data = (np.array(df_sorted[cols]).tolist(),)
            chart.bars[0].fillColor = HexColor('#993668')
            if togroup:
                if transparent == True:
                    chart.bars[0].fillColor = Color(0, 0, 0,
                                                    alpha=0.4)  # alpha determines opacity amount (0=transparent, 1=opaque)
                    chart.bars[0].strokeColor = None
                chart.bars[0].strokeWidth = 0
                chart.bars[0, row_ID].fillColor = HexColor('#F06C01')
                chart.bars[0, row_ID].strokeWidth = 2
                chart.bars[0, row_ID].strokeColor = HexColor('#F06C01')
                chart.categoryAxis.visibleTicks = False  # hide as too many along x axis that it creates a thick line

        if catnames:
            chart.categoryAxis.categoryNames = catnames
        elif time_period == 'Future':
            new = np.array(df_sorted['date']).tolist()
            new = np.transpose(new)
            chart.categoryAxis.categoryNames = new.tolist()
        elif togroup:
            chart.categoryAxis.categoryNames = np.array(df_sorted['Name']).tolist()
        else:
            chart.categoryAxis.categoryNames = np.array(df_sorted['date']).tolist()
        chart.valueAxis.valueMin = 0

        if (chart.width == 130 * mm) & (catnames is None):
            chart.categoryAxis.labels.angle = 35
            chart.categoryAxis.labels.dx = -10
            chart.categoryAxis.labels.dy = -8

        def round_up_to_even(f):
            if roundto:
                return math.ceil(f / roundto) * roundto
            else:
                return math.ceil(f / 2) * 2

        new_max = df_sorted[cols]
        if maxval == True:
            if linecol is not None:
                new_max = df_sorted[linecol]
                if line == True:
                    a = new_max.sum(axis=0)
                    new = np.array(a).tolist()
                    bar_max = (max(new)) * 1.25
                else:
                    new = np.array(np.transpose(new_max)).tolist()
                    bar_max = max(max(new[0]) + max(new[1]), max(new[2]))
                Bar_Max_Value = bar_max
                # chart.valueAxis.valueMax = Bar_Max_Value
            elif line == True:
                new_max = new_max.sum(axis=0)
                Bar_Max_Value = new_max.max() * 1.25
                # chart.valueAxis.valueMax = Bar_Max_Value
            elif (grouped == True) & (stack == True):
                b = new_max.max()
                b = np.array(b).tolist()
                Bar_Max_Value = sum(b)
                # chart.valueAxis.valueMax = Bar_Max_Value
            elif (totals == True):
                Bar_Max_Value = new_max.sum().max()
            elif (grouped == True):
                Bar_Max_Value = new_max.max().max()
            else:
                Bar_Max_Value = new_max.max()
                #############
            if (Bar_Max_Value >= 0) & (Bar_Max_Value <= 25):
                roundto = 4
            elif (Bar_Max_Value >= 20) & (Bar_Max_Value < 30):
                roundto = 5
            elif (Bar_Max_Value >= 20) & (Bar_Max_Value < 100):
                roundto = 10
            elif (Bar_Max_Value >= 100) & (Bar_Max_Value < 200):
                roundto = 50
            elif Bar_Max_Value > 200:
                roundto = 100
            chart.valueAxis.valueMax = round_up_to_even(Bar_Max_Value)

        if (linecol is not None) & (showaxis == False):
            chart.barSpacing = 5
            chart.barWidth = 3.3
            if totals == True:
                chart.barWidth = 2.525

        # def DecimalFormatter(number):
        #    return "{:.1f}".format(number)
        try:
            chart.valueAxis.labelTextFormat = '%i'
        except OverflowError:
            chart.valueAxis.labelTextFormat = '%f'

        def round_down_to_even(f):
            if roundto:
                return math.floor(f / roundto) * roundto
            else:
                return math.floor(f / 1) * 1

        if valuemin == True:
            mydf = df_sorted[cols]
            if linecol is not None:
                mydf = df_sorted[linecol]
            try:
                if (len(cols) == 1) | (len(linecol) == 1):
                    a = min(mydf)
                    if a < 6:
                        a = 5
                    b = max(mydf)
            except TypeError:
                a = min(mydf)
                if a < 6:
                    a = 5
                b = max(mydf)
            else:
                a = mydf.min().min()
                if a < 6:
                    a = 5
                b = mydf.max().max()

            chart.valueAxis.valueMin = round_down_to_even(a)
            chart.categoryAxis.labels.angle = 45
            if wd >= 160 * mm:
                chart.categoryAxis.labels.angle = 0
            if (b > 0) & (a < 0):
                chart.categoryAxis.labels.dy = -75  # dy is the offset from its original positon
            elif (b == 0) & (a < 0):
                chart.categoryAxis.labels.dy = -150
            else:
                chart.categoryAxis.labels.dy = 0
            if b - a == 0:
                chart.valueAxis.labelTextFormat = '%i'
            elif b - a <= 2:
                chart.valueAxis.labelTextFormat = DecimalFormatter

        chart.valueAxis.labels.fontName = 'MaryAnn'
        chart.categoryAxis.labels.fontName = 'MaryAnn'

        if showaxis == False:
            chart.valueAxis.visible = False
            chart.categoryAxis.visible = False
        # ------
        ylabel = Label()
        ylabel.setText('No of Calves')
        if ylab:
            ylabel.setText(ylab)
        if x:
            ylabel.dx = chart.x - 10 * mm
        else:
            ylabel.dx = 8 * mm
        ylabel.dy = chart.y + 22 * mm
        if togroup:
            ylabel.dy = chart.y + 28 * mm
        ylabel.fontSize = 12
        ylabel.angle = 90
        ylabel.fontName = 'MaryAnnBd'
        ylabel.fillColor = HexColor('#4C4C4C')
        # ------
        if ttl:
            title = Label()
            title.setText(ttl)
            title.fontSize = 12
            title.fontName = 'MaryAnnBd'
            title.fillColor = HexColor('#4C4C4C')
            if ttlx:
                title.dx = ttlx
            else:
                title.dx = 105 * mm
            if ttlwidth:
                title.maxWidth = ttlwidth
            title.dy = ttly
        # ------
        if legend == True:
            leg = Legend()
            leg.alignment = 'right'
            if legx:
                leg.x = legx
            else:
                leg.x = 155 * mm
            leg.y = legy
            leg.deltax = 10
            leg.dxTextSpace = 10
            leg.columnMaximum = 3
            leg.fontName = 'MaryAnnBd'
            leg.fontSize = 12
            if grouped == True:
                if len(chart.data) == 5:
                    leg.autoXPadding = -20
                    leg.columnMaximum = 2
                elif len(chart.data) == 4:
                    leg.autoXPadding = -20
            output = []
            if grouped == True:
                for num, label in llabels:
                    result = (chart.bars[num].fillColor, label)
                    output.append(result)
                leg.colorNamePairs = output
                if legrow:
                    leg.columnMaximum = legrow
                else:
                    leg.columnMaximum = 2
            elif (totals == True) & (stack == True):
                for num, label in llabels:
                    result = (chart.bars[num].fillColor, label)
                    output.append(result)
                leg.colorNamePairs = output
            elif togroup:
                leg.colorNamePairs = [(HexColor('#F06C01'), llabels)]
            else:
                leg.colorNamePairs = [(HexColor('#993668'), llabels)]
        # ------
        if (line == True) & (showaxis == True):
            lp = LinePlot_label()
            if x:
                lp.x = x
            else:
                lp.x = 20 * mm
            lp.y = y
            if wd:
                lp.width = wd
            else:
                lp.width = 130 * mm
            lp.height = 50 * mm
            lp.data = [[(0, tot_num[0]), (1, tot_num[0])],
                       [(0, tot_num[0] * 1.25), (1, tot_num[0] * 1.25)]]
            lp.xValueAxis.visible = False
            lp.yValueAxis.visible = False
            lp.lines[0].strokeColor = colors.green
            lp.lines[1].strokeColor = colors.darkgreen
            lp.yValueAxis.valueMin = 0
            lp.yValueAxis.valueMax = chart.valueAxis.valueMax

            def new_format(number):
                if number == tot_num[0]:
                    return 'Green'
                elif number == tot_num[0] * 1.25:
                    return 'Green +'

            lp.lineLabelFormat = new_format
        # ------
        d.add(chart)
        d.add(ylabel)
        if legend == True:
            d.add(leg)
        if ttl:
            d.add(title)
        if (line == True) & (showaxis == True):
            if df_sorted['derogated?'].max() < 2:
                d.add(lp)
        d.drawOn(self, 0, 0)

    def add_pie(self, x, y, cols, time_period='Past', ttl=None, ttlwidth=None, llabels=None):
        d = Drawing(200, 100)
        pc = Pie()
        pc.x = x
        pc.y = y
        pc.width = 55 * mm
        pc.height = 55 * mm

        def zero_to_nan(sample):
            return [np.nan if x == 0 else x for x in sample]

        time_periods_ = ['Past', 'Future', 'Fixed']
        if time_period not in time_periods_:
            raise ValueError("Invalid time_period. Expected one of: %s" % sim_types)

        if time_period == 'Past':
            df_sorted = data[data['dateno'] < today.strftime('%m-%Y')]
        if time_period == 'Future':
            df_sorted = data[data['dateno'] >= today.strftime('%m-%Y')]
        elif time_period == 'Fixed':
            # the function returns the Aug at the start of the fixed period depending on todays month and returns %m-%Y
            last_aug_period = datetime.strptime(find_first_aug_in_period(today.strftime('%m')),
                                                '%m-%Y') + relativedelta(months=12)
            df_sorted = data[
                (data['dateno'] >= find_first_aug_in_period(today.strftime('%m'))) & (data['dateno'] < last_aug_period)]

        new = df_sorted[cols]
        new = new.sum(axis=0)
        new = np.array(new).tolist()

        p = []
        for val in new:
            try:
                div = (val * 100) / sum(new)
                try:
                    int(div)
                except ValueError:
                    pass
                except AttributeError:
                    pass
            except ZeroDivisionError:
                div = 0
            p.append(div)
        if sum(p) > 0:
            pc.data = p
        else:
            pc.data = zero_to_nan(p)

        style1 = ParagraphStyle(name='Normal', fontName='MaryAnn', fontSize=10
                                , textColor=HexColor('#4C4C4C'), alignment=TA_LEFT)
        a = []
        for val in new:
            if (sum(new) >= 1):
                try:
                    b = (val * 100) / sum(new)
                    try:
                        b = int(b)
                    except ValueError:
                        pass
                    except AttributeError:
                        pass
                except ZeroDivisionError:
                    b = val
            else:
                b = 0

            b = str(b)
            # a.append(b + '% \n '+str(val))
            a.append(str(int(val)))

        try:
            pc.labels = a
            pc.sideLabels = 1
        except ZeroDivisionError:
            pass

        colour_list = [HexColor('#cb5c01'), HexColor('#993668'), HexColor('#f38934')
            , HexColor('#8c1d55'), HexColor('#cccccc'), HexColor('#f5984d')
            , HexColor('#7F0442'), HexColor('#f27b1a'), HexColor('#a54f7b')
            , HexColor('#F06C01'), HexColor('#4C4C4C')]
        if llabels:
            for num, label in llabels:
                pc.slices[num].fillColor = colour_list[num]
        pc.slices.strokeColor = colors.white

        # try:
        #    pc.labels = a
        #    pc.sideLabels = 1
        # except ZeroDivisionError:
        #    pass
        #
        # colour_list = [HexColor('#cb5c01'),HexColor('#993668'),HexColor('#f38934')
        #               ,HexColor('#8c1d55'),HexColor('#cccccc'),HexColor('#f5984d')
        #               ,HexColor('#7F0442'),HexColor('#f27b1a'),HexColor('#a54f7b')
        #               ,HexColor('#F06C01'),HexColor('#4C4C4C')]
        # if llabels:
        #    for num,label in llabels:
        #        pc.slices[num].fillColor = colour_list[num]
        # pc.slices.strokeColor = colors.white

        leg = Legend()
        leg.alignment = 'right'
        leg.x = x - 10 * mm
        leg.y = y - 5 * mm
        leg.deltax = 0
        leg.autoXPadding = -30  # distance between keys inside legend
        leg.columnMaximum = 2

        leg.dxTextSpace = 5  # space away from legend colour box
        leg.fontName = 'MaryAnnBd'
        leg.fontSize = 12
        # leg.colorNamePairs = [(pc.slices[0].fillColor, 'supplied')
        #                     ,(pc.slices[1].fillColor, 'Rejected (Ineligible)')
        #                     ,(pc.slices[2].fillColor, 'Rejected (Eligible)')
        #                     ,(pc.slices[3].fillColor, 'Not Presented')]
        if llabels:
            output = []
            for num, label in llabels:
                result = (pc.slices[num].fillColor, label)
                output.append(result)
            leg.colorNamePairs = output
        title = Label()
        title.setText(ttl)
        title.fontSize = 12
        title.fontName = 'MaryAnnBd'
        title.fillColor = HexColor('#4C4C4C')
        title.dx = x + 25 * mm
        title.dy = y + 60 * mm
        if ttlwidth:
            title.maxWidth = ttlwidth
        if (sum(new) >= 1):
            d.add(pc)
            d.add(leg)
        else:
            self.circle(pc.x + (pc.width / 2), pc.y + (pc.height / 2), pc.width / 2)
            self.drawCentredString((pc.x + (pc.width / 2)), (pc.y + (pc.height / 2)), 'No Ineligible')
            self.drawCentredString((pc.x + (pc.width / 2)), ((pc.y + (pc.height / 2)) - 18), 'Rejections')
        d.add(title)
        d.drawOn(self, 0, 0)
        ## END OF PIE CHART ##

    def draw_paragraph(self, text, max_width, max_height, spacing, x=None, y=None, bkgd_col=None,
                       font_col=None, font_size=None, border_col=colors.black, font=None
                       , align=None):
        bodyStyle = ParagraphStyle('Body', fontName='MaryAnn', fontSize=15, leading=28, spaceBefore=6
                                   , borderWidth=1, borderPadding=6, alignment=1, textColor=colors.black)
        if (bkgd_col is not None) | (font_col is not None) | (font is not None):
            bodyStyle = ParagraphStyle('Body', fontName=font, fontSize=font_size
                                       , leading=spacing, spaceBefore=4
                                       , borderColor=border_col, borderWidth=1, borderPadding=6
                                       , backColor=bkgd_col, textColor=font_col, alignment=0, align=align)
        p = Paragraph(text, bodyStyle)
        p.wrap(max_width, max_height)
        if x:
            p.drawOn(self, x, y)
        else:
            p.drawOn(self, 20 * mm, 205 * mm)

    def add_page2(self):
        self.setFont('MaryAnnBd', 16, leading=None)
        self.setFillColor(HexColor('#F06C01'))  # orange
        self.drawCentredString(105 * mm, 280 * mm, 'title here')
        ############# START OF HEADER #############
        add_table(self, matrix=True, y=(280 - 17.5) * mm)

        # the function below find_first_aug returns '%m-%Y'
        string_of_time_period = 'August ' + find_first_aug_in_period(today.strftime('%m'))[-4:] + \
                                ' to July ' + (datetime.strptime(find_first_aug_in_period(today.strftime('%m')),
                                                                 '%m-%Y') + relativedelta(years=1)).strftime('%Y')
        draw_paragraph(self,
                       """
                       description here""" + string_of_time_period + """description here
                       """  # you can add <br /> to force a line break
                       , 178 * mm, 50 * mm, x=16 * mm, y=(280 - 17.5 - 35) * mm, bkgd_col=HexColor('#8c1d55'),
                       border_col=colors.black
                       , font_col=colors.white, font_size=10, font='MaryAnnBd', spacing=20)
        ############# END OF HEADER #############

        # Overall Breakdown Graph (past 12 months)
        add_bar(self, cols=['col names']
                , y=160 * mm, legy=225 * mm, ttly=215 * mm, ttlx=50 * mm, time_period='Fixed'
                , wd=(pgwidth * 0.5) * mm, totals=True, legend=False, maxval=True
                , catnames=['col descriptions for graph']
                , ttl='title'
                )
        

        ############# START FOOTER #############
        self.setFont('MaryAnnBd', 13, leading=None)
        self.setFillColor(HexColor('#4C4C4C'))  # grey
        self.drawCentredString((pgwidth / 2) * mm, 45 * mm,
                               'Period of:  ' + datetime.strptime(find_first_aug_in_period(today.strftime('%m')),
                                                                  '%m-%Y').strftime('%b-%y') + \
                               '  to  Jul-' + (datetime.strptime(find_first_aug_in_period(today.strftime('%m')),
                                                                 '%m-%Y') + relativedelta(years=1)).strftime('%y'))
        add_table(self, page1=True, time_period='Fixed')
        ############# END OF FOOTER #############
        self.showPage()

    if TO_RUN == 'yes':
        ##----------------
        new_df.append(data)
        ##----------------
        # add all pages here
        add_page1(c)
        add_page2(c)

        # save the pdf

        c.save()
        ## END OF GENERATE REPORT ##
end_time = timeit.default_timer()
print('time took = ',round((end_time - start_time)/60,2),' minutes')
