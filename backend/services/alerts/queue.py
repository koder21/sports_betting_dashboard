"""Alert queue for async, non-blocking alert creation"""
import asyncio
from datetime import datetime
from typing import Optional, Callable
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import OperationalError

from ...models.alert import Alert
from ...repositories.alert_repo import AlertRepository


@dataclass
class AlertTask:
    """Represents an alert to be created"""
    severity: str
    category: str
    message: str
    metadata: str = ""


class AlertQueue:
    """Queue alerts and process them asynchronously without blocking scheduler"""
    
    def __init__(self, session: Optional[AsyncSession] = None, session_factory: Optional[Callable[[], AsyncSession]] = None):
        self.session = session
        self.session_factory = session_factory
        self.repo = AlertRepository(session) if session else None
        self.queue: asyncio.Queue = asyncio.Queue()
        self.worker_task: Optional[asyncio.Task] = None
    
    def enqueue(self, severity: str, category: str, message: str, metadata: str = "") -> None:
        """Add alert to queue (non-blocking)"""
        try:
            self.queue.put_nowait(AlertTask(severity, category, message, metadata))
        except asyncio.QueueFull:
            # Queue is full, drop the alert (shouldn't happen with unlimited queue)
            print(f"Alert queue full, dropping: {message}")
    
    async def start_worker(self) -> None:
        """Start the background worker that processes the queue"""
        if self.worker_task is None or self.worker_task.done():
            self.worker_task = asyncio.create_task(self._process_queue())
    
    async def _process_queue(self) -> None:
        """Process alerts from queue with retry logic"""
        while True:
            try:
                # Wait for alert with 1 second timeout
                task = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                
                # Try to create alert with retries
                await self._create_with_retry(task)
                
            except asyncio.TimeoutError:
                # No alerts in queue, continue waiting
                continue
            except Exception as e:
                print(f"Alert queue worker error: {e}")
                await asyncio.sleep(1)
    
    async def _create_with_retry(self, task: AlertTask, max_retries: int = 5) -> None:
        """Create alert with exponential backoff retry logic"""
        retry_delay = 0.25  # Start with 250ms
        
        for attempt in range(max_retries):
            session = None
            try:
                if self.session_factory:
                    async with self.session_factory() as session:
                        repo = AlertRepository(session)
                        await self._create_alert_with_session(session, repo, task)
                else:
                    session = self.session
                    await self._create_alert_with_session(session, self.repo, task)
                
                # Log success if retries happened
                if attempt > 0:
                    print(f"Alert created successfully after {attempt + 1} attempts: {task.message}")
                
                return  # Success
                
            except OperationalError as e:
                if session:
                    await session.rollback()
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    print(f"Database locked (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay:.2f}s...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    print(f"Failed to create alert after {attempt + 1} attempts: {task.message} - {e}")
                    return  # Give up without raising
                    
            except Exception as e:
                if session:
                    await session.rollback()
                print(f"Error creating alert: {task.message} - {e}")
                return  # Give up without raising

    async def _create_alert_with_session(self, session: AsyncSession, repo: AlertRepository, task: AlertTask) -> None:
        # Check for duplicate alerts to prevent double-creation
        # For game_live alerts, check if one already exists for this game
        if task.category == "game_live" and task.metadata:
            import json
            try:
                meta_dict = json.loads(task.metadata)
                game_id = meta_dict.get("game_id")
                
                if game_id:
                    # Check if alert already exists for this game
                    from sqlalchemy import select, and_
                    stmt = select(Alert).where(
                        and_(
                            Alert.category == "game_live",
                            Alert.meta.like(f'%"game_id": "{game_id}"%'),
                            Alert.acknowledged == False
                        )
                    )
                    existing = await session.execute(stmt)
                    if existing.scalar():
                        # Alert already exists, skip creation
                        return
            except Exception:
                # If metadata parsing fails, continue with creation
                pass
        
        alert = Alert(
            created_at=datetime.utcnow(),
            severity=task.severity,
            category=task.category,
            message=task.message,
            meta=task.metadata,
            acknowledged=False,
        )
        
        await repo.add(alert)
        await session.commit()
    
    async def stop_worker(self) -> None:
        """Stop the background worker"""
        if self.worker_task and not self.worker_task.done():
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
