"""Pathfinding helpers used by ghosts and AI routines.

This module exposes a small A* implementation plus helpers used to build
neighbor functions and heuristics for the game grid.
"""

import heapq
from typing import Callable

from enums import Bit_position


def reconstruct_path(came_from: dict[tuple[int, int], tuple[int, int]],
                     current: tuple[int, int]) -> list[tuple[int, int]]:
    """Reconstruct the path from a mapping of predecessor nodes.

    Args:
        came_from: A map from a node to its predecessor on the discovered path.
        current: The goal node to start backtracking from.

    Returns:
        A list of nodes from the start to the goal inclusive.
    """
    total_path = [current]
    while current in came_from:
        current = came_from[current]
        total_path.insert(0, current)
    return total_path


def a_star(start: tuple[int, int], goal: tuple[int, int],
           h: Callable[[tuple[int, int]], int],
           neighbors: Callable[[tuple[int, int]], list[tuple[int, int]]],
           d: Callable[[tuple[int, int], tuple[int, int]],
                       int]) -> list[tuple[int, int]] | None:
    """Perform A* search from start to goal on a grid.

    Args:
        start: Starting node coordinate (x, y).
        goal: Goal node coordinate (x, y).
        h: Heuristic function returning estimated cost to goal for a node.
        neighbors: Function returning accessible neighbor nodes for a node.
        d: Distance function returning the cost between two adjacent nodes.

    Returns:
        The shortest path found as a list of coordinates, or ``None`` if no
        path could be found.
    """
    open_set: list[tuple[int, tuple[int, int]]] = []
    heapq.heappush(open_set, (h(start), start))

    came_from: dict[tuple[int, int], tuple[int, int]] = {}

    g_score: dict[tuple[int, int], int] = {}
    g_score[start] = 0

    f_score: dict[tuple[int, int], int] = {}
    f_score[start] = h(start)

    open_set_hash = {start}

    while open_set:
        current = heapq.heappop(open_set)[1]
        open_set_hash.remove(current)

        if current == goal:
            return reconstruct_path(came_from, current)

        for neighbor in neighbors(current):
            tentative_g_score = g_score[current] + d(current, neighbor)
            if (neighbor not in g_score
                    or tentative_g_score < g_score[neighbor]):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = tentative_g_score + h(neighbor)

                if neighbor not in open_set_hash:
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
                    open_set_hash.add(neighbor)

    return None


def make_neighbors(maze: list[list[int]]) -> Callable[[tuple[int, int]],
                                                      list[tuple[int, int]]]:
    rows = len(maze)
    cols = len(maze[0])

    def neighbors(node: tuple[int, int]) -> list[tuple[int, int]]:
        x, y = int(node[0]), int(node[1])
        cell = maze[y][x]
        result = []

        if not (cell & Bit_position.WEST.value) and x > 0:
            result.append((x - 1, y))
        if not (cell & Bit_position.SOUTH.value) and y < rows - 1:
            result.append((x, y + 1))
        if not (cell & Bit_position.EAST.value) and x < cols - 1:
            result.append((x + 1, y))
        if not (cell & Bit_position.NORTH.value) and y > 0:
            result.append((x, y - 1))
        return result

    return neighbors


def manhattan(goal: tuple[int, int]) -> Callable[[tuple[int, int]], int]:
    def h(node: tuple[int, int]) -> int:
        return abs(node[0] - goal[0]) + abs(node[1] - goal[1])

    return h


def compute_escape_goal(start: tuple[int, int], danger: tuple[int, int],
                        maze: list[list[int]],
                        radius: int = 10) -> tuple[int, int]:
    rows = len(maze)
    cols = len(maze[0])

    best_tile = start
    best_score = -1

    sx, sy = start
    dx, dy = danger

    for y in range(max(0, sy - radius), min(rows, sy + radius)):
        for x in range(max(0, sx - radius), min(cols, sx + radius)):
            cell = maze[y][x]
            if cell == 15:
                continue
            score = (x - dx) ** 2 + (y - dy) ** 2
            if score > best_score:
                best_score = score
                best_tile = (x, y)
    return best_tile


def distance(a: tuple[int, int], b: tuple[int, int]) -> int:
    return 1
