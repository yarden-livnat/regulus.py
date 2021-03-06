from traitlets import observe
from regulus.core.mutable import Mutable
from regulus.core.traittypes import Function
from .transform import TransformTree


class ReduceTree(TransformTree):
    filter = Function(None, allow_none=True)

    def __init__(self, src=None, filter=None):
        super().__init__(src, self._reduce)
        if filter is not None:
            self.filter = filter

    def _reduce(self, tree):
        if self.filter is not None:
            return tree.reduce(self.filter)
        return None

    @observe('filter')
    def _filter(self, change):
        old = change['old']
        if isinstance(old, Mutable):
            old.unobserve(self.apply, names='version')

        new = change['new']
        if isinstance(new, Mutable):
            new.observe(self.apply, names='version')

        self.apply()

    # @observe('tree')
    # def _tree_changed(self, change):
    #     if self.filter is not None and hasattr(self.filter, 'update_range'):
    #         self.filter.update_range(self.tree)
