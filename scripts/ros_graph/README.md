# ROS Graph

Generates the graph of all ROS nodes of the vehicle and the topics connecting
them, and publishes it to the
[ROS Topic Graph](https://github.com/DHBW-Smart-Rollerz/.dotfiles/wiki/ROS-Topic-Graph)
wiki page.

Nothing is built or launched. The topics are extracted from the source code:

- The nodes come from the `ros2 launch` / `ros2 run` / `ros2 topic pub` commands in
  `all.launch.sh` and `base.launch.sh`, plus the `in_development` launch files of
  `config.yaml`.
- Launch files give the node name, remappings and YAML parameter files.
- Python nodes (`SmartyNode` and plain rclpy) are parsed with `ast`, C++ nodes with
  regular expressions. Topic parameters are resolved like at runtime: code default,
  overwritten by the YAML parameters of the launch file.
- Nodes that cannot be parsed (e.g. Simulink generated code) are described in
  `node_overrides` of `config.yaml`.

The wiki page also lists dangling topics, nodes whose state the state machine sets
but that do not exist, and extraction warnings (e.g. YAML parameters the node does
not declare, or unknown executables in the launch scripts).

## Files

- `config.yaml`: Repositories and branches, layers, overrides
- `ros_graph.py`: Entry point (clone, extract, render)
- `extract.py`: Static extraction of nodes and topics
- `render.py`: Graphviz graph and wiki page
- `trigger-ros-graph.yaml`: Workflow template for the analyzed repositories

## Run locally

```bash
sudo apt install graphviz
GH_TOKEN=$(gh auth token) python3 scripts/ros_graph/ros_graph.py --clone \
  --repos-dir /tmp/ros_graph/repos --out /tmp/ros_graph/out
```

Without `--clone` the repositories already in `--repos-dir` are used as they are,
which is handy to check a feature branch before pushing.

## Automation

The [ROS Graph workflow](../../.github/workflows/ros-graph.yaml) regenerates the
graph and pushes it to the `.dotfiles` wiki. It runs

- on `repository_dispatch` (`ros-graph`), sent by `trigger-ros-graph.yaml` in the
  analyzed repositories after a push,
- when the launch scripts or this folder change on `jazzy`,
- nightly (covers repositories without the trigger and non-`jazzy` branches),
- manually (`workflow_dispatch`).

### Setup

1. Create the organization secret `ROS_GRAPH_TOKEN` and give the workflow repositories
   access to it. The token needs:
   - read access to the contents of all repositories in `config.yaml` (some are
     private),
   - write access to the contents of `.dotfiles` (the wiki),
   - write access to the contents of `smarty_workspace` (to send the
     `repository_dispatch`).

   A classic personal access token with the `repo` scope works. Use a bot or shared
   account, so the automation does not break when the owner leaves the team.
2. Copy `trigger-ros-graph.yaml` to `.github/workflows/` of every repository in
   `config.yaml` (optional, the nightly run covers the rest).

### Adding a repository

Add it to `repos` in `config.yaml`. If it is not started by the launch scripts yet,
add its launch file to `in_development`. Add its package to a layer.
