from typing import Sequence

from fman import Task
from fman.fs import FileSystem
from fman.url import basename


class MoveByCopy(Task):
	"""Copy an item to its destination before deleting its source."""

	def __init__(
		self, fs: FileSystem, src_url: str, dst_url: str,
		copy_tasks: Sequence[Task]
	) -> None:
		size = sum(task.get_size() for task in copy_tasks)
		super().__init__('Moving ' + basename(src_url), size=size)
		self._fs = fs
		self._src_url = src_url
		self._dst_url = dst_url
		self._copy_tasks = copy_tasks
	def __call__(self) -> None:
		for task in self._copy_tasks:
			self.run(task)
		self.check_canceled()
		if not self._fs.exists(self._dst_url):
			raise OSError(
				'Copy completed but the destination is missing; the source was kept.'
			)
		self._fs.delete(self._src_url)
