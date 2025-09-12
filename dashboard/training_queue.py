"""
Training Queue Management System
Tracks models currently using GPU resources for training
"""
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid


class TrainingStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TrainingJob:
    """Represents a single training job in the queue"""
    
    def __init__(self, model_id: str, model_type: str, sport: str, user_id: str, 
                 training_config: Dict[str, Any]):
        self.job_id = str(uuid.uuid4())
        self.model_id = model_id
        self.model_type = model_type
        self.sport = sport
        self.user_id = user_id
        self.training_config = training_config
        self.status = TrainingStatus.QUEUED
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.progress = 0
        self.current_epoch = 0
        self.total_epochs = training_config.get('epochs', 50)
        self.gpu_id = None
        self.logs = []
        self.error_message = None
        self.estimated_completion = None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for JSON serialization"""
        return {
            'job_id': self.job_id,
            'model_id': self.model_id,
            'model_type': self.model_type,
            'sport': self.sport,
            'user_id': self.user_id,
            'status': self.status.value,
            'progress': self.progress,
            'current_epoch': self.current_epoch,
            'total_epochs': self.total_epochs,
            'gpu_id': self.gpu_id,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'estimated_completion': self.estimated_completion.isoformat() if self.estimated_completion else None,
            'error_message': self.error_message,
            'training_config': self.training_config,
            'logs': self.logs[-10:]  # Last 10 log entries
        }


class GPUResource:
    """Represents a GPU resource"""
    
    def __init__(self, gpu_id: int, memory_gb: float = 8.0):
        self.gpu_id = gpu_id
        self.memory_gb = memory_gb
        self.available = True
        self.current_job_id = None
        self.memory_used_gb = 0.0
        self.utilization_percent = 0.0
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            'gpu_id': self.gpu_id,
            'memory_gb': self.memory_gb,
            'available': self.available,
            'current_job_id': self.current_job_id,
            'memory_used_gb': self.memory_used_gb,
            'utilization_percent': self.utilization_percent
        }


class TrainingQueueManager:
    """Manages the training queue and GPU resource allocation"""
    
    def __init__(self, num_gpus: int = 2):
        self.jobs: Dict[str, TrainingJob] = {}
        self.queue: List[str] = []  # Job IDs in queue order
        self.running_jobs: Dict[str, str] = {}  # job_id -> gpu_id mapping
        
        # Initialize GPU resources
        self.gpus: Dict[int, GPUResource] = {}
        for i in range(num_gpus):
            self.gpus[i] = GPUResource(i, memory_gb=8.0 if i == 0 else 6.0)
        
        self.max_concurrent_jobs = num_gpus
        self._running = True
        self._queue_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._queue_thread.start()
        
    def submit_job(self, model_id: str, model_type: str, sport: str, user_id: str,
                   training_config: Dict[str, Any]) -> str:
        """Submit a new training job to the queue"""
        job = TrainingJob(model_id, model_type, sport, user_id, training_config)
        
        self.jobs[job.job_id] = job
        self.queue.append(job.job_id)
        
        # Log job submission
        job.logs.append(f"Job submitted to queue at {datetime.now().strftime('%H:%M:%S')}")
        
        return job.job_id
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific job"""
        if job_id not in self.jobs:
            return None
        
        job = self.jobs[job_id]
        return job.to_dict()
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job"""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        
        if job.status == TrainingStatus.QUEUED:
            # Remove from queue
            if job_id in self.queue:
                self.queue.remove(job_id)
            job.status = TrainingStatus.CANCELLED
            job.logs.append(f"Job cancelled at {datetime.now().strftime('%H:%M:%S')}")
            return True
        elif job.status == TrainingStatus.RUNNING:
            # Cancel running job
            job.status = TrainingStatus.CANCELLED
            job.completed_at = datetime.now()
            job.logs.append(f"Job cancelled while running at {datetime.now().strftime('%H:%M:%S')}")
            
            # Free up GPU
            if job_id in self.running_jobs:
                gpu_id = self.running_jobs[job_id]
                self.gpus[int(gpu_id)].available = True
                self.gpus[int(gpu_id)].current_job_id = None
                self.gpus[int(gpu_id)].memory_used_gb = 0.0
                self.gpus[int(gpu_id)].utilization_percent = 0.0
                del self.running_jobs[job_id]
            
            return True
        
        return False
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get overall queue status"""
        queued_jobs = [self.jobs[job_id].to_dict() for job_id in self.queue 
                      if self.jobs[job_id].status == TrainingStatus.QUEUED]
        
        running_jobs = [self.jobs[job_id].to_dict() for job_id in self.running_jobs.keys()
                       if self.jobs[job_id].status == TrainingStatus.RUNNING]
        
        completed_jobs = [job.to_dict() for job in self.jobs.values() 
                         if job.status in [TrainingStatus.COMPLETED, TrainingStatus.FAILED, TrainingStatus.CANCELLED]]
        
        # Sort completed jobs by completion time (most recent first)
        completed_jobs.sort(key=lambda x: x['completed_at'] or x['created_at'], reverse=True)
        
        return {
            'queued_jobs': queued_jobs,
            'running_jobs': running_jobs,
            'completed_jobs': completed_jobs[:20],  # Last 20 completed jobs
            'gpu_resources': [gpu.to_dict() for gpu in self.gpus.values()],
            'queue_length': len(queued_jobs),
            'active_jobs': len(running_jobs),
            'total_gpus': len(self.gpus),
            'available_gpus': sum(1 for gpu in self.gpus.values() if gpu.available)
        }
    
    def _process_queue(self):
        """Background thread to process the training queue"""
        while self._running:
            try:
                # Check for available GPUs and queued jobs
                if self.queue and len(self.running_jobs) < self.max_concurrent_jobs:
                    # Find available GPU
                    available_gpu = None
                    for gpu in self.gpus.values():
                        if gpu.available:
                            available_gpu = gpu
                            break
                    
                    if available_gpu:
                        # Start next job in queue
                        job_id = self.queue.pop(0)
                        job = self.jobs[job_id]
                        
                        # Allocate GPU
                        available_gpu.available = False
                        available_gpu.current_job_id = job_id
                        
                        # Start job
                        job.status = TrainingStatus.RUNNING
                        job.started_at = datetime.now()
                        job.gpu_id = available_gpu.gpu_id
                        
                        # Estimate completion time
                        estimated_duration = job.total_epochs * 30  # 30 seconds per epoch estimate
                        job.estimated_completion = job.started_at + timedelta(seconds=estimated_duration)
                        
                        job.logs.append(f"Training started on GPU {available_gpu.gpu_id} at {job.started_at.strftime('%H:%M:%S')}")
                        
                        self.running_jobs[job_id] = str(available_gpu.gpu_id)
                        
                        # Start training simulation
                        training_thread = threading.Thread(
                            target=self._simulate_training, 
                            args=(job_id,), 
                            daemon=True
                        )
                        training_thread.start()
                
                # Update running job progress
                self._update_running_jobs()
                
                time.sleep(1)  # Check every second
                
            except Exception as e:
                print(f"Error in queue processing: {e}")
                time.sleep(5)
    
    def _simulate_training(self, job_id: str):
        """Simulate training process for demo purposes"""
        job = self.jobs[job_id]
        gpu = self.gpus[job.gpu_id]
        
        try:
            # Simulate training epochs
            for epoch in range(1, job.total_epochs + 1):
                if job.status == TrainingStatus.CANCELLED:
                    break
                
                job.current_epoch = epoch
                job.progress = int((epoch / job.total_epochs) * 100)
                
                # Simulate GPU usage
                gpu.memory_used_gb = min(gpu.memory_gb * 0.8, job.training_config.get('batch_size', 32) * 0.1)
                gpu.utilization_percent = min(95, 70 + (epoch % 10) * 2)
                
                # Add training logs
                if epoch % 10 == 0 or epoch == job.total_epochs:
                    loss = 1.0 - (epoch / job.total_epochs) * 0.6 + (0.1 * (1 - epoch / job.total_epochs))
                    accuracy = 0.5 + (epoch / job.total_epochs) * 0.3
                    job.logs.append(f"Epoch {epoch}/{job.total_epochs} - Loss: {loss:.4f}, Accuracy: {accuracy:.4f}")
                
                # Simulate epoch duration
                epoch_duration = 5 + (job.training_config.get('batch_size', 32) / 32) * 2
                time.sleep(epoch_duration)
            
            # Complete training
            if job.status != TrainingStatus.CANCELLED:
                job.status = TrainingStatus.COMPLETED
                job.progress = 100
                job.completed_at = datetime.now()
                job.logs.append(f"Training completed successfully at {job.completed_at.strftime('%H:%M:%S')}")
            
        except Exception as e:
            job.status = TrainingStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now()
            job.logs.append(f"Training failed: {str(e)}")
        
        finally:
            # Free up GPU
            gpu.available = True
            gpu.current_job_id = None
            gpu.memory_used_gb = 0.0
            gpu.utilization_percent = 0.0
            
            if job_id in self.running_jobs:
                del self.running_jobs[job_id]
    
    def _update_running_jobs(self):
        """Update progress for running jobs"""
        for job_id in list(self.running_jobs.keys()):
            job = self.jobs[job_id]
            if job.status == TrainingStatus.RUNNING and job.started_at:
                # Update estimated completion based on current progress
                elapsed = (datetime.now() - job.started_at).total_seconds()
                if job.progress > 0:
                    estimated_total = elapsed / (job.progress / 100)
                    job.estimated_completion = job.started_at + timedelta(seconds=estimated_total)
    
    def get_user_jobs(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all jobs for a specific user"""
        user_jobs = [job.to_dict() for job in self.jobs.values() if job.user_id == user_id]
        user_jobs.sort(key=lambda x: x['created_at'], reverse=True)
        return user_jobs
    
    def cleanup_old_jobs(self, days: int = 7):
        """Remove jobs older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        jobs_to_remove = [
            job_id for job_id, job in self.jobs.items()
            if job.status in [TrainingStatus.COMPLETED, TrainingStatus.FAILED, TrainingStatus.CANCELLED]
            and job.created_at < cutoff_date
        ]
        
        for job_id in jobs_to_remove:
            del self.jobs[job_id]
        
        return len(jobs_to_remove)


# Global training queue manager instance
training_queue = TrainingQueueManager(num_gpus=2)