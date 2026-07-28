"""
Checkpointing infrastructure using SQLite.

This module provides state persistence and recovery capabilities
using LangGraph's SqliteSaver for workflow checkpointing.
"""

import os
import sqlite3
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from pydantic import BaseModel

from .models import WorkflowState
from .config import get_config


class CheckpointMetadata(BaseModel):
    """Metadata for checkpoint tracking."""
    
    thread_id: str
    checkpoint_id: str
    created_at: datetime
    node_name: str
    workflow_status: str


class CheckpointManager:
    """
    Manages workflow checkpointing using SQLite.
    
    Provides functionality for:
    - State serialization and deserialization
    - Thread ID management for workflow isolation
    - Checkpoint cleanup on workflow completion
    - Checkpoint restoration for workflow resumption
    """
    
    def __init__(self, checkpoint_db_path: Optional[str] = None):
        """
        Initialize checkpoint manager.
        
        Args:
            checkpoint_db_path: Path to SQLite database file.
                              Defaults to config value if not provided.
        """
        config = get_config()
        
        if checkpoint_db_path is None:
            # Remove sqlite:/// prefix if present
            db_path = config.workflow_checkpoint_db.replace("sqlite:///", "")
            checkpoint_db_path = db_path
        
        self.checkpoint_db_path = checkpoint_db_path
        self._ensure_db_directory()
        self._saver: Optional[SqliteSaver] = None
    
    def _ensure_db_directory(self) -> None:
        """Ensure the directory for checkpoint database exists."""
        db_dir = os.path.dirname(self.checkpoint_db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
    
    def get_saver(self) -> SqliteSaver:
        """
        Get or create the SqliteSaver instance.
        
        Returns:
            SqliteSaver instance for checkpoint persistence
        """
        if self._saver is None:
            # SqliteSaver.from_conn_string returns the saver directly
            # Connection is managed internally
            conn = sqlite3.connect(self.checkpoint_db_path, check_same_thread=False)
            self._saver = SqliteSaver(conn)
        return self._saver
    
    def generate_thread_id(self, prefix: str = "workflow") -> str:
        """
        Generate a unique thread ID for workflow isolation.
        
        Args:
            prefix: Prefix for the thread ID
            
        Returns:
            Unique thread ID string
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"{prefix}_{timestamp}"
    
    def serialize_state(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Serialize workflow state for checkpoint storage.
        
        Args:
            state: WorkflowState to serialize
            
        Returns:
            Serialized state as dictionary
        """
        # Pydantic v2 uses model_dump instead of dict
        return state.model_dump(mode='json')
    
    def deserialize_state(self, state_data: Dict[str, Any]) -> WorkflowState:
        """
        Deserialize workflow state from checkpoint storage.
        
        Args:
            state_data: Serialized state dictionary
            
        Returns:
            Reconstructed WorkflowState instance
        """
        return WorkflowState(**state_data)
    
    def list_checkpoints(self, thread_id: Optional[str] = None) -> List[CheckpointMetadata]:
        """
        List all checkpoints, optionally filtered by thread ID.
        
        Args:
            thread_id: Optional thread ID to filter by
            
        Returns:
            List of checkpoint metadata
        """
        checkpoints = []
        
        try:
            # Connect to checkpoint database
            conn = sqlite3.connect(self.checkpoint_db_path)
            cursor = conn.cursor()
            
            # Query checkpoints table
            # LangGraph's SqliteSaver uses 'checkpoints' table
            if thread_id:
                cursor.execute(
                    """
                    SELECT thread_id, checkpoint_id, checkpoint
                    FROM checkpoints
                    WHERE thread_id = ?
                    ORDER BY checkpoint_id DESC
                    """,
                    (thread_id,)
                )
            else:
                cursor.execute(
                    """
                    SELECT thread_id, checkpoint_id, checkpoint
                    FROM checkpoints
                    ORDER BY checkpoint_id DESC
                    """
                )
            
            rows = cursor.fetchall()
            
            for row in rows:
                thread_id_val, checkpoint_id, checkpoint_data = row
                
                # Parse checkpoint data to extract metadata
                try:
                    # The checkpoint_data is typically a pickled or JSON blob
                    # For now, create minimal metadata
                    checkpoints.append(
                        CheckpointMetadata(
                            thread_id=thread_id_val,
                            checkpoint_id=checkpoint_id,
                            created_at=datetime.now(),  # Ideally extract from checkpoint
                            node_name="unknown",  # Would need to parse checkpoint
                            workflow_status="unknown"
                        )
                    )
                except Exception as e:
                    print(f"Warning: Could not parse checkpoint metadata: {e}")
            
            conn.close()
            
        except sqlite3.OperationalError as e:
            # Table might not exist yet
            print(f"Warning: Could not list checkpoints: {e}")
        
        return checkpoints
    
    def get_incomplete_workflows(self) -> List[str]:
        """
        Detect incomplete workflows that can be resumed.
        
        Returns:
            List of thread IDs for incomplete workflows
        """
        incomplete_threads = []
        
        try:
            conn = sqlite3.connect(self.checkpoint_db_path)
            cursor = conn.cursor()
            
            # Query for checkpoints
            cursor.execute(
                """
                SELECT DISTINCT thread_id
                FROM checkpoints
                """
            )
            
            rows = cursor.fetchall()
            
            for row in rows:
                thread_id = row[0]
                # In a real implementation, we would check the workflow_status
                # from the checkpoint data to determine if it's incomplete
                incomplete_threads.append(thread_id)
            
            conn.close()
            
        except sqlite3.OperationalError as e:
            print(f"Warning: Could not query incomplete workflows: {e}")
        
        return incomplete_threads
    
    def cleanup_checkpoint(self, thread_id: str) -> bool:
        """
        Clean up checkpoint data for a completed workflow.
        
        Args:
            thread_id: Thread ID of workflow to clean up
            
        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.checkpoint_db_path)
            cursor = conn.cursor()
            
            # Delete checkpoints for this thread
            try:
                cursor.execute(
                    "DELETE FROM checkpoints WHERE thread_id = ?",
                    (thread_id,)
                )
            except sqlite3.OperationalError:
                # Table might not exist yet - this is ok
                conn.close()
                return True
            
            # Also delete from writes table if it exists
            try:
                cursor.execute(
                    "DELETE FROM checkpoint_writes WHERE thread_id = ?",
                    (thread_id,)
                )
            except sqlite3.OperationalError:
                # Table might not exist
                pass
            
            conn.commit()
            conn.close()
            
            print(f"✅ Cleaned up checkpoints for thread: {thread_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error cleaning up checkpoint for {thread_id}: {e}")
            return False
    
    def cleanup_all_completed(self) -> int:
        """
        Clean up all completed workflow checkpoints.
        
        Returns:
            Number of workflows cleaned up
        """
        # In a real implementation, we would:
        # 1. Query all threads
        # 2. Load their final checkpoint
        # 3. Check if workflow_status == "complete"
        # 4. Delete those checkpoints
        
        # For now, this is a placeholder
        print("⚠️  cleanup_all_completed not fully implemented")
        return 0
    
    def get_checkpoint_stats(self) -> Dict[str, Any]:
        """
        Get statistics about checkpoint storage.
        
        Returns:
            Dictionary with checkpoint statistics
        """
        stats = {
            "checkpoint_count": 0,
            "thread_count": 0,
            "db_size_bytes": 0,
            "db_path": self.checkpoint_db_path
        }
        
        try:
            # Get database file size
            if os.path.exists(self.checkpoint_db_path):
                stats["db_size_bytes"] = os.path.getsize(self.checkpoint_db_path)
            
            # Get checkpoint counts
            conn = sqlite3.connect(self.checkpoint_db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM checkpoints")
            stats["checkpoint_count"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT thread_id) FROM checkpoints")
            stats["thread_count"] = cursor.fetchone()[0]
            
            conn.close()
            
        except Exception as e:
            print(f"Warning: Could not get checkpoint stats: {e}")
        
        return stats
    
    def verify_checkpoint_integrity(self, thread_id: str) -> bool:
        """
        Verify checkpoint data integrity for a thread.
        
        Args:
            thread_id: Thread ID to verify
            
        Returns:
            True if checkpoint data is valid, False otherwise
        """
        try:
            conn = sqlite3.connect(self.checkpoint_db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT checkpoint FROM checkpoints WHERE thread_id = ? ORDER BY checkpoint_id DESC LIMIT 1",
                (thread_id,)
            )
            
            row = cursor.fetchone()
            conn.close()
            
            if row is None:
                return False
            
            # Basic integrity check - ensure checkpoint data exists
            checkpoint_data = row[0]
            return checkpoint_data is not None and len(checkpoint_data) > 0
            
        except Exception as e:
            print(f"❌ Error verifying checkpoint integrity: {e}")
            return False


def create_checkpoint_manager(checkpoint_db_path: Optional[str] = None) -> CheckpointManager:
    """
    Factory function to create a CheckpointManager instance.
    
    Args:
        checkpoint_db_path: Optional path to checkpoint database
        
    Returns:
        Configured CheckpointManager instance
    """
    return CheckpointManager(checkpoint_db_path)
