"""Load small, oriented image previews from local and virtual filesystems."""

from fman import fs
from fman.url import as_human_readable
from PyQt5.QtCore import QByteArray, QBuffer, QIODevice, QSize, Qt
from PyQt5.QtGui import QImage, QImageReader


def load_image_thumbnail(url: str, size: int) -> QImage | None:
	"""Read an image at `url`, scaled to fit within a square `size` edge."""
	try:
		if url.lower().startswith('file://'):
			reader = QImageReader(as_human_readable(url))
			return _read_scaled(reader, size)
		with fs.open(url, 'rb') as image_file:
			data = image_file.read()
		buffer = QBuffer()
		buffer.setData(QByteArray(data))
		if not buffer.open(QIODevice.ReadOnly):
			return None
		try:
			return _read_scaled(QImageReader(buffer), size)
		finally:
			buffer.close()
	except Exception:
		return None


def _read_scaled(reader: QImageReader, size: int) -> QImage | None:
	reader.setAutoTransform(True)
	original_size = reader.size()
	if not original_size.isEmpty():
		reader.setScaledSize(original_size.scaled(
			QSize(size, size), Qt.KeepAspectRatio
		))
	image = reader.read()
	return None if image.isNull() else image
