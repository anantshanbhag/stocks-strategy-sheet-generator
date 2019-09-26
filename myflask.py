from flask import Flask, make_response, request, send_file
import numpy as np
import pandas as pd
from datetime import date, datetime, timedelta
from io import BytesIO
from nsepy import get_history
from nsepy.derivatives import get_expiry_date
from nsetools import Nse
app = Flask(__name__)
# from processing import create_offline_sheet

""" Delayed Job """
# # for delayed job
# from redis import Redis
# from rq import Queue
# q = Queue(connection=Redis())

# r = redis.Redis()
# q = Queue(connection=r)

# def background_task(n):
    # """ Function that returns len(n) and simulates a delay """
    # delay = 2
    # print("Task running")
    # print(f"Simulating a {delay} second delay")
    # time.sleep(delay)
    # print(len(n))
    # print("Task complete")
    # return len(n)
	
# @app.route("/task")
# def index():
    # if request.args.get("n"):
        # job = q.enqueue(background_task, request.args.get("n"))
		# q_len = len(q)
        # return f"Task ({job.id}) added to queue at {job.enqueued_at}, {q_len} tasks in the queue"

    # return "No value for count provided"

# if __name__ == "__main__":
    # app.run()
	
""" Offlinesheet """
def create_offline_sheet(bhav_date_name, expiry_month_name):
    # Constants
    MONTH_NAMES = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
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
    # Temp expiry date
    #expiry_date = get_expiry_date(year=2019, month=8)   # Temp
    expiry_date = date(2019, 9, 26)    # Temp
    expiry_date_format = date(expiry_date.year,expiry_date.month,expiry_date.day).strftime('%d-%b-%Y') #'29-Aug-2019'

    # Get Symbols and Lot Sizes and create Sheet
    fno_lot_sizes = nsetools.get_fno_lot_sizes()
    sheet = pd.DataFrame()
    sheet['SYMBOL'] = fno_lot_sizes.keys()
    sheet['Lot'] = fno_lot_sizes.values()
    ## Temp Dataframe
    # data = {'Name':['Tom', 'nick', 'krish', 'jack'], 'Age':[20, 21, 19, 18]}   # Temp
    # sheet = pd.DataFrame(data)   # Temp

    #++++++++++++ Sheet Processing
    for symbol in sheet['SYMBOL']:
        # Get Futures historical data set Position Values
        is_index_future = True if symbol == 'BANKNIFTY' or symbol == 'NIFTY' or symbol == 'NIFTYIT' else False
        futures_data = get_history(symbol=symbol, start=pre_bhav_date, end=bhav_date, futures=True, index=is_index_future, expiry_date=expiry_date)
        
        sheet.loc[(sheet['SYMBOL']==symbol), 'Open'] = float(futures_data[-1:]['Open'])
        sheet.loc[(sheet['SYMBOL']==symbol), 'High'] = float(futures_data[-1:]['High'])
        sheet.loc[(sheet['SYMBOL']==symbol), 'Low'] = float(futures_data[-1:]['Low'])
        sheet.loc[(sheet['SYMBOL']==symbol), 'Close'] = float(futures_data[-1:]['Close'])
        sheet.loc[(sheet['SYMBOL']==symbol), 'ClosePrev'] = float(futures_data[-2:-1]['Close'])
        sheet['%Close'] = (sheet['Close'] / sheet['ClosePrev'] - 1)*100
        sheet.loc[(sheet['SYMBOL']==symbol), 'OI'] = float(futures_data[-1:]['Open Interest'])
        sheet.loc[(sheet['SYMBOL']==symbol), 'OIPrev'] = float(futures_data[-2:-1]['Open Interest'])
        sheet['%OI'] = (sheet['OI'] / sheet['OIPrev'] - 1)*100
        sheet['OIChg'] = (sheet['OI'] - sheet['OIPrev'])
        sheet.loc[(sheet['SYMBOL']==symbol), 'ExpDt'] = expiry_date_format

        # Set Entry and SL values
        _buy_entry = max(futures_data[-4:]['High']) * 1.01
        _sell_entry = min(futures_data[-4:]['Low']) * .99
        _2day_min_low = min(futures_data[-2:]['Low'])
        _2day_max_high = max(futures_data[-2:]['High'])

        sheet.loc[(sheet['SYMBOL']==symbol), 'BuyEntry'] = _buy_entry
        sheet.loc[(sheet['SYMBOL']==symbol), 'SellEntry'] = _sell_entry
        sheet.loc[(sheet['SYMBOL']==symbol), 'BuySL'] = _2day_min_low if (_2day_min_low > _buy_entry*.97) else _buy_entry*.97
        sheet.loc[(sheet['SYMBOL']==symbol), 'SellSL'] = _2day_max_high if (_2day_max_high < _sell_entry*1.03) else _sell_entry*1.03

        # Get Spot historical data set Moving Averages
        if not is_index_future:
            spot_data = get_history(symbol=symbol, start=inception_date, end=bhav_date)
            sheet.loc[(sheet['SYMBOL']==symbol), 'StockLast'] = spot_data[-1:]['Last'].mean()
            sheet.loc[(sheet['SYMBOL']==symbol), 'MovingAverage50'] = spot_data[-50:]['Last'].mean()
            sheet.loc[(sheet['SYMBOL']==symbol), 'MovingAverage100'] = spot_data[-100:]['Last'].mean()
            sheet.loc[(sheet['SYMBOL']==symbol), 'MovingAverage200'] = spot_data[-200:]['Last'].mean()

    # Set Position type
    sheet.loc[(sheet['%Close']>2) & (sheet['%OI']>10), 'Position'] = 'Long Buildup'
    sheet.loc[(sheet['%Close']<-2) & (sheet['%OI']>10), 'Position'] = 'Short Buildup'
    sheet.loc[(sheet['%Close']<-2) & (sheet['%OI']<-10), 'Position'] = 'Long Unwinding'
    sheet.loc[(sheet['%Close']>2) & (sheet['%OI']<-10), 'Position'] = 'Short Covering'
    sheet = sheet.fillna('')
    sheet.loc[sheet['Position']=='Long Buildup', 'Strategy'] = 'Buy'
    sheet.loc[sheet['Position']=='Short Covering', 'Strategy'] = 'Buy'
    sheet.loc[sheet['Position']=='Short Buildup', 'Strategy'] = 'Sell'
    sheet.loc[sheet['Position']=='Long Unwinding', 'Strategy'] = 'Sell'
    sheet = sheet.sort_values(by='Strategy')
    sheet = sheet.fillna('')

    # Set Target and Scope
    sheet['BuyTarget'] = sheet['BuyEntry'] * 1.03
    sheet['SellTarget'] = sheet['SellEntry'] * .97
    sheet['BuyScope'] = (sheet['BuyEntry'] / sheet['Close'] - 1)*100
    sheet['SellScope'] = (sheet['Close'] / sheet['SellEntry'] - 1)*100

    # Set Pivot, Support and Resistance
    sheet['Pivot'] = (sheet['High'] + sheet['Low'] + sheet['Close']) / 3
    sheet['S3'] = sheet['Low'] - 2 * (sheet['High'] - sheet['Pivot'])
    sheet['S2'] = sheet['Pivot'] - (sheet['High'] - sheet['Low'])
    sheet['S1'] = (2 * sheet['Pivot']) - sheet['High']
    sheet['R1'] = (2 * sheet['Pivot']) - sheet['Low']
    sheet['R2'] = sheet['Pivot'] + (sheet['High'] - sheet['Low'])
    sheet['R3'] = sheet['High'] + 2 * (sheet['Pivot'] - sheet['Low'])

    # Set Rating for Moving Average
    sheet['isAbove50'] = sheet.apply(lambda x: 0.6 if (x['StockLast'] > x['MovingAverage50']) else 0, axis=1)
    sheet['isAbove100'] = sheet.apply(lambda x: 0.3 if (x['StockLast'] > x['MovingAverage100']) else 0, axis=1)
    sheet['isAbove200'] = sheet.apply(lambda x: 0.1 if (x['StockLast'] > x['MovingAverage200']) else 0, axis=1)
    sheet['isBelow50'] = sheet.apply(lambda x: 0.6 if (x['StockLast'] < x['MovingAverage50']) else 0, axis=1)
    sheet['isBelow100'] = sheet.apply(lambda x: 0.3 if (x['StockLast'] < x['MovingAverage100']) else 0, axis=1)
    sheet['isBelow200'] = sheet.apply(lambda x: 0.1 if (x['StockLast'] < x['MovingAverage200']) else 0, axis=1)
    sheet['BuyMovingAverage'] = sheet['isAbove50'] + sheet['isAbove100'] + sheet['isAbove200']
    sheet['SellMovingAverage'] = sheet['isBelow50'] + sheet['isBelow100'] + sheet['isBelow200']

    # Convert column to datatype float
    sheet[["StockLast", "MovingAverage50","MovingAverage100","MovingAverage200"]] = sheet[["StockLast", "MovingAverage50","MovingAverage100","MovingAverage200"]].apply(pd.to_numeric)

    # Set Buy Ratings
    sheet['isBuyPosition'] = sheet.apply(lambda x: 1 if ((x['Position']=='Long Buildup') | (x['Position']=='Short Covering')) else 0, axis=1)
    sheet['isOpenLow'] = sheet.apply(lambda x: 1 if (x['Open'] == x['Low']) else 0, axis=1)
    sheet['isAbovePivot'] = sheet.apply(lambda x: 1 if (x['StockLast'] > x['Pivot']) else 0, axis=1)
    sheet['isBuyEntryHit'] = sheet.apply(lambda x: 1 if (x['Close'] >= x['BuyEntry']) else 0, axis=1)
    sheet['BuyRating'] = sheet['BuyMovingAverage'] + sheet['isBuyPosition'] + sheet['isOpenLow'] + sheet['isAbovePivot'] + sheet['isBuyEntryHit']

    # Set Sell Ratings
    sheet['isSellPosition'] = sheet.apply(lambda x: 1 if ((x['Position']=='Short Buildup') | (x['Position']=='Long Unwinding')) else 0, axis=1)
    sheet['isOpenHigh'] = sheet.apply(lambda x: 1 if (x['Open'] == x['High']) else 0, axis=1)
    sheet['isBelowPivot'] = sheet.apply(lambda x: 1 if (x['StockLast'] < x['Pivot']) else 0, axis=1)
    sheet['isSellEntryHit'] = sheet.apply(lambda x: 1 if (x['Close'] <= x['SellEntry']) else 0, axis=1)
    sheet['SellRating'] = sheet['SellMovingAverage'] + sheet['isSellPosition'] + sheet['isOpenHigh'] + sheet['isBelowPivot'] + sheet['isSellEntryHit']

    # Rename, Align & Round up Sheet
    sheet.rename(columns={'BuyEntry':'↑Entry','BuyTarget':'↑Tgt','BuySL':'↑SL','BuyScope':'↑Scope','BuyRating':'↑Rtg','SellEntry':'↓Entry','SellTarget':'↓Tgt','SellSL':'↓SL','SellScope':'↓Scope','SellRating':'↓Rtg','BuyMovingAverage':'↑MAvg','isAbovePivot':'↑Pvot','isOpenLow':'↑OpnLo','isBuyPosition':'↑Posn','isBuyEntryHit':'↑HitEnt','SellMovingAverage':'↓MAvg','isBelowPivot':'↓Pvot','isOpenHigh':'↓OpnHi','isSellPosition':'↓Posn','isSellEntryHit':'↓HitEnt'}, inplace=True)

    # Align
    sheet['LTP'] = sheet['Close']
    sheet['OInt'] = sheet['OI']
    sheet['%chOI'] = sheet['%OI']
    sheet = sheet[['SYMBOL','Lot','LTP','↑Rtg','↑Scope','↑Entry','↑Tgt','↑SL','↓Rtg','↓Scope','↓Entry','↓Tgt','↓SL','Position','OInt','%chOI','↑MAvg','↑Pvot','↑OpnLo','↑Posn','↓MAvg','↓Pvot','↓OpnHi','↓Posn','↑HitEnt','↓HitEnt','Open','High','Low','Close','ClosePrev','%Close','OI','OIPrev','%OI','OIChg','StockLast','MovingAverage50','MovingAverage100','MovingAverage200','S3','S2','S1','Pivot','R1','R2','R3','isAbove50','isAbove100','isAbove200']]

    # Decimal round up
    sheet = sheet.round(1)

    # Sort sheet to view Bullish symbols
    sheet.sort_values(['↑Scope', '↑Rtg', '↑Posn'], ascending=[True, False, False], inplace=True)

    # Sort sheet to view Bearish symbols
    #sheet.sort_values(['↓Scope', '↓Rtg', '↓Posn'], ascending=[True, False, False], inplace=True)

    return sheet

# @app.route("/")
# def hello_world():
    # return '<h1>Hello, World! Changed :D</h1>'
@app.route("/", methods=["GET", "POST"])
def hello_world():
    errors = ""
    if request.method == "POST":
        bhav_date_name = None
        expiry_month_name = None
        try:
            bhav_date_name = str(request.form["bhav_date_name"])
        except:
            errors += "<p>{!r} is not a string.</p>\n".format(request.form["bhav_date_name"])
        try:
            expiry_month_name = str(request.form["expiry_month_name"])
        except:
            errors += "<p>{!r} is not a string.</p>\n".format(request.form["expiry_month_name"])
        if bhav_date_name is not None and expiry_month_name is not None:
            sheet = create_offline_sheet(bhav_date_name, expiry_month_name)
            #sheet = q.enqueue(create_offline_sheet, args=(bhav_date_name, expiry_month_name))

            #++++++++++++ File operations
            now_date = datetime.now() #now_date.year, now_date.month, now_date.day, now_date.hour, now_date.minute, now_date.second
            file_name = 'offlinesheet'+bhav_date_name+'_'+str(now_date.year)+str(now_date.month)+str(now_date.day)+str(now_date.hour)+str(now_date.minute)+str(now_date.second)
            file_extension = '.csv'
            file_name = file_name + file_extension
            #sheet.to_excel(file_name)

            #output = BytesIO()
            #writer = pd.ExcelWriter(output, engine='xlsxwriter')
            #sheet.to_excel(writer, sheet_name='Sheet1')
            #writer.save()
            #output.seek(0)
            #return send_file(output, attachment_filename='output.xlsx', as_attachment=True)

            response = make_response(sheet.to_csv())
            response.headers["Content-Disposition"] = "attachment; filename="+file_name
            response.headers["Content-Type"] = "text/csv"
            return response

    return '''
        <html>
            <body>
                {errors}
                <p>Enter your numbers:</p>
                <form method="post" action="." enctype="multipart/form-data">
                    Enter Current Date in ddMONyyyy eg. 14AUG2019
                    <p><input name="bhav_date_name" /></p>
                    Enter other Expiry Month name in MON eg. SEP
                    <p><input name="expiry_month_name"  /></p>
                    <p><input type="submit" value="Create Offline Sheet" /></p>
                </form>
            </body>
        </html>
    '''

if __name__ == '__main__':
    app.run()
