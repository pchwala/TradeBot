import asyncio
from xAPI import XAPI

async def main():
    main_api = XAPI("17536313", "Mj%Lc8S8RLG&a", "wss://ws.xtb.com/demo")

    time_task = asyncio.create_task(main_api.get_server_time())
    time = await time_task
    print(time)

    result = await main_api.ping()
    print(result)

    task1 = asyncio.create_task(main_api.get_keep_alive())
    task2 = asyncio.create_task(main_api.get_balance_stream())

    result = await task1
    result = await task2

    main_api.logout()


asyncio.run(main())