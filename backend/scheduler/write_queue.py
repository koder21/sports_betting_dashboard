"""Database write queue to prevent locking conflicts from concurrent writes"""
import asyncio
from typing import Callable, Any, Optional
from dataclasses import dataclass


@dataclass
class WriteTask:
    """Represents a database write operation"""
    name: str  # Task name for logging
    operation: Callable  # async callable that performs the write
    args: tuple = ()
    kwargs: dict = None
    
    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}


class DatabaseWriteQueue:
    """
    Serializes all database writes to prevent SQLite locking conflicts.
    Only one write operation runs at a time, preventing "database is locked" errors.
    """
    
    def __init__(self, max_queue_size: int = 100):
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self.worker_task: Optional[asyncio.Task] = None
    
    def enqueue(
        self, 
        name: str, 
        operation: Callable, 
        *args,
        **kwargs
    ) -> None:
        """Queue a database write operation (non-blocking)"""
        try:
            task = WriteTask(name, operation, args, kwargs)
            self.queue.put_nowait(task)
        except asyncio.QueueFull:
            print(f"Write queue full, dropping operation: {name}")
    
    async def start_worker(self) -> None:
        """Start the background worker that processes the write queue"""
        if self.worker_task is None or self.worker_task.done():
            self.worker_task = asyncio.create_task(self._process_queue())
            print("Database write queue worker started")
    
    async def _process_queue(self) -> None:
        """Process database writes from queue sequentially"""
        while True:
            try:
                # Wait for task with timeout
                task = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                
                try:
                    # Execute the write operation
                    if asyncio.iscoroutinefunction(task.operation):
                        result = await task.operation(*task.args, **task.kwargs)
                    else:
                        result = task.operation(*task.args, **task.kwargs)
                    
                    # Log successful completion (queued size for debugging)
                    queue_size = self.queue.qsize()
                    if queue_size > 0:
                        print(f"✓ {task.name} completed (queue: {queue_size} remaining)")
                    
                except Exception as e:
                    print(f"✗ {task.name} failed: {e}")
                    # Don't raise - continue processing queue
                    
            except asyncio.TimeoutError:
                # No tasks in queue, continue waiting
                continue
            except Exception as e:
                print(f"Write queue worker error: {e}")
                await asyncio.sleep(1)
    
    async def stop_worker(self) -> None:
        """Stop the background worker"""
        if self.worker_task and not self.worker_task.done():
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
            print("Database write queue worker stopped")
    
    async def wait_empty(self, timeout: float = 5.0) -> bool:
        """Wait for queue to empty (useful for shutdown)"""
        start = asyncio.get_event_loop().time()
        while not self.queue.empty():
            if asyncio.get_event_loop().time() - start > timeout:
                return False
            await asyncio.sleep(0.1)
        return True
