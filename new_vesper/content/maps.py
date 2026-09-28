"""Drawing a district map (hand-drawn in content) with you-are-here and fog."""

from new_vesper.content.loader import Content

HERE = "@"
UNKNOWN = "???"


def render_map(
    content: Content, region_id: str, here: str | None, visited: frozenset[str]
) -> list[str]:
    """The region's map with [@] where the character is, and a legend.

    Places the character has never been are listed as ??? until they visit.
    """
    region = content.regions[region_id]
    lines = list(region.map)
    legend = []
    for mark, location_id in sorted(region.map_marks.items()):
        token = f"[{mark}]"
        if location_id == here:
            lines = [line.replace(token, f"[{HERE}]") for line in lines]
            label = f"{content.locations[location_id].name} ({location_id}) <- you are here"
            legend.append(f"  [{HERE}] {label}")
        elif location_id in visited:
            legend.append(f"  {token} {content.locations[location_id].name} ({location_id})")
        else:
            legend.append(f"  {token} {UNKNOWN}")
    return [region.name, "", *lines, "", *legend]
