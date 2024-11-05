from matplotlib import pyplot as plt
import requests
import pandas as pd
import numpy as np


krak_url = r'https://api.kraken.com/0/'
kuc_url = r"https://api.kucoin.com/api/v1/"



def krak_collect_kline(coin_pair, inter_minutes):
    """This method collects a kline from kraken in OHLC format.
    Args:
        coin_pair (str): a string denoting the pair, ex: BTC/USD or ETH/BTC
        inter_minutes (int): an integer which denotes the number of minutes for the kline interval. Acceptable values are:
        1, 5, 15, 30, 60, 240, 1440, 10080, 21600"""
    collect_url = krak_url + r"public/OHLC"
    payload = {}
    headers = {
        'Accept':'application/json'
    }
    params = {
        "pair": coin_pair,
        "interval": inter_minutes,
    }

    response = requests.request("GET", url=collect_url, headers=headers,data=payload, params=params)
    try:
        response = response.json()['result']
    except:
        print("Error in kline retrieval")
    df = pd.DataFrame(response[coin_pair], columns=["time", "open", "high", "low", "close", "vwap", "volume", "count"])
    df = df.astype(float)
    return df

def kuc_collect_kline(coin_pair, interval, start_at, end_at):
    """
    This method is used to collect a single kline from kucoin.
    Args:
        coin_pair (str): a coin pair in the style of BTC-USDT or similar
        interval_unit (str): this is the unit of time used for the kline, acceptable are min, hour, day, week, month 
        interval (str): this is the interval of the kline. Acceptable intervals are as follows: 
        1min, 3min, 5min, 15min, 30min, 1hour, 2hour, 4hour, 6hour, 8hour, 12hour, 1day, 1week, 1month
        Results are: time open close high low volume turnover
    """
    
    kline_url = kuc_url + f"market/candles?type={interval}&symbol={coin_pair}&startAt={start_at}&endAt={end_at}"
    response = requests.request("GET", url=kline_url)
    response = response.json()
    if response['code'] == '200000':
        df = pd.DataFrame(response["data"], columns=["time", "open", "close", "high", "low", "volume", "turnover"])
    else:
        print("Error in kline retrieval")
    
    df = df.astype(float)
    return df

def kuc_collect_multi_kline(coin_pair, interval_unit, interval_int, rounds):
    
    """This is used to collect multiple past klines from kucoin.

    Args:
        coin_pair (str): a coin pair in the style of BTC-USDT or similar
        interval_unit (str): this is the unit of time used for the kline, acceptable are min, hour, day, week, month 
        interval_int (int): this is the amount of said unit, note that the combined acceptable interval_units and interval ints are as follows: 
        1min, 3min, 5min, 15min, 30min, 1hour, 2hour, 4hour, 6hour, 8hour, 12hour, 1day, 1week, 1month
    """
    
    import time
    now = int(time.time())
    #first assume that the step change is for a minute interval
    #remember the step changes and other changes need to be in seconds
    step_change = 60 * interval_int
    if interval_unit == "hour":
        step_change = step_change * 60
    if interval_unit == "day":
        step_change = step_change * 60 * 24
    if interval_unit == "week":
        step_change = step_change * 60 * 24 * 7
    if interval_unit == "month":
        #Approximation of average month, February considerations are ignored
        step_change = step_change * 60 * 24 * 7 * 30
    step_change = int(step_change)
    interval = str(interval_int) + interval_unit
    past = int(now - step_change * 1000)
    first = True
    df = ""
    for r in range(rounds):
        if first:
            df = kuc_collect_kline(coin_pair, interval, start_at=past, end_at=now)
            first = False
        else:
            new_df = kuc_collect_kline(coin_pair, interval, start_at=past, end_at=now)
            df = pd.concat([df, new_df], axis=0).reset_index(drop=True)
        now = now - step_change * 1001
        past = now - step_change * 1000
        
    return df
    
def create_figure(kline):
    """WORK IN PROGRESS,
    This method is to create an updating figure of the kline. 
    The idea is to be able to display a graphed kline as part of a front end down the line"""

    try:
        plt.clf()
    except:
        pass
    disp_kline = kline.iloc[-15:, :]
    print(disp_kline)
    up = disp_kline[disp_kline.close >= disp_kline.open]
    down = disp_kline[disp_kline.close < disp_kline.open]

    up_color = 'green'
    down_color = 'red'
    width = 0.3
    width2 = 0.03
    
    plt.rcParams['axes.facecolor'] = 'black'
    plt.bar(up.index, up.close-up.open, width, bottom=up.open, color = up_color)
    plt.bar(up.index, up.high-up.close, width2, bottom = up.close, color = up_color)
    plt.bar(up.index, up.low - up.open, width2, bottom=up.open, color=up_color)

    plt.bar(down.index, down.close-down.open, width, bottom=down.open, color=down_color) 
    plt.bar(down.index, down.high-down.open, width2, bottom=down.open, color=down_color) 
    plt.bar(down.index, down.low-down.close, width2, bottom=down.close, color=down_color)
    plt.xticks(rotation=30, ha='right')
    lower_y_edge = np.nanmin(disp_kline['low'])
    upper_y_edge = np.nanmax(disp_kline['high'])
    plt.ylim((lower_y_edge - int(0.001 * lower_y_edge), upper_y_edge + int(0.001 * upper_y_edge)))
    plt.savefig("current.png")

def new_fig_gen():
    """This method is to create a new kline then to graph it."""
    kline = krak_collect_kline("ETH/USD", 15)
    create_figure(kline)
    
def collect_changes(kline, forward):
    """This method is to add price and volume changes to the kline. There is also a pessimistic profit prediction column as well as a volume change column"""
    pd.DataFrame().pct_change()
    #the pct_change go "back" in time
    kline["vol_shift"] = kline['volume'].pct_change(forward)
    kline['op_shift'] = kline['open'].pct_change(forward)
    kline['cl_shift'] = kline['close'].pct_change(forward)
    kline['hi_shift'] = kline['high'].pct_change(forward)
    kline['lo_shift'] = kline['low'].pct_change(forward)
    "The shift and -forward allow for looking into the future"
    kline['score_profit'] = (kline['low'].shift(forward) - kline['high']) / kline['high']
    kline['score_vol'] = kline['volume'].pct_change(-forward) 
   
    return kline
     
def change_to_datetime(kline):
    """This is used to change the time column to a datetime column and to set it as the index"""
    kline['time'] = kline['time'].apply(lambda d: datetime.datetime.fromtimestamp(d))
    kline = kline.set_index("time", drop=True)
    kline = kline.iloc[:, 1:]
    kline = kline.sort_index(ascending=True)
    return kline

def load_all_coins(coins, unit, unit_int):
    """This method loads all the coins of a given list that have been gotten
    Args:
    coins(list): an iterable with all the coin names
    unit(str): the unit of the kline interval
    unit_int(int): the number of said unit ex: 15 of the 15min interval"""
    dfs = []
    labels = []
    for c in coins:
        try:
            df = pd.read_csv(f"{c}_{unit + str(unit_int)}.csv")
            #f = df.iloc[:, 1:]
            dfs.append(df)
            labels.append(c)
        except:
            pass
    return dfs, labels

              

if __name__ == "__main__":
    #kline = krak_collect_kline("ETH/USD", 15)
    #create_figure(kline)
    import datetime
    unit = "min"
    unit_int = 30
    forward = 36
    selection = 1
    coins = ["KAVA-USDT", "JUP-USDT", "FTM-USDT", "RARI-USDT", "BTC-USDT", "ETH-USDT", "XMR-USDT"]
    dfs, labels = load_all_coins(coins, unit, unit_int)
    toy_df = dfs[selection]
    toy_df = pd.DataFrame(toy_df)
    print(labels[selection])
    toy_df = change_to_datetime(toy_df)
    
    toy_df = collect_changes(toy_df, forward).dropna()
    scores = toy_df.corr()['score_profit']
    scores_vol = toy_df.corr()['score_vol']
    scores = pd.concat([scores, scores_vol], axis = 1)
    #scores = scores[(scores >= 0.01) | (scores <= -0.01)]
    scores.to_csv("scores.csv")
    toy_df.to_csv("ExampleKlineChanges.csv")
    
    
    
    
    
    
    
    
    
    
    
