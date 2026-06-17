"""
PartScape Patch — Part Category → Item Group mapper (legacy).

The Part Category DocType has been removed; categories are now represented
directly by ERPNext Item Groups. This patch is retained as a no-op for
sites where it was already executed.
"""


def execute():
    print("Part Category mapping skipped: Part Category DocType has been removed.")
