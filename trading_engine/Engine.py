from enum import Enum
import threading
import time
import heapq
import uuid
import random
from concurrent.futures import ThreadPoolExecutor

class OrderType(Enum):
    BUY = 1
    SELL = 2

class Order:
    def __init__(self, order_type: OrderType, ticker_symbol, price, quantity):
        self.order_type = order_type
        self.ticker_symbol = ticker_symbol
        self.price = price
        self.quantity = quantity
        self.timestamp = time.time()
        self.order_id = uuid.uuid4()
    
    def __lt__(self, other):
        if self.order_type == OrderType.BUY:
            # higher buy prices are higher priority
            return self.price > other.price if self.price != other.price else self.timestamp < other.timestamp
        else:
            # lower sell prices are higher priority
            return self.price < other.price if self.price != other.price else self.timestamp < other.timestamp

class OrderBook:
    def __init__(self):
        self.ticker_symbol = None
        self.buy_orders = [] # max heap
        self.sell_orders = [] # min heap
        self.buy_lock = threading.RLock()
        self.sell_lock = threading.RLock()
    
    def add_order(self, order):
        if order.order_type == OrderType.BUY:
            with self.buy_lock:
                heapq.heappush(self.buy_orders, order)
        else:
            with self.sell_lock:
                heapq.heappush(self.sell_orders, order)
    
    def get_best_buy(self):
        with self.buy_lock:
            return self.buy_orders[0] if self.buy_orders else None
    
    def get_best_sell(self):
        with self.sell_lock:
            return self.sell_orders[0] if self.sell_orders else None

    def pop_best_buy(self):
        with self.buy_lock:
            return heapq.heappop(self.buy_orders) if self.buy_orders else None
    
    def pop_best_sell(self):
        with self.sell_lock:
            return heapq.heappop(self.sell_orders) if self.sell_orders else None

class MatchedOrders:
    def __init__(self, buy_order, sell_order):
        self.buy_order_id = buy_order.order_id
        self.sell_order_id = sell_order.order_id
        self.quantity = min(buy_order.quantity, sell_order.quantity)
        self.price = sell_order.price # the price of the sell order
        self.timestamp = time.time()

class TradingEngine:
    def __init__(self):
        self.size = 1600 # size of the list, larger than 1024 to reduce hash collisions
        self.order_books = [OrderBook() for _ in range(self.size)]
        self.trade_locks = [None for _ in range(self.size)] # create a lock for each ticker, increasing concurrency
        self.matches = [] # store the matched orders
        self.match_lock = threading.RLock()
        self.create_ticker_lock = threading.RLock()

        self.running = True
        self.matching_thread = threading.Thread(target=self.continuous_matching)
        self.matching_thread.start()
    
    # map the ticker symbol to an index without using a dictionary
    def ticker_to_index(self, ticker_symbol):
        with self.create_ticker_lock:
            index =  hash(ticker_symbol) % self.size
            order_book = self.order_books[index]
            if order_book.ticker_symbol == ticker_symbol or not order_book.ticker_symbol:
                order_book.ticker_symbol = ticker_symbol

                # dynamically create a lock for each ticker symbol
                if self.trade_locks[index] is None:
                    self.trade_locks[index] = threading.RLock()
                return index
            else:
                for i in range(self.size):
                    order_book = self.order_books[(index + i) % self.size]

                    # if the order book is empty or has the same ticker symbol
                    if order_book.ticker_symbol == ticker_symbol or not order_book.ticker_symbol:
                        order_book.ticker_symbol = ticker_symbol

                        # dynamically create a lock for each ticker symbol
                        if self.trade_locks[(index + i) % self.size] is None:
                            self.trade_locks[(index + i) % self.size] = threading.RLock()
                        return (index + i) % self.size
        
        # no emtpy order book spot found
        return None
    
    # add an order to the order book
    def addOrder(self, order_type: OrderType, ticker_symbol: str, quantity: float, price: float):
        if quantity <= 0 or price <= 0:
            raise ValueError("Quantity and price must be positive numbers")
        
        order = Order(order_type, ticker_symbol, price, quantity)
        index = self.ticker_to_index(ticker_symbol)
        order_book = self.order_books[index]
        order_book.add_order(order)

        return order.order_id
    
    # match orders for a specific ticker symbol
    def match_orders_by_index(self, index):
        if self.order_books[index].ticker_symbol is None: # this is not used
            return
        
        matched = True
        while matched:
            matched = False
            with self.trade_locks[index]:
                order_book = self.order_books[index]
                best_buy = order_book.pop_best_buy()
                best_sell = order_book.pop_best_sell()
                if best_buy and best_sell and best_buy.price >= best_sell.price:
                    # found a match
                    matched = True
                    with self.match_lock:
                        matched_order = MatchedOrders(best_buy, best_sell)
                        self.matches.append(matched_order)
                        print("------ Matched Orders ------")
                        print(f"Matched {best_buy.order_id} with {best_sell.order_id}")
                        print(f"Price: {matched_order.price}, Quantity: {matched_order.quantity}")
                        print("----------------------------")
                    # check if there are partial orders
                    if best_buy.quantity > best_sell.quantity:
                        best_buy.quantity -= best_sell.quantity
                        order_book.add_order(best_buy)
                    elif best_buy.quantity < best_sell.quantity:
                        best_sell.quantity -= best_buy.quantity
                        order_book.add_order(best_sell)
                else:
                    # put the orders back
                    if best_buy:
                        order_book.add_order(best_buy)
                    if best_sell:
                        order_book.add_order(best_sell)
    
    # match all orders
    def matchOrder(self):
        # match all orders
        for i in range(self.size):
            self.match_orders_by_index(i)

    # for the continuous matching thread
    def continuous_matching(self):
        while self.running:
            time.sleep(0.1)
            self.matchOrder()
    
    # stop the trading engine
    def stop(self):
        self.running = False
        self.matching_thread.join()
        print("Trading engine stopped")

def simulate_trading(engine: TradingEngine):
    tickers = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "NVDA", "AMD", "INTC", "IBM"]
    def generate_random_order():
        ticker = random.choice(tickers)
        order_type = random.choice([OrderType.BUY, OrderType.SELL])
        quantity = random.randint(1, 100) * 10
        price = round(random.uniform(10, 500) * 2) / 2
        
        try:
            order_type_str = "BUY" if order_type == OrderType.BUY else "SELL"
            print(f"Added {order_type_str} order: {ticker} - {quantity} @ ${price:.2f}")
            engine.addOrder(order_type, ticker, quantity, price)
        except Exception as e:
            print(f"Error adding order: {e}")
        
    # simulate multiple brokers generating orders
    with ThreadPoolExecutor(max_workers=5) as executor:
        while True:
            time.sleep(0.1)
            executor.submit(generate_random_order)
    
if __name__ == "__main__":
    engine = TradingEngine()
    try:
        simulate_trading(engine)
    except KeyboardInterrupt:
        engine.stop()
        