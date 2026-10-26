import os

from requests import RequestException
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import requests

CHUNK_SIZE = 64 * 1024

def get_bytes(url):
	try:
		return urlopen(url).read()
	except HTTPError:
		raise
	except URLError:
		# Fallback: Some users get "SSL: CERTIFICATE_VERIFY_FAILED" for urlopen.
		try:
			response = requests.get(url)
		except RequestException as e:
			raise URLError(e.__class__.__name__)
		if response.status_code != 200:
			raise HTTPError(
				url, response.status_code, response.reason, response.headers,
				None
			)
		return response.content


def download(url, path, task):
	part_path = path + '.part'

	def write_response(response, streaming):
		content_length = response.headers.get('Content-Length')
		if content_length is not None:
			task.set_size(int(content_length))
		if streaming:
			def iter_chunks():
				try:
					yield from response.iter_content(chunk_size=CHUNK_SIZE)
				except RequestException as e:
					raise URLError(e.__class__.__name__)
			chunks = iter_chunks()
		else:
			chunks = iter(lambda: response.read(CHUNK_SIZE), b'')
		done = 0
		with open(part_path, 'wb') as file:
			for chunk in chunks:
				if not chunk:
					continue
				file.write(chunk)
				done += len(chunk)
				task.set_progress(done)
				task.check_canceled()

	try:
		try:
			with urlopen(url) as response:
				write_response(response, False)
		except HTTPError:
			raise
		except URLError:
			try:
				response = requests.get(url, stream=True)
			except RequestException as e:
				raise URLError(e.__class__.__name__)
			with response:
				if response.status_code != 200:
					raise HTTPError(
						url, response.status_code, response.reason, response.headers,
						None
					)
				write_response(response, True)
		os.replace(part_path, path)
	except BaseException:
		if os.path.exists(part_path):
			os.remove(part_path)
		raise
