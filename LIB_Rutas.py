import numpy, pandas
from matplotlib import pyplot
from pathlib import Path

# Types of route: zig zag, bishop (diagonal) and spiral
ROUTES = ("ZZ", "A", "S")

def StatesMatrix(M, N):
    # Matrix of finite states: S[n, m] = 1 if the agent can go from the cell n to the cell m (8 neighbors)
    A = numpy.ones((M, N));
    S = numpy.zeros((A.size, A.size))
    for m in range(A.shape[0]):
        for n in range(A.shape[1]):
            for x in [-1, 0, 1]:
                for y in [-1, 0 ,1]:
                    if x == 0 and y == 0:
                        continue
                    try:
                        A[m + x, n + y];
                        S[numpy.ravel_multi_index([m, n], A.shape), numpy.ravel_multi_index([m+x, n +y], A.shape)] = 1
                    except:
                        continue
    return S

def DistancesMatrix(M, N, S):
    D = numpy.zeros((M * N, M * N));

    d_base = 0.3; # 30 centimetros de un azulejo

    for n in range(S.shape[0]):
        for m in range(S.shape[1]):
            if n == m:
                continue
            i, j = numpy.unravel_index(n, (M, N)); # convertir el indice lineal en un indice de 2d
            k, l = numpy.unravel_index(m, (M, N))
            D[n,m] = d_base * numpy.linalg.norm( numpy.asarray( [i-k , j -l]) );
    return D

def ProbabilityMatrix(S):
    P = S.copy();

    for i in range(S.shape[0]):
        s_ = numpy.sum( S[i,:]  ); # integral
        P[i, :] /= s_ # porque es una distribucion uniforme
    return P

def ZigZagRoute(M, N):
    B = numpy.zeros((M,N), dtype = numpy.int32);

    for i in range(M):
        for j in range(N):
            B[i,j] = numpy.ravel_multi_index([i, j], B.shape);

    # Ciclo del zig zag
    for i in range(M):
        if i % 2 == 0: continue
        B[i,:] = numpy.flip(B[i,:]) ;

    return B.flatten()

def BishopRoute(M, N):
    r_2 = [];

    for i in range(min(M, N)):
        r_2.append(int( numpy.ravel_multi_index([i, i], (M, N)) ))

    return numpy.asarray(r_2, dtype = numpy.int32)

def SpiralRoute(M, N):
    B = numpy.zeros((M,N), dtype = numpy.int32);

    for i in range(M):
        for j in range(N):
            B[i,j] = numpy.ravel_multi_index([i, j], B.shape);

    # Ciclo de espiral
    Path = [];

    while B.size > 0:
        Path.append( B[0,:] )
        B = numpy.delete(B, 0, axis = 0);
        if B.size == 0: break
        Path.append( B[:, -1] )
        B = numpy.delete(B, -1, axis = 1);
        if B.size == 0: break
        Path.append( numpy.flip( B[-1,:] ) )
        B = numpy.delete(B, -1, axis = 0);
        if B.size == 0: break
        Path.append( numpy.flip( B[:, 0] ) )   # goes up, to continue from the last cell
        B = numpy.delete(B, 0, axis = 1);

    return numpy.concatenate( Path ).astype(numpy.int32)

def CheckRoute(S, P, route):
    # A route is valid if every step goes to a neighbor (S). A repeated node is a stop of the agent (it is not a step).
    # Its probability is -log of the product of the probabilities of the steps (P)
    Valida = True

    for i in range(len(route)-1):
        if route[i] != route[i+1] and S[route[i], route[i+1] ] == 0:
            Valida = False
            break

    p_ = None

    if Valida and len(route) > 1:
        #p_ = 1; # opcion 1 acumulando
        p_ = []; # opcion 2 guardar todas la probabilidad de la ruta

        for i in range(len(route)-1):
            if route[i] != route[i+1]:
                p_.append( P[ route[i] , route[i+1] ])

        p_ = - numpy.log( numpy.prod( numpy.asarray(p_) ))

    return Valida, p_

def Collisions(r_a, r_b, N):
    # Steps where two agents collide: same cell at the same time, or the same edge (or corner) crossed at the same time.
    # An agent that finished its route stays in its last cell.
    n = max(len(r_a), len(r_b))
    a = list(r_a) + [r_a[-1]] * (n - len(r_a))
    b = list(r_b) + [r_b[-1]] * (n - len(r_b))

    steps = [];

    for t in range(n):
        if a[t] == b[t]:
            steps.append(t)
            continue
        if t < n - 1:
            ma = numpy.asarray([a[t] // N + a[t+1] // N, a[t] % N + a[t+1] % N]) # middle point of the move of a
            mb = numpy.asarray([b[t] // N + b[t+1] // N, b[t] % N + b[t+1] % N]) # middle point of the move of b
            if numpy.all(ma == mb):
                steps.append(t)

    return steps

def SecondRoute(r_1, M, N):
    # Route of the second agent: the route of the first one turned (rotated 180 degrees or mirrored), waiting at the start if it is necessary
    for turn in ["rot", "mh", "mv"]:
        r_2 = [];
        for k in r_1:
            i, j = numpy.unravel_index(k, (M, N));
            if turn == "rot":
                i, j = M - 1 - i, N - 1 - j
            elif turn == "mh":
                j = N - 1 - j
            else:
                i = M - 1 - i
            r_2.append(int( numpy.ravel_multi_index([i, j], (M, N)) ))

        for wait in range(len(r_1) + 5):
            r_w = [r_2[0]] * wait + r_2 # a repeated node is a stop of the agent
            if len(Collisions(r_1, r_w, N)) == 0:
                return numpy.asarray(r_w, dtype = numpy.int32)

    return None

def QuadrantRoutes(M, N):
    # 4 agents: the room is divided in 4 parts and each agent works only in its own part, with a different pattern
    m = M // 2;
    n = N // 2;

    zz = ZigZagRoute(m, n)    # zig zag by rows
    zc = ZigZagRoute(n, m)    # zig zag by columns (the zig zag of a room with the rows and the columns changed)
    sp = SpiralRoute(m, n)    # spiral: starts in a corner and finishes in the center

    # (first row, first column, route of the part, how it is read)
    parts = [(0, 0, zz, "rows"), (0, n, sp, "rows"), (m, 0, zc, "columns"), (m, n, sp[::-1], "rows")]

    routes = [];

    for oi, oj, local, how in parts:
        r = [];
        for k in local:
            if how == "rows":
                i, j = numpy.unravel_index(k, (m, n))
            else:
                j, i = numpy.unravel_index(k, (n, m))
            r.append(int( numpy.ravel_multi_index([oi + i, oj + j], (M, N)) ))
        routes.append(numpy.asarray(r, dtype = numpy.int32))

    return routes

def Routes2Web(Options):

    if Options.Type not in ROUTES:
        print("Unknown type of route: " + Options.Type + ". Use one of: " + ", ".join(ROUTES))
        return

    if Options.Agents not in (1, 2, 4):
        print("The number of agents must be 1, 2 or 4")
        return

    M = Options.M;
    N = Options.N;

    if Options.Agents == 4 and (M % 2 != 0 or N % 2 != 0):
        print("For 4 agents the room needs an even number of rows and columns")
        return

    S = StatesMatrix(M, N)
    D = DistancesMatrix(M, N, S)
    P = ProbabilityMatrix(S)

    print(f"Neighbors of the node 9: {numpy.where(S[9,:] != 0)[0]}")
    print(f"Sum of the diagonal of D: {numpy.sum( numpy.diag(D) )}")

    # Matrices of the room
    fig, ax = pyplot.subplots(1, 3, figsize=(15, 5))
    ax[0].matshow(S)
    ax[0].set_title("States (S)")
    ax[1].matshow(D)
    ax[1].set_title("Distances (D)")
    ax[2].matshow(P)
    ax[2].set_title("Probability (P)")
    fig.tight_layout()
    pyplot.savefig(Options.File)
    pyplot.close(fig)
    print(f"Plot saved as: {Options.File}")

    # Routes of the agents
    if Options.Agents == 4:
        routes = QuadrantRoutes(M, N)    # zig zag, spiral, zig zag by columns and inverse spiral (the Type is not used)
    else:
        if Options.Type == "ZZ":
            r_1 = ZigZagRoute(M, N)
        elif Options.Type == "A":
            r_1 = BishopRoute(M, N)
        else:
            r_1 = SpiralRoute(M, N)

        routes = [r_1];

        # Agent 2: its route does not collide with the route of the agent 1
        if Options.Agents == 2:
            r_2 = SecondRoute(r_1, M, N)

            if r_2 is None:
                print("No route without collisions was found for the agent 2")
                return

            routes.append(r_2)

    for i, r in enumerate(routes):
        Valida, p_ = CheckRoute(S, P, r)

        print(f"Route of the agent {i + 1}: {r.tolist()}")
        print(f"Valid route: {Valida}")

        if p_ is not None:
            print(f"Probability of the route: {p_}")

    # Collisions between every pair of agents
    total = 0;

    for i in range(len(routes)):
        for j in range(i + 1, len(routes)):
            total += len(Collisions(routes[i], routes[j], N))

    print(f"Collisions between the agents: {total}")

    # Heat map 1: how many times the agents were in each cell
    H = numpy.zeros(M * N);

    for r in routes:
        for k in r:
            H[k] += 1

    # Heat map 2: random walk with the matrix P, starting where the agents start
    x_k = numpy.zeros(M * N);

    for r in routes:
        x_k[r[0]] += 1

    H_P = x_k.copy();

    for k in range(M * N):
        x_k = x_k @ P
        H_P = H_P + x_k

    fig, ax = pyplot.subplots(1, 2, figsize=(12, 6))
    im = ax[0].imshow(H.reshape(M, N), cmap = "viridis", interpolation = "nearest", origin = "lower")
    fig.colorbar(im, ax = ax[0], label = "Visits")
    ax[0].set_title("Heat map of the routes")
    ax[0].set_xlabel("Column Index")
    ax[0].set_ylabel("Row Index")
    im = ax[1].imshow(H_P.reshape(M, N), cmap = "viridis", interpolation = "nearest", origin = "lower")
    fig.colorbar(im, ax = ax[1], label = "Expected visits")
    ax[1].set_title("Heat map of the random walk (P)")
    ax[1].set_xlabel("Column Index")
    ax[1].set_ylabel("Row Index")
    fig.tight_layout()
    pyplot.savefig(Options.Heat)
    pyplot.close(fig)
    print(f"Heat map saved as: {Options.Heat}")

    # Nodes.csv: one node for each cell of the room
    x, y = numpy.meshgrid(numpy.arange(0,N), numpy.arange(0,M));
    Points = numpy.concatenate( [x.flatten().reshape(-1,1), y.flatten().reshape(-1,1)], axis = 1 )
    Points = ["(%d,%d,0)"%(p[0], p[1])  for p in Points.tolist()];

    DF = pandas.DataFrame();

    DF = DF.assign(Node = numpy.arange(0, M * N));
    DF = DF.assign(Points = Points);
    DF = DF.assign(Dirt = 0);

    DF.to_csv(Path(Options.Folder) / "Nodes.csv", index = False)

    # Routes.csv: the nodes of the route of each agent, in order
    DF = pandas.DataFrame();

    for i, r in enumerate(routes):
        DF = pandas.concat( [DF, pandas.DataFrame( {"Agent": i + 1, "Node": r} )], ignore_index = True )

    DF.to_csv(Path(Options.Folder) / "Routes.csv", index = False)

    print(f"Files saved in: {Options.Folder}")