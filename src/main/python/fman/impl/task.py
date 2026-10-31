class StubProgressDialog:
	def __init__(self):
		self._task_size = 0
		self._progress = 0
		self._was_canceled = False
	def set_text(self, status):
		pass
	def set_task_size(self, size):
		self._task_size = size
	def set_progress(self, progress):
		self._progress = progress
	def get_progress(self):
		return self._progress
	def was_canceled(self):
		return self._was_canceled
	def show_alert(self, *args, **kwargs):
		raise NotImplementedError(
			'Task#show_alert(...) is only supported for tasks with a GUI'
		)
	def show_overwrite_dialog(self, *args, **kwargs):
		raise NotImplementedError(
			'Task#show_overwrite_dialog(...) is only supported for tasks with a GUI'
		)
	def show_prompt(self, *args, **kwargs):
		raise NotImplementedError(
			'Task#show_prompt(...) is only supported for tasks with a GUI'
		)
	def show_workers(self, workers):
		pass

class ChildProgressDialog:
	def __init__(self, parent):
		self._parent = parent
		self._progress_start = parent.get_progress()
	def set_text(self, status):
		self._parent.set_text(status)
	def set_task_size(self, size):
		raise NotImplementedError(
			'Setting the size of a subtask that has already been started is '
			'currently not supported.'
		)
	def set_progress(self, progress):
		self._parent.set_progress(self._progress_start + progress)
	def get_progress(self):
		return self._parent.get_progress() - self._progress_start
	def was_canceled(self):
		return self._parent.was_canceled()
	def show_alert(self, *args, **kwargs):
		return self._parent.show_alert(*args, **kwargs)
	def show_overwrite_dialog(self, *args, **kwargs):
		return self._parent.show_overwrite_dialog(*args, **kwargs)
	def show_prompt(self, *args, **kwargs):
		return self._parent.show_prompt(*args, **kwargs)
	def show_workers(self, workers):
		self._parent.show_workers(workers)
