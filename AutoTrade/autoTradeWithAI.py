import time
import pyupbit
import datetime
import schedule
import numpy as np
from fbprophet import Prophet
import logging

access = "your-access"
secret = "your-secret"
ticker = "KRW-BTC" # 거래 coin
buy_cur = "KRW" # 매수 화폐
sel_cur = "BTC" # 매도 화폐
count_val = 7 #7일간 최적 k value 추출
predicted_close_price = 0
opt_k_val = 0
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

def get_target_price(ticker, k):
    """변동성 돌파 전략으로 매수 목표가 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=2)
    target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k
    return target_price

def get_start_time(ticker):
    """시작 시간 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
    start_time = df.index[0]
    return start_time

def get_ma15(ticker):
    """15일 이동 평균선 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=15)
    ma15 = df['close'].rolling(15).mean().iloc[-1]
    return ma15

def get_balance(ticker):
    """잔고 조회"""
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0
    return 0

def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]

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

def predict_price(ticker):
    """Prophet으로 당일 종가 가격 예측"""
    global predicted_close_price
    df = pyupbit.get_ohlcv(ticker, interval="minute60")
    df = df.reset_index()
    df['ds'] = df['index']
    df['y'] = df['close']
    data = df[['ds','y']]
    model = Prophet()
    model.fit(data)
    future = model.make_future_dataframe(periods=24, freq='H')
    forecast = model.predict(future)
    closeDf = forecast[forecast['ds'] == forecast.iloc[-1]['ds'].replace(hour=9)]
    if len(closeDf) == 0:
        closeDf = forecast[forecast['ds'] == data.iloc[-1]['ds'].replace(hour=9)]
    closeValue = closeDf['yhat'].values[0]
    predicted_close_price = closeValue
predict_price(ticker)
#print("----------",predicted_close_price)
schedule.every().hour.do(lambda: predict_price(ticker))
schedule.every().hour.do(lambda: get_opt_k(1))

   
# 로그인
upbit = pyupbit.Upbit(access, secret)

print(">> autotrade start !!")
logger.info(">> autotrade start !!")

# 자동매매 시작
while True:
    try:
        now = datetime.datetime.now()
        start_time = get_start_time(ticker)
        end_time = start_time + datetime.timedelta(days=1) #09:00 + 1일
        schedule.run_pending()

        # 09:00 < 현재 < #08:59:50
        if start_time < now < end_time - datetime.timedelta(seconds=10):  # 10초 전
            target_price = get_target_price(ticker, opt_k_val)
            ma15 = get_ma15(ticker)
            current_price = get_current_price(ticker)
            #if target_price < current_price and ma15 < current_price:
            #if target_price < current_price:
            if target_price < current_price and current_price < predicted_close_price:   
                logger.info(">> buy_market_order << ")
                krw = get_balance(buy_cur)
                logger.info("target_price :" + str(target_price) + "/ current_price :" + str(current_price) +"/ predicted_close_price :" + str(predicted_close_price)+"/ krw :" + str(krw))
                if krw >= 10000 and krw <= 300000:
                    upbit.buy_market_order(ticker, krw*0.9995)
        else:                   
            logger.info(">> sell_market_order << ")
            btc = get_balance(sel_cur)
            logger.info("target_price :" + str(target_price) + "/ current_price :" + str(current_price) +"/ predicted_close_price :" + str(predicted_close_price)+"/ btc :" + str(btc))
            if btc > 0.00008:
                upbit.sell_market_order(ticker, btc*0.9995)
        time.sleep(1)
    except Exception as e:
        logger.error(e)
        time.sleep(1)
#    finally:
#        logger.error(">> autotrade interrupt occur!!")
#        time.sleep(1)