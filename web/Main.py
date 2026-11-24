import csv, ast, flask
from pathlib import Path
import LIB_Limpieza
import argparse
import datetime

app = flask.Flask(__name__)
BASE = Path(__file__).resolve().parent

def load_nodes():
    nodes = {}
    with open(BASE / "Nodes.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            point = tuple(float(v) for v in ast.literal_eval(row["Points"]))
            nodes[int(row["Node"])] = {
                "node": int(row["Node"]),
                "point": point,
                "dirt": int(row["Dirt"])
            }
    return nodes

def load_routes():
    routes = {}
    with open(BASE / "Routes.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            agent = int(row["Agent"])
            routes.setdefault(agent, []).append(int(row["Node"]))
    return routes

@app.route("/")
def index():
    return flask.render_template("index.html")

@app.route("/api/data")
def data():
    return flask.jsonify({"nodes": load_nodes(), "routes": load_routes()})

def main():
    parser = argparse.ArgumentParser("TC2008B", description = "TC2008B parse");
    subparsers = parser.add_subparsers(dest = "cmd");

    subparser = subparsers.add_parser("Web",  description = "Generate Nodes.csv and Routes.csv for the web simulation");
    subparser.add_argument("--Folder", required = False, default = str(BASE), type = str, help = "Folder of the web project");
    subparser.add_argument("--M", required = False, default = 10, type = int, help = "Rows of the room");
    subparser.add_argument("--N", required = False, default = 10, type = int, help = "Columns of the room");
    subparser.add_argument("--Agents", required = False, default = 1, type = int, help = "Number of agents");
    subparser.add_argument("--Dirty", required = False, default = 30, type = float, help = "Percentage of dirty cells");
    subparser.add_argument("--Obstacles", required = False, default = 10, type = float, help = "Percentage of obstacle cells");
    subparser.add_argument("--MaxTime", required = False, default = 500, type = int, help = "Maximum execution time (steps)");
    subparser.add_argument("--Path", required = False, default = "zigzag", type = str, help = "Type of path: zigzag, random or local");
    subparser.set_defaults(func = LIB_Limpieza.Cleaning2Web);

    Options = parser.parse_args();

    # Without a command, the web server starts
    if Options.cmd is None:
        app.run(debug = True);
        return;

    print(str(Options) + "\n");

    Options.func(Options);


if __name__ == "__main__":
    print("\n" + "\033[0;32m" + "[start] " + str(datetime.datetime.now()) + "\033[0m" + "\n");
    main();
    print("\n" + "\033[0;32m" + "[end] "+ str(datetime.datetime.now()) + "\033[0m" + "\n");