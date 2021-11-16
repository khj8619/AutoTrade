import pyupbit
import time
import datetime
import numpy as np
import logging

def get_target_price(ticker, interval, k):
    """ 변동성 돌파 전략으로 매수 목표가 조회 """
    df = pyupbit.get_ohlcv(ticker, interval=interval, count=2)
    target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k
    return target_price

def get_start_time(ticker, interval): 
    """ 시작 시간 조회 """
    df = pyupbit.get_ohlcv(ticker, interval=interval, count=1)
    start_time = df.index[0]
    return start_time

def get_ma15(ticker):
    """15일 이동 평균선 조회"""
    df = pyupbit.get_ohlcv(ticker, interval=interval, count=15)
    ma15 = df['close'].rolling(15).mean().iloc[-1]
    return ma15

def get_current_price(ticker):
    """ 현재가 조회 """
    return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]

def get_balance(ticker):
    """ 잔고 조회 """
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0
    return 0            

def get_buy_average(currency):
    """ 매수평균가 """
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == currency:
            if b['avg_buy_price'] is not None:
                return float(b['avg_buy_price'])
            else:
                return 0
    return 0 

def get_ror(k):
    df = pyupbit.get_ohlcv(ticker, count=count_val)
    df['range'] = (df['high'] - df['low']) * k
    df['target'] = df['open'] + df['range'].shift(1)

    fee = 0
    df['ror'] = np.where(df['high'] > df['target'],
                         df['close'] / df['target'] - fee,
                         1)
    
    ror = df['ror'].cumprod()[-2]
    return ror  

def get_opt_k(k): 
    list_k = [0 for i in range(9)]
    j = 0    
    global opt_k_val   
    for k in np.arange(0.1, 1.0, 0.1):
        list_k[j] = get_ror(k)
        j = j+1
    k_max = max(list_k)
    opt_k_val = (list_k.index(k_max) + 1)/10     
##########################################################################################################

# 로그인
access = "your-access"
secret = "your-secret"
upbit = pyupbit.Upbit(access, secret)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
#logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(u'%(asctime)s [%(levelname)8s] %(message)s')

"""
 asctime : 날짜 시간 ex)2021.04.10 11:21:55,155
 levelname : 로그 레벨(DEBUS, INFO, WARNING, ERROR, CRITICAL)
 message : 로그 메시지
"""

#FileHandler
file_handler = logging.FileHandler('./logs/output.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

logger.info("Login OK~")

# 총 매수 할 원화, 분할 매수 비율
totalOrderAmt = 1000000
rate30 = 0.3
rate40 = 0.4
rate_minus = 0.95
sel_rate = 0.95

# 시간 간격
interval = "day"
# interval = "minute240"

# ticker, k, currency
ticker = "KRW-BTC" # 거래 coin
buy_cur = "KRW" # 매수 화폐
sel_cur = "BTC" # 매도 화폐
opt_k_val = 0
count_val = 7 #7일간 최적 k value 추출

# 자동 매매 무한반복
while True:
    try:
        # 시간 설정
        start_time = get_start_time(ticker, interval)
        now = datetime.datetime.now()
        end_time = start_time + datetime.timedelta(days=1) - datetime.timedelta(seconds=10)  #09:00 + 1일 10초 전 
        
        # 매매 시작
        if start_time < now < end_time:
            target_price = get_target_price(ticker, interval, opt_k_val)
            ma15 = get_ma15(ticker)
            i = 0
            while i < 3:
                current_price = get_current_price(ticker)
                time.sleep(0.5)
                logger.debug("target_price :" + str(target_price) + "/ current_price :" + str(current_price) + "/ ma15 :" + str(ma15))
                # 매수 1차
                if i == 0 and target_price < current_price and ma15 < current_price:
                    #upbit.buy_market_order(ticker, totalOrderAmt * rate30)
                    logger.info("ticker :" + ticker + "/ buy amt :" + str(totalOrderAmt * rate30))
                    time.sleep(1)
                    buy_average = get_buy_average(buy_cur)
                    i += 1
                    logger.info("%dst Buy OK" %(i))
                    
                # 매수 2차
                if i == 1 and current_price < buy_average * rate_minus:
                    #upbit.buy_market_order(ticker, totalOrderAmt * rate30)
                    logger.info("ticker :" + ticker + "/ buy amt :" + str(totalOrderAmt * rate30))
                    time.sleep(1)
                    buy_average = get_buy_average(buy_cur)
                    i += 1
                    logger.info("%dst Buy OK" %(i))
                
                # 매수 3차
                if i == 2 and current_price < buy_average * rate_minus:
                    #upbit.buy_market_order(ticker, totalOrderAmt * rate40)
                    logger.info("ticker :" + ticker + "/ buy amt :" + str(totalOrderAmt * rate40))
                    time.sleep(1)
                    buy_average = get_buy_average(buy_cur)
                    i += 1
                    logger.info("%dst Buy OK" %(i))
                    
                if now > end_time:
                    break

        elif now > end_time:
            coin = get_balance(sel_cur)
            #upbit.sell_market_order(ticker, coin * sel_rate)
            logger.info("target_price :" + str(target_price) + "/ current_price :" + str(current_price) +"/ coin :" + str(coin))
            time.sleep(1)
        
    except Exception as e:
        logger.error(e)
        time.sleep(1)