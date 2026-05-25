"""
PartScape Patch — Map all Part Categories to ERPNext Item Groups.

Runs the keyword mapper over all 688 Part Categories and caches
results in the Part Category.item_group field.
"""

from partscape.utils.category_mapper import map_all_categories


def execute():
    stats = map_all_categories()
    print(
        f"Category mapping complete: {stats['mapped']} mapped "
        f"({stats['fallback_to_parent']} via parent), "
        f"{stats['unmapped']} unmapped out of {stats['total']} total."
    )
