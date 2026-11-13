"""Static extraction of ROS 2 nodes and their topics from the package sources.

Nothing is built or launched: Python nodes are parsed with `ast`, C++ nodes with
regular expressions and launch files for node names, remappings and parameter
files. Topic names are resolved like at runtime: parameter default from the code,
overwritten by the YAML parameter files loaded by the launch file.
"""

from __future__ import annotations

import ast
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

SKIP_DIRS = {".git", "test", "tests", "build", "install", "log"}
# Parameters every SmartyNode declares implicitly
SMARTY_NODE_PARAMS = {"debug", "state"}


@dataclass
class RosNode:
    """A ROS node and its topic interface."""

    name: str
    package: str
    executable: str
    repo: str = ""
    layer: str = ""
    launched_by: list[str] = field(default_factory=list)
    publishes: dict[str, str] = field(default_factory=dict)
    subscribes: dict[str, str] = field(default_factory=dict)
    controls: list[str] = field(default_factory=list)
    note: str = ""


@dataclass
class Package:
    """A ROS package found in a repository."""

    name: str
    repo: str
    path: Path


@dataclass
class LaunchedNode:
    """A `Node(...)` action of a launch file."""

    package: str
    executable: str
    name: str | None
    remappings: dict[str, str]
    param_files: list[Path]


class Extractor:
    """Extracts the ROS nodes of a set of repositories."""

    def __init__(self, repos_dir: Path, workspace_dir: Path, config: dict[str, Any]):
        """Index all packages in the cloned repositories."""
        self.repos_dir = repos_dir
        self.workspace_dir = workspace_dir
        self.config = config
        self.warnings: list[str] = []
        # in_development packages that are not on the analyzed branch yet
        self.pending: list[str] = []
        self.packages: dict[str, Package] = {}
        for repo in config["repos"]:
            for xml in sorted((repos_dir / repo).rglob("package.xml")):
                if SKIP_DIRS.intersection(xml.relative_to(repos_dir).parts):
                    continue
                match = re.search(r"<name>\s*([\w-]+)\s*</name>", xml.read_text())
                if match:
                    name = match.group(1)
                    self.packages[name] = Package(name, repo, xml.parent)
        self.state_enum = self._find_nodes_enum()

    # ------------------------------------------------------------------ entry
    def extract(self) -> list[RosNode]:
        """Extract all nodes started by the launch scripts or in development."""
        nodes: dict[str, RosNode] = {}

        def add(node: RosNode | None, source: str) -> None:
            if node is None:
                return
            if node.name in nodes:
                if source not in nodes[node.name].launched_by:
                    nodes[node.name].launched_by.append(source)
            else:
                node.launched_by.append(source)
                nodes[node.name] = node

        for script in self.config["launch_scripts"]:
            for kind, args in self._parse_launch_script(self.workspace_dir / script):
                if args[0] in self.config.get("ignore_packages", []):
                    continue
                if kind == "launch":
                    for launched in self._parse_launch_file(*args, source=script):
                        add(self._extract_launched(launched), script)
                elif kind == "run":
                    launched = LaunchedNode(args[0], args[1], None, {}, [])
                    add(self._extract_launched(launched, source=script), script)
                elif kind == "pub":
                    topic, msg_type = args
                    add(
                        RosNode(
                            name="ros2 topic pub",
                            package="ros2cli",
                            executable="ros2",
                            note="CLI helper",
                            publishes={topic: normalize_type(msg_type)},
                        ),
                        script,
                    )

        for entry in self.config.get("in_development", []):
            # Not merged to the analyzed branch yet: added once it is
            if not self._has_launch_file(entry["package"], entry["launch"]):
                self.pending.append(entry["package"])
                continue
            for launched in self._parse_launch_file(
                entry["package"], entry["launch"], source="in_development"
            ):
                node = self._extract_launched(launched)
                if node is not None:
                    node.layer = "dev"
                add(node, "in development")

        self.warnings = list(dict.fromkeys(self.warnings))
        for node in nodes.values():
            if not node.layer:
                node.layer = self._layer_of(node.package)
        return list(nodes.values())

    def _layer_of(self, package: str) -> str:
        for layer, spec in self.config["layers"].items():
            if package in spec.get("packages", []):
                return layer
        return "dev"

    # ---------------------------------------------------------- launch parsing
    def _parse_launch_script(self, path: Path) -> list[tuple[str, tuple[str, ...]]]:
        """Find `ros2 launch|run|topic pub` commands in a shell script."""
        commands = []
        for raw_line in path.read_text().splitlines():
            line = raw_line.strip()
            if line.startswith("#") or "ros2 " not in line:
                continue
            words = shlex.split(line.split("ros2 ", 1)[1].rstrip("&").strip())
            if words[0] in {"launch", "run"} and len(words) >= 3:  # noqa: PLR2004
                commands.append((words[0], (words[1], words[2])))
            elif words[:2] == ["topic", "pub"] and len(words) >= 4:  # noqa: PLR2004
                commands.append(("pub", (words[2], words[3])))
        return commands

    def _has_launch_file(self, package: str, launch_file: str) -> bool:
        pkg = self.packages.get(package)
        return pkg is not None and any(
            ".git" not in p.parts for p in pkg.path.rglob(launch_file)
        )

    def _parse_launch_file(
        self, package: str, launch_file: str, source: str
    ) -> list[LaunchedNode]:
        """Return the `Node(...)` actions of a Python launch file."""
        pkg = self.packages.get(package)
        if pkg is None:
            self.warnings.append(
                f"{source}: package `{package}` of `{launch_file}` not found"
            )
            return []
        path = next(
            (p for p in pkg.path.rglob(launch_file) if ".git" not in p.parts), None
        )
        if path is None:
            self.warnings.append(
                f"{source}: launch file `{launch_file}` not found in `{package}`"
            )
            return []
        tree = ast.parse(path.read_text())
        yaml_files = [
            pkg.path / "config" / Path(c.value).name
            for c in ast.walk(tree)
            if isinstance(c, ast.Constant)
            and isinstance(c.value, str)
            and c.value.endswith(".yaml")
        ]
        launched = []
        for call in ast.walk(tree):
            if not (isinstance(call, ast.Call) and _call_name(call) == "Node"):
                continue
            kw = {k.arg: k.value for k in call.keywords}
            remaps = {}
            if isinstance(kw.get("remappings"), ast.List | ast.Tuple):
                for item in kw["remappings"].elts:
                    if isinstance(item, ast.Tuple) and len(item.elts) == 2:  # noqa: PLR2004
                        src, dst = (_const(e) for e in item.elts)
                        if src and dst:
                            remaps[src] = dst
            launched.append(
                LaunchedNode(
                    package=_const(kw.get("package")) or package,
                    executable=_const(kw.get("executable")) or "",
                    name=_const(kw.get("name")),
                    remappings=remaps,
                    param_files=[f for f in yaml_files if f.exists()],
                )
            )
        return launched

    # -------------------------------------------------------- node extraction
    def _extract_launched(
        self, launched: LaunchedNode, source: str = ""
    ) -> RosNode | None:
        key = f"{launched.package}/{launched.executable}"
        pkg = self.packages.get(launched.package)
        if pkg is None:
            self.warnings.append(f"{source}: package `{launched.package}` not found")
            return None

        override = self.config.get("node_overrides", {}).get(key)
        if override:
            return RosNode(
                name=override.get("name", launched.name or launched.executable),
                package=pkg.name,
                executable=launched.executable,
                repo=pkg.repo,
                note=override.get("note", ""),
                publishes=dict(override.get("publishes", {})),
                subscribes=dict(override.get("subscribes", {})),
            )

        source_file = self._find_executable(pkg, launched.executable)
        if source_file is None:
            self.warnings.append(
                f"{source or 'launch'}: executable `{launched.executable}` "
                f"not found in package `{pkg.name}`"
            )
            return None

        if source_file.suffix == ".py":
            iface = PythonNodeParser(source_file, self.state_enum).parse()
        else:
            iface = CppNodeParser(self._cpp_sources(pkg, launched.executable)).parse()
        if iface is None:
            self.warnings.append(f"`{key}`: no ROS node found in {source_file.name}")
            return None

        name = launched.name or iface.name or launched.executable
        params = self._load_params(name, launched.param_files, iface)
        node = RosNode(name=name, package=pkg.name, executable=launched.executable)
        node.repo = pkg.repo
        for topics, target in (
            (iface.publishes, node.publishes),
            (iface.subscribes, node.subscribes),
        ):
            for ref, msg_type in topics:
                topic = ref.resolve(params)
                if topic is None:
                    self.warnings.append(f"`{name}`: could not resolve topic {ref}")
                    continue
                topic = launched.remappings.get(topic, topic)
                target[topic] = msg_type
        for ref in iface.unused:
            self.warnings.append(
                f"`{name}`: publisher `{ref.param}` ({ref.resolve(params)}) is "
                "created but never used (not drawn)"
            )
        if iface.uses_param_client:
            node.controls = self._controlled_nodes(pkg)
        return node

    def _find_executable(self, pkg: Package, executable: str) -> Path | None:
        """Locate the source file that implements an executable."""
        setup = pkg.path / "setup.py"
        if setup.exists():
            for entry in _console_scripts(setup, pkg.name):
                exe, _, module = entry.partition("=")
                if exe.strip() == executable:
                    rel = module.split(":")[0].strip().replace(".", "/")
                    return pkg.path / f"{rel}.py"
        cmake = pkg.path / "CMakeLists.txt"
        if cmake.exists() and (
            re.search(
                rf"add_executable\(\s*{re.escape(executable)}\b", cmake.read_text()
            )
            or re.search(r"rclcpp_components_register_node", cmake.read_text())
        ):
            return cmake
        # Installed scripts (e.g. install(PROGRAMS scripts/node.py)), never sources
        if Path(executable).suffix in {".py", ""}:
            for candidate in pkg.path.rglob(executable):
                if ".git" not in candidate.parts and candidate.is_file():
                    return candidate
        return None

    def _cpp_sources(self, pkg: Package, executable: str) -> list[Path]:
        cmake = (pkg.path / "CMakeLists.txt").read_text()
        match = re.search(
            rf"add_executable\(\s*{re.escape(executable)}\s+([^)]*)\)", cmake
        )
        files = []
        if match:
            files = [pkg.path / f for f in match.group(1).split() if f.endswith(".cpp")]
        if not files:
            files = sorted((pkg.path / "src").rglob("*.cpp"))
        return [f for f in files if f.exists()]

    def _load_params(
        self, node_name: str, files: list[Path], iface: NodeInterface
    ) -> dict[str, Any]:
        """Merge the code defaults with the YAML parameter files of the launch."""
        params = dict(iface.defaults)
        sections_seen = []
        for path in files:
            data = yaml.safe_load(path.read_text()) or {}
            for section, content in data.items():
                values = (content or {}).get("ros__parameters", {})
                sections_seen.append(section)
                if section.lstrip("/") not in {node_name, "**"}:
                    continue
                if iface.declared is not None:
                    unknown = sorted(set(values) - iface.declared)
                    if unknown:
                        self.warnings.append(
                            f"`{node_name}`: {path.name} sets "
                            f"{', '.join(f'`{u}`' for u in unknown)}, "
                            "which the node does not declare (ignored)"
                        )
                params.update(values)
        if (
            files
            and sections_seen
            and not any(s.lstrip("/") in {node_name, "**"} for s in sections_seen)
        ):
            self.warnings.append(
                f"`{node_name}`: no section for this node name in "
                f"{', '.join(f.name for f in files)} "
                f"(found: {', '.join(sections_seen)}), code defaults are used"
            )
        return params

    # -------------------------------------------------- state machine control
    def _find_nodes_enum(self) -> dict[str, str]:
        """Find `class Nodes(Enum)` of smarty_utils (member -> node name)."""
        for pkg in self.packages.values():
            for path in pkg.path.rglob("enums.py"):
                tree = ast.parse(path.read_text())
                for cls in tree.body:
                    if isinstance(cls, ast.ClassDef) and cls.name == "Nodes":
                        return {
                            t.id: stmt.value.value
                            for stmt in cls.body
                            if isinstance(stmt, ast.Assign)
                            and isinstance(stmt.value, ast.Constant)
                            for t in stmt.targets
                            if isinstance(t, ast.Name)
                        }
        return {}

    def _controlled_nodes(self, pkg: Package) -> list[str]:
        """Nodes whose parameters are set via `Nodes.<MEMBER>` in the package."""
        members = set()
        for path in pkg.path.rglob("*.py"):
            if SKIP_DIRS.intersection(path.relative_to(pkg.path).parts):
                continue
            members.update(re.findall(r"\bNodes\.([A-Z_]+)\b", path.read_text()))
        return sorted(self.state_enum[m] for m in members if m in self.state_enum)


# ---------------------------------------------------------------- interfaces
@dataclass
class TopicRef:
    """A topic name that is either a literal or a node parameter."""

    literal: str | None = None
    param: str | None = None

    def resolve(self, params: dict[str, Any]) -> str | None:
        """Return the effective topic name."""
        if self.param is not None:
            value = params.get(self.param)
            return value if isinstance(value, str) else None
        return self.literal

    def __str__(self) -> str:
        """Describe the reference."""
        return f"param `{self.param}`" if self.param else repr(self.literal)


@dataclass
class NodeInterface:
    """Topics of a node as found in the source (before parameter resolution)."""

    name: str | None = None
    publishes: list[tuple[TopicRef, str]] = field(default_factory=list)
    subscribes: list[tuple[TopicRef, str]] = field(default_factory=list)
    defaults: dict[str, Any] = field(default_factory=dict)
    # Declared parameter names, None if unknown
    declared: set[str] | None = None
    uses_param_client: bool = False
    # SmartyNode publishers that are created but never used
    unused: list[TopicRef] = field(default_factory=list)


class PythonNodeParser:
    """Parses rclpy nodes, including `SmartyNode` subclasses."""

    def __init__(self, path: Path, state_enum: dict[str, str]):
        """Parse the module."""
        self.source = path.read_text()
        self.tree = ast.parse(self.source)
        self.state_enum = state_enum
        self.imports: dict[str, str] = {}
        self.constants: dict[str, ast.expr] = {}
        # self.<attr> -> (assigned value, function of the assignment)
        self._self_assigns: dict[str, tuple[ast.expr, ast.FunctionDef]] = {}
        self._declared_unknown = False
        for stmt in self.tree.body:
            if isinstance(stmt, ast.ImportFrom) and stmt.module:
                for alias in stmt.names:
                    self.imports[alias.asname or alias.name] = (
                        f"{stmt.module}.{alias.name}"
                    )
            elif isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        self.constants[target.id] = stmt.value

    def parse(self) -> NodeInterface | None:
        """Return the interface of the node class of the module."""
        cls = self._node_class()
        if cls is None:
            return None
        iface = NodeInterface(declared=set())
        iface.uses_param_client = "AsyncParameterClient" in self.source
        self._self_assigns = {
            target.attr: (stmt.value, func)
            for func in ast.walk(cls)
            if isinstance(func, ast.FunctionDef)
            for stmt in ast.walk(func)
            if isinstance(stmt, ast.Assign)
            for target in stmt.targets
            if isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "self"
        }

        for func in [f for f in ast.walk(cls) if isinstance(f, ast.FunctionDef)]:
            for call in [c for c in ast.walk(func) if isinstance(c, ast.Call)]:
                name = _call_name(call)
                if name == "__init__" and _is_super(call):
                    self._parse_super_init(call, func, iface)
                elif name == "declare_parameter" and call.args:
                    param = _const(call.args[0])
                    if param:
                        iface.declared.add(param)
                        if len(call.args) > 1:
                            iface.defaults.setdefault(param, _const(call.args[1]))
                elif name == "declare_parameters" and len(call.args) > 1:
                    for item in getattr(call.args[1], "elts", []):
                        if isinstance(item, ast.Tuple) and item.elts:
                            param = _const(item.elts[0])
                            if param:
                                iface.declared.add(param)
                                if len(item.elts) > 1:
                                    iface.defaults[param] = _const(item.elts[1])
                elif name in {"create_publisher", "create_subscription"}:
                    if len(call.args) < 2:  # noqa: PLR2004
                        continue
                    ref = self._resolve_topic(call.args[1], func)
                    msg_type = self._msg_type(call.args[0])
                    target = (
                        iface.publishes
                        if name == "create_publisher"
                        else iface.subscribes
                    )
                    if ref is not None:
                        target.append((ref, msg_type))
        if self._declared_unknown:
            iface.declared = None
        return iface

    def _node_class(self) -> ast.ClassDef | None:
        classes = [
            c
            for c in self.tree.body
            if isinstance(c, ast.ClassDef)
            and any("Node" in ast.unparse(b) for b in c.bases)
        ]
        if len(classes) > 1:
            used = {
                _call_name(c) for c in ast.walk(self.tree) if isinstance(c, ast.Call)
            }
            classes = [c for c in classes if c.name in used] or classes
        return classes[0] if classes else None

    def _parse_super_init(
        self, call: ast.Call, func: ast.FunctionDef, iface: NodeInterface
    ) -> None:
        kw = {k.arg: k.value for k in call.keywords}
        name_expr = call.args[0] if call.args else kw.get("node_name", kw.get("name"))
        iface.name = _const(self._deref(name_expr, func))
        node_params = kw.get("node_parameters")
        if not isinstance(node_params, ast.Dict):
            return
        # SmartyNode: topics are parameters declared in node_parameters
        iface.declared.update(SMARTY_NODE_PARAMS)
        # `**spread` entries hide parameter names: declared set is unknown
        self._declared_unknown = None in node_params.keys
        for key, value in zip(node_params.keys, node_params.values, strict=True):
            param = _const(key)
            if param:
                iface.declared.add(param)
                iface.defaults[param] = _const(self._deref(value, func))
        for kw_name, target in (
            ("published_topics", iface.publishes),
            ("subscribed_topics", iface.subscribes),
        ):
            topics = kw.get(kw_name)
            if not isinstance(topics, ast.Dict):
                continue
            for key, value in zip(topics.keys, topics.values, strict=True):
                param = _const(key)
                if not (param and isinstance(value, ast.Tuple) and value.elts):
                    continue
                if kw_name == "published_topics" and not self._is_used(param):
                    iface.unused.append(TopicRef(param=param))
                    continue
                target.append((TopicRef(param=param), self._msg_type(value.elts[0])))

    def _is_used(self, attr: str) -> bool:
        """Whether `self.<attr>` is accessed, also via getattr(self, f"...")."""
        if re.search(rf"self\.{attr}\b", self.source):
            return True
        for call in ast.walk(self.tree):
            if (
                isinstance(call, ast.Call)
                and _call_name(call) == "getattr"
                and len(call.args) > 1
                and isinstance(call.args[1], ast.JoinedStr)
            ):
                pattern = "".join(
                    ".+" if isinstance(v, ast.FormattedValue) else re.escape(v.value)
                    for v in call.args[1].values
                    if isinstance(v, ast.FormattedValue | ast.Constant)
                )
                if re.fullmatch(pattern, attr):
                    return True
        return False

    def _deref(self, expr: ast.expr | None, func: ast.FunctionDef) -> ast.expr | None:
        """Follow local variables and module constants to their value."""
        for _ in range(5):
            if not isinstance(expr, ast.Name):
                return expr
            local = [
                s.value
                for s in ast.walk(func)
                if isinstance(s, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == expr.id for t in s.targets)
            ]
            if local:
                expr = local[-1]
            elif expr.id in self.constants:
                expr = self.constants[expr.id]
            else:
                return expr
        return expr

    def _resolve_topic(self, expr: ast.expr, func: ast.FunctionDef) -> TopicRef | None:
        for _ in range(5):
            expr = self._deref(expr, func)
            literal = _const(expr)
            if literal is not None:
                return TopicRef(literal=literal)
            # Value of a declare_parameter(...) or get_parameter(...) call
            if (
                isinstance(expr, ast.Attribute)
                and expr.attr == "value"
                and isinstance(expr.value, ast.Call)
                and _call_name(expr.value) in {"declare_parameter", "get_parameter"}
                and expr.value.args
            ):
                return TopicRef(param=_const(expr.value.args[0]))
            # self.<attr> assigned somewhere in the class
            if (
                isinstance(expr, ast.Attribute)
                and isinstance(expr.value, ast.Name)
                and expr.value.id == "self"
                and expr.attr in self._self_assigns
            ):
                expr, func = self._self_assigns[expr.attr]
                continue
            return None
        return None

    def _msg_type(self, expr: ast.expr) -> str:
        dotted = ast.unparse(expr)
        head, _, rest = dotted.partition(".")
        if head in self.imports:
            dotted = self.imports[head] + (f".{rest}" if rest else "")
        return normalize_type(dotted)


class CppNodeParser:
    """Parses rclcpp nodes with regular expressions."""

    TOPIC_CALL = re.compile(
        r"(create_publisher|create_subscription)\s*<\s*([\w:]+)\s*>\s*\(\s*([^,]+?)\s*,",
        re.DOTALL,
    )
    IMAGE_TRANSPORT = re.compile(
        r"image_transport::create_(?:camera_)?publisher\s*\(\s*[^,]+,\s*([^,]+?)\s*,",
        re.DOTALL,
    )

    def __init__(self, files: list[Path]):
        """Read and strip comments of the sources."""
        source = "\n".join(f.read_text(errors="ignore") for f in files)
        source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
        self.source = re.sub(r"//[^\n]*", "", source)

    def parse(self) -> NodeInterface | None:
        """Return the interface of the node."""
        iface = NodeInterface()
        defaults = dict(
            re.findall(
                r"declare_parameter(?:<[^>]*>)?\(\s*\"(\w+)\"\s*,\s*\"([^\"]*)\"",
                self.source,
            )
        )
        iface.defaults = defaults
        variables = dict(
            re.findall(
                r"(\w+)\s*=\s*(?:this->)?get_parameter\(\s*\"(\w+)\"\s*\)", self.source
            )
        )

        def ref(arg: str) -> TopicRef:
            arg = arg.strip()
            if arg.startswith('"'):
                return TopicRef(literal=arg.strip('"'))
            return TopicRef(param=variables.get(arg, arg))

        for kind, msg_type, arg in self.TOPIC_CALL.findall(self.source):
            target = iface.publishes if kind == "create_publisher" else iface.subscribes
            target.append((ref(arg), normalize_type(msg_type)))
        for arg in self.IMAGE_TRANSPORT.findall(self.source):
            iface.publishes.append((ref(arg), "sensor_msgs/Image"))
        if not iface.publishes and not iface.subscribes:
            return None
        match = re.search(r"(?:Node|base)\s*[({]\s*\"(\w+)\"", self.source)
        iface.name = match.group(1) if match else None
        return iface


# ------------------------------------------------------------------- helpers
def normalize_type(name: str) -> str:
    """Turn `pkg.msg.Type`, `pkg::msg::Type` and `pkg/msg/Type` into `pkg/Type`."""
    parts = [p for p in re.split(r"\.|::|/", name) if p]
    if "msg" in parts:
        idx = parts.index("msg")
        if 0 < idx < len(parts) - 1:
            return f"{parts[idx - 1]}/{parts[-1]}"
    return name


def _console_scripts(setup: Path, package: str) -> list[str]:
    """Return the console_scripts entries of a setup.py (f-strings resolved)."""
    tree = ast.parse(setup.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values, strict=True):
            if _const(key) == "console_scripts" and isinstance(value, ast.List):
                return [_render_str(e, {"package_name": package}) for e in value.elts]
    return []


def _render_str(expr: ast.expr, names: dict[str, str]) -> str:
    """Evaluate a string constant or simple f-string."""
    if isinstance(expr, ast.JoinedStr):
        return "".join(
            _render_str(v.value, names)
            if isinstance(v, ast.FormattedValue)
            else _render_str(v, names)
            for v in expr.values
        )
    if isinstance(expr, ast.Name):
        return names.get(expr.id, "")
    return _const(expr) or ""


def _const(expr: ast.expr | None) -> str | None:
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return expr.value
    return None


def _call_name(call: ast.Call) -> str:
    func = call.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def _is_super(call: ast.Call) -> bool:
    return (
        isinstance(call.func, ast.Attribute)
        and isinstance(call.func.value, ast.Call)
        and _call_name(call.func.value) == "super"
    )
