#%% packages & adding fonts
import pandas as pd
import numpy as np
from numpy import inf
import math, os, glob, re, timeit
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

start_time = timeit.default_timer()

USER = os.getcwd().split('\\')[2]
MYPATH = fr"C:\Users\{USER}\{data path here}"


# if the font is a 'true type font' we download (I downloaded from https://www.onlinewebfonts.com)
# can do the following to add it in:
pdfmetrics.registerFont(TTFont('PTSans',   os.path.join(MYPATH,'TTFonts','PTSans-Regular.ttf')))
pdfmetrics.registerFont(TTFont('PTSansBd', os.path.join(MYPATH,'TTFonts','PTSans-Bold.ttf')))
pdfmetrics.registerFont(TTFont('PTSansI',  os.path.join(MYPATH,'TTFonts','PTSans-Italic.ttf')))
pdfmetrics.registerFont(TTFont('PTSansBdI',os.path.join(MYPATH,'TTFonts','PTSans-BoldItalic.ttf')))

registerFontFamily('PTSans',normal='PTSans',bold='PTSansBd',italic='PTSansI',boldItalic='PTSansBdI')

#%% adding data

df = pd.read_excel(os.path.join(MYPATH , 'folder name','file name.xlsx'))

#%% the loop

###########################################################################
#                           DO NOT TOUCH !!!                              #
###########################################################################
pgwidth = 210 * mm
pgheight = 295 * mm


def generate_report(df, data, pdf_file_name):
    c = canvas.Canvas(pdf_file_name, pagesize=A4)
    c.setFont('PTSansBd', 18, leading=None)
    c.setFillColor(HexColor('#425563'))  # grey
    c.drawString(pgwidth * 0.25, 280 * mm,
                 'Herd Performance: ' + str(np.array(data['Reference']).tolist()[0]) + ' ' + str(
                     np.array(data['Unit Name']).tolist()[0]))
    c.drawImage(os.path.join(MYPATH,'Input', 'ref_logo.png'), 12.5 * mm, 285 * mm, 20 * mm
                , mask=None, preserveAspectRatio=True, anchorAtXY=True)
    c.drawImage(os.path.join(MYPATH,'Input', 'moa_logo.jpg'), 35 * mm, 285 * mm, 20 * mm
                , mask=None, preserveAspectRatio=True, anchorAtXY=True)

    def all_pages(self):
        self.setFont('PTSansBd', 10, leading=None)
        self.setFillColor(HexColor('#425563'))
        self.setFont('PTSans', 10, leading=None)
        
        time_period = ' - '.join(data['year_label'].iloc[0].split(' | ')[0:2])
        self.drawRightString(pgwidth - 5 * mm, pgheight - 5 * mm, time_period)
        self.drawImage(os.path.join(MYPATH,'Input', 'image1.png'), pgwidth - 35 * mm, 50 * mm, height=45 * mm
                       , mask=None, preserveAspectRatio=True, anchorAtXY=True)
        
        self.drawImage(os.path.join(MYPATH,'Input', 'logo1.png'), pgwidth - 60 * mm, 10 * mm, height=20 * mm
                       , mask=None, preserveAspectRatio=True, anchorAtXY=True)
        self.drawImage(os.path.join(MYPATH,'Input', 'logo2.jpg'), pgwidth - 25 * mm, 10 * mm, height=20 * mm
                       , mask=None, preserveAspectRatio=True, anchorAtXY=True)

    def add_table(self, x, y, row=None, wd=None, catnames=False, names=None, numbers=None
                  , change_row=None, change_row1=None):
        style = ParagraphStyle(name='Normal', fontName='PTSans', fontSize=8
                               , textColor=HexColor('#425563'), alignment=TA_LEFT)
        if catnames == True:
            t = Table(row, colWidths=wd * (1 / len(row[0])), rowHeights=15 * mm, style=None)
        elif wd:
            if names is not None:
                col1 = names
                col2 = np.array(data[numbers]).tolist()[0]
                output = []
                for num in range(len(names)):
                    row = [names[num], col2[num]]
                    output.append(row)
                row = output
            if (change_row is not None) | (change_row1 is not None):
                b = [change_row] * 4 + [6 * mm] * (len(row) - 4)
                if change_row1:
                    b = [6 * mm] * (len(row) - 1) + [change_row]
                t = Table(row, colWidths=(wd * 0.692, wd * 0.307), rowHeights=b, style=None)
            else:
                t = Table(row, colWidths=(wd * 0.692, wd * 0.307), rowHeights=6 * mm, style=None)
        else:
            if names is not None:
                col1 = names
                col2 = np.array(data[numbers]).tolist()[0]
                output = []
                for num in range(len(names)):
                    row = [names[num], col2[num]]
                    output.append(row)
                row = output
                if (change_row is not None) | (change_row1 is not None):
                    b = [change_row] * 4 + [6 * mm] * (len(row) - 4)
                    if change_row1:
                        b = [6 * mm] * (len(row) - 1) + [change_row]
                    t = Table(row, colWidths=(135 * mm, 60 * mm), rowHeights=b, style=None)
                else:
                    t = Table(row, colWidths=(135 * mm, 60 * mm), rowHeights=6 * mm, style=None)

        if catnames == False:
            table_style = []
            for i, col in enumerate(np.transpose(row)):  # using transpose to flip the data so we only get
                # the number of columns
                if i % 2 == 0:
                    table_style.append(('TEXTCOLOR', (i, 0), (i, -1), HexColor('#425563')))  # dark grey
                    table_style.append(('BACKGROUND', (i, 0), (i, -1), colors.white))
                    table_style.append(('GRID', (i, 0), (i, -1), .5, HexColor('#425563')))
                    table_style.append(('FONTSIZE', (i, 0), (i, -1), 8))
                    table_style.append(('ALIGN', (i, 0), (i, -1), 'LEFT'))
                else:
                    table_style.append(('TEXTCOLOR', (i, 0), (i, -1), HexColor('#425563')))  # dark grey
                    table_style.append(('BACKGROUND', (i, 0), (i, -1), HexColor('#D9D2D0')))  # warm dusk
                    table_style.append(('GRID', (i, 0), (i, -1), .5, HexColor('#425563')))

        t.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')  # rows,cols
                                  , ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
                                  , ('FONTSIZE', (0, 0), (-1, -1), 8)
                                  , ('FONTNAME', (0, 0), (-1, -1), 'PTSans')
                               ]))
        if catnames == False:
            t.setStyle(table_style)

        t.wrapOn(self, 0, 0)  # w,h
        t.drawOn(self, x, y)

    def add_bar(self, x, y, ylab, cols=None, cols1=None, cols2=None, catnames=False, wd=None, ht=None, future=False
                , legend=False, legx=None, legy=None, leg_row=None, llabels=None, maxval=False, valuemin=False
                , ttl=None, ttly=None, ttlx=None, grouped=False, stack=False, totals=False, roundto=None):

        d = Drawing(200, 100)
        chart = VerticalBarChart()
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
        if (grouped == True) | (stack == True):
            if cols is not None:
                new = np.array(data[cols]).tolist()
            else:
                row1 = np.array(data[cols1]).tolist()
                row2 = np.array(data[cols2]).tolist()
                new = [row1[0], [0] + row2[0]]
            # new = np.transpose(new).tolist()
            chart.data = new
            if len(data) == 2:
                chart.bars[0].fillColor = HexColor('#A7A110')  # grass
                chart.bars[1].fillColor = HexColor('#CD1719')  # red
            if len(data) == 1:
                chart.bars[0].fillColor = HexColor('#4D87A4')  # blue slate
            chart.bars.strokeWidth = 0.2
            chart.bars.strokeColor = colors.white
            if stack == True:
                chart.categoryAxis.style = 'stacked'
        else:
            chart.data = [np.array(data[cols]).tolist()[0]]
            chart.bars[0].fillColor = HexColor('#4D87A4')

        if catnames:
            chart.categoryAxis.categoryNames = catnames
        else:
            chart.categoryAxis.categoryNames = ['  '] * len(data)

        # if chart.width <= 130*mm:
        #    chart.categoryAxis.labels.angle = 35

        def round_up_to_even(f):
            if f == np.nan:
                pass
            else:
                if roundto:
                    return math.ceil(f / roundto) * roundto
                else:
                    return math.ceil(f / 2) * 2
                    # Sort out max values

        if maxval == True:
            if cols1 is not None:
                data1 = data[cols1].loc[:, data[cols1].dtypes == 'int']
                data2 = data[cols2].loc[:, data[cols2].dtypes == 'int']
                Bar_Max_Value = max(data1.max().max(), data2.max().max())
            elif len(cols) > 1:
                Bar_Max_Value = data[cols].max().max()
            elif len(cols) == 1:
                Bar_Max_Value = data[cols].max()
                #####
            if Bar_Max_Value > 20:
                roundto = 10
                if Bar_Max_Value > 200:
                    roundto = 100
            chart.valueAxis.valueMax = round_up_to_even(Bar_Max_Value)

        # Formatting the numbers dependant on bar scale
        if maxval == True:
            if (Bar_Max_Value <= 2) & (Bar_Max_Value > 0) & (valuemin == False):
                chart.valueAxis.labelTextFormat = 'specify_here'
            else:
                try:
                    chart.valueAxis.labelTextFormat = '%i'
                except OverflowError:
                    chart.valueAxis.labelTextFormat = '%f'

        ##########
        # ------
        if ylab:
            ylabel = Label()
            ylabel.setText(ylab)
            if x:
                ylabel.dx = chart.x - 10 * mm
            else:
                ylabel.dx = 8 * mm
            ylabel.dy = chart.y + 22 * mm
            ylabel.fontSize = 12
            ylabel.angle = 90
            ylabel.fontName = 'PTSansBd'
            ylabel.fillColor = HexColor('#425563')
        # ------
        if ttl:
            title = Label()
            title.setText(ttl)
            title.fontSize = 12
            title.fontName = 'PTSansBd'
            title.fillColor = HexColor('#425563')
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
            leg.fontName = 'PTSansBd'
            leg.fontSize = 8
            if (grouped == True) | (stack == True):
                leg.autoXPadding = 25
                # leg.deltax = 20
                # leg.dxTextSpace = 20
            output = []
            if (grouped == True) | (stack == True):
                for num, label in llabels:
                    result = (chart.bars[num].fillColor, label)
                    output.append(result)
                leg.colorNamePairs = output
                if leg_row:
                    leg.columnMaximum = leg_row
                else:
                    leg.columnMaximum = 2
            # else:
            #    leg.colorNamePairs = [(chart.bars[0].fillColor, llabels) ]
        #########
        d.add(chart)
        if ylab:
            d.add(ylabel)
        if legend == True:
            d.add(leg)
        if ttl:
            d.add(title)
        d.drawOn(self, 0, 0)

    def add_paragraph(self, text, x, y, max_width, max_height, spacing, bkgd_col=None,
                      font_col=None, font_size=None, border_col=None, font=None
                      , align=None):
        bodyStyle = ParagraphStyle('Body', fontName=font, fontSize=font_size
                                   , leading=spacing, spaceBefore=4
                                   , borderColor=border_col, borderWidth=1, borderPadding=6
                                   , backColor=bkgd_col, textColor=font_col, alignment=0, align=align)
        p = Paragraph(text, bodyStyle)

        p.wrap(max_width, max_height)
        p.drawOn(self, x, y)

    def add_page_1(self):
        all_pages(self)
        self.setStrokeColor(HexColor('#F06C01'))
        self.setLineWidth(1)
        # self.line(5*mm, pgheight/2, pgwidth-5*mm, pgheight/2)
        self.setFont('PTSansBd', 10, leading=None)

        current_year = data['year_label'].iloc[0].split(' | ')[1]
        # current_year = df['year_start'].astype(str)

        self.drawString(10 * mm, 269 * mm, 'refking levels')
        self.drawString(74.5 * mm, 269 * mm, data['year_label'].iloc[0])

        style = ParagraphStyle(name='Normal', fontName='PTSans', fontSize=8
                               , textColor=HexColor('#425563'), alignment=TA_LEFT)
        # names: description for left side of table, numbers are the values to pull to place in right hand coumn of table
        # for a cell you can add a Paragraph object or a plain text object
        # example 1
        add_table(self, 5 * mm, 191.5 * mm, wd=195 * mm * 0.5, change_row=10 * mm  # 187.5
                  , names=[Paragraph("""description here""" + current_year, style)
                , Paragraph("""description here""", style)
                , Paragraph("""description here""" + current_year, style)
                , Paragraph("""description here""", style)
                , 'col 2'
                , 'col 14']
                  , numbers=['col name here' + '_' + current_year
                , 'col name here'
                , 'col name here' + '_' + current_year
                , 'col name here'
                , 'col name here'
                , 'col name here']
        )
        # self.setStrokeColor(HexColor('#F06C01'))
        self.drawString(110 * mm, 269 * mm, 'title')
        self.drawString(176 * mm, 269 * mm, data['coldate'].iloc[0])
        

    add_page_1(c)

    # save the pdf
    c.save()

    ## END OF GENERATE REPORT ##


def import_data(df):
    for farm, farms in tqdm(df.groupby('Unit ID')):
        farmname = farms['Unit Name'].unique()
        ref = farms['Reference'].unique()
        pdf_name = str(farm) + '_name_reports_' + str(ref[0]) + '_' + str(farmname[0]) + '.pdf'
        pdf_file_name = os.path.join(MYPATH,'name_reports', pdf_name)
        generate_report(farm, farms, pdf_file_name)


import_data(df)
