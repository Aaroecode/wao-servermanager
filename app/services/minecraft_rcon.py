# app/services/minecraft_rcon.py
import asyncio
import struct
import logging
import time
import os
from dataclasses import dataclass, field
from typing import Optional, Callable, Any, List

logger = logging.getLogger("minecraft_rcon")
logger.setLevel(logging.INFO)

@dataclass
class _QueuedCommand:
    command: str
    future: asyncio.Future
    retries_left: int
    timeout: float
    created_at: float = field(default_factory=time.time)

class AdvancedAsyncRCON:

    # RCON packet types
    _TYPE_AUTH = 3
    _TYPE_AUTH_RESPONSE = 2   # note: some docs label types differently; we use the common pattern
    _TYPE_COMMAND = 2
    _TYPE_RESPONSE = 0

    def __init__(
        self,
        host: str,
        port: int,
        password: str,
        *,
        reconnect_delay: float = 2.0,
        max_retries: int = 3,
        command_timeout: float = 8.0,
        response_assemble_timeout: float = 0.06,
        # rate limiting: tokens per interval
        rate_limit_tokens: int = 60,
        rate_limit_interval: float = 1.0,
        worker_count: int = 1,
    ):
        self.host = host
        self.port = port
        self.password = password
        self.reconnect_delay = reconnect_delay
        self.max_retries = max_retries
        self.command_timeout = command_timeout
        self.response_assemble_timeout = response_assemble_timeout

        # connection state
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        self._authed = False
        self._running = False

        # internal synchronization
        self._send_lock = asyncio.Lock()           # ensures single writer at a time
        self._queue: asyncio.Queue[_QueuedCommand] = asyncio.Queue()
        self._worker_tasks: List[asyncio.Task] = []

        # rate limiter (token bucket)
        self._rate_tokens = rate_limit_tokens
        self._rate_capacity = rate_limit_tokens
        self._rate_interval = rate_limit_interval
        self._last_rate_refill = time.monotonic()
        self._rate_lock = asyncio.Lock()

        # worker count
        self.worker_count = max(1, worker_count)

        # reconnect / lifecycle tasks
        self._connection_task: Optional[asyncio.Task] = None

        # event callbacks
        self.on_connect: Optional[Callable[[], Any]] = None
        self.on_disconnect: Optional[Callable[[], Any]] = None
        self.on_error: Optional[Callable[[Exception], Any]] = None
        self.on_response: Optional[Callable[[str, str], Any]] = None  # (command, response)

    # ----------------------
    # Public lifecycle API
    # ----------------------
    async def start(self):
        """Start the connection manager and workers."""
        if self._running:
            return
        self._running = True
        self._connection_task = asyncio.create_task(self._connection_loop())
        # workers handle commands sequentially; we keep worker_count but each worker still awaits lock before send
        for i in range(self.worker_count):
            t = asyncio.create_task(self._worker_loop(i))
            self._worker_tasks.append(t)
        logger.info("AdvancedAsyncRCON started")

    async def stop(self):
        """Stop workers and close connection."""
        self._running = False
        # cancel tasks
        if self._connection_task:
            self._connection_task.cancel()
        for t in self._worker_tasks:
            t.cancel()
        self._worker_tasks.clear()
        # close writer
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
        self._connected = False
        self._authed = False
        logger.info("AdvancedAsyncRCON stopped")

    # ----------------------
    # Public command API
    # ----------------------
    async def run(self, command: str, *, timeout: Optional[float] = None, retries: Optional[int] = None) -> str:
        """
        Run a single command. Returns the response text (may be empty string).
        This enqueues the command to the internal queue and returns when the command completes.
        """
        if timeout is None:
            timeout = self.command_timeout
        if retries is None:
            retries = self.max_retries
        
        
        fut = asyncio.get_running_loop().create_future()
        queued = _QueuedCommand(command=command, future=fut, retries_left=retries, timeout=timeout)
        await self._queue.put(queued)
        return await asyncio.wait_for(fut, timeout=(timeout + 10))  # total wait (command timeout + slack)

    async def run_batch(self, commands: List[str], *, timeout: Optional[float] = None, retries: Optional[int] = None) -> List[str]:
        """
        Enqueue many commands as a batch, returns list of results in same order.
        Implementation enqueues commands individually and waits for all futures.
        """
        if timeout is None:
            timeout = self.command_timeout
        if retries is None:
            retries = self.max_retries

        futures = []
        for cmd in commands:
            fut = asyncio.get_running_loop().create_future()
            queued = _QueuedCommand(command=cmd, future=fut, retries_left=retries, timeout=timeout)
            await self._queue.put(queued)
            futures.append(fut)

        # wait for all
        results = []
        for fut in futures:
            res = await asyncio.wait_for(fut, timeout=(timeout + 10))
            results.append(res)
        return results

    # ----------------------
    # internal helpers
    # ----------------------
    async def _connection_loop(self):
        """Maintain connection and authentication; reconnect on errors."""
        backoff = self.reconnect_delay
        while self._running:
            if not self._connected:
                try:
                    await self._connect()
                    await self._authenticate()
                    backoff = self.reconnect_delay
                    if callable(self.on_connect):
                        try:
                            self.on_connect()
                        except Exception as e:
                            logger.exception("on_connect callback failed: %s", e)
                    logger.info("RCON connected and authenticated")
                except Exception as exc:
                    self._connected = False
                    self._authed = False
                    if callable(self.on_error):
                        try:
                            self.on_error(exc)
                        except Exception:
                            logger.exception("on_error callback raised")
                    logger.exception("RCON connection/auth failed, retrying in %.1fs", backoff)
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 60.0)
            await asyncio.sleep(0.2)

    async def _connect(self):
        """Open TCP connection."""
        logger.debug("Connecting to %s:%s", self.host, self.port)
        self._reader, self._writer = await asyncio.open_connection(self.host, self.port)
        self._connected = True

    async def _authenticate(self):
        """Authenticate using RCON auth packet."""
        resp = await self._send_packet(packet_type=self._TYPE_AUTH, payload=self.password, expect_response=True)
        # Many servers reply with an empty body on auth success but allow further commands; treat None as auth fail
        if resp is None:
            raise RuntimeError("RCON auth failed (no response)")
        self._authed = True

    async def _worker_loop(self, worker_id: int):
        """Worker that pulls commands from queue and executes them, with retries and rate limiting."""
        logger.info("RCON worker %d started", worker_id)
        while self._running:
            try:
                queued: _QueuedCommand = await self._queue.get()
            except asyncio.CancelledError:
                break

            if queued.future.done():
                self._queue.task_done()
                continue

            # wait for connection/auth
            wait_start = time.monotonic()
            while not (self._connected and self._authed) and (time.monotonic() - wait_start) < queued.timeout:
                await asyncio.sleep(0.05)

            if not (self._connected and self._authed):
                # connection not ready; retry later or fail
                if queued.retries_left > 0:
                    queued.retries_left -= 1
                    await asyncio.sleep(0.5)
                    await self._queue.put(queued)
                else:
                    queued.future.set_exception(RuntimeError("RCON not connected/authenticated"))
                self._queue.task_done()
                continue

            # respect rate limiter
            await self._consume_rate_token()

            # attempt send
            try:
                result = await self._execute_with_retries(queued)
                if not queued.future.done():
                    queued.future.set_result(result)
                # event callback
                if callable(self.on_response):
                    try:
                        self.on_response(queued.command, result)
                    except Exception:
                        logger.exception("on_response callback failed")
            except Exception as exc:
                if not queued.future.done():
                    queued.future.set_exception(exc)
                if callable(self.on_error):
                    try:
                        self.on_error(exc)
                    except Exception:
                        logger.exception("on_error callback failed")
            finally:
                self._queue.task_done()

    async def _execute_with_retries(self, queued: _QueuedCommand) -> str:
        """Try running queued command with retries (exponential)."""
        attempt = 0
        backoff = 0.2
        last_exc: Optional[Exception] = None
        while queued.retries_left >= 0:
            try:
                attempt += 1
                result = await asyncio.wait_for(self._send_packet(packet_type=self._TYPE_COMMAND, payload=queued.command, expect_response=True, assemble_timeout=self.response_assemble_timeout), timeout=queued.timeout)
                return result or ""
            except asyncio.TimeoutError as e:
                last_exc = e
                logger.warning("RCON command timeout (attempt %d) for '%s'", attempt, queued.command)
            except Exception as e:
                last_exc = e
                logger.warning("RCON command error (attempt %d) for '%s': %s", attempt, queued.command, e)
                # If connection dropped, break and let reconnection logic handle it
                if not self._connected:
                    # re-enqueue if we still have retries
                    pass

            # retry logic
            queued.retries_left -= 1
            if queued.retries_left < 0:
                break
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 4.0)
        raise last_exc or RuntimeError("RCON command failed after retries")

    # ----------------------
    # Rate limiter (token bucket)
    # ----------------------
    async def _consume_rate_token(self):
        """Consume one token; if none available, wait until refill."""
        while True:
            async with self._rate_lock:
                now = time.monotonic()
                # refill
                elapsed = now - self._last_rate_refill
                if elapsed >= self._rate_interval:
                    # refill fully (simple strategy)
                    self._rate_tokens = self._rate_capacity
                    self._last_rate_refill = now

                if self._rate_tokens > 0:
                    self._rate_tokens -= 1
                    return
            await asyncio.sleep(0.005)

    # ----------------------
    # Low-level packet send/receive
    # ----------------------
    async def _send_packet(self, packet_type: int, payload: str, *, expect_response: bool = True, assemble_timeout: float = 0.05) -> Optional[str]:
        """
        Send one RCON packet and optionally read & assemble response(s).
        - packet_type: RCON packet type (2 = exec, 3 = auth)
        - payload: command or password
        - expect_response: if True, attempt to read response
        - assemble_timeout: after first response fragment read, wait up to this time for additional fragments
        Returns response string or None.
        """
        async with self._send_lock:
            if not self._connected or self._writer is None or self._reader is None:
                raise RuntimeError("RCON not connected")

            # create packet: [size][id][type][payload][2xNULL]
            # request id: use monotonic timestamp truncated to int for uniqueness
            request_id = int(time.time() * 1000) & 0x7fffffff
            payload_bytes = payload.encode("utf-8")
            packet_len = 4 + 4 + len(payload_bytes) + 2  # id(4) + type(4) + payload + 2 nulls
            header = struct.pack("<i", packet_len)
            body = struct.pack("<ii", request_id, packet_type) + payload_bytes + b"\x00\x00"
            packet = header + body

            try:
                self._writer.write(packet)
                await self._writer.drain()
            except Exception as e:
                logger.exception("RCON write failed: %s", e)
                self._connected = False
                self._authed = False
                raise

            if not expect_response:
                return ""

            # read response(s)
            response_parts = []
            start = time.monotonic()
            # read at least one response packet (block until available or timeout)
            try:
                # read length header
                raw_len = await asyncio.wait_for(self._reader.readexactly(4), timeout=self.command_timeout)
            except Exception as e:
                logger.exception("RCON read header failed: %s", e)
                self._connected = False
                self._authed = False
                raise

            try:
                (resp_len,) = struct.unpack("<i", raw_len)
                # read the rest
                data = await asyncio.wait_for(self._reader.readexactly(resp_len), timeout=self.command_timeout)
                # parse
                rid, rtype = struct.unpack("<ii", data[:8])
                body = data[8:-2].decode("utf-8", errors="ignore")
                response_parts.append(body)
            except Exception as e:
                logger.exception("RCON read body failed: %s", e)
                self._connected = False
                self._authed = False
                raise

            # attempt to gather extra fragments that might arrive quickly (multi-packet)
            while True:
                try:
                    elapsed = time.monotonic() - start
                    remaining = max(0.0, assemble_timeout - elapsed)
                    if remaining <= 0:
                        break
                    # try to read next header without blocking long
                    raw_len = await asyncio.wait_for(self._reader.readexactly(4), timeout=remaining)
                    (resp_len,) = struct.unpack("<i", raw_len)
                    data = await asyncio.wait_for(self._reader.readexactly(resp_len), timeout=remaining)
                    rid, rtype = struct.unpack("<ii", data[:8])
                    body = data[8:-2].decode("utf-8", errors="ignore")
                    response_parts.append(body)
                    start = time.monotonic()  # reset assemble timeout after receiving piece
                except asyncio.TimeoutError:
                    # no more data within assemble timeout -> done
                    break
                except Exception:
                    # treat other errors as disconnect and stop assembling
                    logger.exception("Error while assembling multi-packet response")
                    break

            final = "".join(response_parts)
            return final

    # ----------------------
    # Convenience helpers (common commands)
    # ----------------------
    async def say(self, message: str) -> str:
        return await self.run(f"say {message}")

    async def broadcast(self, message: str) -> str:
        return await self.run(f"broadcast {message}")

    async def run_raw(self, raw_command: str) -> str:
        return await self.run(raw_command)

    # ----------------------
    # register callbacks
    # ----------------------
    def set_on_connect(self, cb: Callable[[], Any]):
        self.on_connect = cb

    def set_on_disconnect(self, cb: Callable[[], Any]):
        self.on_disconnect = cb

    def set_on_error(self, cb: Callable[[Exception], Any]):
        self.on_error = cb

    def set_on_response(self, cb: Callable[[str, str], Any]):
        self.on_response = cb


rcon = AdvancedAsyncRCON(
    host=os.getenv("MINECRAFT_RCON_HOST", "127.0.0.1"),
    port=int(os.getenv("MINECRAFT_RCON_PORT", 25575)),
    password=os.getenv("MINECRAFT_RCON_PASSWORD", "password"),
    reconnect_delay=2.0,
    max_retries=3,
    command_timeout=8.0,
    response_assemble_timeout=0.06,
    rate_limit_tokens=60,
    rate_limit_interval=1.0,
    worker_count=2,
)
