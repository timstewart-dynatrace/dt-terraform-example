"""Post-export topology analysis: map entity relationships in exported configs."""

import json
import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

from tabulate import tabulate

from ..core.types import TopologyNode, TopologyReport

logger = logging.getLogger("pipeline")

# UUID pattern (Dynatrace entity IDs and config IDs)
_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)

# Known cross-reference field names in Dynatrace configs
_REFERENCE_FIELDS = {
    "managementZoneId", "managementZoneIds", "managementZones",
    "alertingProfile", "alertingProfileId",
    "entityId", "entityIds",
    "tagFilterIncludeMode", "tagFilters",
    "dashboardMetadata",
}


class TopologyAnalyzer:
    """Analyze entity relationships in exported configuration files."""

    def __init__(self, export_dir: Path, config_types: List[str]):
        self.export_dir = export_dir
        self.config_types = config_types

    def analyze(self) -> TopologyReport:
        """Scan exported JSON files and build a dependency graph."""
        report = TopologyReport()

        # Collect all known item IDs per type
        all_ids: Dict[str, Set[str]] = defaultdict(set)
        nodes_by_id: Dict[str, TopologyNode] = {}

        for config_type in self.config_types:
            type_dir = self.export_dir / config_type
            if not type_dir.is_dir():
                continue

            for json_file in sorted(type_dir.glob("*.json")):
                data = json.loads(json_file.read_text())
                item_id = data.get("id", data.get("entityId", json_file.stem))
                item_name = data.get("name", data.get("displayName", json_file.stem))

                all_ids[config_type].add(str(item_id))

                # Find references to other IDs in this config
                refs = self._find_references(data)

                node = TopologyNode(
                    config_type=config_type,
                    item_id=str(item_id),
                    item_name=str(item_name),
                    references=list(refs),
                )
                report.nodes.append(node)
                nodes_by_id[str(item_id)] = node

        # Build edges: if node A references an ID that belongs to node B
        all_known_ids: Dict[str, str] = {}  # id -> config_type
        for ct, ids in all_ids.items():
            for i in ids:
                all_known_ids[i] = ct

        for node in report.nodes:
            for ref_id in node.references:
                if ref_id in all_known_ids and ref_id != node.item_id:
                    report.edges.append((
                        node.item_id,
                        ref_id,
                        f"{node.config_type} -> {all_known_ids[ref_id]}",
                    ))

        # Compute dependency layers
        report.layers = self._compute_layers(report.nodes, report.edges, all_ids)

        return report

    def _find_references(self, data: Dict, depth: int = 0) -> Set[str]:
        """Recursively scan a JSON object for UUID references."""
        if depth > 10:
            return set()

        refs: Set[str] = set()

        if isinstance(data, dict):
            for key, value in data.items():
                if key in _REFERENCE_FIELDS and isinstance(value, str):
                    refs.update(_UUID_RE.findall(value))
                elif isinstance(value, (dict, list)):
                    refs.update(self._find_references(value, depth + 1))
                elif isinstance(value, str) and key in _REFERENCE_FIELDS:
                    refs.update(_UUID_RE.findall(value))
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    refs.update(self._find_references(item, depth + 1))

        return refs

    def _compute_layers(
        self,
        nodes: List[TopologyNode],
        edges: List[Tuple[str, str, str]],
        all_ids: Dict[str, Set[str]],
    ) -> Dict[int, List[str]]:
        """Compute deployment order layers (topological sort by type)."""
        # Build a type-level dependency graph
        type_deps: Dict[str, Set[str]] = defaultdict(set)
        for source_id, target_id, label in edges:
            source_type = label.split(" -> ")[0]
            target_type = label.split(" -> ")[1] if " -> " in label else ""
            if source_type != target_type and target_type:
                type_deps[source_type].add(target_type)

        # Simple layered topological sort
        layers: Dict[int, List[str]] = {}
        assigned: Set[str] = set()
        all_types = set(all_ids.keys())

        layer = 0
        while assigned != all_types:
            # Types whose dependencies are all assigned (or have none)
            ready = [
                t for t in all_types - assigned
                if type_deps.get(t, set()).issubset(assigned)
            ]
            if not ready:
                # Remaining types have circular deps — assign them all
                ready = list(all_types - assigned)

            layers[layer] = sorted(ready)
            assigned.update(ready)
            layer += 1

        return layers

    @staticmethod
    def format_report(report: TopologyReport) -> str:
        """Format topology report as markdown."""
        lines = [
            "## Topology Analysis",
            "",
            f"- **Nodes:** {len(report.nodes)}",
            f"- **Cross-references:** {len(report.edges)}",
            "",
        ]

        # Dependency layers
        if report.layers:
            lines.append("### Deployment Order (by dependency layer)")
            lines.append("")
            for layer_num in sorted(report.layers.keys()):
                types = report.layers[layer_num]
                type_summary = ", ".join(types)
                lines.append(f"- **Layer {layer_num + 1}** (no deps)" if layer_num == 0
                             else f"- **Layer {layer_num + 1}**")
                lines.append(f"  {type_summary}")
            lines.append("")

        # Edge summary
        if report.edges:
            lines.append("### Cross-Reference Summary")
            lines.append("")
            edge_counts: Dict[str, int] = defaultdict(int)
            for _, _, label in report.edges:
                edge_counts[label] += 1
            rows = [[label, count] for label, count in sorted(edge_counts.items())]
            lines.append(tabulate(rows, headers=["Relationship", "Count"], tablefmt="github"))
            lines.append("")

        if report.cycles:
            lines.append("### Circular Dependencies")
            for cycle in report.cycles:
                lines.append(f"- {' -> '.join(cycle)}")
        else:
            lines.append("*No circular dependencies detected.*")

        return "\n".join(lines)
