import yfinance as yf
cba = yf.Ticker("CBA.AX")
hist = cba.history(period="3mo")

num_shares = 100

# print(hist)
# print(hist.columns)
open_hist = hist["Open"]

profit = 0
counter = 1
date_indexes = open_hist.index
start_date = date_indexes[0]
value = round(open_hist[start_date], 2) * num_shares
print(start_date, round(open_hist[start_date], 2), value)

i = 0
num_date_indexes = len(date_indexes)
print(num_date_indexes)
# for idx in hist.index:
    # print(hist["Open"][idx])
    # if counter % 7 == 0:    # Either buy or sell
    #     if open_hist[idx] > open_hist[idx - 1]
    #     counter = 0
    # counter += 1
