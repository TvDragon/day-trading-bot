import argparse
import datetime
import os.path
import sys
import backtrader

class MaxCostSizer(backtrader.Sizer):
    params = (
            ('max_trade_value', 0), # Set the maximum cost per trade parameter
            ('starting_cash', 0),

        )

    def _getsizing(self, comminfo, cash, data, isbuy):
        if isbuy:
            # Calculate the maximum number of shares that can be purchased
            max_shares = int(self.params.max_trade_value / data.open[0])
            # Ensure that the maximum number of shares does not exceed available cash
            max_shares = min(max_shares, int(cash / data.open[0]))
            return max_shares
        # For selling, use the default sizing logic
        else:
            # Max trade value is 1% of account's value for buy option
            self.params.max_trade_value = (self.params.starting_cash + cash) * 0.01
            return self.broker.getposition(data).size

def parse_args():
    parser = argparse.ArgumentParser(
        description='Simple Trading Strategy')

    parser.add_argument('--dataname', default='cba', required=False,
                        choices=['cba', 'gmg', 'ioo', 'ndq', 'vas', 'wes'],
                        help='File Data to Load')

    parser.add_argument('--timeframe', default='weekly', required=False,
                        choices=['daily', 'weekly', 'monthly'],
                        help='Timeframe to resample to')

    # This will allow us to compress data to display customised timeframes like 1 day, 2 weeks, etc
    parser.add_argument('--compression', default=1, required=False, type=int,
                        help='Compress n bars into 1')

    return parser.parse_args()


def perform_simulation(args):

    # Create a cerebro entity
    cerebro = backtrader.Cerebro()

    # Add a strategy

    # Data file location
    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    datapath = os.path.join(
            modpath, 
            './data/historical-prices/{}-2019-2024.csv'.format(args.dataname))

    # Create a data feed
    data = backtrader.feeds.YahooFinanceCSVData(
            dataname=datapath,
            name=args.dataname.upper(),
            fromdate=datetime.datetime(2019, 1, 1),
            todate=datetime.datetime(2024, 1, 1),
            reverse=False)

    # dictionary for argument timeframe conversion
    tframes = dict(
            daily=backtrader.TimeFrame.Days,
            weekly=backtrader.TimeFrame.Weeks,
            monthly=backtrader.TimeFrame.Months)

    # Resample data to timeframe
    cerebro.resampledata(
            data,
            timeframe=tframes[args.timeframe],
            compression=args.compression)

    # Set desired cash start
    cash = 10000
    cerebro.broker.setcash(cash)

    # Add a sizer to determine number of shares should be brought with max value for a buy trade
    cerebro.addsizer(MaxCostSizer, max_trade_value=cash*0.01, starting_cash=cash)

    # Set the commission - 0% ... divide by 100 to remove the %
    cerebro.broker.setcommission(commission=0.0)

    # Run over everything
    cerebro.run()
    
    # Plot the result
    cerebro.plot()

if __name__ == '__main__':

    args = parse_args()
    perform_simulation(args)
