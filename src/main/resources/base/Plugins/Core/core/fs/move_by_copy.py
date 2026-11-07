# Keep the Core import path working while sharing the move task with fman.
from fman.impl.plugins.stream_transfer import MoveByCopy

__all__ = ['MoveByCopy']
