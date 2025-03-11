# To implement a stock trading engine, I wrote the following classes:

## Order:
### this class stores all information related to an order

## OrderBook:
### OrderBook is used to store and manipulate stock operations for a specific stock, in this task, there are many instances of OrderBook (one for each stock), and them are stored in the TradingEngine. This class supports multiple workers adding/getting orders. It used two heaps to keep the operations efficient.

## MatchedOrder:
### this class is used for store information on matched orders.

## TradingEngine:
### this is our engine class, it can store at most 1600 stocks (I set this to be greater than 1024 to reduce the probability of hash collisions). It also stores all the matched orders while it is running. It supports addOrder() and matchOrder(). (matchOrder() keeps running in a working thread once the engine starts)
### matchOrder() has a time-complexity of O(n). addOrder() has a time-complexity of O(logn).

## simulate_trading()
### To simulate trading, you can directly run the python file; relevant information (added orders and matched orders) is printed.

## the main ideas when implementing this engine
### to support efficient operations, OrderBook used two heaps to store buy and sell orders separately (higher buy price and lower sell price have higher priority ). To check if there are any matches, it looks at the first element of the two heaps and check if the price condition is satisfied. If satisfied, then there is a match and the engine handles possible partial orders (happens when quantities does not match).
### to avoid the use of map, TradingEngine has its own hashing mechanisms (linear probing) to map ticker_symbol to index in the list.