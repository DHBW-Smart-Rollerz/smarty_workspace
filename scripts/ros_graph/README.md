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

Authentication uses the GitHub App `smarty-ros-graph` of the organization
(repository permission *Contents: Read and write*, installed on all repositories
in `config.yaml` plus `.dotfiles` and `smarty_workspace`). Each run creates a
short-lived installation token with `actions/create-github-app-token`.

1. Organization variable `ROS_GRAPH_APP_ID`: the App ID.
2. Organization secret `ROS_GRAPH_APP_KEY`: the content of the App's private key
   (`.pem`).
3. Give `smarty_workspace` and every repository with the trigger workflow access to
   both (repository access of the variable and the secret).
4. Copy `trigger-ros-graph.yaml` to `.github/workflows/` of every repository in
   `config.yaml` (optional, the nightly run covers the rest).

If the private key leaks, revoke it in the App settings and generate a new one.

### Adding a repository

Add it to `repos` in `config.yaml`. If it is not started by the launch scripts yet,
add its launch file to `in_development`. Add its package to a layer.
