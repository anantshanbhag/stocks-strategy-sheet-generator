import numpy as np
import pandas as pd
from datetime import date, datetime, timedelta
from nsepy import get_history
from nsepy.derivatives import get_expiry_date
from nsetools import Nse

def create_offline_sheet(bhav_date_name, expiry_month_name):
    # Constants
    MONTH_NAMES = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN","JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
    nsetools = Nse()

    # Set Bhav Date
    bhav_month_name = bhav_date_name[2:5]
    bhav_month = MONTH_NAMES.index(bhav_month_name) + 1
    bhav_day = int(bhav_date_name[:2])
    bhav_year = int(bhav_date_name[5:])

    bhav_date = date(bhav_year, bhav_month, bhav_day)
    pre_bhav_date = bhav_date - timedelta(10)
    inception_date = bhav_date - timedelta(400)
    now_date = datetime.now() #now_date.year, now_date.month, now_date.day, now_date.hour, now_date.minute, now_date.second

    # Get Expiry Date
    expiry_month = (MONTH_NAMES.index(expiry_month_name) + 1) if expiry_month_name != "" and expiry_month_name.upper() != "NA" else now_date.month
    #expiry_date = get_expiry_date(year=now_date.year, month=expiry_month)
    #expiry_date = get_expiry_date(year=2019, month=8)   # Temp
    expiry_date = date(2019, 9, 26)
    expiry_date_format = date(expiry_date.year,expiry_date.month,expiry_date.day).strftime('%d-%b-%Y') #'29-Aug-2019'

    # Get Symbols and Lot Sizes and create Sheet
    fno_lot_sizes = nsetools.get_fno_lot_sizes()
    sheet = pd.DataFrame()
    sheet['SYMBOL'] = fno_lot_sizes.keys()
    sheet['Lot'] = fno_lot_sizes.values()

    return sheet