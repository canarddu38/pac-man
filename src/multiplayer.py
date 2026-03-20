"""Multiplayer networking helpers for Pac-Man.

This module implements the ``MultiPlayerPacMan`` class which manages UDP
networking for hosting or joining multiplayer games. It provides a simple
non-blocking message loop, client tracking (on the host), and periodic
state synchronization between peers.

All public methods and the main class use Google-style docstrings.
"""

import socket
import json
from typing import Any

from config import Level, ParserException
from enums import LevelEnding


class MultiPlayerPacMan:
    """Manage multiplayer networking and shared game state over UDP.

    This class encapsulates the UDP socket, client tracking (when acting
    as host), and periodic state synchronization between host and clients.

    Attributes:
        manager: Graphics manager that owns scenes/config.
        is_host: True when this instance is the server/host.
        server_addr: Address of the host when acting as client.
        connected: Whether the client successfully connected to the host.
        connection_failed: Whether a connection attempt failed or timed out.
    """

    def __init__(self, manager: Any, is_host: bool,
                 level: Level | None, ip: str = "127.0.0.1") -> None:
        """Create networking socket and initialize multiplayer state.

        Args:
            manager: The Graphics manager instance that owns the game.
            is_host: If True, this instance will bind a server socket.
            level: The level to host (only meaningful when is_host=True).
            ip: Host IP to connect to when acting as a client.
        """
        self.is_host = is_host
        self.config = manager.config
        self.manager = manager
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self.clients: set[tuple[str, int]] = set()
        self.server_addr: tuple[str, int] | None = ((ip, 6240)
                                                    if not is_host else None)
        self.level = level if is_host else None
        self.connected = False
        self.connection_failed = False
        self.other_players: dict[str, dict[str, Any]] = {}
        self.ghost_states: list[dict[str, Any]] = []
        self.last_seen: dict[tuple[str, int], float] = {}
        self.disconnect_timeout = 5.0
        self.game_started = False

        if is_host:
            try:
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.sock.bind(("0.0.0.0", 6240))
            except OSError:
                raise ParserException("Address is already in use")
        else:
            self.sock.bind(("0.0.0.0", 0))
            import time as _time
            self._join_time = _time.time()
            self.send_to_server({"type": "join",
                                 "state": self.config.name})

    def send_to_server(self, packet: dict[str, Any]) -> None:
        """Send a JSON-serializable packet to the configured server address.

        Args:
            packet: Dictionary payload that will be JSON-encoded and sent to
                the server address (if set).
        """
        if self.server_addr:
            try:
                self.sock.sendto(json.dumps(packet).encode("utf-8"),
                                 self.server_addr)
            except Exception:
                pass

    def send_to_clients(self, packet: dict[str, Any],
                        client_address: tuple[str, int] | None = None) -> None:
        """Send a JSON-serializable packet to one or all connected clients.

        If a `client_address` is provided the packet will be sent directly to
        that address. Otherwise the payload is broadcast to all addresses in
        the `self.clients` set.

        Args:
            packet: The payload to send.
            client_address: Optional (host, port) tuple to target a single
                client directly.
        """
        data = json.dumps(packet).encode("utf-8")
        if client_address:
            try:
                self.sock.sendto(data, client_address)
            except Exception:
                pass
        else:
            for client in self.clients:
                try:
                    self.sock.sendto(data, client)
                except Exception:
                    pass

    def start_game(self) -> None:
        """Notify connected clients to start the game.

        Only valid on the host. Builds an initialization packet containing
        level metadata and broadcasts it to all clients.
        """
        if not self.is_host:
            return
        self.send_to_clients(
            {
                "type": "init",
                "seed": self.config.get("seed"),
                "level_name": self.level.name if self.level else "level0",
                "level_size": ((self.level.width, self.level.height)
                               if self.level else (10, 10)),
            }
        )
        self.game_started = True

    def update_network(self) -> None:
        """Process incoming/outgoing network activity.

        This method should be called frequently from the main loop. It:
        - Sends periodic pings/state when appropriate.
        - Receives and processes incoming UDP packets.
        - Handles join/leave/timeouts and sets `connection_failed` when a
          connection attempt times out on a client.

        Notes:
            This is a non-blocking loop: it relies on the socket being
            non-blocking and handles ``BlockingIOError`` to break out when no
            more data is available.
        """
        import time

        if getattr(self, "connection_failed", False):
            return

        current_time = time.time()

        if (
            not self.is_host
            and not self.connected
            and not self.connection_failed
            and hasattr(self, "_join_time")
            and current_time - getattr(self, "_join_time", 0)
            > self.disconnect_timeout
        ):
            print("connection timeout")
            self.connection_failed = True
            try:
                self.sock.close()
            except Exception:
                pass
            return

        if not self.game_started:
            if (
                not hasattr(self, "_last_ping")
                or current_time - getattr(self, "_last_ping", 0) > 1.0
            ):
                if self.is_host or self.connected:
                    self.send_state(None, True)
                self._last_ping = current_time

        if self.is_host:
            to_remove = []
            for client in list(self.clients):
                if (
                    current_time - self.last_seen.get(client, current_time)
                    > self.disconnect_timeout
                ):
                    print("client disconnected")
                    to_remove.append(client)
            for client in to_remove:
                self.clients.remove(client)
                if client in self.last_seen:
                    del self.last_seen[client]
                client_str = str(client)
                if client_str in self.other_players:
                    del self.other_players[client_str]
        else:
            if self.connected and self.server_addr and self.level:
                if (
                    current_time - self.last_seen.get(
                        self.server_addr, current_time
                    )
                    > self.disconnect_timeout
                ):
                    print("host disconnected")
                    self.manager.go_back()
                    self.connected = False

        while True:
            try:
                data, addr = self.sock.recvfrom(4096)
                if not data:  # server closed connection
                    print("Server disconnected")
                    break

                self.last_seen[addr] = current_time

                packet = json.loads(data.decode("utf-8"))

                if packet.get("type") not in ["player_state", "state"]:
                    print(
                        f"{'host' if self.is_host else 'client'} recieved:",
                        packet,
                    )

                if self.is_host:
                    if packet.get("type") == "join":
                        if not self.connected:
                            name_list = []
                            for v in self.other_players.values():
                                if "name" in v:
                                    name_list.append(v["name"])
                            name_list.append(self.config.name)

                            new_name = packet.get("state")
                            if new_name in name_list:
                                self.send_to_clients(
                                    {
                                        "type": "connection",
                                        "state": False
                                    },
                                    addr)
                            else:
                                self.clients.add(addr)
                                self.other_players[str(addr)] = \
                                    {"name": new_name}
                                print(
                                    f"{':'.join([str(x) for x in list(addr)])}\
 joined the server!"
                                )
                                self.send_to_clients(
                                    {
                                        "type": "connection",
                                        "state": not self.connected
                                    },
                                    addr
                                )
                        if not self.connected:
                            self.send_state(None, True)
                    elif packet.get("type") == "player_state":
                        self.other_players[str(addr)] = packet.get("state")
                else:
                    if packet.get("type") == "connection":
                        if packet.get("state") is True:
                            self.connected = True
                            self.connection_failed = False
                        else:
                            self.connected = False
                            self.connection_failed = True
                            print("connection failed!")
                            self.sock.close()
                            break
                    if packet.get("type") == "init":
                        self.config.data["seed"] = packet.get("seed")
                        self.level = Level(
                            id=-1,
                            name=packet.get("level_name"),
                            width=packet.get("level_size")[0],
                            height=packet.get("level_size")[1],
                        )
                    elif packet.get("type") == "state":
                        self.ghost_states = packet.get("ghosts", [])
                        self.other_players = packet.get("players", {})
                        if "time" in packet:
                            self.time = packet["time"]
                    elif packet.get("type") == "event":
                        from scenes import DeathScreenScene

                        match (packet.get("data")):
                            case "Ending.SUCCESS":
                                self.manager.change_scene(
                                    DeathScreenScene(
                                        self.manager,
                                        LevelEnding.SUCCESS,
                                        getattr(self.manager.current_scene,
                                                "pacman"),
                                        False,
                                        True,
                                    )
                                )
                            case "Ending.FAILURE":
                                self.manager.change_scene(
                                    DeathScreenScene(
                                        self.manager,
                                        LevelEnding.FAILURE,
                                        getattr(self.manager.current_scene,
                                                "pacman"),
                                        False,
                                        True,
                                    )
                                )
                            case "Ending.NO_TIME":
                                self.manager.change_scene(
                                    DeathScreenScene(
                                        self.manager,
                                        LevelEnding.NO_TIME,
                                        getattr(self.manager.current_scene,
                                                "pacman"),
                                        False,
                                        True,
                                    )
                                )
                            case _ as key:
                                print("unknown key:", key)
            except BlockingIOError:
                break
            except ConnectionResetError:
                print("disconnected: connection reset")
                break
            except TimeoutError:
                self.connected = False
                self.connection_failed = True
                self.sock.close()
                break
            except Exception as e:
                print(e)
                break

    def send_state(self, scene: Any, waiting: bool = False) -> None:
        """Transmit the current player/ghost state to peers.

        When acting as a host the method will build a full state packet
        including ghost positions and the list of connected players and
        broadcast it to all clients. When acting as a client it will send
        this client's player state to the host.

        Args:
            scene: The active GameScene instance (or None when waiting).
            waiting: If True, send a "spectator" placeholder state instead
                of a real player state.
        """
        if waiting:
            my_state = {
                "spectator_mode": True,
                "pos": (-1, -1),
                "dir": 0,
                "active": False,
                "health": 0,
                "score": 0,
                "name": self.config.name,
                "death_frame": 0,
                "edible_time": 0,
            }
        else:
            pacman = scene.pacman
            my_state = {
                "spectator_mode": pacman.spectator_mode,
                "pos": pacman.pos,
                "dir": pacman.direction.value if pacman.direction else 0,
                "active": pacman.is_active,
                "health": pacman.health,
                "score": pacman.score,
                "name": pacman.name,
                "death_frame": pacman.death_anim_frame,
                "edible_time": getattr(pacman, "last_edible_mode", 0),
            }
        if self.is_host:
            if not waiting and self.game_started:
                if my_state.get("spectator_mode", False) and all(
                    p.get("spectator_mode", False)
                    for p in self.other_players.values()
                ):
                    from scenes import DeathScreenScene

                    self.send_to_clients({"type": "event",
                                          "data": "Ending.FAILURE"})
                    self.manager.change_scene(
                        DeathScreenScene(
                            self.manager,
                            LevelEnding.FAILURE,
                            getattr(self.manager.current_scene, "pacman"),
                            False,
                            True,
                        )
                    )
                    self.game_started = False
                    return

            ghosts = []
            if not waiting:
                ghosts = [
                    {
                        "pos": g.pos,
                        "dir": g.direction.value if g.direction else 0,
                        "active": g.is_active,
                        "edible": g.ghost_is_edible_mode,
                    }
                    for g in scene.ghosts
                ]
            out: dict[str, Any] = {
                "type": "state",
                "ghosts": ghosts,
                "players": {k: v for k, v in self.other_players.items()},
            }
            if scene is not None and hasattr(scene, "remaining_time"):
                out["time"] = scene.remaining_time
            out["players"]["host"] = my_state
            self.send_to_clients(out)
        else:
            if self.connected:
                self.send_to_server({"type": "player_state",
                                     "state": my_state})
