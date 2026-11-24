import numpy, mesa, csv
import imageio.v2 as imageio
from matplotlib import pyplot
from pathlib import Path

# Values of the cells of the room
CLEAN = 0
DIRTY = 1
OBSTACLE = 2

# Moves of the agent (row, column): right, down, left, up
MOVES = ((0, 1), (1, 0), (0, -1), (-1, 0))

# Types of path
PATHS = ("zigzag", "random", "local")

class CleanerAgent(mesa.Agent):
    def __init__(self, model, row, col, path):
        super().__init__(model)
        self.row = row
        self.col = col
        self.path = path
        self.battery = 100
        self.moves = 0
        self.cleaned = 0
        self.charges = 0             # steps spent charging in a station
        self.charging = False
        self.resume = None           # cell where the agent was before going to charge
        self.direction = 1           # zigzag: 1 = right, -1 = left
        self.vdirection = 1          # zigzag: 1 = down, -1 = up

        # Memory: the agent only knows its own station at the beginning
        self.stations = [(row, col)]
        self.visited = {(row, col)}
        self.trail = [(row, col)]    # cells where the agent has been, in order (for the web simulation)
        self.frontier = set()        # free cells seen but not visited yet

    def free(self, cell):
        # A cell is free if it is inside the room and it is not an obstacle
        r, c = cell
        if r < 0 or r >= self.model.rows or c < 0 or c >= self.model.cols:
            return False
        return self.model.grid[r, c] != OBSTACLE

    def look(self):
        # Perception: the own cell and the 4 cells around it
        cells = [(self.row, self.col)]
        for dr, dc in MOVES:
            cells.append((self.row + dr, self.col + dc))

        for cell in cells:
            if self.free(cell):
                if cell in self.model.stations and cell not in self.stations:
                    self.stations.append(cell)
                if cell not in self.visited:
                    self.frontier.add(cell)

    def go(self, cell):
        # Every action takes 1% of battery
        self.row, self.col = cell
        self.visited.add(cell)
        self.trail.append(cell)
        self.frontier.discard(cell)
        self.moves += 1
        self.battery -= 1
        self.look()

    def route(self, goals):
        # Breadth-first search over the cells the agent already knows: returns the cells to follow to reach a goal
        start = (self.row, self.col)
        queue = [start]
        before = {start: None}

        while len(queue) > 0:
            cell = queue.pop(0)
            if cell in goals:
                route = []
                while cell != start:
                    route.append(cell)
                    cell = before[cell]
                route.reverse()
                return route

            if cell not in self.visited:
                continue    # a goal cell that was only seen: it is not expanded

            for dr, dc in MOVES:
                nxt = (cell[0] + dr, cell[1] + dc)
                if nxt not in before and (nxt in self.visited or nxt in goals):
                    before[nxt] = cell
                    queue.append(nxt)

        return None

    def random_move(self):
        options = [(self.row + dr, self.col + dc) for dr, dc in MOVES if self.free((self.row + dr, self.col + dc))]
        if len(options) == 0:
            return None
        return options[int(numpy.random.rand() * len(options))]

    def zigzag(self):
        # Sweep the room row by row: along the row, and at the end of the row go one row down (or up) and turn around
        cell = (self.row, self.col + self.direction)
        if self.free(cell):
            return cell

        cell = (self.row + self.vdirection, self.col)
        if self.free(cell):
            self.direction = -self.direction
            return cell

        # Blocked: change the directions and try a random move
        self.vdirection = -self.vdirection
        self.direction = -self.direction
        return self.random_move()

    def local(self):
        # Local exploration: go to a free cell not visited yet, the closest one
        near = [(self.row + dr, self.col + dc) for dr, dc in MOVES if (self.row + dr, self.col + dc) in self.frontier]
        if len(near) > 0:
            return near[int(numpy.random.rand() * len(near))]

        route = self.route(self.frontier)
        if route is not None and len(route) > 0:
            return route[0]
        return None

    def step(self):
        # Returns True if the agent did something in this step (an action or charging)
        here = (self.row, self.col)
        self.look()

        # Subsumption layers, from the highest priority to the lowest one:
        # 1. Survive: go back to a known station when the battery is just enough to get there, and charge
        route = self.route(self.stations)
        if route is not None and self.battery <= len(route) + 2:
            self.charging = True

        if self.charging:
            if here in self.model.stations:
                self.battery = min(100, self.battery + 5)   # 5% each episode in the station
                self.charges += 1
                self.trail.append(here)                     # the agent stays in the station (web simulation)
                if self.battery >= 100:
                    self.charging = False
                return True

            if self.resume is None:
                self.resume = here
            self.go(route[0])
            return True

        # 2. After charging, go back to the cell where the agent stopped cleaning
        if self.resume is not None:
            if here == self.resume:
                self.resume = None
            else:
                self.go(self.route({self.resume})[0])
                return True

        # 3. Clean the cell where the agent is
        if self.model.grid[here] == DIRTY:
            self.model.grid[here] = CLEAN
            self.cleaned += 1
            self.battery -= 1
            return True

        # 4. Go to a dirty cell next to the agent
        for dr, dc in MOVES:
            cell = (self.row + dr, self.col + dc)
            if self.free(cell) and self.model.grid[cell] == DIRTY:
                self.go(cell)
                return True

        # 5. Follow the path: zigzag, random or local exploration
        if self.path == "zigzag":
            cell = self.zigzag()
        elif self.path == "random":
            cell = self.random_move()
        else:
            cell = self.local()

        if cell is not None:
            self.go(cell)
            return True

        # Nothing to do: no action, so no battery is used
        return False

class RoomModel(mesa.Model):
    # agents = 1  -> Simulation 1: the agent starts in [1,1] (cell 0,0), where there is a charging station
    # agents > 1  -> Simulation 2: the agents start in random cells, where there are charging stations
    def __init__(self, rows=20, cols=20, agents=1, dirty=30, obstacles=10, max_time=300, path="zigzag"):
        super().__init__()
        self.rows = rows
        self.cols = cols
        self.max_time = max_time
        self.grid = numpy.zeros((rows, cols), dtype=numpy.uint8)

        # Random order of all the cells of the room
        order = [int(i) for i in numpy.argsort(numpy.random.rand(rows * cols))]

        if agents == 1:
            starts = [0]
        else:
            starts = order[:agents]

        # Obstacles and dirty cells in random cells, but not in the starting cells
        rest = [i for i in order if i not in starts]
        n_obstacles = int(round(rows * cols * obstacles / 100))
        n_dirty = int(round(rows * cols * dirty / 100))

        for i in rest[:n_obstacles]:
            self.grid[numpy.unravel_index(i, self.grid.shape)] = OBSTACLE
        for i in rest[n_obstacles:n_obstacles + n_dirty]:
            self.grid[numpy.unravel_index(i, self.grid.shape)] = DIRTY

        self.stations = set()
        self.cleaners = []
        for i in starts:
            r, c = numpy.unravel_index(i, self.grid.shape)
            self.stations.add((int(r), int(c)))
            self.cleaners.append(CleanerAgent(self, int(r), int(c), path))

        self.step_count = 0
        self.time_clean = None       # step when all the cells were clean

    def clean_percent(self):
        free = numpy.sum(self.grid != OBSTACLE)
        dirty = numpy.sum(self.grid == DIRTY)
        return 100 * (free - dirty) / free

    def step(self):
        acted = False
        for cleaner in self.cleaners:
            if cleaner.step():
                acted = True

        self.step_count += 1

        if numpy.sum(self.grid == DIRTY) == 0:
            self.time_clean = self.step_count
            self.running = False
        elif self.step_count >= self.max_time or not acted:
            self.running = False

def room_image(model):
    image = numpy.ones((model.rows, model.cols, 3))
    image[model.grid == DIRTY] = [0.55, 0.35, 0.15]    # dirty: brown
    image[model.grid == OBSTACLE] = [0, 0, 0]          # obstacle: black

    for r, c in model.stations:
        image[r, c] = [0, 0.7, 0]                      # charging station: green
    for cleaner in model.cleaners:
        image[cleaner.row, cleaner.col] = [0, 0.4, 1]  # agent: blue

    return image

def Cleaning2GIFF(Options):

    if Options.Path not in PATHS:
        print("Unknown path: " + Options.Path + ". Use one of: " + ", ".join(PATHS))
        return

    model = RoomModel(rows = Options.M, cols = Options.N, agents = Options.Agents, dirty = Options.Dirty,
                      obstacles = Options.Obstacles, max_time = Options.MaxTime, path = Options.Path)
    frames = []

    # Initial frame plus one frame for each step.
    for _ in range(Options.MaxTime + 1):
        fig, ax = pyplot.subplots(figsize=(6, 6))
        ax.imshow(room_image(model), interpolation="nearest")
        ax.set_title(f"Cleaning Agents — {Options.Path} — Step {model.step_count} — Clean {model.clean_percent():.1f}%")
        ax.set_xlabel("Battery: " + " ".join(f"{cleaner.battery}%" for cleaner in model.cleaners))
        ax.set_ylabel("Row")
        ax.set_xticks(numpy.arange(0, Options.N, 5))
        ax.set_yticks(numpy.arange(0, Options.M, 5))
        fig.tight_layout()

        fig.canvas.draw()
        frame = numpy.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy()
        frames.append(frame)
        pyplot.close(fig)

        if model.running:
            model.step()
        else:
            break

    imageio.mimsave(Options.File, frames, duration = 1000 / Options.FPS, loop=0)  # duration in milliseconds
    print(f"GIF saved as: {Options.File}")

    # Information collected during the execution
    if model.time_clean is None:
        print(f"Time: {model.step_count} (not all the cells are clean)")
    else:
        print(f"Time until all the cells are clean: {model.time_clean}")
    print(f"Clean cells at the end: {model.clean_percent():.1f}%")
    for i, cleaner in enumerate(model.cleaners):
        print(f"Agent {i}: moves = {cleaner.moves}, cleaned cells = {cleaner.cleaned}, charging steps = {cleaner.charges}, battery = {cleaner.battery}%")
    print(f"Total moves: {sum(cleaner.moves for cleaner in model.cleaners)}")

def Cleaning2Stats(Options):

    if Options.Path not in PATHS:
        print("Unknown path: " + Options.Path + ". Use one of: " + ", ".join(PATHS))
        return

    agents = numpy.arange(1, Options.MaxAgents + 1)
    time = numpy.zeros(len(agents))
    moves = numpy.zeros(len(agents))
    clean = numpy.zeros(len(agents))

    for i, n in enumerate(agents):
        for _ in range(Options.Runs):
            model = RoomModel(rows = Options.M, cols = Options.N, agents = int(n), dirty = Options.Dirty,
                              obstacles = Options.Obstacles, max_time = Options.MaxTime, path = Options.Path)
            while model.running:
                model.step()

            time[i] += model.step_count / Options.Runs
            moves[i] += sum(cleaner.moves for cleaner in model.cleaners) / Options.Runs
            clean[i] += model.clean_percent() / Options.Runs

        print(f"Agents = {n}: time = {time[i]:.1f}, total moves = {moves[i]:.1f}, clean cells = {clean[i]:.1f}%")

    fig, ax = pyplot.subplots(1, 2, figsize=(10, 4))
    ax[0].plot(agents, time, marker="o")
    ax[0].set_title("Time")
    ax[0].set_xlabel("Agents")
    ax[0].set_ylabel("Steps")
    ax[0].grid(True)
    ax[1].plot(agents, moves, marker="o")
    ax[1].set_title("Total moves")
    ax[1].set_xlabel("Agents")
    ax[1].set_ylabel("Moves")
    ax[1].grid(True)
    fig.tight_layout()

    pyplot.savefig(Options.File)
    print(f"Plot saved as: {Options.File}")

def Cleaning2Web(Options):

    if Options.Path not in PATHS:
        print("Unknown path: " + Options.Path + ". Use one of: " + ", ".join(PATHS))
        return

    model = RoomModel(rows = Options.M, cols = Options.N, agents = Options.Agents, dirty = Options.Dirty,
                      obstacles = Options.Obstacles, max_time = Options.MaxTime, path = Options.Path)

    # Nodes.csv: one node for each free cell (the dirt is the initial state of the room)
    with open(Path(Options.Folder) / "Nodes.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Node", "Points", "Dirt"])
        for r in range(model.rows):
            for c in range(model.cols):
                if model.grid[r, c] != OBSTACLE:
                    writer.writerow([r * model.cols + c + 1, f"({c},{model.rows - 1 - r},0)", int(model.grid[r, c] == DIRTY)])

    while model.running:
        model.step()

    # Routes.csv: the cells that each agent visited, in order
    with open(Path(Options.Folder) / "Routes.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Agent", "Node"])
        for i, cleaner in enumerate(model.cleaners):
            for r, c in cleaner.trail:
                writer.writerow([i + 1, r * model.cols + c + 1])

    print(f"Files saved in: {Options.Folder}")
    print(f"Clean cells at the end: {model.clean_percent():.1f}%")
    for i, cleaner in enumerate(model.cleaners):
        print(f"Agent {i + 1}: moves = {cleaner.moves}, cleaned cells = {cleaner.cleaned}, charging steps = {cleaner.charges}, battery = {cleaner.battery}%")