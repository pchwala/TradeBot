import asyncio
import json
import pandas as pd
import sqlite3 as sql
from time import sleep

from xAPI import XAPI


class Scrapper:
    def __init__(self, credentials):
        self.symbols_short = []   # All symbols with short-selling enabled

        with open(credentials, 'r') as file:
            credentials = json.load(file)

        self.main_api = XAPI(credentials['id'], credentials['password'])
        result = self.main_api.establish_connection()    # Establish new connection with credentials.json
        if result is False:
            return False

        # testing variable
        self.default_time = self.main_api.date_to_milliseconds("03.02.2025")

        # Connect to SQLite
        self.con_sql = sql.connect("candlestick.db")
        self.cursor_sql = self.con_sql.cursor()

        self.cursor_sql.execute("""
        CREATE TABLE IF NOT EXISTS candlestick_data (
            n INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            ctm INTEGER NOT NULL,
            open REAL NOT NULL,
            close REAL NOT NULL,
            vol REAL NOT NULL
        )
        """)


    async def main_loop(self):
        """Main loop running all tasks using asyncio await"""

        #task1 = asyncio.create_task(self.main_api.get_keep_alive_s())
        #task2 = asyncio.create_task(self.main_api.close_all_stream_connections())
        #task3 = asyncio.create_task(self.main_api.ping_interval(1))  # ping server with 1s interval to avoid closing connection
        task4 = asyncio.create_task(self.get_all_symbols())
        #task5 = asyncio.create_task(self.get_candles_from_time("EURUSD", 1, self.default_time))

        #result = await task1
        #result = await task2
        #result = await task3
        result = await task4

        print("Logout")
        result = await self.main_api.get_server_time()
        print(result)
        self.main_api.logout()


    async def get_all_symbols(self):
        all_symbols = await self.main_api.get_all_symbols()
        for symbol in all_symbols:
            if symbol['shortSelling'] is True:
                self.symbols_short.append(symbol['symbol'])

        n = 0
        keys_to_remove = ["ctmString", "high", "low"]
        for symbol in self.symbols_short:
            if n < 20000:   # Temporary
                print(f"{n},  {symbol}")
                n += 1
                
                self.cursor_sql.execute("SELECT MAX(ctm) FROM candlestick_data WHERE ticker = ?", (symbol,))
                time = self.cursor_sql.fetchone() # Result is a tuple e.g. (value,)
                try:
                    await asyncio.sleep(0.2) # Sending commands faster than 200ms will cause connection drop
                    if time[0] is not None:
                        result = await self.get_candles_from_time(symbol, 1, time[0]+60000) # Time plus 1minute to not double value
                    else:
                        result = await self.get_candles_from_time(symbol, 1, self.default_time)
                except Exception as e:
                    print(e)
                    continue
                    
                candles = result["returnData"]["rateInfos"]
                for candle in candles:
                    for key in keys_to_remove:
                        del candle[key]

                self.cursor_sql.executemany(
                    f"INSERT INTO candlestick_data (ticker, ctm, open, close, vol) VALUES ('{symbol}', :ctm, :open, :close, :vol)",
                    candles
                )

                self.con_sql.commit()

        #value = 1739198700000
        #result = self.search_candles("DEA.US_4", value, value+180000)
        if result:
            print("Search Results:")
            for row in result:
                print(row)
        else:
            print("No matching records found.")


        self.con_sql.close()

    
    async def get_candles_from_time(self, symbol, period, start):
        command = {
            "command": "getChartLastRequest",
            "arguments": {
                "info":{
                    "period": period,
                    "start": start,
                    "symbol": symbol
                }
            }
        }

        result = await self.main_api.execute_command(command)
        return result


    def search_candles(self, ticker, start_ctm, end_ctm):
        self.cursor_sql.execute("""
        SELECT * FROM candlestick_data 
        WHERE ticker = ? AND ctm BETWEEN ? AND ?
        ORDER BY ctm ASC
        """, (ticker, start_ctm, end_ctm))
        return self.cursor_sql.fetchall()



async def main():
    scrapper = Scrapper('credentials.json')
    await scrapper.main_loop()

asyncio.run(main())