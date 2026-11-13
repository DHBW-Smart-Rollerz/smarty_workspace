"""Generate the ROS topic graph of the Smarty vehicle stack.

Usage:
    python3 scripts/ros_graph/ros_graph.py --clone --repos-dir /tmp/repos --out out/

With `--clone` the repositories of `config.yaml` are cloned into `--repos-dir`
(set GH_TOKEN to access private repositories). Without it, existing clones in
`--repos-dir` are used as they are.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from dataclasses import asdict
from pathlib import Path

import yaml
from extract import Extractor
from render import Graph, Source, to_dot, to_markdown

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parents[1]


def git(*args: str, cwd: Path | None = None) -> str:
    """Run git and return its output."""
    return subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def clone(org: str, repo: str, branch: str, target: Path, token: str | None) -> None:
    """Shallow clone (or update) a repository."""
    auth = f"x-access-token:{token}@" if token else ""
    url = f"https://{auth}github.com/{org}/{repo}.git"
    if target.exists():
        git("fetch", "--depth", "1", "origin", branch, cwd=target)
        git("checkout", "-q", "--force", "FETCH_HEAD", cwd=target)
    else:
        git("clone", "-q", "--depth", "1", "--branch", branch, url, str(target))


def is_archived(org: str, repo: str, token: str | None) -> bool:
    """Ask the GitHub API whether a repository is archived."""
    request = urllib.request.Request(
        f"https://api.github.com/repos/{org}/{repo}",
        headers={"Authorization": f"Bearer {token}"} if token else {},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
            return bool(json.load(response).get("archived"))
    except OSError:
        return False


def main() -> int:
    """Run the generator."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repos-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--clone", action="store_true", help="clone/update repos")
    parser.add_argument("--config", type=Path, default=SCRIPT_DIR / "config.yaml")
    parser.add_argument(
        "--image-dir",
        default="images/ros_graph",
        help="path of the images relative to the markdown page",
    )
    args = parser.parse_args()

    config = yaml.safe_load(args.config.read_text())
    org = config["org"]
    token = os.environ.get("GH_TOKEN")
    args.repos_dir.mkdir(parents=True, exist_ok=True)

    sources = {}
    for repo, spec in config["repos"].items():
        branch = (spec or {}).get("branch", "jazzy")
        target = args.repos_dir / repo
        if args.clone:
            print(f"Cloning {repo}@{branch}", file=sys.stderr)
            clone(org, repo, branch, target, token)
        commit = git("rev-parse", "HEAD", cwd=target) if target.exists() else ""
        sources[repo] = Source(repo, branch, commit, is_archived(org, repo, token))

    extractor = Extractor(args.repos_dir, WORKSPACE_DIR, config)
    nodes = extractor.extract()
    graph = Graph(nodes, config, sources)

    out = args.out
    image_out = out / args.image_dir
    image_out.mkdir(parents=True, exist_ok=True)
    dot_path = image_out / "smarty_ros_graph.dot"
    dot_path.write_text(to_dot(graph))
    for fmt, extra in (("svg", []), ("png", ["-Gdpi=130"])):
        subprocess.run(  # noqa: S603
            [  # noqa: S607
                "dot",
                f"-T{fmt}",
                *extra,
                str(dot_path),
                "-o",
                str(dot_path.with_suffix(f".{fmt}")),
            ],
            check=True,
        )
    (out / "ROS-Topic-Graph.md").write_text(
        to_markdown(graph, extractor.warnings, args.image_dir)
    )
    (image_out / "smarty_ros_graph.json").write_text(
        json.dumps([asdict(n) for n in nodes], indent=2) + "\n"
    )

    for warning in extractor.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    print(f"Wrote {out / 'ROS-Topic-Graph.md'} and {image_out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
