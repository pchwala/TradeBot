import asyncio
import json
from time import sleep

from xAPI import XAPI
from scrapper import Scrapper


async def main():
    with open('credentials.json', 'r') as file:
        credentials = json.load(file)

    main_api = XAPI(credentials['id'], credentials['password'])
    scrapper = Scrapper()
    result = main_api.establish_connection()
    if result is False:
        return False

    # testing functions
    # print(main_api.ping())
    # print(main_api.get_server_time())
    # print(main_api.get_balance())
    # print(main_api.get_margin("BITCOIN", 0.1))
    # print(main_api.get_symbol("BITCOIN"))
    # print(main_api.get_history())



    task1 = asyncio.create_task(main_api.get_keep_alive_s())
    task2 = asyncio.create_task(main_api.close_all_stream_connections())
    task3 = asyncio.create_task(main_api.get_candles_s("BITCOIN"))
    task4 = asyncio.create_task(main_api.ping_interval(1))  # ping server with 1s interval to avoid closing connection

    result = await task1
    result = await task2
    result = await task3
    result = await task4

    print("xd")
    print(main_api.get_server_time())

    main_api.logout()


asyncio.run(main())