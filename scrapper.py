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

        # Create database if if doesn't exist
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

        # Create and await task downloading all specified symbols candlestick data with resolution of 1minute
        task1 = asyncio.create_task(self.get_all_symbols())
        result = await task1

        # Logout and end program
        result = await self.main_api.get_server_time()
        print(result)
        print("Logout")
        self.main_api.logout()


    async def get_all_symbols(self):
        """
        Downloads specified symbols candlestick data with resolution of 1minute
        For now it downloads all and only symbols that allow short-selling
        """
        all_symbols = await self.main_api.get_all_symbols() # Get all availalble symbols from XTB
        for symbol in all_symbols:
            if symbol['shortSelling'] is True:
                self.symbols_short.append(symbol['symbol']) # List of symbols with short-selling enabled

        keys_to_remove = ["ctmString", "high", "low"] # Only saving ctm, open, close
        for n, symbol in enumerate(self.symbols_short):
            print(f"{n},  {symbol}")
            
            # Find last saved candle, the most recent one
            self.cursor_sql.execute("SELECT MAX(ctm) FROM candlestick_data WHERE ticker = ?", (symbol,))
            time = self.cursor_sql.fetchone() # Result is a tuple e.g. (value,)
            time = time[0]                    # So take only the value
            try:
                # Sending commands faster than 200ms for 6 executing times will cause connection drop, so put the sleep.
                # It can be done faster by measuring time of executing this function and calling this fucntion 5 times with no delay
                # and then only calling it after 200ms, rinse repeat, but as this program will be run only once a month
                # to retrieve a new portion of data and on a 24/7h running server it is not necesarry
                await asyncio.sleep(0.2)
                # If there is saved data for current symbol then save only new data
                # Else save all available data for that symbol
                if time is not None:
                    result = await self.get_candles_from_time(symbol, 1, time+60000) # Time plus 1minute to not double already saved value
                else:
                    result = await self.get_candles_from_time(symbol, 1, self.default_time)
            except Exception as e:
                print(e)
                continue
                
            candles = result["returnData"]["rateInfos"]
            for candle in candles:
                for key in keys_to_remove:
                    del candle[key] # Remove non-important and redundant values

            # Add new symbol data to the database
            self.cursor_sql.executemany(
                f"INSERT INTO candlestick_data (ticker, ctm, open, close, vol) VALUES ('{symbol}', :ctm, :open, :close, :vol)",
                candles
            )

            self.con_sql.commit()

        self.con_sql.close()

    
    async def get_candles_from_time(self, symbol, period, start):
        """Retrieve from API all candles for given symbol from start time with specified period"""
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

async def main():
    scrapper = Scrapper('credentials.json')
    await scrapper.main_loop()

asyncio.run(main())