import yfinance as yf
import pandas as pd
import argparse
import sys
import datetime
import os.path

def parse_args():
    parser = argparse.ArgumentParser(
            description='Download historical prices ticks')

    parser.add_argument('--sharename', default='CBA.AX', required=False,
                        help='Share name to download')
    
    parser.add_argument('--interval', default='1m', required=False,
                        choices=['1m', '5m', '15m', '30m'],
                        help='Interval ticks to get data for')

    return parser.parse_args()

def download_data(args):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    days_ago = None
    if args.interval == "1m":
        # Only allowed up to last 7 days of data
        days_ago = (datetime.datetime.now() - datetime.timedelta(days = 7)).strftime("%Y-%m-%d")
    if args.interval == "15m":
        # Only allowed up to last 60 days of data
        days_ago = (datetime.datetime.now() - datetime.timedelta(days = 59)).strftime("%Y-%m-%d")

    dataF = yf.download("{}".format(args.sharename), start=days_ago, end=today, interval=args.interval)
    market_data = dataF.iloc[:,:]
    date_indexes = market_data.index
    f = open("./data/historical-prices/ticks/{}-{}-{}-{}.csv".format(args.sharename.lower().split(".")[0], today, days_ago, args.interval), "w")
    f.write("Date,Open,High,Close,Adj Close,Volume\n")
    for idx in date_indexes:
        f.write("{},{},{},{},{},{},{}\n".format(idx,market_data["Open"][idx],
                                                market_data["High"][idx],
                                                market_data["Low"][idx],
                                                market_data["Close"][idx],
                                                market_data["Adj Close"][idx],
                                                market_data["Volume"][idx]))
    # dataF.open.iloc

    f.close()

if __name__ == "__main__":
    args = parse_args()
    download_data(args)

#-------------------------------- OLD CODE --------------------------------#
# import yfinance as yf
# cba = yf.Ticker("CBA.AX")
# hist = cba.history(period="3mo")

# num_shares = 100

# # print(hist)
# # print(hist.columns)
# open_hist = hist["Open"]

# profit = 0
# counter = 1
# date_indexes = open_hist.index
# start_date = date_indexes[0]
# value = round(open_hist[start_date], 2) * num_shares
# # print(start_date, round(open_hist[start_date], 2), value)

# i = 0
# num_date_indexes = len(date_indexes)
# # print(num_date_indexes)
# # for idx in hist.index:
#     # print(hist["Open"][idx])
#     # if counter % 7 == 0:    # Either buy or sell
#     #     if open_hist[idx] > open_hist[idx - 1]
#     #     counter = 0
#     # counter += 1

