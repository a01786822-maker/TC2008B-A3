import LIB_Limpieza
import LIB_Rutas
import argparse
import datetime

def main():
	parser = argparse.ArgumentParser("TC2008B", description = "TC2008B parse");
	subparsers = parser.add_subparsers(dest = "cmd");

	subparser = subparsers.add_parser("Cleaning",  description = "Cleaning Agents");
	subparser.add_argument("--File", required = False, default = "out.gif", type = str, help = "Output file");
	subparser.add_argument("--M", required = False, default = 10, type = int, help = "Rows of the room");
	subparser.add_argument("--N", required = False, default = 10, type = int, help = "Columns of the room");
	subparser.add_argument("--Agents", required = False, default = 1, type = int, help = "Number of agents");
	subparser.add_argument("--Dirty", required = False, default = 30, type = float, help = "Percentage of dirty cells");
	subparser.add_argument("--Obstacles", required = False, default = 10, type = float, help = "Percentage of obstacle cells");
	subparser.add_argument("--MaxTime", required = False, default = 500, type = int, help = "Maximum execution time (steps)");
	subparser.add_argument("--Path", required = False, default = "zigzag", type = str, help = "Type of path: zigzag, random or local");
	subparser.add_argument("--FPS", required = False, default = 5, type = int, help = "Frames Per Second");
	subparser.set_defaults(func = LIB_Limpieza.Cleaning2GIFF);

	subparser = subparsers.add_parser("Stats",  description = "Statistics by number of agents");
	subparser.add_argument("--File", required = False, default = "stats.png", type = str, help = "Output file");
	subparser.add_argument("--M", required = False, default = 10, type = int, help = "Rows of the room");
	subparser.add_argument("--N", required = False, default = 10, type = int, help = "Columns of the room");
	subparser.add_argument("--MaxAgents", required = False, default = 5, type = int, help = "Maximum number of agents");
	subparser.add_argument("--Runs", required = False, default = 10, type = int, help = "Runs for each number of agents");
	subparser.add_argument("--Dirty", required = False, default = 30, type = float, help = "Percentage of dirty cells");
	subparser.add_argument("--Obstacles", required = False, default = 10, type = float, help = "Percentage of obstacle cells");
	subparser.add_argument("--MaxTime", required = False, default = 500, type = int, help = "Maximum execution time (steps)");
	subparser.add_argument("--Path", required = False, default = "zigzag", type = str, help = "Type of path: zigzag, random or local");
	subparser.set_defaults(func = LIB_Limpieza.Cleaning2Stats);

	subparser = subparsers.add_parser("Web",  description = "Nodes.csv and Routes.csv for the web simulation");
	subparser.add_argument("--Folder", required = False, default = ".", type = str, help = "Folder of the web project");
	subparser.add_argument("--M", required = False, default = 10, type = int, help = "Rows of the room");
	subparser.add_argument("--N", required = False, default = 10, type = int, help = "Columns of the room");
	subparser.add_argument("--Agents", required = False, default = 1, type = int, help = "Number of agents");
	subparser.add_argument("--Dirty", required = False, default = 30, type = float, help = "Percentage of dirty cells");
	subparser.add_argument("--Obstacles", required = False, default = 10, type = float, help = "Percentage of obstacle cells");
	subparser.add_argument("--MaxTime", required = False, default = 500, type = int, help = "Maximum execution time (steps)");
	subparser.add_argument("--Path", required = False, default = "zigzag", type = str, help = "Type of path: zigzag, random or local");
	subparser.set_defaults(func = LIB_Limpieza.Cleaning2Web);

	subparser = subparsers.add_parser("Routes",  description = "Matrices S, D, P, routes of 1, 2 or 4 agents without collisions and heat map: Nodes.csv and Routes.csv for the web simulation");
	subparser.add_argument("--File", required = False, default = "matrices.png", type = str, help = "Output file of the matrices");
	subparser.add_argument("--Heat", required = False, default = "heatmap.png", type = str, help = "Output file of the heat map");
	subparser.add_argument("--Folder", required = False, default = "web", type = str, help = "Folder of the web project");
	subparser.add_argument("--M", required = False, default = 8, type = int, help = "Rows of the room");
	subparser.add_argument("--N", required = False, default = 8, type = int, help = "Columns of the room");
	subparser.add_argument("--Agents", required = False, default = 1, type = int, help = "Number of agents (1, 2 or 4)");
	subparser.add_argument("--Type", required = False, default = "ZZ", type = str, help = "Type of route: ZZ (zig zag), A (bishop) or S (spiral)");
	subparser.set_defaults(func = LIB_Rutas.Routes2Web);

	Options = parser.parse_args();

	print(str(Options) + "\n");

	Options.func(Options);


if __name__ == "__main__":
	print("\n" + "\033[0;32m" + "[start] " + str(datetime.datetime.now()) + "\033[0m" + "\n");
	main();
	print("\n" + "\033[0;32m" + "[end] "+ str(datetime.datetime.now()) + "\033[0m" + "\n");