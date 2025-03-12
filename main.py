from aiohttp import ClientSession
import asyncio
image_urls = [
    "https://hub.docker.com/_/nginx/tags"
]



async def get_tags_data(image_url):
    async with ClientSession() as session:  # 使用 ClientSession 来发送请求
        async with session.get(image_url) as response:  # 发起 GET 请求
            html = await response.text()  # 获取响应的 HTML 内容
            print(html)  # 打印 HTML 内容


async def main():
    await asyncio.gather(get_tags_data(image_urls[0]))


if __name__ == "__main__":
    asyncio.run(main())
