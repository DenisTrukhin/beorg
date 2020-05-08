import os
import argparse
import pika
from helpers import log


def parse_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('path_to_catalog', type=str, help='Path to catalog')
	args = parser.parse_args()
	if os.path.exists(args.path_to_catalog):
		return args.path_to_catalog
	log('Wrong path')
	return


def follow(path):
	with pika.BlockingConnection(pika.ConnectionParameters('localhost')) as connection:
		log('Server started')
		channel = connection.channel()
		channel.queue_declare(queue='catalog_monitoring')
		walk_gen = os.walk(path)
		before_dirs, before_files = next(walk_gen)[1:]
		msg = '\nPath: {}\n'.format(path) + \
			'Current condition:\nFolders: {dirs}\nFiles: {files}'.format(
				dirs=before_dirs, 
				files=before_files
		)
		channel.basic_publish(exchange='', routing_key='catalog_monitoring', body=msg)
		try:
			while True:
				walk_gen = os.walk(path)
				after_dirs, after_files = next(walk_gen)[1:]
				added_dirs = [f for f in after_dirs if not f in before_dirs]
				added_files = [f for f in after_files if not f in before_files]
				removed_dirs = [f for f in before_dirs if not f in after_dirs]
				removed_files = [f for f in before_files if not f in after_files]
				msg = ''
				if added_dirs:
					event = 'Added folders: {}'.format(added_dirs)
					msg += event
					log(event)
				if added_files:
					event = 'Added files: {}'.format(added_files)
					msg += event
					log(event)
				if removed_dirs:
					event = 'Removed folders: {}'.format(removed_dirs)
					msg += event
					log(event)
				if removed_files:
					event = 'Removed files: {}'.format(removed_files)
					msg += event
					log(event)
				if msg:
					msg = '\nPath: {}\n'.format(path) + msg + '\nCurrent condition:\nFolders: {}\nFiles: {}'.format(
						after_dirs, after_files
					)
					channel.basic_publish(exchange='', routing_key='catalog_monitoring', body=msg)
				before_files = after_files
				before_dirs = after_dirs
		except KeyboardInterrupt:
			log('Server interrupted')
		except Exception as e:
			log('Error occured: {}'.format(e.args))

if __name__ == '__main__':
	path = parse_args()
	if path:
		follow(path)
	