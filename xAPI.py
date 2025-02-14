import websocket, json, openpyxl
import websockets
from websockets.exceptions import WebSocketException
from datetime import datetime, timedelta
import asyncio


class XAPI:
    __version__ = "1.0"

    def __init__(self, ID, PSW, dest):

        self._dest_main = "wss://ws.xtb.com/demo"
        self._dest_stream = "wss://ws.xtb.com/demoStream"
        self._ID = ID
        self._PSW = PSW
        self._ws_main = None    # main websocket
        self._ws_stream = None  # streaming socket
        self._stream_id = None
        self.exec_start = self.get_time()
        self.ws_main = self.connect()
        self.login()
        self._ws_stream = self.connect_stream()


    def login(self):
        login = {
            "command": "login",
            "arguments": {
                "userId": self._ID,
                "password": self._PSW
            }
        }
        login_json = json.dumps(login)
        # Sending Login Request
        result = self.send(login_json)
        result = json.loads(result)
        self._stream_id = result["streamSessionId"]
        status = result["status"]
        if str(status) == "True":
            return True
        else:
            print("Error during logging attempt: ", result)
            return False


    def logout(self):
        logout = {
            "command": "logout"
        }
        logout_json = json.dumps(logout)
        # Sending Logout Request
        result = self.send(logout_json)
        result = json.loads(result)
        status = result["status"]
        self.disconnect()
        self.disconnect_stream()
        if str(status) == "True":
            return True
        else:
            print("Error during logging attempt: ", result)
            return False


    async def get_keep_alive(self):

        command = {
            "command": "getKeepAlive",
	        "streamSessionId": self._stream_id
        }

        command_json = json.dumps(command)

        async with websockets.connect(self._dest_stream) as ws:
            await ws.send(command_json)
            while True:
                msg = await ws.recv()
                print(msg)

        return None


    async def get_balance_stream(self):

        command = {
            "command": "getBalance",
            "streamSessionId": self._stream_id
        }

        command_json = json.dumps(command)

        async with websockets.connect(self._dest_stream) as ws:
            await ws.send(command_json)
            while True:
                msg = await ws.recv()
                print(msg)

        return None

    async def listen(self):
        try:
            async for message in self._ws_stream:
                yield message
        except Exception as e:
            print("Error ", e)


    async def get_server_time(self):
        """Returns current time on trading server, the time in the server is the number of miliseconds from 01/01/1970 00:00:00 until the current moment"""

        time = {
            "command": "getServerTime"
        }
        time_json = json.dumps(time)
        result = self.send(time_json)
        result = json.loads(result)
        time = result["returnData"]["time"]
        return time


    def get_balance(self):
        """Returns the current balance in the account"""

        balance = {
            "command": "getMarginLevel"
        }
        balance_json = json.dumps(balance)
        result = self.send(balance_json)
        result = json.loads(result)
        balance = result["returnData"]["balance"]
        return balance


    def get_margin(self, symbol, volume):
        """Returns expected margin for given instrument and volume. The value is calculated as expected margin value, and therefore might not be perfectly accurate"""

        margin = {
            "command": "getMarginTrade",
            "arguments": {
                "symbol": symbol,
                "volume": volume
            }
        }
        margin_json = json.dumps(margin)
        result = self.send(margin_json)
        result = json.loads(result)
        margin = result["returnData"]["margin"]
        return margin


    def get_symbol(self, symbol):
        """Returns a dictionary with information about symbol available for the user"""

        symbol = {
            "command": "getSymbol",
            "arguments": {
                "symbol": symbol
            }
        }
        symbol_json = json.dumps(symbol)
        result = self.send(symbol_json)
        result = json.loads(result)
        symbol = result["returnData"]
        return symbol


    def get_history(self, start=0, end=0, days=0, hours=0, minutes=0):
        """Returns list of user's trades closed within specified period of time"""

        if start != 0:
            start = self.time_conversion(start)
        if end != 0:
            end = self.time_conversion(end)

        if days != 0 or hours != 0 or minutes != 0:
            if end == 0:
                end = self.get_server_time()
            start = end - self.to_milliseconds(days=days, hours=hours, minutes=minutes)

        history = {
            "command": "getTradesHistory",
            "arguments": {
                "end": end,
                "start": start
            }
        }
        history_json = json.dumps(history)
        result = self.send(history_json)
        result = json.loads(result)
        history = result["returnData"]
        return history


    # TEMP FUNCTION
    def make_trade(self, symbol, cmd, transaction_type, volume, comment="", order=0, sl=0, tp=0, days=0, hours=0,
                   minutes=0):
        TRADE_TRANS_INFO = {
            "cmd": cmd,
            "customComment": comment,
            "expiration": 0,
            "order": 0,
            "price": 1.4,
            "sl": sl,
            "symbol": symbol,
            "tp": tp,
            "type": transaction_type,
            "volume": volume
        }
        trade = {
            "command": "tradeTransaction",
            "arguments": {
                "tradeTransInfo": TRADE_TRANS_INFO
            }
        }
        trade_json = json.dumps(trade)
        result = self.send(trade_json)
        result = json.loads(result)
        if result["status"] == True:
            return True, result["returnData"]["order"]
        else:
            return False, 0

    async def ping(self):
        """Regularly calling this function is enough to refresh the internal state of all the components in the system.
         It is recommended that any application that does not execute other commands, should call this command at least once every 10 minutes."""
        ping = {
            "command": "ping"
        }
        ping_json = json.dumps(ping)
        result = self.send(ping_json)
        result = json.loads(result)
        return result


    @staticmethod
    def get_time():
        time = datetime.today().strftime('%m/%d/%Y %H:%M:%S%f')
        time = datetime.strptime(time, '%m/%d/%Y %H:%M:%S%f')
        return time


    @staticmethod
    def to_milliseconds(days=0, hours=0, minutes=0):
        milliseconds = (days * 24 * 60 * 60 * 1000) + (hours * 60 * 60 * 1000) + (minutes * 60 * 1000)
        return milliseconds


    @staticmethod
    def time_conversion(date):
        start = "01/01/1970 00:00:00"
        start = datetime.strptime(start, '%m/%d/%Y %H:%M:%S')
        date = datetime.strptime(date, '%m/%d/%Y %H:%M:%S')
        final_date = date - start
        temp = str(final_date)
        temp1, temp2 = temp.split(", ")
        hours, minutes, seconds = temp2.split(":")
        days = final_date.days
        days = int(days)
        hours = int(hours)
        hours += 2
        minutes = int(minutes)
        seconds = int(seconds)
        time = (days * 24 * 60 * 60 * 1000) + (hours * 60 * 60 * 1000) + (minutes * 60 * 1000) + (seconds * 1000)
        return time


    def connect(self):
        try:
            ws = websocket.create_connection(self._dest_main)
            return ws
        except:
            return False


    def disconnect(self):
        try:
            self.ws_main.close()
            return True
        except:
            return False


    def send(self, msg):
        self.ws_main.send(msg)
        result = self.ws_main.recv()
        return result + "\n"


    def connect_stream(self):
        try:
            ws = websocket.create_connection(self._dest_stream)
            return ws
        except:
            return False


    def disconnect_stream(self):
        try:
            self._ws_stream.close()
            return True
        except:
            return False

    async def send_stream(self, msg):
        self._ws_stream.send(msg)
        return None
