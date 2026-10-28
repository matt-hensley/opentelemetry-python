"""Exact-base constructor specialization for local timing experiments.

Load SOURCE into a copy of the live attributes module globals and assign the
resulting function to BoundedAttributes.__init__. Subclasses retain the normal
virtual _set_items path. This ignored prototype does not change live source.
"""

SOURCE = '''\
def __init__(
    self,
    maxlen: int | None = None,
    attributes: types.Attributes = None,
    immutable: bool = True,
    max_value_len: int | None = None,
    extended_attributes: bool = False,
) -> None:
    if maxlen is not None and maxlen < 0:
        raise ValueError("maxlen must be valid int greater or equal to 0")
    if max_value_len is not None and max_value_len < 0:
        raise ValueError("max_value_len must be valid int greater or equal to 0")
    self._dict: dict[str, types.AnyValue] = {}
    self.maxlen = maxlen
    self.dropped = 0
    self.max_value_len = max_value_len
    self._lock = threading.Lock()
    self._dropped_logged = False
    self._immutable = False
    if attributes:
        if type(self) is not BoundedAttributes:
            self._set_items(attributes)
        elif maxlen == 0:
            self.dropped = len(attributes)
        elif maxlen is not None and maxlen > 0 and len(attributes) > maxlen:
            self._set_items(attributes)
        else:
            cleaned_attributes: Mapping[str, types.AnyValue] = _clean_attribute_value(
                attributes, max_value_len
            )
            if isinstance(cleaned_attributes, dict) and (
                maxlen is None or len(cleaned_attributes) <= maxlen
            ):
                self.dropped = len(attributes) - len(cleaned_attributes)
                self._dict = cleaned_attributes
            else:
                self.dropped = len(attributes) - len(cleaned_attributes)
                with self._lock:
                    for key, value in cleaned_attributes.items():
                        self._setitem_locked(key, value)
    self._immutable = immutable
'''
