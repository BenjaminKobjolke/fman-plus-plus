from collections import namedtuple
from fman.impl.model.diff import ComputeDiff
from fman.impl.util import Event
from fman.impl.util.qt import DisplayRole, EditRole, DecorationRole, \
	ToolTipRole, ItemIsDropEnabled, ItemIsSelectable, ItemIsEnabled, \
	ItemIsEditable, ItemIsDragEnabled
from PyQt5.QtCore import QModelIndex, QVariant, Qt
from threading import RLock

# Draw this row faded.
DimmedRole = Qt.UserRole + 1

class TableModel:
	"""
	Mixin for QAbstractTableModel. Encapsulates the logic for a table where each
	row has an optional icon and the first column is editable, drag enabled and
	potentially drop enabled.
	"""
	def __init__(self, column_headers):
		super().__init__()
		self.transaction_ended = Event()
		self._column_headers = column_headers
		self._rows = Rows()
		self._dimmer = None
		self._transaction_level = 0
		self._transaction_made_changes = False
	def rowCount(self, parent=QModelIndex()):
		# According to the Qt docs for QAbstractItemModel#rowCount(...):
		#  > When implementing a table based model, rowCount() should
		#  > return 0 when the parent is valid.
		# So in theory, we should check parent.isValid() here. But because this
		# is a 2d-table, `parent` will never be anything but an invalid index.
		# So we forego this check to save ~100ms in performance.
		return len(self._rows)
	def columnCount(self, parent=QModelIndex()):
		# According to the Qt docs for QAbstractItemModel#columnCount(...):
		#  > When implementing a table based model, columnCount() should
		#  > return 0 when the parent is valid.
		# So in theory, we should check parent.isValid() here. But because this
		# is a 2d-table, `parent` will never be anything but an invalid index.
		# So we forego this check to save ~100ms in performance.
		return len(self._column_headers)
	def data(self, index, role=DisplayRole):
		if self._index_is_valid(index):
			if role == DimmedRole:
				return self._dimmer is not None \
					and self._dimmer(self._rows[index.row()].key)
			elif role in (DisplayRole, EditRole):
				return self._rows[index.row()].cells[index.column()].str
			elif role == DecorationRole and index.column() == 0:
				return self._rows[index.row()].icon
			elif role == ToolTipRole:
				return super().data(index, DisplayRole)
		return QVariant()
	def set_dimmer(self, dimmer):
		self._dimmer = dimmer
		if self.rowCount():
			self.dataChanged.emit(
				self.index(0, 0),
				self.index(self.rowCount() - 1, self.columnCount() - 1),
				[DimmedRole]
			)
	def headerData(self, section, orientation, role=DisplayRole):
		if orientation == Qt.Horizontal and role == DisplayRole \
			and 0 <= section < self.columnCount():
			return QVariant(self._column_headers[section])
		return QVariant()
	def flags(self, index):
		if index == QModelIndex():
			# The index representing our current location:
			return ItemIsDropEnabled
		# Need to set ItemIsEnabled - in particular for the last column - to
		# make keyboard shortcut "End" work. When we press this shortcut in a
		# QTableView, Qt jumps to the last column of the last row. But only if
		# this cell is enabled. If it isn't enabled, Qt simply does nothing.
		# So we set the cell to enabled.
		result = ItemIsSelectable | ItemIsEnabled
		if index.column() == 0:
			result |= ItemIsEditable | ItemIsDragEnabled
			if self._rows[index.row()].drop_enabled:
				result |= ItemIsDropEnabled
		return result
	def set_rows(self, rows):
		diff = ComputeDiff(self._rows, rows, key_fn=lambda row: row.key)()
		self._apply_diff(diff)
	def _apply_diff(self, diff):
		self._begin_transaction()
		for entry in diff:
			entry.apply(
				self.insert_rows, self.move_rows, self.update_rows,
				self.remove_rows
			)
			self._transaction_made_changes = True
		self._end_transaction()
	def insert_rows(self, rows, first_rownum=-1):
		if first_rownum == -1:
			first_rownum = len(self._rows)
		self.beginInsertRows(
			QModelIndex(), first_rownum, first_rownum + len(rows) - 1
		)
		self._rows.insert(rows, first_rownum)
		self.endInsertRows()
	def move_rows(self, cut_start, cut_end, insert_start):
		dst_row = _get_move_destination(cut_start, cut_end, insert_start)
		assert self.beginMoveRows(
			QModelIndex(), cut_start, cut_end - 1, QModelIndex(), dst_row
		)
		self._rows.move(cut_start, cut_end, insert_start)
		self.endMoveRows()
	def update_rows(self, rows, first_rownum):
		self._rows.update(rows, first_rownum)
		top_left = self.index(first_rownum, 0)
		bottom_right = \
			self.index(first_rownum + len(rows) - 1, self.columnCount() - 1)
		self.dataChanged.emit(top_left, bottom_right)
	def remove_rows(self, start, end=-1):
		if end == -1:
			end = start + 1
		self.beginRemoveRows(QModelIndex(), start, end - 1)
		self._rows.remove(start, end)
		self.endRemoveRows()
	def _index_is_valid(self, index):
		if not index.isValid() or index.model() != self:
			return False
		return 0 <= index.row() < self.rowCount() and \
			   0 <= index.column() < self.columnCount()
	def _begin_transaction(self):
		self._transaction_level += 1
	def _end_transaction(self):
		self._transaction_level -= 1
		if self._transaction_made_changes and not self._transaction_level:
			self._transaction_made_changes = False
			self.transaction_ended.trigger()

def _get_move_destination(cut_start, cut_end, insert_start):
	if cut_start == insert_start:
		raise ValueError('Not a move operation (%d, %d)' % (cut_start, cut_end))
	num_rows = cut_end - cut_start
	return insert_start + (num_rows if cut_start < insert_start else 0)

class Rows:
	def __init__(self):
		self._rows = []
		# key -> rownum, or None when rows were added or removed since it was
		# last built. Shifting every later rownum on each insert / remove
		# instead cost O(n) in Python per call - with thousands of inserts in
		# one directory listing, the bulk of a GUI freeze. #find(...) rebuilds.
		self._keys = {}
		self._lock = RLock()
	def __len__(self):
		return len(self._rows)
	def __getitem__(self, item):
		return self._rows[item]
	def __setitem__(self, i, row):
		with self._lock:
			old_row = self._rows[i]
			self._rows[i] = row
			if self._keys is not None:
				del self._keys[old_row.key]
				self._keys[row.key] = i
			self._check_integrity()
	def __iter__(self):
		return iter(self._rows)
	def reset_to(self, new_rows):
		new_keys = {row.key: i for i, row in enumerate(new_rows)}
		with self._lock:
			self._rows = new_rows
			self._keys = new_keys
			self._check_integrity()
	def insert(self, rows, first_rownum):
		with self._lock:
			# Perform this check here, once we have the lock:
			if first_rownum < 0 or first_rownum > len(self._rows) + 1:
				raise ValueError('Invalid first_rownum: %d' % first_rownum)
			self._rows = \
				self._rows[:first_rownum] + rows + self._rows[first_rownum:]
			self._keys = None
	def move(self, cut_start, cut_end, insert_start):
		with self._lock:
			rows = self._cut(cut_start, cut_end)
			self.insert(rows, insert_start)
	def update(self, rows, first_rownum):
		with self._lock:
			if self._keys is not None:
				for row in self._rows[first_rownum: first_rownum + len(rows)]:
					del self._keys[row.key]
				self._keys.update(
					(row.key, first_rownum + i) for i, row in enumerate(rows)
				)
			self._rows[first_rownum: first_rownum + len(rows)] = rows
			self._check_integrity()
	def remove(self, start, end):
		with self._lock:
			del self._rows[start:end]
			self._keys = None
	def find(self, key):
		with self._lock:
			if self._keys is None:
				self._keys = {row.key: i for i, row in enumerate(self._rows)}
				self._check_integrity()
			return self._keys[key]
	def _cut(self, cut_start, cut_end):
		with self._lock:
			num_rows = len(self._rows)
			if cut_start < 0 or cut_start >= num_rows:
				raise ValueError('Invalid cut_start: %d' % cut_start)
			if cut_end < 0 or cut_end > num_rows or cut_end <= cut_start:
				raise ValueError('Invalid cut_end: %d' % cut_end)
			result = self._rows[cut_start:cut_end]
			self._rows = self._rows[:cut_start] + self._rows[cut_end:]
			self._keys = None
			return result
	def _check_integrity(self):
		assert self._keys is None or len(self._rows) == len(self._keys), \
			'Integrity error, likely caused by duplicate rows'

# Bumped whenever the icons themselves change - see invalidate_icons().
_ICON_GENERATION = 0

def invalidate_icons():
	"""
	Marks every Row built from here on as different from the ones built
	before. Call this when the icons a file gets actually change - a new icon
	set or a new icon color - so that the diff a pane reload computes doesn't
	discard the new icons. See Row#__eq__.
	"""
	global _ICON_GENERATION
	_ICON_GENERATION += 1

class Row:
	def __init__(self, key, icon, drop_enabled, cells):
		self.key = key
		self.icon = icon
		self.drop_enabled = drop_enabled
		self.cells = cells
		self._icon_generation = _ICON_GENERATION
	def __eq__(self, other):
		"""
		Exclude .icon from == comparisons. The reason for this is that
		QFileIconProvider returns objects that don't compare equal even if they
		are equal. This is a problem particularly on Windows. For when we reload
		a directory, QFileIconProvider returns "new" icon values so our
		implementation must assume that all files in the directory have changed
		(when most likely they haven't).

		An earlier implementation used QIcon#cacheKey() in an attempt to solve
		the above problem. In theory, #cacheKey() is precisely meant to help
		with this. But in reality, especially on Windows, the problem remains
		(loading the icon of a file with QFileIconProvider twice gives two QIcon
		instances that look the same but have different cacheKey's).

		The icon generation is how a *real* icon change still gets through.
		Nothing else about a row changes when the user switches icon set or
		icon color, so without it ComputeDiff produces no update entry for the
		reload that follows - dataChanged is never emitted, self._rows keeps
		the old Rows, and the panes draw the old icons until you browse to
		another directory.
		"""
		try:
			return (
				self.key, self.cells, self.drop_enabled, self._icon_generation
			) == (
				other.key, other.cells, other.drop_enabled,
				other._icon_generation
			)
		except AttributeError:
			return NotImplemented
	def __hash__(self):
		return hash(self.key)
	def __repr__(self):
		return '<%s: %s>' % (self.__class__.__name__, self.key)

Cell = namedtuple('Cell', ('str', 'sort_value_asc', 'sort_value_desc'))
