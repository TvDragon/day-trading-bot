import backtrader as bt
import argparse
import datetime
import os.path
import sys

class ScalpingStrategy(bt.Strategy):
    params = (
            ('exitbars', 5),
            ('file_handle', None),
            ('ema_period_1', 25),
            ('ema_period_2', 50),
            ('ema_period_3', 100)
        )

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        self.params.file_handle.write("{}, {}\n".format(dt.isoformat(), txt))
    
    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.data_close = self.datas[0].close

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buy_price = None
        self.buy_comm = None
        self.size = 0

        # Create EMAs
        self.ema25 = bt.indicators.ExponentialMovingAverage(self.data, period=self.params.ema_period_1)
        self.ema50 = bt.indicators.ExponentialMovingAverage(self.data, period=self.params.ema_period_2)
        self.ema100 = bt.indicators.ExponentialMovingAverage(self.data, period=self.params.ema_period_3)

        self.is_uptrend = self.is_downtrend = False
        self.is_below_25_or_50_ema = self.is_above_25_or_50_ema = False
        self.stop_loss = 0
        self.take_profit = 0
        self.buy_order = self.sell_order = False
        self.duration_for_order = 0
        self.max_duration = 30

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted by broker so do nothing
            return

        # Check if an order has been completed
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                        'BUY EXECUTED, Size: %d, Price: %.2f, Cost: %.2f, Comm %.2f' %
                        (order.executed.size, order.executed.price,
                        order.executed.value, order.executed.comm))
                self.buy_price = order.executed.price
                self.buy_comm = order.executed.comm
            else:   # Sell order
                self.log(
                        'SELL EXECUTED, Size: %d, Price: %.2f, Cost: %.2f, Comm %.2f' %
                        (order.executed.size, order.executed.price,
                        order.executed.value, order.executed.comm))
                self.bar_executed = len(self)
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            # Broker may have rejected order because not enough cash
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                    (trade.pnl, trade.pnlcomm))

    def next(self):
        self.log('Open, %.2f' % self.data_close[0])

        # If order is still pending we cannot place another order
        if self.order:
            return

        # Check if we are in the market
        if not self.position:
            # Check if in uptrend
            # TODO: Still needs fixing bc on 08-08-2023 we could've placed a buy order
            if self.is_uptrend == False and self.is_downtrend == False and self.buy_order == False:
                # Set up for potential buy order
                self.is_uptrend = True
                for i in range(15):
                    if not (self.ema25[-i] >= self.ema25[-i-1] and \
                            self.ema50[-i] >= self.ema50[-i-1] and \
                            self.ema100[-i] >= self.ema100[-i-1] and \
                            self.data_close[-i] > self.ema25[-i] > self.ema50[-i] > self.ema100[-i]):
                        self.is_uptrend = False
                        break
            elif self.is_uptrend == True and self.buy_order == False:
                # Is in an uptrend so could place buy order if criteria is met
                if self.data_close[0] <= self.ema25[0] and self.data_close[0] > self.ema100[0]:
                    self.is_below_25_or_50_ema = True
                elif self.data_close[0] > self.ema25[0] > self.ema50[0] > self.ema100[0]:
                    if self.is_below_25_or_50_ema:
                        cash = self.broker.get_cash()
                        max_shares_to_buy = int(cash / self.data_close[0])
                        self.order = self.buy(size=max_shares_to_buy)
                        self.buy_order = True
                        self.is_uptrend = self.is_below_25_or_50_ema = False
                        self.stop_loss = round(self.ema50[0], 2)
                        self.take_profit = round(self.data_close[0] + (self.data_close[0] - self.stop_loss) * 1.5, 2)
                else:
                    self.is_uptrend = self.is_below_25_or_50_ema = False

            # Check if in downtrend
            if self.is_uptrend == False and self.is_downtrend == False and self.sell_order == False:
                # Set up for potential sell order
                self.is_downtrend = True
                for i in range(15):
                    if not (self.ema25[-i] <= self.ema25[-i-1] and \
                            self.ema50[-i] <= self.ema50[-i-1] and \
                            self.ema100[-i] <= self.ema100[-i-1] and \
                            self.data_close[-i] < self.ema25[-i] < self.ema50[-i] < self.ema100[-i]):
                        self.is_downtrend = False
                        break
            elif self.is_downtrend == True and self.sell_order == False:
                # Is in a downtrend so could place sell order if criteria is met
                if self.data_close[0] >= self.ema25[0] and self.data_close[0] < self.ema100[0]:
                    self.is_above_25_or_50_ema = True
                elif self.data_close[0] < self.ema25[0] < self.ema50[0] < self.ema100[0]:
                    if self.is_above_25_or_50_ema:
                        cash = self.broker.get_cash()
                        max_shares_to_sell = int(cash / self.data_close[0])
                        self.order = self.sell(size=max_shares_to_sell)
                        self.sell_order = True
                        self.is_downtrend = self.is_above_25_or_50_ema = False
                        self.stop_loss = round(self.ema50[0], 2)
                        self.take_profit = round(self.data_close[0] - (self.stop_loss - self.data_close[0]) * 1.5, 2)
                else:
                    self.is_downtrend = self.is_above_25_or_50_ema = False
        else:
            # Sell for the placed buy order
            if self.data_close[0] <= self.stop_loss or \
                    self.data_close[0] >= self.take_profit or \
                    self.duration_for_order == self.max_duration and \
                    self.buy_order == True:
                self.order = self.sell(size=self.position.size)
                self.is_uptrend = self.is_below_25_or_50_ema = self.buy_order = False
                self.duration_for_order = -1

            # Buy for the placed sell order
            if self.data_close[0] >= self.stop_loss or \
                    self.data_close[0] <= self.take_profit or \
                    self.duration_for_order == self.max_duration and \
                    self.sell_order == True:
                self.order = self.buy(size=self.position.size)
                self.is_downtrend = self.is_above_25_or_50_ema = self.sell_order = False
                self.duration_for_order = -1

            self.duration_for_order += 1


def parse_args():
    parser = argparse.ArgumentParser(
        description='Scalping Trading Strategy')

    parser.add_argument('--dataname', default='cba', required=False,
                        choices=['cba', 'gmg', 'ioo', 'ndq', 'vas', 'wes'],
                        help='File Data to Load')

    parser.add_argument('--timeframe', default='daily', required=False,
                        choices=['daily', 'weekly', 'monthly'],
                        help='Timeframe to resample to')

    # This will allow us to compress data to display customised timeframes like 1 day, 2 weeks, etc
    parser.add_argument('--compression', default=1, required=False, type=int,
                        help='Compress n bars into 1')

    return parser.parse_args()

def perform_simulation(args):

    # Create a cerebro entity
    cerebro = bt.Cerebro()
    
    f = open("./order-execs/scalping/{}/scalping-{}-{}-{}.txt".format(args.dataname, args.dataname, args.compression, args.timeframe), "w")
    # Add a strategy
    cerebro.addstrategy(ScalpingStrategy, file_handle=f)

    # Data file location
    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    datapath = os.path.join(
            modpath, 
            './data/historical-prices/{}-2019-2024.csv'.format(args.dataname))

    # Create a data feed
    data = bt.feeds.YahooFinanceCSVData(
            dataname=datapath,
            name=args.dataname.upper(),
            fromdate=datetime.datetime(2019, 1, 1),
            todate=datetime.datetime(2024, 1, 1),
            reverse=False)

    # dictionary for argument timeframe conversion
    tframes = dict(
            daily=bt.TimeFrame.Days,
            weekly=bt.TimeFrame.Weeks,
            monthly=bt.TimeFrame.Months)

    # Resample data to timeframe
    cerebro.resampledata(
            data,
            timeframe=tframes[args.timeframe],
            compression=args.compression)

    # Set desired cash start
    cash = 1000
    cerebro.broker.setcash(cash)

    # Add a sizer to determine number of shares should be brought with max value for a buy trade
    # cerebro.addsizer(MaxCostSizer, max_trade_value=cash, initial_trade_value=cash)

    # Set the commission - 0% ... divide by 100 to remove the %
    cerebro.broker.setcommission(commission=0.0)

    # Write starting cash into file
    f.write("Share Name: {}\n".format(args.dataname.upper()))
    f.write("Starting Portfolio Value: {:.2f}\n".format(cerebro.broker.getvalue()))
    print("Share Name: {}".format(args.dataname.upper()))
    print("Starting Portfolio Value: {:.2f}".format(cerebro.broker.getvalue()))

    # Run over everything
    cerebro.run()
 
    f.write("Final Portfolio Value: {:.2f}\n".format(cerebro.broker.getvalue()))
    f.write("Total Profit: {:.2f}\n".format(cerebro.broker.getvalue() - cash))
    print("Final Portfolio Value: {:.2f}".format(cerebro.broker.getvalue()))
    print("Total Profit: {:.2f}".format(cerebro.broker.getvalue() - cash))
    f.close()
    # Plot the result
    cerebro.plot()

if __name__ == '__main__':

    args = parse_args()
    perform_simulation(args)

