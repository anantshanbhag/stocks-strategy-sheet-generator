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
