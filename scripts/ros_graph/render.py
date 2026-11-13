"""Rendering of the extracted ROS graph as Graphviz image and wiki page."""

from __future__ import annotations

import html
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from extract import RosNode

DEBUG_KEYWORDS = ("debug", "markers", "/points", "/objects")


@dataclass
class Source:
    """A repository the graph was generated from."""

    repo: str
    branch: str
    commit: str
    archived: bool = False


@dataclass
class Graph:
    """Nodes plus the derived topic table."""

    nodes: list[RosNode]
    config: dict[str, Any]
    sources: dict[str, Source]

    def __post_init__(self) -> None:
        """Index topics by publisher and subscriber."""
        self.external = [
            (ext["name"], ext.get("note", ""), ext.get("publishes", {}))
            for ext in self.config.get("external_nodes", [])
        ]
        self.types: dict[str, str] = {}
        self.publishers: dict[str, list[str]] = {}
        self.subscribers: dict[str, list[str]] = {}
        for node in self.nodes:
            for topic, msg_type in node.publishes.items():
                self.types.setdefault(topic, msg_type)
                self.publishers.setdefault(topic, []).append(node.name)
            for topic, msg_type in node.subscribes.items():
                self.types.setdefault(topic, msg_type)
                self.subscribers.setdefault(topic, []).append(node.name)
        for name, _note, publishes in self.external:
            for topic, msg_type in publishes.items():
                self.types.setdefault(topic, msg_type)
                self.publishers.setdefault(topic, []).append(name)
        node_names = {n.name for n in self.nodes}
        self.missing_controlled = sorted(
            {c for n in self.nodes for c in n.controls} - node_names
        )

    def without_publisher(self) -> list[str]:
        """Topics that are subscribed but never published."""
        return sorted(t for t in self.types if not self.publishers.get(t))

    def without_subscriber(self) -> list[str]:
        """Non-debug topics that are published but never subscribed."""
        return sorted(
            t for t in self.types if not self.subscribers.get(t) and not is_debug(t)
        )

    def mismatched_types(self) -> list[tuple[str, str]]:
        """Topics used with different message types."""
        result = []
        for topic in sorted(self.types):
            used = {
                n.publishes.get(topic) or n.subscribes.get(topic)
                for n in self.nodes
                if topic in n.publishes or topic in n.subscribes
            }
            if len(used) > 1:
                result.append((topic, ", ".join(sorted(used))))
        return result


def is_debug(topic: str) -> bool:
    """Return whether the topic is a debug/visualization output."""
    return any(k in topic for k in DEBUG_KEYWORDS)


def _q(name: str) -> str:
    return '"' + name.replace('"', '\\"') + '"'


def _e(text: str) -> str:
    return html.escape(text, quote=False)


def to_dot(graph: Graph) -> str:
    """Build the Graphviz DOT source."""
    layers = graph.config["layers"]
    scripts = graph.config["launch_scripts"]
    out = [
        "digraph smarty {",
        "  graph [rankdir=LR, splines=true, nodesep=0.18, ranksep=0.9,"
        ' fontname="Helvetica", bgcolor="white", pad=0.4,'
        " label=<<b>Smarty vehicle stack - ROS 2 nodes and topics</b><br/>"
        f'<font point-size="11">{_e(graph.config["org"])} · generated from source'
        " (launch YAML params resolved)</font>>, labelloc=t, fontsize=20];",
        '  node [fontname="Helvetica", fontsize=10];',
        '  edge [fontname="Helvetica", fontsize=8, color="#555555", arrowsize=0.6];',
    ]

    for node in graph.nodes:
        color = layers.get(node.layer, layers["dev"])["color"]
        source = graph.sources.get(node.repo)
        repo = node.repo or node.package
        if source and source.branch != "jazzy":
            repo += f"@{source.branch}"
        if source and source.archived:
            repo += " (archived)"
        notes = [node.note] if node.note else []
        partial = [s for s in node.launched_by if s in scripts]
        if partial and len(partial) < len(scripts):
            notes.append("only " + ", ".join(partial))
        extra = "".join(
            f'<br/><font point-size="8"><i>{_e(n)}</i></font>' for n in notes
        )
        shape = "note" if node.package == "ros2cli" else "box"
        out.append(
            f'  {_q(node.name)} [shape={shape}, style="rounded,filled",'
            f' fillcolor="{color}", penwidth=1.4, label=<<b>{_e(node.name)}</b><br/>'
            f'<font point-size="8" color="#444444">{_e(repo)}</font>{extra}>];'
        )

    for name, note, _publishes in graph.external:
        out.append(
            f'  {_q(name)} [shape=box, style="rounded,dashed", fontsize=9,'
            f' label=<{_e(name)}<br/><font point-size="8">{_e(note)}</font>>];'
        )
    out.extend(
        f'  {_q(name)} [shape=box, style="rounded,dashed", color="#c0392b",'
        f' fontcolor="#c0392b", fontsize=9, label="{name}\\n(does not exist)"];'
        for name in graph.missing_controlled
    )

    for hw in graph.config.get("hardware", []):
        out.append(
            f'  {_q(hw["name"])} [shape=box3d, style=filled, fillcolor="#b9d3ee",'
            f" label=<<b>{_e(hw['name'])}</b><br/>"
            f'<font point-size="8">{_e(hw.get("note", ""))}</font>>];'
        )
        style = f'style=bold, color="#2c6fad", label="{hw.get("label", "")}"'
        out.extend(
            f"  {_q(hw['name'])} -> {_q(n)} [{style}];" for n in hw.get("to", [])
        )
        # Feedback edges must not affect the ranking, otherwise the
        # sensor side ends up at the far right of the graph
        out.extend(
            f"  {_q(n)} -> {_q(hw['name'])} [{style}, constraint=false];"
            for n in hw.get("from", [])
        )

    for topic, msg_type in graph.types.items():
        debug = is_debug(topic)
        if not graph.publishers.get(topic):
            style = (
                'style="filled,dashed", fillcolor="#fde2e2", color="#c0392b",'
                " penwidth=1.5"
            )
        elif debug:
            style = (
                'style=filled, fillcolor="#f4f4f4", color="#aaaaaa",'
                ' fontcolor="#777777"'
            )
        elif not graph.subscribers.get(topic):
            style = 'style="filled,dashed", fillcolor="#fff4d6", color="#d68910"'
        else:
            style = 'style=filled, fillcolor="white", color="#333333"'
        size = 8 if debug else 9
        out.append(
            f'  {_q(topic)} [shape=ellipse, {style}, margin="0.04,0.02",'
            f' label=<<font point-size="{size + 1}">{_e(topic)}</font><br/>'
            f'<font point-size="{size - 1}" color="#666666">{_e(msg_type)}</font>>];'
        )

    for topic, names in graph.publishers.items():
        color = "#aaaaaa" if is_debug(topic) else "#1f6f43"
        out.extend(f'  {_q(n)} -> {_q(topic)} [color="{color}"];' for n in names)
    for topic, names in graph.subscribers.items():
        color = "#aaaaaa" if is_debug(topic) else "#2c3e94"
        out.extend(f'  {_q(topic)} -> {_q(n)} [color="{color}"];' for n in names)

    for node in graph.nodes:
        out.extend(
            f'  {_q(node.name)} -> {_q(c)} [style=dotted, color="#8e44ad",'
            " constraint=false, arrowhead=odot, penwidth=1.3];"
            for c in node.controls
        )

    out += _legend(layers)
    out.append("}")
    return "\n".join(out)


def _legend(layers: dict[str, Any]) -> list[str]:
    lines = [
        "  subgraph cluster_legend {",
        '    label=<<b>Legend</b>>; style=rounded; color="#999999"; fontsize=12;',
        '    "lg_node" [shape=box, style="rounded,filled", fillcolor="#ffffff",'
        ' label=<<b>ROS node</b><br/><font point-size="8">repo</font>>];',
        '    "lg_topic" [shape=ellipse, style=filled, fillcolor=white,'
        ' label=<topic<br/><font point-size="8">msg type</font>>];',
        '    "lg_nosub" [shape=ellipse, style="filled,dashed", fillcolor="#fff4d6",'
        ' color="#d68910", label="published,\\nnobody subscribes", fontsize=9];',
        '    "lg_nopub" [shape=ellipse, style="filled,dashed", fillcolor="#fde2e2",'
        ' color="#c0392b", label="subscribed,\\nnobody publishes", fontsize=9];',
        '    "lg_debug" [shape=ellipse, style=filled, fillcolor="#f4f4f4",'
        ' color="#aaaaaa", fontcolor="#777777", label="debug / visualization",'
        " fontsize=9];",
        '    "lg_a" [shape=point, width=0.05]; "lg_b" [shape=point, width=0.05];',
        '    "lg_c" [shape=point, width=0.05]; "lg_d" [shape=point, width=0.05];',
        '    "lg_e" [shape=point, width=0.05]; "lg_f" [shape=point, width=0.05];',
        '    "lg_a" -> "lg_b" [color="#1f6f43", label="publishes"];',
        '    "lg_c" -> "lg_d" [color="#2c3e94", label="subscribes"];',
        '    "lg_e" -> "lg_f" [style=dotted, color="#8e44ad", arrowhead=odot,'
        ' label="sets node state param"];',
        '    "lg_node" -> "lg_topic" -> "lg_nosub" -> "lg_nopub" -> "lg_debug"'
        " [style=invis];",
    ]
    lines += [
        f'    "lg_{layer}" [shape=box, style="rounded,filled",'
        f' fillcolor="{spec["color"]}", label=<{_e(spec["label"])}>, fontsize=9];'
        for layer, spec in layers.items()
    ]
    lines.append(
        "    " + " -> ".join(f'"lg_{layer}"' for layer in layers) + " [style=invis];"
    )
    lines.append("  }")
    return lines


def to_markdown(
    graph: Graph, warnings: list[str], image_dir: str, pending: list[str]
) -> str:
    """Build the wiki page."""
    org = graph.config["org"]
    pending_note = (
        [
            "Tracked, but not on the analyzed branch yet (added automatically once"
            " merged): " + ", ".join(f"`{p}`" for p in pending),
            "",
        ]
        if pending
        else []
    )
    md = [
        "# ROS Topic Graph",
        "",
        "> **Auto-generated, do not edit.** This page is updated by the"
        f" [ROS graph workflow](https://github.com/{org}/smarty_workspace/actions/"
        "workflows/ros-graph.yaml) whenever one of the analyzed repositories changes."
        f" The generator lives in [smarty_workspace/scripts/ros_graph](https://github.com/"
        f"{org}/smarty_workspace/tree/jazzy/scripts/ros_graph).",
        "",
        "Nodes started by "
        + " / ".join(f"`{s}`" for s in graph.config["launch_scripts"])
        + " plus packages in development. Topic names are extracted from the"
        " source code and resolved with the YAML parameters of the launch files.",
        "",
        *pending_note,
        f"[![ROS topic graph]({image_dir}/smarty_ros_graph.png)]"
        f"({image_dir}/smarty_ros_graph.svg)",
        "",
        "*Click the image for the zoomable SVG.*",
        "",
        "## Issues",
        "",
    ]

    def node_list(names: list[str]) -> str:
        return ", ".join(f"`{n}`" for n in names)

    issues = [
        f"| `{topic}` | `{graph.types[topic]}` | nobody publishes, subscribed by "
        f"{node_list(graph.subscribers.get(topic, []))} |"
        for topic in graph.without_publisher()
    ]
    issues.extend(
        f"| `{topic}` | `{graph.types[topic]}` | nobody subscribes, published by "
        f"{node_list(graph.publishers.get(topic, []))} |"
        for topic in graph.without_subscriber()
    )
    for topic, types in graph.mismatched_types():
        issues.append(f"| `{topic}` | {types} | used with different message types |")
    for name in graph.missing_controlled:
        controller = [n.name for n in graph.nodes if name in n.controls]
        issues.append(
            f"| `{name}` | node | {node_list(controller)} sets its state, "
            "but the node does not exist |"
        )
    if issues:
        md += ["| Topic / Node | Type | Problem |", "| --- | --- | --- |", *issues]
    else:
        md.append("No dangling topics found.")
    if warnings:
        md += ["", "### Extraction warnings", ""]
        md += [f"- {w}" for w in warnings]

    md += [
        "",
        "## Nodes",
        "",
        "| Node | Repository | Started by | Publishes | Subscribes |",
        "| --- | --- | --- | --- | --- |",
    ]
    for node in sorted(graph.nodes, key=lambda n: (n.layer, n.name)):

        def topics(entries: dict[str, str]) -> str:
            return "<br>".join(f"`{t}`" for t in sorted(entries)) or "-"

        md.append(
            f"| `{node.name}` | {node.repo} | {', '.join(node.launched_by)} | "
            f"{topics(node.publishes)} | {topics(node.subscribes)} |"
        )

    md += [
        "",
        "## Sources",
        "",
        "| Repository | Branch | Commit |",
        "| --- | --- | --- |",
    ]
    for source in graph.sources.values():
        url = f"https://github.com/{org}/{source.repo}"
        commit = (
            f"[`{source.commit[:7]}`]({url}/commit/{source.commit})"
            if source.commit
            else "-"
        )
        archived = " (archived)" if source.archived else ""
        md.append(
            f"| [{source.repo}]({url}){archived} | `{source.branch}` | {commit} |"
        )
    md.append("")
    return "\n".join(md)
