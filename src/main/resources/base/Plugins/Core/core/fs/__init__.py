from importlib import import_module as _import_module

__all__ = []
for _module_name in ('local', 'zip', 'rar'):
	_module = _import_module('.' + _module_name, __name__)
	_module_names = getattr(
		_module, '__all__',
		(name for name in vars(_module) if not name.startswith('_'))
	)
	for _name in _module_names:
		globals()[_name] = getattr(_module, _name)
		__all__.append(_name)
