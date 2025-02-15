import asyncio
from time import sleep

from xAPI import XAPI

async def main():
    main_api = XAPI("17536313", "Mj%Lc8S8RLG&a")
    result = main_api.establish_connection()
    if result is False:
        return False

    # testing functions
    print(main_api.ping())
    print(main_api.get_server_time())
    print(main_api.get_balance())
    print(main_api.get_margin("BITCOIN", 0.1))
    print(main_api.get_symbol("BITCOIN"))
    print(main_api.get_history())


    task1 = asyncio.create_task(main_api.get_keep_alive())
    task2 = asyncio.create_task(main_api.close_all_stream_connections())

    result = await task1
    result = await task2

    print("xd")

    main_api.logout()


asyncio.run(main())