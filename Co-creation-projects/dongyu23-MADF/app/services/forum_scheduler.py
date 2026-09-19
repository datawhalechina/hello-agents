import asyncio
import logging
import time
import traceback
import uuid
from datetime import datetime
from typing import Any, Optional
from app.db.session import db_manager
from app.crud import (
    get_forum, 
    get_forum_participants, 
    create_message, 
    get_forum_messages,
    update_forum,
    update_forum_participant,
    get_persona
)
from app.db.client import fetch_all
from app.schemas import MessageCreate
from app.agent.agent import ModeratorAgent, ParticipantAgent
from hello_agents import Message
from app.agent.memory import SharedMemory
from app.core.websockets import manager
# Removed SQLAlchemy models import as we use schemas/dicts
from app.core.time_utils import get_beijing_time, get_beijing_time_iso
from app.core.async_utils import async_generator_wrapper
from contextlib import contextmanager

logger = logging.getLogger(__name__)


def restore_framework_history(agent, persisted_messages, self_name=None):
    """Replay persisted forum messages into a HelloAgents conversation."""
    for persisted in persisted_messages:
        role = "assistant" if self_name and persisted.speaker_name == self_name else "user"
        agent.add_message(
            Message(
                content=f"[{persisted.speaker_name}] {persisted.content}",
                role=role,
            )
        )


def to_epoch_seconds(value) -> float:
    """Normalize LibSQL datetime representations for restart recovery."""
    if isinstance(value, datetime):
        return value.timestamp()
    if isinstance(value, (int, float)):
        # LibSQL persists Python datetimes as millisecond Unix timestamps.
        return float(value) / 1000 if abs(value) >= 100_000_000_000 else float(value)
    if isinstance(value, str):
        try:
            numeric_value = float(value)
        except ValueError:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        return numeric_value / 1000 if abs(numeric_value) >= 100_000_000_000 else numeric_value
    raise TypeError(f"Unsupported forum start_time type: {type(value).__name__}")


def forum_deadline_epoch(start_time, duration_minutes: int) -> float:
    """Return the authoritative forum deadline in epoch seconds."""
    return to_epoch_seconds(start_time) + int(duration_minutes or 30) * 60


class ForumScheduler:
    def __init__(self):
        self.running_tasks = {}
        self.child_tasks = {}
        self.user_message_queues = {} # forum_id -> asyncio.Queue

    def _spawn_forum_task(self, forum_id: int, coroutine):
        task = asyncio.create_task(coroutine)
        tasks = self.child_tasks.setdefault(forum_id, set())
        tasks.add(task)

        def finish(finished):
            tasks.discard(finished)
            if finished.cancelled():
                return
            try:
                finished.result()
            except Exception:
                logger.exception("Forum %s background task failed", forum_id)

        task.add_done_callback(finish)
        return task

    def _is_forum_running(self, forum_id: int) -> bool:
        with self._get_db() as db:
            forum = get_forum(db, forum_id)
            return bool(forum and forum.status == "running")

    async def recover_running_forums(self):
        with self._get_db() as db:
            forum_ids = [row.id for row in fetch_all(db.execute("SELECT id FROM forums WHERE status = ?", ["running"]))]
        for forum_id in forum_ids:
            await self.start_forum(forum_id, recovering=True)
        return forum_ids

    async def shutdown(self):
        """Cancel local tasks while preserving DB state for restart recovery."""
        main_tasks = list(self.running_tasks.values())
        child_tasks = [task for tasks in self.child_tasks.values() for task in tasks]
        for task in main_tasks + child_tasks:
            task.cancel()
        if main_tasks or child_tasks:
            await asyncio.gather(*main_tasks, *child_tasks, return_exceptions=True)
        self.running_tasks.clear()
        self.child_tasks.clear()

    async def push_user_message(self, forum_id: int, user_name: str, content: str):
        """External API calls this to inject user message"""
        if forum_id not in self.user_message_queues:
            self.user_message_queues[forum_id] = asyncio.Queue()
        
        await self.user_message_queues[forum_id].put({
            "speaker": user_name,
            "content": content,
            "timestamp": get_beijing_time_iso()
        })
        logger.info(f"User message queued for forum {forum_id}: {content[:20]}...")

    async def _process_user_messages(self, forum_id: int) -> bool:
        """
        Process all pending user messages: save to DB, broadcast, and return True if any were processed.
        """
        if forum_id not in self.user_message_queues:
            return False
            
        q = self.user_message_queues[forum_id]
        if q.empty():
            return False
            
        processed_any = False
        
        # Process all currently available messages
        while not q.empty():
            try:
                msg_data = q.get_nowait()
                processed_any = True
                
                # 1. Save to DB
                with self._get_db() as db:
                    msg = create_message(db, MessageCreate(
                        forum_id=forum_id,
                        persona_id=None, # User has no persona
                        moderator_id=None,
                        speaker_name=msg_data["speaker"],
                        content=msg_data["content"],
                        turn_count=0 
                    ))
                    
                # 2. Broadcast to frontend (so everyone sees it)
                await self._broadcast_message(
                    forum_id, 
                    msg_data["speaker"], 
                    msg_data["content"], 
                    msg_id=msg.id,
                    stream_id=str(uuid.uuid4())
                )
                
                await self._broadcast_system_log(forum_id, f"观众 [{msg_data['speaker']}] 发言: {msg_data['content']}", "info")
                
            except Exception as e:
                logger.error(f"Failed to process user message: {e}")
        
        return processed_any

    async def _close_for_unavailable_agents(self, forum_id: int):
        """End a forum when no participant can produce a usable thought."""
        with self._get_db() as db:
            if get_forum(db, forum_id):
                update_forum(db, forum_id, status="closed")
        await manager.broadcast(forum_id, {
            "type": "status_update",
            "status": "closed",
        })
        await self._broadcast_system_log(
            forum_id,
            "论坛已停止：当前没有可用的智能体响应，请检查模型配置后重新发起讨论。",
            "error",
        )

    async def start_forum(
        self,
        forum_id: int,
        ablation_flags: dict = None,
        recovering: bool = False,
    ):
        if forum_id in self.running_tasks:
            logger.warning(f"Forum {forum_id} is already running.")
            return

        task = asyncio.create_task(
            self._run_forum_loop(forum_id, ablation_flags, recovering=recovering)
        )
        self.running_tasks[forum_id] = task
        
        # Remove task from dict when done
        task.add_done_callback(lambda t: self.running_tasks.pop(forum_id, None))

    async def stop_forum(self, forum_id: int):
        # Close the persisted forum first. In-flight LLM threads cannot be
        # forcefully cancelled, so every late-result guard must observe the
        # closed state before local tasks are cancelled and drained.
        with self._get_db() as db:
            if get_forum(db, forum_id):
                update_forum(db, forum_id, status="closed")

        if forum_id in self.running_tasks:
            self.running_tasks[forum_id].cancel()
            try:
                await self.running_tasks[forum_id]
            except asyncio.CancelledError:
                pass
            logger.info(f"Forum {forum_id} stopped.")
        children = list(self.child_tasks.pop(forum_id, set()))
        for task in children:
            task.cancel()
        if children:
            await asyncio.gather(*children, return_exceptions=True)
        await manager.broadcast(forum_id, {
            "type": "status_update",
            "status": "closed",
        })

    @contextmanager
    def _get_db(self):
        """Helper to get a fresh DB connection and ensure it closes"""
        db = db_manager.get_connection()
        try:
            yield db
        finally:
            try:
                db.close()
            except:
                pass

    async def _broadcast_system_log(
        self,
        forum_id: int,
        message: str,
        level: str = "info",
        source: str = "System",
        db: Any = None,
        require_running: bool = False,
    ):
        """Broadcast system log to frontend for 'terminal-like' view and optionally persist"""
        if require_running and not self._is_forum_running(forum_id):
            return
        
        # 1. Broadcast immediately (async) so frontend gets it ASAP
        # This is the "Native" passing path - extremely fast via WebSocket
        timestamp = get_beijing_time_iso()
        
        try:
            await manager.broadcast(forum_id, {
                "type": "system_log",
                "data": {
                    "timestamp": timestamp,
                    "level": level,
                    "content": message,
                    "source": source
                }
            })
        except Exception as e:
            logger.error(f"Broadcast failed: {e}")

        # 2. Fire-and-forget persistence (Background Task)
        # Don't wait for Redis/DB write to complete before returning
        self._spawn_forum_task(
            forum_id,
            self._persist_log_bg(
                forum_id,
                message,
                level,
                source,
                timestamp,
                require_running=require_running,
            ),
        )

    async def _persist_log_bg(
        self,
        forum_id: int,
        message: str,
        level: str,
        source: str,
        timestamp: str,
        require_running: bool = False,
    ):
        """Background persistence logic decoupled from main flow"""
        from app.core.cache import cache_service

        if require_running and not self._is_forum_running(forum_id):
            return
        
        try:
            log_entry = {
                "forum_id": forum_id,
                "level": level,
                "source": source,
                "content": message,
                "timestamp": timestamp
            }
            # Push to Redis buffer
            if not cache_service.push_message("system_logs_buffer", log_entry):
                 # Fallback to direct DB write if Redis fails
                 raise Exception("Redis push failed")
                 
        except Exception as e:
            # Fallback to direct DB persistence in thread
            from app.crud.crud_system_log import create_system_log
            from app.schemas.system_log import SystemLogCreate
            
            def persist_log_sync():
                local_db = None
                try:
                    local_db = db_manager.get_connection()
                    create_system_log(local_db, SystemLogCreate(
                        forum_id=forum_id,
                        level=level,
                        source=source,
                        content=message,
                        timestamp=timestamp
                    ))
                except Exception as inner_e:
                    logger.error(f"Failed to persist system log (thread): {inner_e}")
                finally:
                    if local_db:
                        try:
                            local_db.close()
                        except:
                            pass

            persist_task = asyncio.create_task(asyncio.to_thread(persist_log_sync))
            try:
                await asyncio.shield(persist_task)
            except asyncio.CancelledError:
                # Cancelling asyncio.to_thread does not stop its worker thread.
                # Drain it so stop_forum cannot return while a late DB write is
                # still running in the executor.
                await persist_task
                raise

    async def _flush_logs_to_db(self):
        """Batch flush logs from Redis buffer to DB"""
        from app.core.cache import cache_service
        from app.crud.crud_system_log import create_system_log
        from app.schemas.system_log import SystemLogCreate
        import json

        # Use cache_service wrapper
        # Pop up to 100 logs
        try:
            # cache_service.pop_messages returns a list of dicts (already json loaded)
            logs = cache_service.pop_messages("system_logs_buffer", count=100)
        except Exception as e:
            logger.error(f"Redis pop failed: {e}")
            return

        if not logs:
            return

        # Batch insert to DB
        # Since we use sync DB client, we should do this in a thread
        def batch_insert():
            local_db = None
            try:
                local_db = db_manager.get_connection()
                
                with local_db.transaction() as tx:
                    for data in logs:
                        try:
                            # data is already a dict
                            log_obj = SystemLogCreate(
                                forum_id=data["forum_id"],
                                level=data["level"],
                                source=data["source"],
                                content=data["content"],
                                timestamp=data.get("timestamp") # Pass original timestamp!
                            )
                            create_system_log(tx, log_obj)
                        except Exception as inner_e:
                            logger.error(f"Failed to insert log item: {inner_e}")
                    
                    # FORCE COMMIT BATCH
                    if hasattr(tx, 'commit'):
                        tx.commit()
                    elif hasattr(local_db, 'commit'):
                        local_db.commit()
                        
            except Exception as e:
                logger.error(f"Batch log insert failed: {e}")
            finally:
                if local_db:
                    try:
                        local_db.close()
                    except:
                        pass

        await asyncio.to_thread(batch_insert)

    async def _mock_stream_generator(self, content: str):
        # Simulate streaming
        chunk_size = 5
        for i in range(0, len(content), chunk_size):
            yield content[i:i+chunk_size]
            await asyncio.sleep(0.05)

    async def _run_forum_loop(
        self,
        forum_id: int,
        ablation_flags: dict = None,
        recovering: bool = False,
    ):
        ablation_flags = ablation_flags or {}
        logger.info(f"Starting forum loop for {forum_id} with flags: {ablation_flags}")
        
        # NOTE: We DO NOT keep a long-lived DB connection here anymore to avoid locks.
        # We open/close DB connections for each operation or logical block.
        
        try:
            # Persist the start log
            await self._broadcast_system_log(forum_id, f"论坛主循环启动... (配置: {ablation_flags})")
            await self._flush_logs_to_db() # FLUSH 1
            
            # Initial setup
            with self._get_db() as db:
                forum = get_forum(db, forum_id)
                if not forum:
                    logger.error(f"Forum {forum_id} not found.")
                    return

                # ForumService persists the authoritative clock before scheduling.
                # Recovery and a normal start both consume it without rewriting it.
                if recovering:
                    persisted_start_time = forum.start_time
                    persisted_flags = getattr(forum, "ablation_flags", {}) or {}
                    if isinstance(persisted_flags, str):
                        import json
                        try:
                            persisted_flags = json.loads(persisted_flags)
                        except json.JSONDecodeError:
                            persisted_flags = {}
                    ablation_flags = persisted_flags if isinstance(persisted_flags, dict) else {}
                else:
                    persisted_start_time = forum.start_time
                if persisted_start_time is None:
                    raise ValueError(f"Running forum {forum_id} has no persisted start_time")
                
                # Initialize Agents
                participants_db = get_forum_participants(db, forum_id)
                persisted_messages = get_forum_messages(db, forum_id)
                
                moderator_db = forum.moderator
                
                # OPTIMIZATION: Cache participants/moderator info in memory to avoid repeated DB reads in loop
                # We already do this by creating `participants` list.
                # But we re-read forum status/messages every loop.
            
            # Setup Agents (in memory)
            participants = []
            n_participants = len(participants_db)
            
            for p_db in participants_db:
                persona = p_db.persona
                if not persona:
                    continue
                
                persona_dict = {
                    "name": persona.name,
                    "title": persona.title,
                    "bio": persona.bio,
                    "theories": persona.theories,
                    "stance": persona.stance,
                    "system_prompt": persona.system_prompt
                }
                
                agent = ParticipantAgent(
                    name=persona.name,
                    persona=persona_dict,
                    n_participants=n_participants,
                    theme=forum.topic,
                    ablation_flags=ablation_flags
                )

                # Rehydrate the framework conversation after process restart.
                # The scheduler still owns turn selection, while HelloAgents
                # receives the persisted transcript as explicit messages.
                restore_framework_history(agent, persisted_messages, self_name=agent.name)
                
                # Restore memory
                if not ablation_flags.get("no_private_memory"):
                    if hasattr(p_db, 'thoughts_history') and p_db.thoughts_history:
                        import json
                        history = []
                        if isinstance(p_db.thoughts_history, str):
                            try:
                                history = json.loads(p_db.thoughts_history)
                            except:
                                history = []
                        elif isinstance(p_db.thoughts_history, list):
                            history = p_db.thoughts_history
                            
                        for t in history:
                            agent.private_memory.add_thought(t)
                
                participants.append(agent)

            if moderator_db:
                moderator = ModeratorAgent(
                    theme=forum.topic, 
                    name=moderator_db.name, 
                    system_prompt=moderator_db.system_prompt
                )
                await self._broadcast_system_log(forum_id, f"主持人 [{moderator.name}] 已就位")
            else:
                moderator = ModeratorAgent(theme=forum.topic)
                await self._broadcast_system_log(forum_id, "系统默认主持人已就位")

            restore_framework_history(moderator, persisted_messages)
            
            # Speaker Queue for multi-speaker management
            speaker_queue = []
            # Track agents who have spoken in the current "batch" (until queue is cleared)
            batch_spoken_agents = set()
            
            if not recovering:
                await self._broadcast_system_message(forum_id, "论坛开始，主持人正在开场...")
                await self._broadcast_system_log(forum_id, "主持人正在进行开场白...")
                await self._flush_logs_to_db() # FLUSH 2

                await self._moderator_speak(
                    forum_id,
                    moderator,
                    "opening",
                    guests=participants,
                    ablation_flags=ablation_flags,
                )

                await self._broadcast_system_log(forum_id, "DEBUG: 主持人开场结束，进入主循环", "info")
                await self._flush_logs_to_db() # FLUSH 3
            else:
                await self._broadcast_system_log(forum_id, "论坛已从上次运行状态恢复")
            
            # Main Loop
            end_time = forum_deadline_epoch(persisted_start_time, forum.duration_minutes or 30)
            
            turn_count = 0
            fallback_speaker_idx = 0
            
            while True:
                # --- NEW: Process User (Audience) Messages FIRST ---
                # If there are user messages, clear the current agent queue and force a re-think
                has_user_msgs = await self._process_user_messages(forum_id)
                if has_user_msgs:
                    logger.info(f"Forum {forum_id}: User messages detected. Clearing queue and forcing re-think.")
                    speaker_queue.clear()
                    # We don't break, we just continue the loop which will rebuild context including user message
                
                # Reload forum status
                with self._get_db() as db:
                    forum = get_forum(db, forum_id)
                
                if not forum:
                    logger.error(f"Forum {forum_id} disappeared during loop.")
                    break
                    
                if forum.status != "running":
                    logger.info(f"Forum {forum_id} status changed to {forum.status}, stopping loop.")
                    break
                
                current_time = time.time()
                
                # 1. Check Time -> Closing
                if current_time >= end_time:
                    logger.info(f"Forum {forum_id} time up. Closing.")
                    
                    # Push "closed" status to frontend immediately BEFORE moderator starts speaking closing remarks
                    # This ensures UI updates (e.g. stops timer) right away.
                    await manager.broadcast(forum_id, {
                        "type": "status_update",
                        "status": "closed"
                    })
                    
                    # Also update DB early to prevent race conditions
                    with self._get_db() as db:
                        update_forum(db, forum_id, status="closed")
                        
                    await self._moderator_speak(forum_id, moderator, "closing", ablation_flags=ablation_flags)
                    break

                # 2. Reconstruct Context (Shared Memory)
                # We need messages.
                # OPTIMIZATION: Only fetch last N messages if memory grows too large.
                # But SharedMemory might need full history? 
                # Let's trust get_forum_messages to be fast enough or add limit.
                with self._get_db() as db:
                    messages = get_forum_messages(db, forum_id)
                
                # OPTIMIZATION: Move SharedMemory reconstruction to background or only append new?
                # For now, it's fast enough.
                shared_memory = SharedMemory(n_participants)
                if forum.summary_history:
                    summaries = forum.summary_history
                    if isinstance(summaries, str):
                        import json
                        try:
                            summaries = json.loads(summaries)
                        except:
                            summaries = []
                    
                    for s in summaries:
                        shared_memory.add_summary(s)
                        
                for m in messages:
                    shared_memory.add_message(m.speaker_name, m.content)
                
                # Sync private memories
                if not ablation_flags.get("no_private_memory"):
                    for agent in participants:
                        agent.private_memory.speech_history = []
                        my_msgs = [m for m in messages if m.speaker_name == agent.name]
                        for m in my_msgs:
                            agent.private_memory.add_speech(m.content)

                # 3. Check Summary
                # OPTIMIZATION: Check summary ASYNC? Or just skip if not needed.
                # Summary generation can take time (LLM call).
                # Move summary to background task? 
                # Yes, but "moderator speaks" is blocking the flow usually.
                # If we make it non-blocking, the agents might continue speaking while mod is summarizing.
                # That might be confusing. 
                # Let's keep it blocking for now but only trigger when strictly necessary.
                
                msg_count = len(messages)
                N_WINDOW = 20
                
                if not ablation_flags.get("no_summary"):
                    if msg_count > 0 and msg_count % N_WINDOW == 0:
                        last_msg = messages[-1]
                        if last_msg.speaker_name != moderator.name:
                             # Check if we already have a summary for this window? 
                             # (implied by turn count check)
                             
                            logger.info(f"Forum {forum_id} triggering summary (msg count {msg_count}).")
                            msgs_to_summarize = messages[-N_WINDOW:]
                            await self._moderator_speak(forum_id, moderator, "periodic_summary", messages=msgs_to_summarize, ablation_flags=ablation_flags)

                # 4. Select Speaker
                if ablation_flags.get("no_shared_memory"):
                    if messages:
                        last_m = messages[-1]
                        context_str = f"【最新发言】\n{last_m.speaker_name}: {last_m.content}"
                    else:
                        context_str = "(暂无发言)"
                else:
                    context_str = shared_memory.get_context_str()

                # --- NEW: Dynamic Narrative Injection ---
                # Check if the VERY LAST message is from a user (audience)
                # FIX: Ensure we don't treat the Moderator (who might have moderator_id=None if default) as a user
                if messages and messages[-1].speaker_name and not messages[-1].persona_id and not messages[-1].moderator_id:
                    last_msg = messages[-1]
                    # Double check it's not the moderator by name
                    if last_msg.speaker_name != moderator.name:
                        # Inject narrative description only for this turn
                        context_str += f"\n\n(此时，台下的观众 {last_msg.speaker_name} 大声说：“{last_msg.content}”)"

                # --- NEW: Check for user interruption right BEFORE thinking ---
                # If a user message arrived while we were summarizing or reconstructing context,
                # we should catch it now to include it in the think context.
                if await self._process_user_messages(forum_id):
                    # Loop back to reconstruct context with new message
                    logger.info("User message detected before thinking. Restarting loop.")
                    speaker_queue.clear()
                    continue

                speaker = None
                thoughts_map = {}
                
                # OPTIMIZATION: If we already have a queue, maybe we don't need everyone to think?
                # But current logic requires everyone to think to update their internal state or react.
                # However, to speed up, we can start the NEXT speaker's preparation earlier?
                # No, because context depends on the previous speaker's FULL message.
                
                # Broadcast thinking log - Use create_task to not block thinking
                self._spawn_forum_task(forum_id, self._broadcast_system_log(forum_id, "所有参与者正在思考中...", "info"))
                logger.info(f"Forum {forum_id}: Agents start thinking...")
                
                async def agent_think(ag):
                    try:
                        await self._broadcast_system_log(forum_id, f"嘉宾 [{ag.name}] 正在思考...", "thought")
                        
                        if ablation_flags.get("mock_llm"):
                            await asyncio.sleep(1)
                            # Simple mock thought
                            thought = {
                                "action": "apply_to_speak", 
                                "mind": f"Mock thought from {ag.name}. I should speak."
                            }
                        else:
                            thought = await asyncio.to_thread(ag.think, context_str)

                        if not self._is_forum_running(forum_id):
                            return ag, None
                        
                        if thought:
                            import json
                            display_thought = {
                                "decision": thought.get("action", "listen"),
                                "inner_monologue": thought.get("mind", "")
                            }
                            await self._broadcast_system_log(forum_id, json.dumps(display_thought, ensure_ascii=False), "thought", f"Agent:{ag.name}")
                            
                        return ag, thought
                    except Exception as e:
                        logger.error(f"Agent {ag.name} think failed: {e}")
                        await self._broadcast_system_log(
                            forum_id,
                            f"嘉宾 [{ag.name}] 思考失败，已跳过本轮。",
                            "error",
                        )
                        return ag, None

                # Execute thinking in parallel - NO DB LOCK HELD HERE
                # Prefetch next speaker logic? No, we don't know who speaks until they think.
                # Optimization: Don't wait for ALL to think if we just need ONE to speak?
                # But we need everyone to decide "action".
                # Current bottleneck: waiting for the SLOWEST thinker.
                # Optimization: Set a timeout? Or just let them be.
                # Let's keep full gather for fairness, but maybe optimize the gap after thinking.
                
                # OPTIMIZATION: Use asyncio.wait for first_completed if we have a queue?
                # No, we need to know if anyone ELSE wants to speak urgently.
                # But we can update the UI *as soon as* someone decides.
                
                # think_results = await asyncio.gather(*[agent_think(p) for p in participants])
                
                # --- NEW: Interruptible Thinking with Polling ---
                think_tasks = [self._spawn_forum_task(forum_id, agent_think(p)) for p in participants]
                think_results = []
                interrupted = False

                while think_tasks:
                    # Poll every 0.5s
                    done, pending = await asyncio.wait(think_tasks, timeout=0.5, return_when=asyncio.FIRST_COMPLETED)
                    think_tasks = list(pending)
                    for t in done:
                        try:
                            res = await t
                            if res: think_results.append(res)
                        except Exception as e:
                            logger.error(f"Think task failed: {e}")
                    
                    # Check for interruption
                    if await self._process_user_messages(forum_id):
                        logger.info(f"Forum {forum_id}: User message detected during thinking. Interrupting.")
                        for t in think_tasks:
                            t.cancel()
                        interrupted = True
                        break

                if interrupted:
                    speaker_queue.clear()
                    continue 

                # New Logic: Use asyncio.as_completed to process thoughts as they arrive?
                # But we need to collect ALL results to make a fair decision if multiple apply.
                # However, we can process the DB updates in parallel.
                
                # Reduce timeout risk
                # If someone thinks too long, should we skip?
                # For now, no.
                
                # think_results = await asyncio.gather(*[agent_think(p) for p in participants])
                    
                logger.info(f"Forum {forum_id}: Agents finished thinking.")
                
                # --- NEW: Check for user interruption right AFTER thinking ---
                # If a user message arrived while agents were thinking, their thoughts are now STALE.
                # We must discard them, save the user message, and restart the loop to re-think.
                if await self._process_user_messages(forum_id):
                    logger.info("User message detected after thinking. Discarding thoughts and restarting.")
                    speaker_queue.clear()
                    # Discard thoughts implicitly by continuing loop
                    continue

                valid_thoughts = [thought for _, thought in think_results if thought]
                if participants and not valid_thoughts:
                    logger.error(
                        "Forum %s has no usable participant thoughts; ending to avoid retry loops.",
                        forum_id,
                    )
                    await self._close_for_unavailable_agents(forum_id)
                    break

                # Process thoughts (need DB to save thoughts)
                # Optimization: Do this ASYNC or in background if possible?
                # We need to know who speaks to proceed.
                # But saving history can be done in parallel with speaking start?
                # No, we need consistency.
                # Let's optimize the DB access pattern.
                
                # We can prepare the next speaker IMMEDIATELY after deciding, 
                # while saving thoughts in background.
                
                speaker_candidates = []
                # Simple in-memory processing first
                for agent, thought in think_results:
                    if thought:
                        thoughts_map[agent] = thought
                        if thought.get('action') == 'apply_to_speak':
                             speaker_candidates.append(agent)

                # Update Queue (In-Memory)
                for agent in speaker_candidates:
                    if agent not in speaker_queue:
                         if agent not in batch_spoken_agents or not speaker_queue:
                             speaker_queue.append(agent)

                # Select Speaker (In-Memory)
                if speaker_queue:
                    # Enforce constraint: A speaker cannot speak twice in a row
                    # even if they are in the queue.
                    
                    last_speaker_name = None
                    if messages:
                        last_speaker_name = messages[-1].speaker_name
                    
                    candidate = speaker_queue[0]
                    
                    # If candidate is same as last speaker, try to find another one in queue
                    if last_speaker_name and candidate.name == last_speaker_name:
                        # Find first non-consecutive speaker
                        found_alt = False
                        for i in range(1, len(speaker_queue)):
                            alt = speaker_queue[i]
                            if alt.name != last_speaker_name:
                                # Swap and pop
                                speaker = speaker_queue.pop(i)
                                found_alt = True
                                break
                        
                        if not found_alt:
                            # If everyone in queue is the same person (unlikely) or queue has only 1 person who just spoke
                            # Then we MUST skip them to avoid monologue.
                            # Fallback to general pool logic below.
                            logger.info(f"Skipping queued speaker {candidate.name} to avoid consecutive speech.")
                            speaker = None # Force fallback
                            # Note: We do NOT pop them, they stay in queue for next turn?
                            # Or should we pop and discard? 
                            # Better to keep them for next turn if possible, but for now let's just not pick them.
                            # Actually, if we don't pop, they block the queue forever if logic loops.
                            # Let's move them to end of queue?
                            if len(speaker_queue) > 1:
                                # Rotate
                                speaker_queue.append(speaker_queue.pop(0))
                                # Try again next loop? No, we need a speaker NOW.
                                # If we rotated, the new [0] is different (handled by swap logic above usually).
                                # If we are here, it means we couldn't find anyone else in queue.
                                speaker = None
                            else:
                                # Queue has only this guy, and he just spoke.
                                # Ignore queue, try fallback.
                                pass
                    else:
                        speaker = speaker_queue.pop(0)

                    if speaker:
                        batch_spoken_agents.add(speaker)
                
                # If no speaker selected from queue (empty or skipped due to consecutive rule)
                if not speaker and participants:
                    remaining = [p for p in participants if p not in batch_spoken_agents]
                    
                    # Filter out last speaker from remaining to be safe
                    last_speaker_name = messages[-1].speaker_name if messages else None
                    valid_remaining = [p for p in remaining if p.name != last_speaker_name]
                    
                    if valid_remaining:
                        # 随机从valid_remaining中选择一个
                        import random
                        speaker = random.choice(valid_remaining)
                    else:
                        # Reset batch if everyone spoke or valid ones exhausted
                        batch_spoken_agents.clear()
                        
                        # Fallback round-robin
                        # Ensure fallback doesn't pick last speaker either
                        attempts = 0
                        valid_fallbacks = [p for p in participants if p.name != last_speaker_name]
                        if valid_fallbacks:
                             import random
                             speaker = random.choice(valid_fallbacks)
                        
                        # while attempts < len(participants):
                        #     candidate = participants[fallback_speaker_idx % len(participants)]
                        #     fallback_speaker_idx += 1
                        #     attempts += 1
                        #     if candidate.name != last_speaker_name:
                        #         speaker = candidate
                        #         break
                        
                        # If still None (e.g. only 1 participant total), then allow consecutive
                        if not speaker and participants:
                             speaker = participants[0]

                    if speaker:
                        batch_spoken_agents.add(speaker)
                
                # Fire and forget DB updates for thoughts (using create_task)
                # This removes the DB write latency from the critical path of "Next Speaker"
                async def save_thoughts_bg(results, f_id):
                    if not self._is_forum_running(f_id):
                        return
                    with self._get_db() as db:
                        # Re-fetch only if needed, or pass IDs.
                        # We need persona_id. We can cache it or fetch once.
                        parts = get_forum_participants(db, f_id)
                        p_map = {p.persona.name: p for p in parts}
                        
                        for ag, th in results:
                            if not th: continue
                            p_db = p_map.get(ag.name)
                            if p_db:
                                current = []
                                if p_db.thoughts_history:
                                    try:
                                        if isinstance(p_db.thoughts_history, str):
                                            current = json.loads(p_db.thoughts_history)
                                        elif isinstance(p_db.thoughts_history, list):
                                            current = p_db.thoughts_history
                                    except: pass
                                update_forum_participant(db, f_id, p_db.persona_id, thoughts_history=current + [th])
                
                if think_results:
                    self._spawn_forum_task(forum_id, save_thoughts_bg(think_results, forum_id))

                # --- Queue Logic Refinement ---
                # Broadcasting logs is fast (Redis/WS), keep it.
                queue_names = [a.name for a in speaker_queue]
                if queue_names:
                    # Optimized: Use background task for log persistence to avoid blocking
                    self._spawn_forum_task(forum_id, self._broadcast_system_log(forum_id, f"当前发言队列: {', '.join(queue_names)}", "info"))
                
                if speaker:
                    # Async log to not block speaking
                    self._spawn_forum_task(forum_id, self._broadcast_system_log(forum_id, f"下一位发言: [{speaker.name}]", "info"))
                    
                    thought = thoughts_map.get(speaker) or {}
                    
                    await self._agent_speak(forum_id, speaker, thought, context_str, ablation_flags=ablation_flags)
                
                turn_count += 1
                
                # Periodic WAL checkpoint
                if turn_count % 10 == 0:
                    with self._get_db() as db:
                        try:
                            if not db_manager.is_postgres and not db_manager.is_remote:
                                 db.execute("PRAGMA wal_checkpoint(PASSIVE)")
                        except Exception as e:
                            logger.warning(f"WAL checkpoint failed: {e}")
                
                # Flush system logs
                await self._flush_logs_to_db()

        except Exception as e:
            logger.error(f"Forum loop crashed: {e}")
            logger.error(traceback.format_exc())
            try:
                await self._broadcast_system_log(forum_id, "论坛异常终止，请查看服务端日志", "error")
            except:
                pass

    async def _moderator_speak(self, forum_id: int, moderator: ModeratorAgent, action: str, guests=None, messages=None, ablation_flags: dict = None):
        content = ""
        gen = None
        stream_id = str(uuid.uuid4())
        ablation_flags = ablation_flags or {}
        
        # Read data
        with self._get_db() as db:
            forum = get_forum(db, forum_id)
            moderator_id = forum.moderator_id
        
        # await self._broadcast_system_log(forum_id, f"主持人 [{moderator.name}] 正在构思...", "info")
        try:
            if ablation_flags.get("mock_llm"):
                await asyncio.sleep(1)
                gen = self._mock_stream_generator(f"Mock moderator speech for {action} on topic {forum.topic}...")
            elif action == "opening":
                # Fix: guest object in list is ParticipantAgent, it has .persona dict attribute if we stored it?
                # No, ParticipantAgent stores persona data in self.title, self.stance etc.
                # Let's check ParticipantAgent init.
                # It has self.title, self.stance.
                guest_list = [{"name": g.name, "title": g.title, "stance": g.stance} for g in guests]
                gen = await asyncio.to_thread(moderator.opening, guest_list)
            elif action == "closing":
                # Need summaries
                summaries = forum.summary_history or []
                if isinstance(summaries, str):
                    import json
                    try:
                        summaries = json.loads(summaries)
                    except:
                        summaries = []
                        
                gen = await asyncio.to_thread(moderator.closing, summaries)
            elif action == "periodic_summary":
                msgs_text = [{"speaker": m.speaker_name, "content": m.content} for m in messages[-20:]]
                gen = await asyncio.to_thread(moderator.periodic_summary, msgs_text)

            if gen:
                try:
                    # Async log
                    self._spawn_forum_task(
                        forum_id,
                        self._broadcast_system_log(
                            forum_id,
                            f"主持人 [{moderator.name}] 正在构思...",
                            "thought",
                            require_running=True,
                        ),
                    )
                    
                    first_token = True
                    async for chunk in async_generator_wrapper(gen):
                        if not self._is_forum_running(forum_id):
                            return
                        # --- NEW: Interruption Check ---
                        if await self._process_user_messages(forum_id):
                            logger.info(f"Moderator {moderator.name} interrupted by user.")
                            await self._broadcast_system_log(forum_id, f"主持人被观众打断", "warning")
                            break
                            
                        if first_token:
                            await self._broadcast_system_log(forum_id, f"主持人 [{moderator.name}] 开始发言...", "speech")
                            first_token = False

                        if chunk:
                            token = chunk
                            content += token
                            await self._broadcast_chunk(forum_id, moderator.name, token, None, moderator_id, stream_id)
                except Exception as e:
                     logger.error(f"Error consuming generator: {e}")
            else:
                logger.warning("Moderator speak returned None generator")
                
        except Exception as e:
            logger.error(f"Moderator speak failed: {e}")
            await self._broadcast_system_log(forum_id, f"主持人发言生成失败: {str(e)}", "error")
            return

        if content and (action == "closing" or self._is_forum_running(forum_id)):
            with self._get_db() as db:
                msg = create_message(db, MessageCreate(
                    forum_id=forum_id,
                    moderator_id=moderator_id,
                    speaker_name=moderator.name,
                    content=content,
                    turn_count=0 
                ))
                
                if action == "periodic_summary":
                    # Refresh forum
                    forum = get_forum(db, forum_id)
                    current = forum.summary_history or []
                    if isinstance(current, str):
                        import json
                        try:
                            current = json.loads(current)
                        except:
                            current = []
                    new_history = current + [content]
                    update_forum(db, forum_id, summary_history=new_history)

            await self._broadcast_message(forum_id, moderator.name, content, None, moderator_id, stream_id, msg.id)
            await self._broadcast_system_log(forum_id, content, "speech", moderator.name)

    async def _agent_speak(self, forum_id: int, agent: ParticipantAgent, thought: dict, context: str, ablation_flags: dict = None):
        content = ""
        stream_id = str(uuid.uuid4())
        ablation_flags = ablation_flags or {}
        
        with self._get_db() as db:
            participants = get_forum_participants(db, forum_id)
            p_db = next((p for p in participants if p.persona.name == agent.name), None)
            persona_id = p_db.persona_id if p_db else None

        # Optimization: No need to log "thinking" again if thought is already done.
        # But we might need to do the actual LLM call for speaking now.
        
        try:
            if ablation_flags.get("mock_llm"):
                await asyncio.sleep(1)
                gen = self._mock_stream_generator(f"Mock speech from {agent.name}. My thought was: {thought.get('mind')}")
            else:
                gen = await asyncio.to_thread(agent.speak, thought, context)

            if not self._is_forum_running(forum_id):
                return
            
            if gen:
                try:
                    # await self._broadcast_system_log(forum_id, f"嘉宾 [{agent.name}] 正在构思...", "thought")
                    
                    first_token = True
                    start_speak_time = time.time()
                    thought_sent = False
                    thought_content = thought.get('mind') if thought else None
                    
                    async for chunk in async_generator_wrapper(gen):
                        if not self._is_forum_running(forum_id):
                            return
                        # --- NEW: Interruption Check ---
                        if await self._process_user_messages(forum_id):
                            logger.info(f"Agent {agent.name} interrupted by user.")
                            await self._broadcast_system_log(forum_id, f"嘉宾 [{agent.name}] 被观众打断", "warning")
                            break

                        if first_token:
                            ttft = time.time() - start_speak_time
                            logger.info(f"Agent {agent.name} TTFT: {ttft:.2f}s")
                            await self._broadcast_system_log(forum_id, f"嘉宾 [{agent.name}] 开始发言...", "speech")
                            first_token = False
                            
                        if chunk:
                            token = chunk
                            content += token
                            
                            send_thought = None
                            if not thought_sent and thought_content:
                                send_thought = thought_content
                                thought_sent = True
                                
                            await self._broadcast_chunk(forum_id, agent.name, token, persona_id, None, stream_id, thought=send_thought)
                except Exception as e:
                    logger.error(f"Error consuming agent generator: {e}")
                    await self._broadcast_system_log(forum_id, f"嘉宾 [{agent.name}] 发言中断，请查看服务端日志", "error")
            else:
                logger.warning(f"Agent {agent.name} speak returned None")
                content = "(沉默)"
                await self._broadcast_system_log(forum_id, f"嘉宾 [{agent.name}] 放弃发言 (API无响应或返回空)", "warning")
        except Exception as e:
            logger.error(f"Agent {agent.name} speak failed: {e}")
            await self._broadcast_system_log(forum_id, f"嘉宾 [{agent.name}] 发言生成失败，请查看服务端日志", "error")
            return

        if content and self._is_forum_running(forum_id):
            thought_content = None
            if thought:
                thought_content = thought.get('mind')
                
            with self._get_db() as db:
                msg = create_message(db, MessageCreate(
                    forum_id=forum_id,
                    persona_id=persona_id,
                    speaker_name=agent.name,
                    content=content,
                    thought=thought_content,
                    turn_count=0
                ))
            
            await self._broadcast_message(forum_id, agent.name, content, persona_id, None, stream_id, msg.id, thought=thought_content)
            await self._broadcast_system_log(forum_id, content, "speech", agent.name)

    async def _broadcast_chunk(self, forum_id: int, speaker: str, chunk: str, persona_id: int = None, moderator_id: int = None, stream_id: str = None, thought: str = None):
        if not chunk:
            return
            
        data = {
            "speaker_name": speaker,
            "content": chunk,
            "persona_id": persona_id,
            "moderator_id": moderator_id,
            "stream_id": stream_id,
            "timestamp": get_beijing_time_iso()
        }
        
        if thought:
            data["thought"] = thought
            
        await manager.broadcast(forum_id, {
            "type": "message_chunk",
            "data": data
        })

    async def _broadcast_message(self, forum_id: int, speaker: str, content: str, persona_id: int = None, moderator_id: int = None, stream_id: str = None, msg_id: int = None, thought: str = None):
        """Broadcast message immediately to WS"""
        # Optimized: Send to WS immediately, do NOT wait for any DB operations or complex logic
        timestamp = get_beijing_time_iso()
        
        try:
            await manager.broadcast(forum_id, {
                "type": "new_message",
                "data": {
                    "id": msg_id, # Can be None if optimized to send before DB insert (frontend should handle temp ID)
                    "forum_id": forum_id,
                    "speaker_name": speaker,
                    "content": content,
                    "persona_id": persona_id,
                    "moderator_id": moderator_id,
                    "stream_id": stream_id,
                    "thought": thought,
                    "timestamp": timestamp
                }
            })
        except Exception as e:
            logger.error(f"Message broadcast failed: {e}")

    async def _broadcast_system_message(self, forum_id: int, content: str):
        await manager.broadcast(forum_id, {
            "type": "system",
            "content": content
        })

scheduler = ForumScheduler()
