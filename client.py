import os
import re
import json
import argparse
import asyncio
import aio_pika
from aiohttp import web
import jinja2
import aiohttp_jinja2
from helpers import log


basedir = os.path.abspath(os.path.dirname(__file__))


async def index(request):
	return aiohttp_jinja2.render_template('index.html', request, context=None)


async def update(request):
	global current_condition
	return web.Response(text=json.dumps(current_condition))


app = web.Application()
app.router.add_route('GET', '/', index)
app.router.add_route('POST', '/update', update)
app.router.add_static('/static', os.path.join(basedir, 'static'))
aiohttp_jinja2.setup(
	app,
	loader=jinja2.FileSystemLoader(os.path.join(basedir, 'templates'))
)


async def pull(loop, broker_address):
	global connection
	global channel
	global current_condition
	connection = await aio_pika.connect_robust(
		f'amqp://{broker_address}/', loop=loop
	)

	async with connection:
		queue_name = 'catalog_monitoring'
		channel = await connection.channel()
		queue = await channel.declare_queue(queue_name)
		async with queue.iterator() as queue_iter:
			async for message in queue_iter:
				async with message.process():
					body = message.body.decode()
					condition = body.split('Current condition:\n')[1]
					path = body.split('\n')[1].split(':')[-1].strip()
					current_condition['path'] = path
					current_condition['files'] = [s.strip().strip("'") for s in re.search('\[(.*?)\]', condition.split('\n')[1]).group(1).split(',')]
					current_condition['folders'] = [s.strip().strip("'") for s in re.search('\[(.*?)\]', condition.split('\n')[0]).group(1).split(',')]
					log(body)


async def get_handler(app):
	handler = web.AppRunner(app)
	await handler.setup()
	return handler


async def start_site(handler):
	site = web.TCPSite(handler, '0.0.0.0', 8080)
	await site.start()


async def stop_handler(handler):
	await handler.cleanup()


def parse_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('broker_address', type=str, help='Broker address')
	args = parser.parse_args()
	return args.broker_address


if __name__ == '__main__':
	broker_address = parse_args()
	connection = channel = None
	current_condition = dict()
	loop = asyncio.get_event_loop()
	handler = loop.run_until_complete(get_handler(app))
	loop.run_until_complete(start_site(handler))
	try:
		loop.run_until_complete(pull(loop, broker_address))
	except KeyboardInterrupt:
		pass
	finally:
		loop.run_until_complete(channel.close())
		loop.run_until_complete(connection.close())
		loop.run_until_complete(stop_handler(handler))
	loop.close()