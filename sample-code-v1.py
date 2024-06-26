from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import argparse

import datetime  # For datetime objects
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])

# Import the backtrader platform
import backtrader as bt

MAX_COST = 1000

class MaxCostSizer(bt.Sizer):
    params = (
            ('max_cost', MAX_COST), # Set the maximum cost parameter
            ('initial_max_cost', MAX_COST)
        )

    def _getsizing(self, comminfo, cash, data, isbuy):
        if isbuy:
            # Calculate the maximum number of shares that can be purchased
            max_shares = int(self.params.max_cost / data.open[0])
            # Ensure that the maximum number of shares does not exceed available cash
            max_shares = min(max_shares, int(cash / data.open[0]))
            return max_shares
        # For selling, use the default sizing logic
        else:
            # Increase max cost based off cash in account from selling
            # Should change this for next bot where we only have 1% or 2% of account's value per trade
            self.params.max_cost = self.params.initial_max_cost + cash
            return self.broker.getposition(data).size

class FixedCommissionScheme(bt.CommInfoBase):
    params = (
        ('commission', 5),  # Fixed commission per trade
        ('commtype', bt.CommInfoBase.COMM_FIXED),
    )

    def getvaluesize(self, size, price):
        pass  # No need to return any value for getvaluesize

    def getsize(self, price, cash):
        return self.p.commission

    def getcommission(self, size, price):
        return self.p.commission

# Create a Stratey
class TestStrategy(bt.Strategy):
    params = (
        ('exitbars', 5),
        ('file_handle', None)
    )

    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        # print('%s, %s' % (dt.isoformat(), txt))
        self.params.file_handle.write("{}, {}\n".format(dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "open" line in the data[0] dataseries
        self.data_open = self.datas[0].open

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buy_price = None
        self.buycomm = None
        self.size = 0

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Size: %d, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.size,
                     order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buy_price = order.executed.price
                self.buycomm = order.executed.comm
                self.size = order.executed.size
            else:  # Sell
                self.log('SELL EXECUTED, Size: %d, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.size,
                          order.executed.price,
                          order.executed.value,
                          order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        # Simply log the closing price of the series from the reference
        self.log('Open, %.2f' % self.data_open[0])

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # Check if we are in the market
        if not self.position:

            # Not yet ... we MIGHT BUY if ...
            if self.data_open[0] < self.data_open[-1]:
                    # current open less than previous open
                    # Keep track of the created order to avoid a 2nd order
                    self.order = self.buy()
                    # print(self.order)

        else:

            if self.data_open[0] * self.size > self.buy_price * self.size + self.buycomm:
                # Keep track ot created order to avoid a 2nd order
                self.order = self.sell()

            # # Already in the market ... we might sell
            # if len(self) >= (self.bar_executed + self.params.exitbars):
            #     # SELL, SELL, SELL!!! (with all possible default parameters)
            #     self.log('SELL CREATE, %.2f' % self.data_open[0])

            #     # Keep track of the created order to avoid a 2nd order
            #     self.order = self.sell()

def parse_args():
    parser = argparse.ArgumentParser(
        description='Pandas test script')

    parser.add_argument('--dataname', default='', required=False,
                        help='File Data to Load')

    parser.add_argument('--timeframe', default='weekly', required=False,
                        choices=['daily', 'weekly', 'monthly'],
                        help='Timeframe to resample to')

    parser.add_argument('--compression', default=1, required=False, type=int,
                        help='Compress n bars into 1')

    return parser.parse_args()


def perform_simulation(args):
    share_name = args.dataname or 'cba'
    # Create a cerebro entity
    cerebro = bt.Cerebro()
    
    f = open("./order-execs/{}-{}.txt".format(share_name, args.timeframe), "w")
    # Add a strategy
    cerebro.addstrategy(TestStrategy, file_handle=f)

    # Datas are in a subfolder of the samples. Need to find where the script is
    # because it could have been called from anywhere
    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    datapath = os.path.join(modpath, './data/historical-prices/{}-2019-2024.csv'.format(share_name))

    # Create a Data Feed
    data = bt.feeds.YahooFinanceCSVData(
        dataname=datapath,
        name=share_name.upper(),
        # Do not pass values before this date
        fromdate=datetime.datetime(2019, 1, 1),
        # Do not pass values after this date
        todate=datetime.datetime(2024, 1, 1),
        # Do not pass values after this date
        reverse=False)

    # Handy dictionary for the argument timeframe conversion
    tframes = dict(
        daily=bt.TimeFrame.Days,
        weekly=bt.TimeFrame.Weeks,
        monthly=bt.TimeFrame.Months)

    # Add the Data Feed to Cerebro
    # cerebro.adddata(data)
    
    # Resample data to timeframe specified with default being weekly
    cerebro.resampledata(
            data,
            timeframe=tframes[args.timeframe],
            compression=args.compression)

    # Set our desired cash start
    initial_value = 1000.0
    cerebro.broker.setcash(initial_value)

    # # Add a FixedSize sizer according to the stake
    # cerebro.addsizer(bt.sizers.FixedSize, stake=10)

    # Add a sizer to determine number of shares should be brought with max value for a buy trade
    cerebro.addsizer(MaxCostSizer, max_cost=MAX_COST, initial_max_cost=MAX_COST)

    # Set the commission - 0.12% ... divide by 100 to remove the %
    # cerebro.broker.setcommission(commission=0.0012)

    # Need to set a flat fee if order placed is less than $25,000
    # cerebro.broker.addcommissioninfo(FixedCommissionScheme)
    # cerebro.broker.setcommission(commission=0.5,
    #                              commtype=bt.CommInfoBase.COMM_FIXED)

    share_name_txt = 'Share Name: {}\n'.format(share_name.upper())
    print(share_name_txt)
    f.write(share_name_txt)
    # Print out the starting conditions
    portfolio_value = 'Starting Portfolio Value: %.2f\n' % cerebro.broker.getvalue()
    print(portfolio_value)
    f.write(portfolio_value)

    # Run over everything
    cerebro.run()

    # Print out the final result
    portfolio_value = 'Final Portfolio Value: %.2f\n' % cerebro.broker.getvalue()
    print(portfolio_value)
    f.write(portfolio_value)
    profit = "Total Profit: {:.2f}\n".format(cerebro.broker.getvalue() - initial_value)
    print(profit)
    f.write(profit)
    f.close()

    # Plot the result
    cerebro.plot()
    # cerebro.plot(style='bar')

if __name__ == '__main__':

    args = parse_args()
    perform_simulation(args)
