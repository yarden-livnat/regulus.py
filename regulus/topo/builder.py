from collections import defaultdict


class Merge(object):
    def __init__(self, level, is_max, src, dest):
        self.level = level
        self.is_max = is_max
        self.src = src
        self.dest = dest


class PartitionNode(object):
    _id_generator = -1
    _pts = None

    @staticmethod
    def gen_id():
        PartitionNode._id_generator += 1
        return PartitionNode._id_generator

    @staticmethod
    def reset(pts):
        PartitionNode._id_generator = -1
        PartitionNode._pts = pts

    def __init__(self, persistence, base_pts=None, min_idx=None, max_idx=None, from_partition=None, is_max=None):
        self.id = PartitionNode.gen_id()
        self.persistence = persistence
        self.span = []
        self.parent = None
        self.children = []
        self.orig = from_partition
        self.base = self.id

        self.extrema = set()
        self.base_pts = base_pts if base_pts is not None else []
        self.min_idx = min_idx
        self.max_idx = max_idx
        self.max_merge = is_max

        if from_partition is not None:
            self.add_child(from_partition)
            self.base = from_partition.base
        else:
            self.extrema.add(self.min_idx)
            self.extrema.add(self.max_idx)

    def add_child(self, child):
        child.parent = self
        self.children.append(child)
        self.extrema |= child.extrema
        if self.min_idx is None or PartitionNode._pts[child.min_idx] < PartitionNode._pts[self.min_idx]:
            self.min_idx = child.min_idx
            self.orig = child
            self.base = child.base
        if self.max_idx is None or PartitionNode._pts[child.max_idx] > PartitionNode._pts[self.max_idx]:
            self.max_idx = child.max_idx
            self.orig = child
            self.base = child.base

    def add_extrema(self, extrema_idx):
        if PartitionNode._pts[extrema_idx] <= PartitionNode._pts[self.min_idx]:
            self.min_idx = extrema_idx
        elif PartitionNode._pts[self.max_idx] <= PartitionNode._pts[extrema_idx]:
            self.max_idx = extrema_idx
        else:
            print("*** BUG: extrema_idx is not an extrema")
        self.extrema.add(extrema_idx)

    def merge(self, other):
        self.base_pts.extend(other.base_pts)
        self.extrema |= other.extrema
        if PartitionNode._pts[other.min_idx] < PartitionNode._pts[self.min_idx]:
            self.min_idx = other.min_idx
            self.orig = other
            self.base = other.base
        if PartitionNode._pts[other.max_idx] > PartitionNode._pts[self.max_idx]:
            self.max_idx = other.max_idx
            self.orig = other
            self.base = other.base


class Builder(object):
    def __init__(self, debug=False):
        self.base = None
        self.merges = []
        self.maxima = set()
        self.min_map = defaultdict(set)
        self.max_map = defaultdict(set)
        self.active = set()
        self.root = None
        self.pts = []
        self.original_pts = set()
        self.debug = debug
        self.mapping = dict()
        self.unique = set()
        self.hierarchy = None

        self.all = dict()
        self.data_pts = []
        self.single = 0

    def data(self, pts):
        self.data_pts = pts
        return self

    def msc(self, base, hierarchy):
        self.base = base
        self.hierarchy = hierarchy
        return self

    def build(self):
        self.prepare()
        self.count_pts()
        self.merge()
        self.create_root()
        if self.debug:
            print('simplification:')
            print(f'\tbefore: partitions:{self.total(self.root)}  depth={self.depth(self.root, 0)}')
        self.simplify(self.root)
        if self.debug:
            print(f'\tafter:  partitions={self.total(self.root)}  depth={self.depth(self.root, 0)}')

        self.single = 0
        idx = self.build_idx(self.root, 0)

        self.rename(self.root, 0)
        if self.debug and self.single > 0:
            print('found {} singles'.format(self.single))
        if len(self.pts) != len(self.data_pts):
            print(f'*** error: data has {len(self.data_pts)} but only {len(self.pts)} are accounted for')
        return self

    # internal

    def total(self, p):
        n = 1
        for child in p.children:
            n += self.total(child)
        return n

    def depth(self, p, d):
        pd = d+1
        for child in p.children:
            pd = max(pd, self.depth(child, d+1))
        return pd

    def prepare(self):
        PartitionNode.reset(self.data_pts)
        for key, pts in self.base.items():
            p = PartitionNode(persistence=0, base_pts=pts.tolist(), min_idx=key[0], max_idx=key[1])
            self.maxima.add(key[1])
            self.add_active(p)
        print(f'Base: {len(self.active)} partitions {len(self.data_pts)} points')

        for key, record in self.hierarchy.items():
            is_max = key in self.maxima
            self.merges.append(Merge(record[0], is_max, key, record[1]))

        self.merges.sort(key=lambda m: (m.level, m.src))
        high = self.merges[-1].level
        for merge in self.merges:
            merge.level /= high

    def merge(self):
        for record in self.merges:
            # print(record.level, record.is_max, record.src, record.dest)
            if record.src == record.dest:
                continue

            # check for a degenerate case: merge.dest may have been merged already (same persistence level)
            dest = self.current(record.dest)
            src = self.current(record.src)
            if src == dest:
                continue

            record.dest = dest
            record.src = src
            self.mapping[record.src] = record.dest

            if record.is_max:
                self.collapse(record, self.max_map, lambda item: item.min_idx)
            else:
                self.collapse(record, self.min_map, lambda item: item.max_idx)

    def collapse(self, merge, idx_map, idx):
        add_partitions = []
        remove_partitions = set()

        for d in idx_map[merge.dest]:
            new_partition = None
            remove_src = set()
            for s in idx_map[merge.src]:
                if idx(s) == idx(d):
                    if new_partition is None:
                        new_partition = PartitionNode(merge.level, from_partition=d, is_max=merge.is_max)
                        remove_partitions.add(d)  # can't be removed during the loop
                        add_partitions.append(new_partition)
                    new_partition.add_child(s)
                    remove_src.add(s)
            for s in remove_src:
                self.remove_active(s)

        sources = set(idx_map[merge.src])
        for s in sources:
            if s.persistence != merge.level:
                # create a new partition with a single child because the extrema value has changed
                new_partition = PartitionNode(merge.level, from_partition=s)
                new_partition.add_extrema(merge.dest)
                add_partitions.append(new_partition)
                remove_partitions.add(s)
            else:
                # degenerated case: reuse the partition
                self.remove_active(s)
                s.add_extrema(merge.dest)
                self.add_active(s)

        for r in remove_partitions:
            self.remove_active(r)
        for partition in add_partitions:
            self.add_active(partition)

    def simplify(self, p):
        children = []
        for child in p.children:
            self.simplify(child)
            if child.persistence == p.persistence:
                if len(child.children) > 0:
                    # print(f'simplify : child id={child.id} p={child.persistence} pts={len(child.base_pts)}  parent id={p.id} p={p.persistence}')
                    for grandchild in child.children:
                        children.append(grandchild)
                        grandchild.parent = p
                else:
                    # print(f'merging pts: {p.id}  {p.persistence} {len(p.base_pts)}  child {child.id} {child.persistence} {len(child.base_pts)}')
                    p.base_pts.extend(child.base_pts)
                    p.extrema |= child.extrema
                    if self.data_pts[child.min_idx] < self.data_pts[p.min_idx]:
                        p.min_idx = child.min_idx
                    if self.data_pts[child.max_idx] > self.data_pts[p.max_idx]:
                        p.max_idx = child.max_idx
            else:
                children.append(child)
        p.children = children

    def create_root(self):
        if len(self.active) != 1:
            print(len(self.active), 'active')
            raise RuntimeError('Error: found {} roots'.format(len(self.active)))
        self.root = self.active.pop()

    #
    # helpers
    #

    def current(self, partition):
        while partition in self.mapping:
            partition = self.mapping[partition]
        return partition

    def add_active(self, n):
        self.min_map[n.min_idx].add(n)
        self.max_map[n.max_idx].add(n)
        self.active.add(n)

    def remove_active(self, p):
        self.min_map[p.min_idx].discard(p)
        self.max_map[p.max_idx].discard(p)
        self.active.remove(p)

    def build_idx(self, partition, idx):
        first = idx
        if len(partition.children) == 0:
            n = len(partition.base_pts)
            if n > 0:
                self.pts.extend(partition.base_pts)
                idx += n
        else:
            if len(partition.children) == 1:
                self.single += 1
            for child in partition.children:
                idx = self.build_idx(child, idx)

        partition.span = (first, idx)
        span = self.pts[first:idx]
        extrema = set(filter(lambda p: p not in span, partition.extrema))
        partition.extrema = extrema
        return idx

    def describe(self, p, depth):
        print(f'{"."*depth} {p.id}: pts:{len(p.base_pts)} persistence={p.persistence} orig={p.orig}  base={p.base}')
        for child in p.children:
            self.describe(child, depth+1)

    def count_pts(self):
        pts = set()
        extrema = set()
        for p in self.active:
            self._count(p, pts, extrema)
        if len(pts) != len(self.data_pts):
            s = set(pts)
            s |= extrema
            print(
                f'lost some points: #pts={len(pts)}  #base_pts{len(self.data_pts)}  #extrema={len(extrema)}  #combined:{len(s)}')
        if not extrema <= pts:
            print(f'extrema not in points. extrema={extrema} #pts={len(pts)}')
        return len(pts), len(extrema)

    def _count(self, p, pts, extrema):
        for pt in p.base_pts:
            pts.add(pt)
        extrema |= p.extrema
        for child in p.children:
            self._count(child, pts, extrema)

    def rename(self, node, idx):
        node.id = idx
        idx += 1
        if node.persistence > 0:
            for child in node.children:
                idx = self.rename(child, idx)
        return idx

    def statistics(self):
        levels = defaultdict(list)
        self.stat(self.root, levels)
        n = 0
        b = 0
        for level in levels.keys():
            if level > 0:
                n += len(levels[level])
            else:
                b = len(levels[level])
        print('statistics: {} levels {} base, {} new'.format(len(levels), b, n))

