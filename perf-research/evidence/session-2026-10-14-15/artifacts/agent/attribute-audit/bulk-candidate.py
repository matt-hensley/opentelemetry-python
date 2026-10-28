"""Candidate BoundedAttributes._set_items for local timing experiments.

Load this source into a copy of the live attributes module globals, then assign
the resulting function to the live BoundedAttributes class. Keeping the
function's globals bound to the live module lets it use the live cleaner,
types, logger, and class while this file remains an ignored prototype.
"""

SOURCE = '''\
def _set_items(self, attributes: Mapping[str, types.AnyValue]) -> None:
    self._raise_if_immutable()
    if self.maxlen is not None and self.maxlen == 0:
        with self._lock:
            self.dropped += len(attributes)
        return
    cleaned_attributes: Mapping[str, types.AnyValue] = _clean_attribute_value(
        attributes, self.max_value_len
    )
    with self._lock:
        self.dropped += len(attributes) - len(cleaned_attributes)
        if (
            type(self) is BoundedAttributes
            and not self._dict
            and isinstance(cleaned_attributes, dict)
            and (self.maxlen is None or len(cleaned_attributes) <= self.maxlen)
        ):
            self._dict = cleaned_attributes
            return
        if (
            type(self) is BoundedAttributes
            and type(cleaned_attributes) is dict
            and len(cleaned_attributes) >= 2
            and (self.maxlen is None or len(self._dict) + len(cleaned_attributes) <= self.maxlen)
            and self._dict.keys().isdisjoint(cleaned_attributes)
        ):
            self._dict.update(cleaned_attributes)
            return
        for key, value in cleaned_attributes.items():
            self._setitem_locked(key, value)
'''
