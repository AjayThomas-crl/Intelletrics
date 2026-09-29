"""Bounded, expiring process-local dataset cache; Supabase is the source of truth."""
from collections import OrderedDict
from collections.abc import MutableMapping
from threading import RLock
from time import monotonic


class DatasetCache(MutableMapping):
    def __init__(self, max_entries=4, ttl=1800, max_bytes=64 * 1024 * 1024):
        self.max_entries, self.ttl, self.max_bytes = max_entries, ttl, max_bytes
        self._entries = OrderedDict()
        self._lock = RLock()

    def _expire(self):
        now = monotonic()
        for key, (_, expires, _) in list(self._entries.items()):
            if expires <= now:
                del self._entries[key]

    def __getitem__(self, key):
        with self._lock:
            self._expire()
            value, _, _ = self._entries[key]
            self._entries.move_to_end(key)
            return value

    def __setitem__(self, key, value):
        size = int(value["dataframe"].memory_usage(index=True, deep=True).sum())
        with self._lock:
            self._expire()
            self._entries.pop(key, None)
            if size > self.max_bytes:
                return  # Large datasets still work; they simply bypass this cache.
            self._entries[key] = (value, monotonic() + self.ttl, size)
            while len(self._entries) > self.max_entries or sum(item[2] for item in self._entries.values()) > self.max_bytes:
                self._entries.popitem(last=False)

    def __delitem__(self, key):
        with self._lock:
            del self._entries[key]

    def __iter__(self):
        with self._lock:
            self._expire()
            return iter(list(self._entries))

    def __len__(self):
        with self._lock:
            self._expire()
            return len(self._entries)


datasets = DatasetCache()
