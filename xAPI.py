from idlelib.debugger_r import restart_subprocess_debugger

import websocket, json, openpyxl
import websockets
from datetime import datetime, timedelta
import asyncio



class XAPI:
    __version__ = "1.0"

    def __init__(self, id, pswd):

        self._dest_main = "wss://ws.xtb.com/demo"
        self._dest_stream = "wss://ws.xtb.com/demoStream"
        self._id = id
        self._pswd = pswd
        self._ws_main = None    # main websocket
        self._ws_stream = None  # streaming socket
        self._stream_id = None  # ID for streaming connections
        self.exec_start = None

        # List with all created stream connections
        self.stream_socket_list = []


    def establish_connection(self):
        """Establishes main connection from which all the different stream connections emerge"""
        self.exec_start = self.get_time()
        self._ws_main = self.connect()
        result = self.login()
        if result is not None:
            print(f"Main login attempt failed {result}")
            return False
        else:
            return True


    def login(self):
        login = {
            "command": "login",
            "arguments": {
                "userId": self._id,
                "password": self._pswd
            }
        }
        login_json = json.dumps(login)
        # Sending Login Request
        result = self.send(login_json)
        result = json.loads(result)
        if result['status'] is False:     # Sending failed
            return result

        self._stream_id = result["streamSessionId"]

        return None


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
        if str(status) == "True":
            return True
        else:
            print("Error during logging attempt: ", result)
            return False


    async def subscribe_command(self, command):
        """Creates stream connection and subscribes for server messages with specific command.
        Available commands: http://developers.xstore.pro/documentation/#available-streaming-commands"""
        command_json = json.dumps(command)
        ws = await self.create_stream_connection()
        await ws.send(command_json)
        return ws


    async def unsubscribe_command(self, command):
        """Creates new stream connection just to send unsubscribe command then closes it.
        This action causes connection that was subscribing to also close.
        Available commands: http://developers.xstore.pro/documentation/#available-streaming-commands"""
        command_json = json.dumps(command)
        async with websockets.connect(self._dest_stream) as ws:
            result = await ws.send(command_json)
            print(f"Unsubscribed: {result}")


    async def get_keep_alive_s(self):
        """Establishes stream connection with getKeepAlive command.
        This makes XTB server send 'keep alive' messages every 3 seconds """
        command = {
            "command": "getKeepAlive",
	        "streamSessionId": self._stream_id
        }
        ws = await self.subscribe_command(command)

        while True:
            try:
                msg = await ws.recv()
                print(msg)
            except Exception as e:
                print(f"get_keep_alive_s connection closed: {e}")
                return e


    async def get_balance_s(self):
        """Establishes stream connection with getBalance command.
        This makes XTB server send account indicator values in real-time as soon as they are available in the system"""
        command = {
            "command": "getBalance",
            "streamSessionId": self._stream_id
        }
        ws = await self.subscribe_command(command)

        while True:
            try:
                msg = await ws.recv()
                print(msg)
            except Exception as e:
                print(f"get_balance_s connection closed: {e}")
                return e


    async def get_candles_s(self, symbol):
        """Establishes stream connection with getCandles command.
        Subscribes for and unsubscribes from API chart candles. The interval of every candle is 1 minute.
        A new candle arrives every minute."""
        command = {
            "command": "getCandles",
            "streamSessionId": self._stream_id,
            "symbol": symbol
        }
        ws = await self.subscribe_command(command)

        while True:
            try:
                msg = await ws.recv()
                print(msg)
            except Exception as e:
                print(f"get_balance_s connection closed: {e}")
                return e


    def get_server_time(self):
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


    def ping(self):
        """Regularly calling this function is enough to refresh the internal state of all the components in the system.
         It is recommended that any application that does not execute other commands, should call this command at least once every 10 minutes."""
        ping = {
            "command": "ping"
        }
        ping_json = json.dumps(ping)
        result = self.send(ping_json)
        result = json.loads(result)
        return result


    async def ping_interval(self, interval):
        time = 0
        while True:
            result = self.ping()
            print("ping:", result, " time: ", time)
            time += 1
            await asyncio.sleep(interval)

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
        except Exception as e:
            print(f"Can't establish main connection: {e}")
            return False


    def disconnect(self):
        try:
            self._ws_main.close()
            return True
        except Exception as e:
            print(f"Error while trying to disconnect: {e}")
            return False


    def send(self, msg):
        try:
            self._ws_main.send(msg)
            result = self._ws_main.recv()
            return result + "\n"
        except Exception as e:
            print(f"Sending error: {e}")
            return False


    async def create_stream_connection(self):
        ws = await websockets.connect(self._dest_stream)  # Create connection
        self.stream_socket_list.append(ws)  # Add connect object to a list of all connections
        ws = self.stream_socket_list[-1]  # Return pointer to that element
        return ws

    async def close_all_stream_connections(self):
        for ws in self.stream_socket_list:  # Iterate list of all connections and try to close them
            try:
                await ws.close()
            except:
                pass